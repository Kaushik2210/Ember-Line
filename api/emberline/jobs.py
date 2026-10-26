"""Analysis jobs: run in the background, stream progress, cache results on disk.

A job id is a hash of the request and the code version, so asking for the same analysis twice
returns the same job (idempotent) and a finished result is served from disk, also after a restart.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from emberline import __version__
from emberline.data.cache import ParquetCache
from emberline.data.chunking import BBox, snap_bbox
from emberline.data.coverage import (
    containing_tile,
    load_availability,
    observed_dates,
    save_availability,
)
from emberline.data.firms import Availability, FirmsClient, FirmsError
from emberline.data.ingest import ingest_source, plan_missing
from emberline.data.store import HotspotStore
from emberline.guardrails import (
    GuardrailError,
    bbox_of,
    check_bbox,
    check_period,
    geometry_from_geojson,
)
from emberline.pipeline import REAL_SOURCES, AnalysisError, run_analysis
from emberline.regions import get_region
from emberline.schemas import AnalyzeRequest
from emberline.serialize import result_payload

log = logging.getLogger(__name__)
# A gap this small does not stop an analysis: missing days are reported as gaps, not as zeros.
TOLERATED_GAP = 0.05

CACHE_VERSION = "2"  # bump when the result format or science changes, to invalidate cached results


def request_key(req: AnalyzeRequest) -> str:
    blob = json.dumps(
        {"v": f"{__version__}/{CACHE_VERSION}", "req": req.model_dump(mode="json")},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:20]


@dataclass
class Job:
    id: str
    status: str = "queued"
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created: float = field(default_factory=time.time)
    cached: bool = False
    _changed: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)

    @property
    def stage(self) -> str | None:
        return self.events[-1]["stage"] if self.events else None

    async def emit(self, stage: str, **extra: Any) -> None:
        async with self._changed:
            self.events.append({"stage": stage, "status": self.status, **extra})
            self._changed.notify_all()

    async def finish(self, status: str, error: str | None = None) -> None:
        async with self._changed:
            self.status, self.error = status, error
            self.events.append(
                {"stage": "done" if status == "done" else "error", "status": status, "error": error}
            )
            self._changed.notify_all()

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        """Yield every event, past and future, until the job ends."""
        i = 0
        while True:
            async with self._changed:
                while i >= len(self.events) and self.status in ("queued", "running"):
                    await self._changed.wait()
                batch = self.events[i:]
                i = len(self.events)
                ended = self.status in ("done", "error")
            for e in batch:
                yield e
            if ended and i >= len(self.events):
                return


class JobManager:
    def __init__(
        self,
        store: HotspotStore,
        results_dir: Path,
        max_kept: int = 200,
        firms_factory: Callable[[], FirmsClient] | None = None,
        max_fetch_requests: int = 300,
    ) -> None:
        self.store = store
        self._factory = firms_factory
        self._max_fetch = max_fetch_requests
        self.results_dir = Path(results_dir)
        self.jobs: dict[str, Job] = {}
        self._max_kept = max_kept
        self._tasks: set[asyncio.Task[None]] = set()
        self._sem = asyncio.Semaphore(2)  # analyses are CPU heavy: two at a time

    def _path(self, job_id: str) -> Path:
        return self.results_dir / f"{job_id}.json"

    def get(self, job_id: str) -> Job | None:
        job = self.jobs.get(job_id)
        if job is None and self._path(job_id).is_file():
            job = Job(job_id, status="done", cached=True)
            job.result = json.loads(self._path(job_id).read_text(encoding="utf-8"))
            job.events.append({"stage": "done", "status": "done", "error": None})
            self.jobs[job_id] = job
        return job

    def submit(self, req: AnalyzeRequest) -> Job:
        bbox, rings = resolve_area(req)
        check_bbox(bbox)
        check_period(req.start, req.end)
        key = request_key(req)
        existing = self.get(key)
        if existing is not None and existing.status != "error":
            existing.cached = existing.status == "done"
            return existing
        job = Job(key)
        self.jobs[key] = job
        self._trim()
        task = asyncio.create_task(self._run(job, req, bbox, rings))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    def _trim(self) -> None:
        if len(self.jobs) > self._max_kept:
            for k in sorted(self.jobs, key=lambda k: self.jobs[k].created)[
                : len(self.jobs) - self._max_kept
            ]:
                if self.jobs[k].status in ("done", "error"):
                    del self.jobs[k]

    async def _run(self, job: Job, req: AnalyzeRequest, bbox: Any, rings: Any) -> None:
        loop = asyncio.get_running_loop()

        def progress(stage: str) -> None:  # called from the worker thread
            asyncio.run_coroutine_threadsafe(job.emit(stage), loop)

        async with self._sem:
            job.status = "running"
            await job.emit("Starting analysis")
            try:
                if not req.synthetic:
                    await self._ensure_data(job, bbox, req)
                analysis = await asyncio.to_thread(
                    run_analysis,
                    self.store,
                    bbox,
                    req.start,
                    req.end,
                    req.quality_policy,
                    req.grid,
                    req.metric,
                    req.synthetic,
                    progress,
                    rings,
                    None if req.model == "auto" else req.model,
                )
                job.result = await asyncio.to_thread(result_payload, analysis)
                await asyncio.to_thread(self._save, job)
                await job.finish("done")
            except (AnalysisError, GuardrailError) as exc:
                await job.finish("error", str(exc))
            except Exception:  # unexpected: log everything, show nothing internal
                log.exception("analysis %s failed", job.id)
                await job.finish("error", "The analysis failed unexpectedly. Please try again.")

    async def _ensure_data(self, job: Job, bbox: Any, req: AnalyzeRequest) -> None:
        """Download what is missing for this region and period, within hard request limits.

        What is missing is judged from the days actually on disk, so a box inside a cached preset
        needs nothing. A new area is fetched on a half-degree-snapped box so nearby boxes share it."""
        root = self.store.root
        client = self._factory() if self._factory else None
        try:
            if client is not None:
                live = await client.availability()
                save_availability(root, live)
                avail = {k: (v.min_date, v.max_date) for k, v in live.items()}
            else:
                avail = load_availability(root)
            gaps: dict[str, float] = {}  # source -> fraction of the wanted days not downloaded
            for sources in REAL_SOURCES.values():
                for src in sources:
                    if src not in avail:
                        continue
                    lo, hi = max(req.start, avail[src][0]), min(req.end, avail[src][1])
                    need = {date.fromordinal(lo.toordinal() + i) for i in range((hi - lo).days + 1)}
                    missing = len(need - set(observed_dates(root, src, bbox, avail)))
                    if missing:
                        gaps[src] = missing / max(1, len(need))
            if not gaps:
                return
            tolerable = all(f <= TOLERATED_GAP for f in gaps.values())
            if client is None:
                if tolerable:
                    return  # the pipeline reports the gaps; nothing more can be done offline
                raise AnalysisError(
                    f"Data for {', '.join(gaps)} is not cached for this region and period, and live "
                    f"download is off (no FIRMS_MAP_KEY). Run scripts/prefetch.py or pick a preset region."
                )
            cache = ParquetCache(root)
            plans: dict[str, tuple[BBox, int]] = {}
            for s_ in gaps:
                # extend a cached tile that already holds this area; otherwise a new snapped tile
                target = containing_tile(root, s_, bbox) or snap_bbox(bbox)
                todo = plan_missing(
                    cache, s_, Availability(s_, *avail[s_]), target, req.start, req.end
                )[0]
                plans[s_] = (target, todo)
            total = sum(n for _, n in plans.values())
            if total > self._max_fetch:
                if tolerable:
                    return
                raise AnalysisError(
                    f"This area is not cached and fetching it needs {total} FIRMS requests (limit "
                    f"{self._max_fetch}). Choose a preset region or a shorter period."
                )
            loop = asyncio.get_running_loop()
            done = 0

            def on_wait(msg: str) -> None:
                loop.create_task(job.emit(msg))

            client.on_wait = on_wait

            def on_progress(msg: str) -> None:
                nonlocal done
                done += 1
                loop.create_task(job.emit(f"{msg} ({done}/{total})"))

            for src, (target, _n) in plans.items():
                await ingest_source(
                    client,
                    cache,
                    src,
                    Availability(src, *avail[src]),
                    target,
                    req.start,
                    req.end,
                    on_progress=on_progress,
                )
        except FirmsError as exc:
            raise AnalysisError(f"Could not download data from NASA FIRMS: {exc}") from exc
        finally:
            if client is not None:
                await client.aclose()

    def _save(self, job: Job) -> None:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._path(job.id).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.result, allow_nan=False), encoding="utf-8")
        tmp.replace(self._path(job.id))


def resolve_area(req: AnalyzeRequest) -> tuple[tuple[float, float, float, float], Any]:
    """(bbox, rings) for the request; rings is None unless a shape was uploaded."""
    if req.region_id is not None:
        return get_region(req.region_id).bbox, None
    if req.geojson is not None:
        rings = geometry_from_geojson(req.geojson)
        return bbox_of(rings), rings
    assert req.bbox is not None
    return req.bbox, None


ProgressFn = Callable[[str], None]
