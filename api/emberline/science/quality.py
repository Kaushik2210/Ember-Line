"""Quality policy: which detections count, plus a persistent-heat-source mask.

Defaults (all configurable, shown in the UI):
  * MODIS confidence >= 30 (numeric 0-100)
  * VIIRS confidence in {nominal, high}   (l = low is dropped)
  * type == 0 (presumed vegetation fire) where the column is present; rows with no type kept
  * persistent sources removed: footprint cells active on more than `persistent_min_frac`
    of all observed days (gas flares, industrial heat, volcanoes)
"""

from __future__ import annotations

from typing import Literal

import polars as pl
from pydantic import BaseModel, Field


class QualityPolicy(BaseModel):
    modis_min_conf: int = Field(default=30, ge=0, le=100)
    viirs_classes: tuple[str, ...] = ("n", "h")
    fire_types: tuple[int, ...] = (0,)
    keep_null_type: bool = True
    persistent_mask: bool = True
    persistent_min_frac: float = Field(default=0.10, gt=0, le=1)
    persistent_cell_deg: float = Field(default=0.02, gt=0)
    # a "fraction of days" is meaningless on a short window: skip the mask below this many days
    persistent_min_record_days: int = Field(default=365, ge=1)
    daynight: Literal["both", "D", "N"] = "both"


def _cell_expr(cell_deg: float) -> list[pl.Expr]:
    return [
        (pl.col("longitude") / cell_deg).floor().cast(pl.Int64).alias("cx"),
        (pl.col("latitude") / cell_deg).floor().cast(pl.Int64).alias("cy"),
    ]


def persistent_cells(
    df: pl.DataFrame,
    cell_deg: float = 0.02,
    min_frac: float = 0.10,
    min_record_days: int = 365,
) -> pl.DataFrame:
    """Cells (cx, cy) with detections on more than `min_frac` of the observed days.

    Needs at least `min_record_days` distinct days, otherwise returns no cells.
    The denominator is the number of distinct local dates with any detection in `df`, so the
    threshold means the same thing for a short or a long record.
    """
    if df.height == 0:
        return pl.DataFrame(schema={"cx": pl.Int64, "cy": pl.Int64})
    total_days = df["local_date"].n_unique()
    if total_days < min_record_days:
        # too short to tell a flare from a field that burned on a few consecutive days
        return pl.DataFrame(schema={"cx": pl.Int64, "cy": pl.Int64})
    return (
        df.with_columns(_cell_expr(cell_deg))
        .group_by("cx", "cy")
        .agg(pl.col("local_date").n_unique().alias("days"))
        .filter(pl.col("days") / total_days > min_frac)
        .select("cx", "cy")
    )


def apply_quality(
    df: pl.DataFrame, policy: QualityPolicy | None = None, mask: pl.DataFrame | None = None
) -> pl.DataFrame:
    """Filter detections by the policy. `mask` overrides the persistent mask computed from df."""
    policy = policy or QualityPolicy()
    if df.height == 0:
        return df
    conf_ok = (
        pl.when(pl.col("sensor") == "modis")
        .then(pl.col("conf_num") >= policy.modis_min_conf)
        .otherwise(pl.col("conf_class").is_in(list(policy.viirs_classes)))
    )
    type_ok = pl.col("fire_type").is_in(list(policy.fire_types))
    if policy.keep_null_type:
        type_ok = type_ok | pl.col("fire_type").is_null()
    out = df.filter(conf_ok.fill_null(False) & type_ok)
    if policy.daynight != "both":
        out = out.filter(pl.col("daynight") == policy.daynight)
    if policy.persistent_mask:
        if mask is None:
            mask = persistent_cells(
                df,
                policy.persistent_cell_deg,
                policy.persistent_min_frac,
                policy.persistent_min_record_days,
            )
        if mask.height:
            out = (
                out.with_columns(_cell_expr(policy.persistent_cell_deg))
                .join(mask, on=["cx", "cy"], how="anti")
                .drop("cx", "cy")
            )
    return out
