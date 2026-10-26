"""Turn an Analysis into the JSON payload served to the web app and exported as a methods card."""

from __future__ import annotations

import math
import platform
import sys
from datetime import UTC, date, datetime
from typing import Any

import numpy as np
import polars as pl
import sklearn
import statsmodels

from emberline import __version__
from emberline.pipeline import Analysis
from emberline.science.anomalies import describe_event, describe_season
from emberline.science.seasonality import DOY, doy_matrix

ACKNOWLEDGMENT = (
    "We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource "
    "Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, "
    "Atmosphere Near real-time Capability for Earth observations (LANCE) "
    "(https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System "
    "(ESDIS)."
)
SIG_DIGITS = 4


def clean(x: Any) -> Any:
    """JSON-safe: NaN/inf -> None, numpy scalars -> python, dates -> ISO strings, rounded floats."""
    if x is None or isinstance(x, bool | str):
        return x
    if isinstance(x, float | np.floating):
        v = float(x)
        if not math.isfinite(v):
            return None
        return float(f"{v:.{SIG_DIGITS}g}") if v != 0 else 0.0
    if isinstance(x, int | np.integer):
        return int(x)
    if isinstance(x, datetime | date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return [clean(v) for v in x.tolist()]
    if isinstance(x, pl.Series):
        return [clean(v) for v in x.to_list()]
    return str(x)


def records(df: pl.DataFrame | None, drop: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if df is None or df.height == 0:
        return []
    keep = [c for c in df.columns if c not in drop]
    return [clean(r) for r in df.select(keep).iter_rows(named=True)]


def _matrix(daily: pl.DataFrame, col: str, years: list[int]) -> list[list[float | None]]:
    """Years x 365 matrix on a shared year axis; a year with no data in `col` is a row of nulls.

    Every matrix must use the same `years`, or rows would not line up between sensors."""
    mat, have = doy_matrix(daily.select("local_date", col), col)
    by_year = {y: row for y, row in zip(have, mat, strict=True)}
    return [[clean(v) for v in by_year[y]] if y in by_year else [None] * DOY for y in years]


def methods_card(a: Analysis) -> dict[str, Any]:
    """Exactly what produced this result: parameters, versions and sources (reproducibility)."""
    card: dict[str, Any] = clean(
        {
            "emberline_version": __version__,
            "run_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "synthetic": a.synthetic,
            "bbox": a.bbox,
            "period": {"start": a.start, "end": a.end},
            "metric": a.metric,
            "grid": a.grid.model_dump(),
            "quality_policy": a.policy.model_dump(),
            "model": {
                "chosen": a.norm.chosen if a.norm else None,
                "fitted_on": "weekly totals, log1p scale",
                "validation": "leave-one-year-out",
                "interval": f"cross-conformal, {a.norm.level:.0%} nominal" if a.norm else None,
            },
            "sources": {
                "modis": "FIRMS MODIS_SP (Terra + Aqua)" if not a.synthetic else "SYNTHETIC_MODIS",
                "viirs": "FIRMS VIIRS_SNPP_SP (Suomi NPP)"
                if not a.synthetic
                else "SYNTHETIC_VIIRS",
            },
            "versions": {
                "python": sys.version.split()[0],
                "platform": platform.system(),
                "polars": pl.__version__,
                "numpy": np.__version__,
                "scikit-learn": sklearn.__version__,
                "statsmodels": statsmodels.__version__,
            },
            "acknowledgment": ACKNOWLEDGMENT,
        }
    )
    return card


def result_payload(a: Analysis) -> dict[str, Any]:
    h = a.harmonized
    out: dict[str, Any] = {
        "meta": methods_card(a),
        "bbox": list(a.bbox),
        "synthetic": a.synthetic,
        "quality": {
            "counts": a.counts,
            "notes": a.notes,
            "platforms": records(a.platforms),
            "annotations": [
                {
                    "when": e.when,
                    "precision": e.precision,
                    "kind": e.kind,
                    "title": e.title,
                    "detail": e.detail,
                    "affects": list(e.affects),
                    "source": e.source,
                }
                for e in a.annotations
            ],
        },
        "daily": {  # raw per-sensor series, null where a sensor was not observing
            "dates": clean(a.daily["local_date"]),
            "modis": clean(a.daily["modis"]),
            "viirs": clean(a.daily["viirs"]),
        },
        "validation": {
            "overpass": clean(a.overpass),
            "frp_ratio": clean(a.frp_ratio),
            "tables": {
                k: records(t, drop=tuple(c for c in t.columns if c.endswith("_i")))
                for k, t in a.overpass_tables.items()
            },
            "normalization": None,
        },
        "harmonized": None,
        "calendar": None,
        "seasonality": None,
        "anomalies": {"events": [], "seasons": []},
    }
    if a.norm_early:
        e = a.norm_early
        out["validation"]["normalization_terra_only"] = {
            "chosen": e.chosen,
            "cv": records(e.cv),
            "n_weeks": e.n_weeks,
            "years": e.years,
            "interval_halfwidth_log1p": clean(e.q),
            "level": e.level,
            "pairs": records(e.pairs),
            "used_before": a.early_cutoff,
        }
    if a.norm:
        n = a.norm
        out["validation"]["normalization"] = {
            "chosen": n.chosen,
            "cv": records(n.cv),
            "n_weeks": n.n_weeks,
            "years": n.years,
            "interval_halfwidth_log1p": clean(n.q),
            "level": n.level,
            "pairs": records(n.pairs),
        }
    if h is not None:
        out["harmonized"] = {
            "modis_basis": h["modis_basis"].to_list() if "modis_basis" in h.columns else None,
            "dates": clean(h["local_date"]),
            "value": clean(h["harmonized"]),
            "lo": clean(h["lo"]),
            "hi": clean(h["hi"]),
            "reconstructed": [int(bool(v)) for v in h["reconstructed"].to_list()],
        }
        years = sorted(set(h["local_date"].dt.year().to_list()))
        cal: dict[str, Any] = {}
        for key, col in (
            ("harmonized", "harmonized"),
            ("lo", "lo"),
            ("hi", "hi"),
            ("modis", "modis_raw"),
            ("viirs", "viirs_raw"),
        ):
            cal[key] = _matrix(h, col, years)
        rec = h.with_columns(pl.col("reconstructed").cast(pl.Float64).alias("rec"))
        cal["reconstructed"] = _matrix(rec, "rec", years)
        out["calendar"] = {"years": years, "days_per_year": DOY, **cal}
    if a.climatology is not None:
        c = a.climatology
        out["seasonality"] = {
            "climatology": {k: clean(c[k]) for k in c.columns},
            "markers": clean(a.markers.__dict__) if a.markers else None,
            "segments": [clean(m.__dict__) for m in a.segments],
            "stl": ({k: clean(a.stl[k]) for k in a.stl.columns} if a.stl is not None else None),
        }
    out["anomalies"]["events"] = [
        {**clean(e.__dict__), "text": describe_event(e)} for e in a.events
    ]
    if a.seasons is not None and a.seasons.height:
        n_years = a.seasons.height
        out["anomalies"]["seasons"] = [
            {**clean(r), "text": describe_season(str(r["season"]), float(r["z"]), n_years)}
            for r in a.seasons.iter_rows(named=True)
        ]
    return out
