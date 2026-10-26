"""Unusual periods: robust z-scores against leave-one-year-out day-of-year baselines.

For each year the baseline is built from every OTHER year, so an extreme season never
contaminates its own baseline. Scores are on log1p values, with a floor on the scale
(a fraction of the series' high positive values) so that a handful of detections in an
otherwise empty off-season do not produce enormous scores.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import polars as pl

from emberline.science.seasonality import DOY, _window_pool, doy_matrix, season_markers

MAD_TO_SIGMA = 1.4826


def loyo_zscores(
    daily: pl.DataFrame,
    value: str = "harmonized",
    half_window: int = 7,
    scale_floor_frac: float = 0.05,
) -> pl.DataFrame:
    """Per day: z (robust, log1p scale), baseline median (original units) and value.

    Needs at least 3 years. 29 February is skipped (it has no counterpart in other years).
    """
    mat, years = doy_matrix(daily, value)
    if len(years) < 3:
        raise ValueError("need at least 3 years for leave-one-year-out baselines")
    lm = np.log1p(mat)
    pos = lm[np.isfinite(lm) & (lm > 0)]
    floor = scale_floor_frac * (np.percentile(pos, 90) if pos.size else 1.0)
    z = np.full_like(lm, np.nan)
    base = np.full_like(lm, np.nan)
    for i in range(len(years)):
        pool = _window_pool(np.delete(lm, i, axis=0), half_window)
        with np.errstate(all="ignore"):
            med = np.nanmedian(pool, axis=0)
            mad = np.nanmedian(np.abs(pool - med), axis=0)
        scale = np.maximum(MAD_TO_SIGMA * mad, floor)
        z[i] = (lm[i] - med) / scale
        base[i] = np.expm1(med)
    rows = []
    for yi, y in enumerate(years):
        for k in range(DOY):
            if np.isfinite(z[yi, k]):
                rows.append(
                    (_date_of(y, k + 1), float(z[yi, k]), float(base[yi, k]), float(mat[yi, k]))
                )
    return pl.DataFrame(rows, schema=["local_date", "z", "baseline", value], orient="row").sort(
        "local_date"
    )


def _date_of(year: int, doy365: int) -> date:
    """Inverse of the 365-column calendar used by doy_matrix (29 Feb removed)."""
    d = date(year, 1, 1) + timedelta(days=doy365 - 1)
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    return d + timedelta(days=1) if leap and doy365 > 59 else d


@dataclass(frozen=True)
class Event:
    start: date
    end: date
    days: int
    direction: str  # "high" or "low"
    peak_z: float
    mean_z: float
    excess: float  # sum of (value - baseline) over the event, original units


def flag_events(
    scores: pl.DataFrame,
    value: str = "harmonized",
    threshold: float = 2.5,
    min_days: int = 3,
    max_gap: int = 1,
) -> list[Event]:
    """Sustained exceedances: |z| > threshold for at least `min_days` consecutive days of the same
    sign. Gaps of up to `max_gap` non-exceeding days inside a run are bridged."""
    if max_gap not in (0, 1):
        raise ValueError("max_gap must be 0 or 1")
    dates = scores["local_date"].to_list()
    z = scores["z"].to_numpy()
    val = scores[value].to_numpy()
    base = scores["baseline"].to_numpy()
    events: list[Event] = []
    for sign, name in ((1, "high"), (-1, "low")):
        hit = sign * z > threshold
        i, n = 0, len(z)
        while i < n:
            if not hit[i]:
                i += 1
                continue
            j = i
            last_hit = i
            while j + 1 < n:
                contiguous = (dates[j + 1] - dates[j]).days == 1
                if contiguous and hit[j + 1]:
                    j += 1
                    last_hit = j
                elif contiguous and j + 1 - last_hit <= max_gap and j + 2 < n and hit[j + 2]:
                    j += 1
                else:
                    break
            seg = slice(i, last_hit + 1)
            if last_hit - i + 1 >= min_days:
                zz = z[seg]
                events.append(
                    Event(
                        dates[i],
                        dates[last_hit],
                        (dates[last_hit] - dates[i]).days + 1,
                        name,
                        float(np.max(sign * zz) * sign),
                        float(zz.mean()),
                        float(np.nansum(val[seg] - base[seg])),
                    )
                )
            i = last_hit + 1
    return sorted(events, key=lambda e: e.start)


def season_totals(daily: pl.DataFrame, value: str = "harmonized") -> pl.DataFrame:
    """Total per fire year. The year is cut at the quietest day of the climatology, so a season
    that straddles New Year stays in one piece. Incomplete fire years are dropped."""
    mat, years = doy_matrix(daily, value)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN calendar days
        clim = np.nan_to_num(np.nanmedian(mat, axis=0))
    markers = season_markers(clim)
    if markers is None:
        return pl.DataFrame(schema={"season": pl.Utf8, "total": pl.Float64, "year0": pl.Int64})
    sm = np.convolve(np.concatenate([clim[-15:], clim, clim[:15]]), np.ones(31) / 31, mode="same")
    cut = int(np.argmin(sm[15:-15]))  # 0-based day of year where a fire year starts
    # A season is named by the calendar year its peak falls in. Only a season that itself
    # straddles New Year (10% start after 90% end in calendar terms, e.g. the austral summer)
    # is named like "2019-20".
    straddles = markers.start_doy > markers.end_doy
    peak_year_offset = 0 if markers.peak_doy > cut else 1
    rows = []
    for yi, y in enumerate(years):
        a = mat[yi, cut:]
        b = mat[yi + 1, :cut] if yi + 1 < len(years) else np.full(cut, np.nan)
        part = np.concatenate([a, b]) if cut > 0 else mat[yi]
        if np.isnan(part).any():
            continue
        label = f"{y}-{str(y + 1)[-2:]}" if straddles else str(y + peak_year_offset)
        rows.append((label, float(part.sum()), y))
    return pl.DataFrame(rows, schema=["season", "total", "year0"], orient="row")


def rank_seasons(totals: pl.DataFrame) -> pl.DataFrame:
    """Rank fire years by robust z of the log1p season total against all OTHER years."""
    n = totals.height
    if n < 4:
        raise ValueError("need at least 4 complete fire years to rank seasons")
    lt = np.log1p(totals["total"].to_numpy())
    z = np.empty(n)
    for i in range(n):
        o = np.delete(lt, i)
        med = np.median(o)
        sig = max(MAD_TO_SIGMA * np.median(np.abs(o - med)), 0.05 * max(np.ptp(lt), 1e-9), 1e-9)
        z[i] = (lt[i] - med) / sig
    out = totals.with_columns(pl.Series("z", z)).with_columns(
        pl.col("z").abs().rank("ordinal", descending=True).alias("rank")
    )
    return out.sort("rank")


def describe_event(e: Event, unit: str = "") -> str:
    kind = "above" if e.direction == "high" else "below"
    span = f"{e.start:%d %b %Y}" if e.days == 1 else f"{e.start:%d %b %Y} to {e.end:%d %b %Y}"
    return (
        f"{span} ({e.days} days): activity ran {abs(e.mean_z):.1f} robust standard deviations "
        f"{kind} the typical level for those dates (peak {abs(e.peak_z):.1f}). Baseline is built "
        f"from the other years only{(' (' + unit + ')') if unit else ''}."
    )


def describe_season(season: str, z: float, n_years: int) -> str:
    kind = "above" if z >= 0 else "below"
    return (
        f"{season} was {abs(z):.1f} robust standard deviations {kind} the median of the other "
        f"{n_years - 1} fire years."
    )
