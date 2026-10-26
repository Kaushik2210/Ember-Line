"""HTTP routes. All heavy work happens in jobs; handlers only validate, look up and stream."""

from __future__ import annotations

import csv
import io
import json
import time
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sse_starlette.sse import EventSourceResponse

from emberline import __version__
from emberline.data.coverage import load_availability
from emberline.findings import findings
from emberline.guardrails import GuardrailError, check_bbox
from emberline.hotspots import hotspots_geojson
from emberline.jobs import JobManager, request_key
from emberline.regions import REGIONS
from emberline.schemas import AnalyzeRequest, JobStatus

router = APIRouter(prefix="/api")
RETRY_AFTER_S = 300.0  # how long a failed showcase analysis is remembered before trying again


def _jobs(request: Request) -> JobManager:
    return request.app.state.jobs  # type: ignore[no-any-return]


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "firms_key_configured": bool(request.app.state.settings.firms_map_key),
    }


@router.get("/availability")
def availability(request: Request) -> dict[str, Any]:
    """Per-source date ranges as last reported by FIRMS (saved by the prefetch script)."""
    avail = load_availability(request.app.state.settings.data_dir)
    return {
        "sources": {k: {"min": a.isoformat(), "max": b.isoformat()} for k, (a, b) in avail.items()},
        "note": "Ranges come from FIRMS at the time of the last prefetch."
        if avail
        else "No availability has been saved yet: run scripts/prefetch.py.",
    }


@router.get("/regions")
def regions() -> list[dict[str, Any]]:
    return [r.model_dump() for r in REGIONS]


@router.get("/showcase")
async def showcase(request: Request) -> list[dict[str, Any]]:
    """Headline findings per preset region, computed from each region's default analysis.

    Never downloads from FIRMS: a region whose data is not on disk is reported as unavailable, with
    the reason. A region still being computed is reported as computing, so callers can poll."""
    jobs = _jobs(request)
    cache: dict[str, dict[str, Any]] = request.app.state.findings
    out = []
    for r in REGIONS:
        entry: dict[str, Any] = {
            "id": r.id,
            "name": r.name,
            "bbox": r.bbox,
            "blurb": r.blurb,
            "start": r.default_start,
            "end": r.default_end,
            "state": "unavailable",
            "job_id": None,
            "findings": None,
            "reason": None,
        }
        req = AnalyzeRequest(
            region_id=r.id,
            start=date.fromisoformat(r.default_start),
            end=date.fromisoformat(r.default_end),
        )
        try:
            job = jobs.get(request_key(req))
            # a failed region is remembered for a few minutes; retrying on every poll would hide the
            # failure behind a permanent "computing" and redo the work
            if job is None or (job.status == "error" and time.time() - job.created > RETRY_AFTER_S):
                job = jobs.submit(req, allow_fetch=False)
        except GuardrailError as exc:
            entry["reason"] = str(exc)
            out.append(entry)
            continue
        entry["job_id"] = job.id
        if job.status == "done" and job.result is not None:
            if job.id not in cache:
                cache[job.id] = findings(job.result)
            entry["state"], entry["findings"] = "ready", cache[job.id]
        elif job.status == "error":
            entry["reason"] = job.error
        else:
            entry["state"] = "computing"
        out.append(entry)
    return out


@router.post("/analyze", status_code=202, response_model=JobStatus)
async def analyze(req: AnalyzeRequest, request: Request) -> JobStatus:
    try:
        job = _jobs(request).submit(req)
    except GuardrailError as exc:
        raise _bad_request(exc) from exc
    return JobStatus(job_id=job.id, status=job.status, stage=job.stage, cached=job.cached)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str, request: Request) -> JobStatus:
    job = _jobs(request).get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job. It may have expired: submit the analysis again.")
    return JobStatus(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        error=job.error,
        cached=job.cached,
    )


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request) -> EventSourceResponse:
    job = _jobs(request).get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job. It may have expired: submit the analysis again.")

    async def gen() -> AsyncIterator[dict[str, str]]:
        async for e in job.stream():
            if await request.is_disconnected():
                return
            yield {
                "event": "progress" if e["stage"] not in ("done", "error") else e["stage"],
                "data": json.dumps(e),
            }

    return EventSourceResponse(gen())


@router.get("/jobs/{job_id}/result")
def job_result(job_id: str, request: Request) -> Response:
    job = _jobs(request).get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job. It may have expired: submit the analysis again.")
    if job.status == "error":
        raise HTTPException(422, job.error or "The analysis failed.")
    if job.result is None:
        raise HTTPException(409, "The analysis is still running.")
    return Response(json.dumps(job.result, allow_nan=False), media_type="application/json")


@router.get("/hotspots")
def hotspots(
    request: Request,
    bbox: str = Query(description="west,south,east,north"),
    start: date = Query(),
    end: date | None = Query(default=None),
    sensors: str = Query(default="modis,viirs"),
    synthetic: bool = False,
    max_features: int = Query(default=50_000, ge=100, le=50_000),
) -> Response:
    try:
        w, s, e, n = (float(x) for x in bbox.split(","))
        box = check_bbox((w, s, e, n))
        fc = hotspots_geojson(
            request.app.state.store,
            box,
            start,
            end or start,
            tuple(x for x in sensors.split(",") if x in ("modis", "viirs")),
            synthetic,
            max_features,
        )
    except (ValueError, GuardrailError) as exc:
        raise _bad_request(exc) from exc
    return Response(json.dumps(fc), media_type="application/geo+json")


def _csv(result: dict[str, Any]) -> str:
    h, d = result.get("harmonized"), result["daily"]
    buf = io.StringIO()
    w = csv.writer(buf)
    if h is None:
        w.writerow(["date", "modis", "viirs"])
        w.writerows(zip(d["dates"], d["modis"], d["viirs"], strict=True))
        return buf.getvalue()
    raw = dict(zip(d["dates"], zip(d["modis"], d["viirs"], strict=True), strict=True))
    w.writerow(["date", "harmonized", "lo", "hi", "reconstructed", "modis_raw", "viirs_raw"])
    for i, day in enumerate(h["dates"]):
        m, v = raw.get(day, (None, None))
        w.writerow([day, h["value"][i], h["lo"][i], h["hi"][i], h["reconstructed"][i], m, v])
    return buf.getvalue()


def _geojson(result: dict[str, Any]) -> dict[str, Any]:
    w, s, e, n = result["bbox"]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
                },
                "properties": {
                    "synthetic": result["synthetic"],
                    "model": (result["validation"]["normalization"] or {}).get("chosen"),
                    "season_markers": (result["seasonality"] or {}).get("markers"),
                    "events": result["anomalies"]["events"],
                    "seasons": result["anomalies"]["seasons"],
                    "acknowledgment": result["meta"]["acknowledgment"],
                },
            }
        ],
    }


@router.get("/export")
def export(
    job_id: str, request: Request, format: str = Query(pattern="^(csv|geojson|methods)$")
) -> Response:
    job = _jobs(request).get(job_id)
    if job is None or job.result is None:
        raise HTTPException(404, "No finished analysis with that id.")
    r = job.result
    if format == "csv":
        return Response(
            _csv(r),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="emberline_{job_id}.csv"'},
        )
    if format == "geojson":
        return Response(
            json.dumps(_geojson(r)),
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="emberline_{job_id}.geojson"'},
        )
    return Response(
        json.dumps(r["meta"], indent=1),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="emberline_{job_id}_methods.json"'},
    )
