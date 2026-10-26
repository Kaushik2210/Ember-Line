"""Common grid and per-cell, per-local-day metrics shared by both sensors.

Metrics per (cell, local day, sensor, day/night):
  det_count    raw detections. Shown only to demonstrate the sensor mismatch.
  active_1km   unique ~1 km footprints (0.01 degree) with at least one detection. VIIRS 375 m
               pixels that fall in the same footprint collapse to one, so this presence
               metric does not scale with pixel size.
  frp_sum_mw   summed fire radiative power, the most physically comparable quantity.
  cell_active  1 for every row present: the cell had at least one detection that day, so
               summing it over days gives cell-days active.
"""

from __future__ import annotations

from typing import Literal

import h3
import numpy as np
import polars as pl
from pydantic import BaseModel, Field, model_validator

FOOTPRINT_DEG = 0.01  # ~1 km


class GridSpec(BaseModel):
    kind: Literal["regular", "h3"] = "regular"
    size_deg: float = Field(default=0.25, gt=0)
    h3_res: int = Field(default=5, ge=4, le=6)

    @model_validator(mode="after")
    def _check(self) -> GridSpec:
        if self.kind == "regular" and self.size_deg < FOOTPRINT_DEG:
            raise ValueError("grid cells must not be smaller than a 1 km footprint")
        return self


def footprint_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Snap each detection to its ~1 km footprint (fx, fy)."""
    return df.with_columns(
        (pl.col("longitude") / FOOTPRINT_DEG).floor().cast(pl.Int64).alias("fx"),
        (pl.col("latitude") / FOOTPRINT_DEG).floor().cast(pl.Int64).alias("fy"),
    )


def _h3_for_footprints(fp: pl.DataFrame, res: int) -> pl.DataFrame:
    """H3 cell for each unique footprint centre. Done on unique footprints, not on every row."""
    u = fp.select("fx", "fy").unique()
    lat = (u["fy"].to_numpy() + 0.5) * FOOTPRINT_DEG
    lon = (u["fx"].to_numpy() + 0.5) * FOOTPRINT_DEG
    cells = np.array([h3.latlng_to_cell(a, b, res) for a, b in zip(lat, lon, strict=True)])
    return u.with_columns(pl.Series("cell", cells, dtype=pl.Utf8))


def assign_cells(df: pl.DataFrame, grid: GridSpec) -> pl.DataFrame:
    """Add fx, fy (footprint) and `cell` (string id on the chosen grid)."""
    out = footprint_columns(df)
    if out.height == 0:
        return out.with_columns(pl.lit(None, dtype=pl.Utf8).alias("cell"))
    if grid.kind == "regular":
        # cells are whole multiples of the grid size from the origin; footprint centre decides
        ix = ((pl.col("fx") + 0.5) * FOOTPRINT_DEG / grid.size_deg).floor().cast(pl.Int64)
        iy = ((pl.col("fy") + 0.5) * FOOTPRINT_DEG / grid.size_deg).floor().cast(pl.Int64)
        return out.with_columns(
            pl.format("{}:{}:{}", pl.lit(f"{grid.size_deg:g}"), ix, iy).alias("cell")
        )
    mapping = _h3_for_footprints(out, grid.h3_res)
    return out.join(mapping, on=["fx", "fy"], how="left")


def cell_days(
    df: pl.DataFrame, grid: GridSpec, by: tuple[str, ...] = ("sensor", "daynight")
) -> pl.DataFrame:
    """One row per (cell, local_date, *by) with the metrics described in the module docs."""
    cols = ["cell", "local_date", *by]
    if df.height == 0:
        return pl.DataFrame(
            schema={
                **{c: pl.Utf8 for c in cols},
                "local_date": pl.Date,
                "det_count": pl.UInt32,
                "active_1km": pl.UInt32,
                "frp_sum_mw": pl.Float64,
                "cell_active": pl.Int64,
            }
        )
    g = assign_cells(df, grid)
    return (
        g.group_by(cols)
        .agg(
            pl.len().alias("det_count"),
            pl.struct("fx", "fy").n_unique().alias("active_1km"),
            pl.col("frp").sum().alias("frp_sum_mw"),
        )
        .with_columns(pl.lit(1).alias("cell_active"))
        .sort(cols)
    )


def daily_series(cd: pl.DataFrame, by: tuple[str, ...] = ("sensor", "daynight")) -> pl.DataFrame:
    """Region totals per local day from `cell_days` output."""
    return (
        cd.group_by("local_date", *by)
        .agg(
            pl.col("det_count").sum(),
            pl.col("active_1km").sum(),
            pl.col("frp_sum_mw").sum(),
            pl.col("cell_active").sum().alias("cells_active"),
        )
        .sort("local_date", *by)
    )
