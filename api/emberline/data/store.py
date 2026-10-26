"""DuckDB access to the parquet cache.

Real FIRMS data (<root>/raw) and synthetic data (<root>/synthetic) are kept in separate
directories and are never mixed in one query: callers choose one with `synthetic=`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb
import polars as pl

from emberline.data.schema import COMMON_SCHEMA, empty_frame

BBox = tuple[float, float, float, float]
_COLS = ", ".join(COMMON_SCHEMA)


class HotspotStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _glob(self, synthetic: bool) -> str:
        sub = "synthetic" if synthetic else "raw"
        return (self.root / sub).as_posix() + "/**/*.parquet"

    def has_data(self, synthetic: bool = False) -> bool:
        sub = self.root / ("synthetic" if synthetic else "raw")
        return sub.is_dir() and any(sub.rglob("*.parquet"))

    def query(
        self,
        bbox: BBox,
        start: date,
        end: date,
        sources: Sequence[str] | None = None,
        synthetic: bool = False,
    ) -> pl.DataFrame:
        """Hotspots inside bbox with local_date in [start, end], de-duplicated across tiles."""
        if not self.has_data(synthetic):
            return empty_frame()
        w, s, e, n = bbox
        sql = f"""
            SELECT DISTINCT {_COLS}
            FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
            WHERE longitude BETWEEN ? AND ?
              AND latitude BETWEEN ? AND ?
              AND local_date BETWEEN ? AND ?
        """
        params: list[object] = [self._glob(synthetic), w, e, s, n, start, end]
        if sources:
            sql += f" AND source IN ({', '.join('?' * len(sources))})"
            params += list(sources)
        sql += " ORDER BY acq_utc, latitude, longitude"
        with duckdb.connect(":memory:") as con:
            out = pl.from_arrow(con.sql(sql, params=params).to_arrow_table())
        return out.cast(COMMON_SCHEMA)  # type: ignore[arg-type]

    def coverage(self, synthetic: bool = False) -> pl.DataFrame:
        """Per-source min/max local date and de-duplicated row count held on disk."""
        if not self.has_data(synthetic):
            return pl.DataFrame(
                schema={
                    "source": pl.Utf8,
                    "min_date": pl.Date,
                    "max_date": pl.Date,
                    "rows": pl.Int64,
                }
            )
        with duckdb.connect(":memory:") as con:
            return pl.from_arrow(
                con.sql(
                    f"""SELECT source, min(local_date) AS min_date, max(local_date) AS max_date,
                          count(*)::BIGINT AS rows
                   FROM (SELECT DISTINCT {_COLS}
                         FROM read_parquet(?, hive_partitioning = true, union_by_name = true))
                   GROUP BY source ORDER BY source""",
                    params=[self._glob(synthetic)],
                ).to_arrow_table()
            )
