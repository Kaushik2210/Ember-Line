"""On-disk parquet cache keyed by (source, tile, date chunk).

Layout (hive-style so DuckDB can prune partitions):
    <root>/raw/src=<SOURCE>/tile=<W_S_E_N>/chunk=<YYYY-MM-DD>.parquet
Empty chunks are stored as empty parquet files so they are not re-downloaded.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import polars as pl

from emberline.data.schema import COMMON_SCHEMA


class ParquetCache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    def path(
        self, source: str, tile_key: str, chunk_start: date, partial_days: int | None = None
    ) -> Path:
        """Path of a chunk file. `partial_days` marks an incomplete chunk (data still arriving):
        it gets its own filename, so `has()` never treats it as complete."""
        suffix = f"~{partial_days}d" if partial_days else ""
        return (
            self.raw_dir
            / f"src={source}"
            / f"tile={tile_key}"
            / f"chunk={chunk_start.isoformat()}{suffix}.parquet"
        )

    def has(self, source: str, tile_key: str, chunk_start: date) -> bool:
        return self.path(source, tile_key, chunk_start).is_file()

    def write(
        self,
        df: pl.DataFrame,
        source: str,
        tile_key: str,
        chunk_start: date,
        partial_days: int | None = None,
    ) -> Path:
        """Write atomically so an interrupted run never leaves a half-written file."""
        target = self.path(source, tile_key, chunk_start, partial_days)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".parquet.tmp")
        df.write_parquet(tmp, compression="zstd")
        os.replace(tmp, target)
        return target

    def read(self, source: str, tile_key: str, chunk_start: date) -> pl.DataFrame:
        p = self.path(source, tile_key, chunk_start)
        if not p.is_file():
            return pl.DataFrame(schema=COMMON_SCHEMA)
        return pl.read_parquet(p)
