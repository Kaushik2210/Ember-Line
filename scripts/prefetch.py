"""Download and cache FIRMS data for the demo regions so the live demo never waits on the API.

Resumable: chunks already on disk are skipped, so you can stop and restart at any time.
Use --dry-run first to see how many requests a run needs.

    uv run python ../scripts/prefetch.py --dry-run
    uv run python ../scripts/prefetch.py --regions punjab-haryana --start 2019-10-01 --end 2019-11-30
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date
from pathlib import Path

from emberline.config import get_settings
from emberline.data.cache import ParquetCache
from emberline.data.chunking import clip_chunk, date_chunks, tiles_for
from emberline.data.firms import Availability, FirmsClient
from emberline.data.ingest import ingest_source
from emberline.regions import REGIONS, get_region

DEFAULT_SOURCES = ["MODIS_SP", "VIIRS_SNPP_SP"]  # add VIIRS_NOAA20_SP via --sources if wanted
NRT_FOR = {
    "MODIS_SP": "MODIS_NRT",
    "VIIRS_SNPP_SP": "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_SP": "VIIRS_NOAA20_NRT",
}


def plan_requests(
    cache: ParquetCache, source: str, av: Availability, bbox, start, end, tile_deg=None
) -> tuple[int, int]:
    """(to_fetch, already_cached) for a source, mirroring ingest_source's logic."""
    todo = done = 0
    for tile in tiles_for(bbox, tile_deg):
        for chunk in date_chunks(start, end):
            if clip_chunk(chunk, av.min_date, av.max_date) is None:
                continue
            if cache.has(source, tile.key, chunk.start):
                done += 1
            else:
                todo += 1
    return todo, done


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    cache = ParquetCache(args.data_dir or settings.data_dir)
    regions = [get_region(r) for r in args.regions] if args.regions else REGIONS
    sources = list(args.sources)
    if args.nrt:
        sources += [NRT_FOR[s] for s in args.sources if s in NRT_FOR]

    async with FirmsClient(settings.firms_map_key) as client:
        avail = await client.availability()
        status = await client.key_status()
        print(f"FIRMS key status: {status}")
        for src in sources:
            if src in avail:
                a = avail[src]
                print(f"  {src}: {a.min_date} .. {a.max_date}")
        total_todo = 0
        for region in regions:
            start = args.start or date.fromisoformat(region.default_start)
            end = args.end or date.fromisoformat(region.default_end)
            for src in sources:
                if src not in avail:
                    print(f"[{region.id}] {src}: not offered by FIRMS, skipping")
                    continue
                todo, done = plan_requests(cache, src, avail[src], region.bbox, start, end, args.tile_deg)
                total_todo += todo
                print(f"[{region.id}] {src}: {todo} to fetch, {done} cached")
                if args.dry_run or todo == 0:
                    continue
                stats = await ingest_source(
                    client,
                    cache,
                    src,
                    avail[src],
                    region.bbox,
                    start,
                    end,
                    concurrency=args.concurrency,
                    tile_deg=args.tile_deg,
                    on_progress=(lambda m: print("   ", m)) if args.verbose else None,
                    max_requests=args.max_requests,
                )
                print(f"    fetched {stats.fetched} chunks, {stats.rows} rows")
        if args.dry_run:
            print(f"dry run: {total_todo} requests would be made, nothing downloaded")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--regions", nargs="*", choices=[r.id for r in REGIONS])
    ap.add_argument("--sources", nargs="*", default=DEFAULT_SOURCES)
    ap.add_argument("--nrt", action="store_true", help="also fetch near-real-time sources")
    ap.add_argument("--start", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--tile-deg", type=float, default=None, help="grid tiles instead of one bbox")
    ap.add_argument("--max-requests", type=int, default=None, help="cap per region+source")
    ap.add_argument("--data-dir", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
