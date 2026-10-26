"""Seasonality: day-of-year climatology, fire-season markers and STL decomposition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from statsmodels.tsa.seasonal import STL

DOY = 365


def doy_matrix(daily: pl.DataFrame, value: str = "harmonized") -> tuple[np.ndarray, list[int]]:
    """Years x 365 matrix of daily values (NaN where missing). 29 Feb is dropped, so every year
    has the same 365 calendar positions and a given column is the same date in all years."""
    d = daily.drop_nulls(value).with_columns(
        pl.col("local_date").dt.year().alias("year"),
        pl.col("local_date").dt.ordinal_day().alias("doy"),
        pl.col("local_date").dt.is_leap_year().alias("leap"),
        pl.col("local_date").dt.month().alias("month"),
        pl.col("local_date").dt.day().alias("day"),
    )
    d = d.filter(~((pl.col("month") == 2) & (pl.col("day") == 29)))
    d = d.with_columns(
        pl.when(pl.col("leap") & (pl.col("doy") > 59))
        .then(pl.col("doy") - 1)
        .otherwise(pl.col("doy"))
        .alias("doy")
    )
    years = sorted(d["year"].unique().to_list())
    mat = np.full((len(years), DOY), np.nan)
    idx = {y: i for i, y in enumerate(years)}
    for y, doy, v in zip(d["year"], d["doy"], d[value], strict=True):
        mat[idx[y], doy - 1] = v
    return mat, years


def _window_pool(mat: np.ndarray, half: int) -> np.ndarray:
    """For each calendar day, all values within +-half days (circular), across years: (n, 365)."""
    stacks = [np.roll(mat, s, axis=1) for s in range(-half, half + 1)]
    return np.concatenate(stacks, axis=0)


def climatology(
    mat: np.ndarray, half_window: int = 7, exclude_row: int | None = None
) -> pl.DataFrame:
    """Median, IQR and P10-P90 for each day of year, pooling +-half_window days across years.
    `exclude_row` leaves one year out (used for leave-one-year-out baselines)."""
    m = mat if exclude_row is None else np.delete(mat, exclude_row, axis=0)
    pool = _window_pool(m, half_window)
    with np.errstate(all="ignore"):
        q = np.nanpercentile(pool, [10, 25, 50, 75, 90], axis=0)
    return pl.DataFrame(
        {
            "doy": np.arange(1, DOY + 1),
            "p10": q[0],
            "p25": q[1],
            "median": q[2],
            "p75": q[3],
            "p90": q[4],
        }
    )


@dataclass(frozen=True)
class SeasonMarkers:
    start_doy: int
    peak_doy: int
    end_doy: int
    length_days: int
    total: float


def season_markers(
    profile: np.ndarray, pct: tuple[float, float, float] = (0.10, 0.50, 0.90)
) -> SeasonMarkers | None:
    """Fire season start / peak / end as the days where cumulative activity reaches 10/50/90%.

    The year is cut at the quietest day of the (lightly smoothed) profile, so a season that
    straddles 1 January is not split. `peak` is the 50% point (the activity-weighted median
    day), not the single busiest day. Returns None if there is no activity.
    """
    p = np.nan_to_num(np.asarray(profile, dtype=float), nan=0.0)
    if p.sum() <= 0:
        return None
    sm = np.convolve(np.concatenate([p[-15:], p, p[:15]]), np.ones(31) / 31, mode="same")[15:-15]
    cut = int(np.argmin(sm))
    rolled = np.roll(p, -cut)
    cum = np.cumsum(rolled) / rolled.sum()
    days = [int(np.searchsorted(cum, q)) for q in pct]
    to_doy = [((d + cut) % DOY) + 1 for d in days]
    return SeasonMarkers(to_doy[0], to_doy[1], to_doy[2], days[2] - days[0] + 1, float(p.sum()))


def stl_decompose(weekly: pl.DataFrame, value: str = "value", period: int = 52) -> pl.DataFrame:
    """STL (robust) on a weekly series: columns week, trend, seasonal, resid. Needs 2 periods."""
    s = weekly.drop_nulls(value).sort("week")
    if s.height < 2 * period:
        raise ValueError(f"need at least {2 * period} weeks for STL, have {s.height}")
    y = np.log1p(s[value].to_numpy().astype(float))
    res = STL(y, period=period, robust=True).fit()
    return pl.DataFrame(
        {"week": s["week"], "trend": res.trend, "seasonal": res.seasonal, "resid": res.resid}
    )
