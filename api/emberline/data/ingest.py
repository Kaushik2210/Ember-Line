"""Chunked, resumable download of FIRMS data into the parquet cache.

For each (tile, date chunk) the cache is checked first, so re-runs only fetch what is
missing. Requested ranges are clipped to what FIRMS reports as available for the source.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from emberline.data.cache import ParquetCache
from emberline.data.chunking import BBox, clip_chunk, date_chunks, tiles_for
from emberline.data.firms import Availability, FirmsClient
from emberline.data.schema import normalize_firms_csv

ProgressFn = Callable[[str], None]


@dataclass
class IngestStats:
    fetched: int = 0
    from_cache: int = 0
    unavailable: int = 0
    partial: int = 0
    rows: int = 0

    def merge(self, other: IngestStats) -> None:
        self.fetched += other.fetched
        self.from_cache += other.from_cache
        self.unavailable += other.unavailable
        self.partial += other.partial
        self.rows += other.rows


async def ingest_source(
    client: FirmsClient,
    cache: ParquetCache,
    source: str,
    avail: Availability,
    bbox: BBox,
    start: date,
    end: date,
    concurrency: int = 4,
    tile_deg: float = 10.0,
    on_progress: ProgressFn | None = None,
    max_requests: int | None = None,
) -> IngestStats:
    """Download everything missing for one source. Safe to re-run."""
    stats = IngestStats()
    sem = asyncio.Semaphore(concurrency)
    todo = []
    for tile in tiles_for(bbox, tile_deg):
        for chunk in date_chunks(start, end):
            clipped = clip_chunk(chunk, avail.min_date, avail.max_date)
            if clipped is None:
                stats.unavailable += 1
            elif cache.has(source, tile.key, chunk.start):
                stats.from_cache += 1
            else:
                todo.append((tile, chunk, clipped))
    if max_requests is not None:
        todo = todo[:max_requests]

    async def one(tile, chunk, clipped) -> None:  # type: ignore[no-untyped-def]
        async with sem:
            if on_progress:
                on_progress(f"Fetching {source} {clipped.start.isoformat()} tile {tile.key}")
            text = await client.area_csv(source, tile.bbox, clipped.start, clipped.days)
            df = normalize_firms_csv(text, source)
            # A chunk cut short at the newest available date will grow later: mark it partial.
            if clipped.end < chunk.end:
                cache.write(df, source, tile.key, chunk.start, partial_days=clipped.days)
                stats.partial += 1
            else:
                cache.write(df, source, tile.key, chunk.start)
            stats.fetched += 1
            stats.rows += df.height

    await asyncio.gather(*(one(*t) for t in todo))
    return stats


async def ingest(
    client: FirmsClient,
    cache: ParquetCache,
    sources: Sequence[str],
    bbox: BBox,
    start: date,
    end: date,
    **kw: object,
) -> dict[str, IngestStats]:
    avail = await client.availability()
    out: dict[str, IngestStats] = {}
    for src in sources:
        if src not in avail:
            continue
        out[src] = await ingest_source(client, cache, src, avail[src], bbox, start, end, **kw)  # type: ignore[arg-type]
    return out
