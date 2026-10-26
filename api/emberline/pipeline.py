"""End-to-end analysis of one region and period, from cached hotspots to harmonized outputs.

Stages (reported through `progress`): load, quality, grid, overpass matching, normalisation,
harmonisation, seasonality, anomalies. Every number in the result is computed from the loaded
data; notes about data quality are derived from it as well.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

import numpy as np
import polars as pl

from emberline.annotations import (
    AQUA_FIRE_START,
    Annotation,
    annotations_for,
    platform_coverage,
)
from emberline.data.coverage import load_availability, observed_dates
from emberline.data.store import HotspotStore
from emberline.guardrails import points_in_rings
from emberline.science.anomalies import (
    Event,
    flag_events,
    loyo_zscores,
    rank_seasons,
    season_totals,
)
from emberline.science.grid import GridSpec, cell_days, daily_series
from emberline.science.normalize import (
    NormalizationResult,
    fit_normalizer,
    harmonize,
    harmonize_with_early,
)
from emberline.science.overpass import combine_summaries, match_coincident
from emberline.science.quality import QualityPolicy, apply_quality, persistent_cells
from emberline.science.seasonality import (
    SeasonMarkers,
    climatology,
    doy_matrix,
    season_markers,
    season_segments,
    stl_decompose,
)
from emberline.science.series import calendar_series, weekly_pairs

log = logging.getLogger(__name__)
BBox = tuple[float, float, float, float]
Progress = Callable[[str], None]

REAL_SOURCES = {"modis": ["MODIS_SP"], "viirs": ["VIIRS_SNPP_SP"]}
SYNTHETIC_SOURCES = {"modis": ["SYNTHETIC_MODIS"], "viirs": ["SYNTHETIC_VIIRS"]}


class AnalysisError(RuntimeError):
    """A problem the user can act on (no data for the region, record too short, ...)."""


@dataclass
class Analysis:
    bbox: BBox
    start: date
    end: date
    policy: QualityPolicy
    grid: GridSpec
    metric: str
    synthetic: bool
    counts: dict[str, int]
    daily: pl.DataFrame  # local_date, modis, viirs (null = not observed)
    ds: pl.DataFrame  # region daily totals per sensor and day/night, all metrics
    observed: dict[str, list[date]] | None  # downloaded days per sensor (None: synthetic)
    norm: NormalizationResult | None = None
    norm_early: NormalizationResult | None = None  # Terra-only model for weeks before Aqua
    early_cutoff: date | None = None
    harmonized: pl.DataFrame | None = None
    climatology: pl.DataFrame | None = None
    markers: SeasonMarkers | None = None
    segments: list[SeasonMarkers] = field(default_factory=list)  # one per burning season
    scores: pl.DataFrame | None = None
    events: list[Event] = field(default_factory=list)
    seasons: pl.DataFrame | None = None
    overpass: dict[str, float] = field(default_factory=dict)
    frp_ratio: dict[str, float] = field(default_factory=dict)
    overpass_tables: dict[str, pl.DataFrame] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    platforms: pl.DataFrame = field(default_factory=pl.DataFrame)  # first/last day per platform
    annotations: list[Annotation] = field(default_factory=list)  # documented events
    stl: pl.DataFrame | None = None  # weekly trend / seasonal / residual (log1p scale)


def _merge_tables(tables: list[pl.DataFrame], key: str) -> pl.DataFrame:
    """Combine per-year rate tables, weighting each rate by its count."""
    tables = [t for t in tables if t.height]
    if not tables:
        return pl.DataFrame()
    cat = pl.concat(tables, how="diagonal")
    keys = [key, f"{key}_i"] if f"{key}_i" in cat.columns else [key]
    pairs = [
        (c, c.replace("n_", "") + "_corroborated")
        for c in cat.columns
        if c.startswith("n_") and c.replace("n_", "") + "_corroborated" in cat.columns
    ]
    aggs: list[pl.Expr] = []
    for n_col, r_col in pairs:
        w = pl.col(n_col).fill_null(0)
        aggs += [
            w.sum().alias(n_col),
            (pl.col(r_col).fill_null(0) * w)
            .sum()
            .truediv(pl.max_horizontal(w.sum(), pl.lit(1)))
            .alias(r_col),
        ]
    return cat.group_by(keys).agg(aggs).sort(keys[-1])


def _overpass_by_year(
    q: pl.DataFrame, progress: Progress
) -> tuple[dict[str, float], dict[str, float], dict[str, pl.DataFrame]]:
    modis = q.filter((pl.col("sensor") == "modis") & (pl.col("platform") == "Aqua"))
    viirs = q.filter(pl.col("platform") == "SNPP")
    if modis.height == 0 or viirs.height == 0:
        return {}, {}, {}
    years = sorted(
        set(modis["local_date"].dt.year().to_list()) & set(viirs["local_date"].dt.year().to_list())
    )
    sums, logs, frp_t, dn_t, scan_t = [], [], [], [], []
    for y in years:
        progress(f"Matching overpasses {y}")
        m = modis.filter(pl.col("local_date").dt.year() == y)
        v = viirs.filter(pl.col("local_date").dt.year() == y)
        r = match_coincident(m, v)
        if "n_modis_eval" not in r.summary:
            continue
        sums.append(r.summary)
        if r.pairs.height:
            logs.append(r.pairs["log10_ratio"].to_numpy())
        frp_t.append(r.by_frp)
        dn_t.append(r.by_daynight)
        scan_t.append(r.by_scan)
    if not sums:
        return {}, {}, {}
    ratio: dict[str, float] = {}
    if logs:
        lr = np.concatenate(logs)
        ratio = {
            "n_pairs": float(len(lr)),
            "median_viirs_over_modis": float(10 ** np.median(lr)),
            "p10": float(10 ** np.percentile(lr, 10)),
            "p90": float(10 ** np.percentile(lr, 90)),
        }
    tables = {
        "by_frp": _merge_tables(frp_t, "frp_bin"),
        "by_daynight": _merge_tables(dn_t, "daynight"),
        "by_scan": _merge_tables(scan_t, "scan_bin"),
    }
    return combine_summaries(sums), ratio, tables


def run_analysis(
    store: HotspotStore,
    bbox: BBox,
    start: date,
    end: date,
    policy: QualityPolicy | None = None,
    grid: GridSpec | None = None,
    metric: str = "frp_sum_mw",
    synthetic: bool = False,
    progress: Progress | None = None,
    rings: list[np.ndarray] | None = None,
    model: str | None = None,
) -> Analysis:
    policy = policy or QualityPolicy()
    grid = grid or GridSpec()
    say: Progress = progress or (lambda _m: None)
    sources = SYNTHETIC_SOURCES if synthetic else REAL_SOURCES
    flat = [s for v in sources.values() for s in v]

    say("Loading hotspots")
    df = store.query(bbox, start - timedelta(days=1), end, sources=flat, synthetic=synthetic)
    if df.height == 0:
        raise AnalysisError("No hotspot data is cached for this region and period.")
    if rings is not None:  # uploaded shape: keep only points inside it
        inside = points_in_rings(df["latitude"].to_numpy(), df["longitude"].to_numpy(), rings)
        df = df.filter(pl.Series(inside))
        if df.height == 0:
            raise AnalysisError("No hotspot data falls inside the uploaded shape.")
    for sensor in ("modis", "viirs"):
        if df.filter(pl.col("sensor") == sensor).height == 0:
            raise AnalysisError(f"No {sensor.upper()} data is cached for this region and period.")

    say("Applying quality policy")
    mask = persistent_cells(
        df,
        policy.persistent_cell_deg,
        policy.persistent_min_frac,
        policy.persistent_min_record_days,
    )
    q = apply_quality(df, policy, mask=mask)
    counts = {
        "raw": df.height,
        "kept": q.height,
        "persistent_cells": mask.height,
        "modis_kept": q.filter(pl.col("sensor") == "modis").height,
        "viirs_kept": q.filter(pl.col("sensor") == "viirs").height,
    }
    q = q.filter(pl.col("local_date").is_between(start, end))
    if q.height == 0:
        raise AnalysisError("No detections remain after the quality policy for this period.")

    say("Aggregating to the common grid")
    ds = daily_series(cell_days(q, grid))

    avail = load_availability(store.root)
    observed: dict[str, list[date]] | None = None
    if not synthetic:
        observed = {}
        for sensor, srcs in sources.items():
            days: set[date] = set()
            for s in srcs:
                days |= set(observed_dates(store.root, s, bbox, avail))
            observed[sensor] = sorted(d for d in days if start <= d <= end)
    daily = calendar_series(ds, metric, start, end, observed=observed)

    a = Analysis(bbox, start, end, policy, grid, metric, synthetic, counts, daily, ds, observed)
    a.notes += _data_notes(q, daily, counts, synthetic)
    a.platforms = platform_coverage(df)
    a.annotations = [] if synthetic else annotations_for(start, end)

    a.overpass, a.frp_ratio, a.overpass_tables = _overpass_by_year(q, say)

    say("Fitting normalisation models")
    pairs = weekly_pairs(daily)
    try:
        a.norm = fit_normalizer(pairs, metric=metric, force=model)
    except ValueError as exc:
        a.notes.append(f"Normalisation not fitted: {exc}.")
        return a

    cv = {r["model"]: r for r in a.norm.cv.iter_rows(named=True)}
    chosen, scale = cv[a.norm.chosen], cv["scale"]
    if chosen["mae_log"] >= 0.98 * scale["mae_log"]:
        a.notes.append(
            f"A single multiplicative factor (error {scale['mae_log']:.2f}) does about as well as "
            f"{a.norm.chosen} ({chosen['mae_log']:.2f}) here, so the extra model complexity is not "
            f"clearly justified for this region."
        )
    a.notes.append(
        f"Prediction intervals are about x{np.expm1(a.norm.q) + 1:.1f} wide on weekly totals at "
        f"{a.norm.level:.0%} nominal coverage: the sensors' weekly totals disagree by more than a "
        f"constant factor."
    )
    say("Harmonising the record")
    a.harmonized = _harmonize(a, q, observed, grid, metric, daily, start, end, say)
    rec = a.harmonized.filter(pl.col("reconstructed") & pl.col("harmonized").is_not_null())
    a.notes.append(
        f"{rec.height} of {a.harmonized.height} days are reconstructed from MODIS "
        f"(VIIRS-equivalent, with prediction bands); the rest are observed by VIIRS."
    )

    say("Seasonality and unusual periods")
    mat, years = doy_matrix(a.harmonized)
    if len(years) >= 3:
        a.climatology = climatology(mat)
        a.markers = season_markers(np.nanmedian(mat, axis=0))
        a.segments = season_segments(np.nanmedian(mat, axis=0))
        a.stl = _weekly_stl(a.harmonized)
        a.scores = loyo_zscores(a.harmonized)
        yearly_total = float(np.nansum(mat)) / len(years)
        a.events = flag_events(a.scores, min_excess=0.01 * yearly_total)  # >= 1% of a typical year
        if a.early_cutoff is not None:
            cutoff = a.early_cutoff
            a.events = [
                replace(
                    e,
                    caveat="Less reliable: this falls in the Terra-only years, when a single "
                    "morning overpass sampled each day.",
                )
                if e.start < cutoff
                else e
                for e in a.events
            ]
        try:
            a.seasons = rank_seasons(season_totals(a.harmonized))
        except ValueError as exc:
            a.notes.append(f"Seasons not ranked: {exc}.")
    else:
        a.notes.append("Fewer than 3 years: no climatology or anomaly baseline.")
    return a


def _data_notes(
    q: pl.DataFrame, daily: pl.DataFrame, counts: dict[str, int], synthetic: bool
) -> list[str]:
    notes: list[str] = []
    if synthetic:
        notes.append("SYNTHETIC DATA: generated for development, not real observations.")
    if counts["persistent_cells"]:
        notes.append(
            f"{counts['persistent_cells']} persistent heat-source cells (flares, industry, "
            f"volcanoes) were removed."
        )
    else:
        notes.append(
            "No persistent-source mask was applied (record shorter than a year, or none found)."
        )
    modis = q.filter(pl.col("sensor") == "modis")
    aqua = modis.filter(pl.col("platform") == "Aqua")["local_date"]
    terra = modis.filter(pl.col("platform") == "Terra")["local_date"]
    if aqua.len() and terra.len():
        first_aqua, first_terra = aqua.min(), terra.min()
        if (
            isinstance(first_aqua, date)
            and isinstance(first_terra, date)
            and (first_aqua - first_terra).days >= 30  # a real gap, not a quiet first day
        ):
            notes.append(
                f"MODIS reports from Terra alone before {first_aqua.isoformat()}, with fewer "
                f"overpasses; reconstructed values there are less certain."
            )
    for sensor in ("modis", "viirs"):
        col = daily[sensor]
        missing = int(col.is_null().sum())
        if 0 < missing < daily.height:
            first = daily.filter(pl.col(sensor).is_not_null())["local_date"].min()
            if isinstance(first, date):
                notes.append(
                    f"{sensor.upper()} is observed from {first.isoformat()}; "
                    f"{missing} days have no data."
                )
    return notes


def _weekly_stl(harmonized: pl.DataFrame) -> pl.DataFrame | None:
    """STL on weekly harmonised totals (complete weeks only); None if under two years."""
    w = (
        harmonized.with_columns(pl.col("local_date").dt.truncate("1w").alias("week"))
        .group_by("week")
        .agg(
            pl.col("harmonized").count().alias("n"),
            pl.col("harmonized").sum().alias("value"),
        )
        .filter(pl.col("n") == 7)
        .select("week", "value")
        .sort("week")
    )
    try:
        return stl_decompose(w)
    except ValueError:
        return None


def _harmonize(
    a: Analysis,
    q: pl.DataFrame,
    observed: dict[str, list[date]] | None,
    grid: GridSpec,
    metric: str,
    daily: pl.DataFrame,
    start: date,
    end: date,
    say: Progress,
) -> pl.DataFrame:
    """Harmonise the record; weeks before Aqua use a Terra-only model when the window reaches back."""
    assert a.norm is not None
    modis = q.filter(pl.col("sensor") == "modis")
    terra_only_era = (
        start < AQUA_FIRE_START and modis.filter(pl.col("platform") == "Terra").height > 0
    )
    if not terra_only_era:
        return harmonize(daily, a.norm)

    say("Calibrating the Terra-only years")
    terra = q.filter((pl.col("sensor") == "viirs") | (pl.col("platform") == "Terra"))
    daily_t = calendar_series(
        daily_series(cell_days(terra, grid)), metric, start, end, observed=observed
    )
    try:
        a.norm_early = fit_normalizer(weekly_pairs(daily_t), metric=metric)
    except ValueError as exc:
        a.notes.append(
            f"Terra-only years are reconstructed with the two-satellite model: no separate Terra-only "
            f"model could be fitted ({exc}); those years are biased low."
        )
        return harmonize(daily, a.norm)
    a.early_cutoff = AQUA_FIRE_START
    n = a.norm_early
    row = n.cv.filter(pl.col("model") == n.chosen).row(0, named=True)
    a.notes.append(
        f"Before {AQUA_FIRE_START.isoformat()} only Terra reports, with far fewer detections. Those "
        f"weeks use a Terra-only model ({n.chosen}, cross-validated error {row['mae_log']:.2f} in log "
        f"units, intervals about x{np.expm1(n.q) + 1:.1f}) so they are not mistaken for quiet years."
    )
    return harmonize_with_early(daily, a.norm, daily_t, n, AQUA_FIRE_START)
