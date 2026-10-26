"""Headline findings for a region, computed from a finished analysis payload.

Used by the landing page, the atlas and the method page. Nothing here is typed in: every number
comes from the result, and a field is None when the result cannot support it.
"""

from __future__ import annotations

import math
from typing import Any


def _num(x: Any) -> float | None:
    return float(x) if isinstance(x, int | float) and math.isfinite(x) else None


def overlap_totals(daily: dict[str, list[Any]]) -> dict[str, Any]:
    """Totals over days both sensors were observing, and VIIRS divided by MODIS."""
    modis = viirs = 0.0
    days = 0
    for m, v in zip(daily["modis"], daily["viirs"], strict=True):
        if m is None or v is None:
            continue
        modis += m
        viirs += v
        days += 1
    return {
        "days": days,
        "modis_total": modis,
        "viirs_total": viirs,
        "ratio": viirs / modis if modis > 0 else None,
    }


def busiest_observed_day(payload: dict[str, Any]) -> str | None:
    """Busiest day VIIRS actually observed (where the sensors can be compared), else busiest overall."""
    h = payload.get("harmonized")
    if not h:
        return None
    best: int | None = None
    best_obs: int | None = None
    for i, v in enumerate(h["value"]):
        if v is None:
            continue
        if best is None or v > h["value"][best]:
            best = i
        if not h["reconstructed"][i] and (best_obs is None or v > h["value"][best_obs]):
            best_obs = i
    pick = best_obs if best_obs is not None else best
    return str(h["dates"][pick]) if pick is not None else None


def findings(payload: dict[str, Any]) -> dict[str, Any]:
    val = payload["validation"]
    ov = val.get("overpass") or {}
    norm = val.get("normalization")
    cal = payload.get("calendar")
    h = payload.get("harmonized")

    out: dict[str, Any] = {
        "metric": payload["meta"]["metric"],
        "synthetic": payload["synthetic"],
        "years": [cal["years"][0], cal["years"][-1]] if cal and cal["years"] else None,
        "overlap": overlap_totals(payload["daily"]),
        "overpass": None,
        "normalization": None,
        "reconstructed_share": None,
        "busiest_day": busiest_observed_day(payload),
        "top_season": None,
        "top_events": [],
        "segments": (payload.get("seasonality") or {}).get("segments", []),
        "notes": payload["quality"]["notes"][:4],
    }
    if ov.get("n_modis_eval"):
        out["overpass"] = {
            "n_modis": ov["n_modis_eval"],
            "n_viirs": ov["n_viirs_eval"],
            "modis_seen_by_viirs": _num(ov.get("modis_corroborated_by_viirs")),
            "viirs_seen_by_modis": _num(ov.get("viirs_corroborated_by_modis")),
        }
    if norm:
        cv = {r["model"]: r for r in norm["cv"]}
        raw, best, scale = cv.get("raw"), cv.get(norm["chosen"]), cv.get("scale")
        q = _num(norm.get("interval_halfwidth_log1p"))

        def pick(r: dict[str, Any] | None) -> dict[str, float | None] | None:
            return (
                None
                if r is None
                else {
                    k: _num(r.get(k))
                    for k in ("r2_log", "mae_log", "bias_rel", "spearman", "coverage")
                }
            )

        out["normalization"] = {
            "chosen": norm["chosen"],
            "n_weeks": norm["n_weeks"],
            "years": [norm["years"][0], norm["years"][-1]],
            "before": pick(raw),
            "after": pick(best),
            "scale_baseline": pick(scale),
            "band_factor": math.expm1(q) + 1 if q is not None else None,
            "level": norm["level"],
            "cv": norm["cv"],
        }
    if h:
        valid = [
            (r, v) for r, v in zip(h["reconstructed"], h["value"], strict=True) if v is not None
        ]
        if valid:
            out["reconstructed_share"] = sum(1 for r, _ in valid if r) / len(valid)
    seasons = payload["anomalies"]["seasons"]
    if seasons:
        s = seasons[0]
        out["top_season"] = {"season": s["season"], "z": s["z"], "text": s["text"]}
    events = sorted(
        payload["anomalies"]["events"], key=lambda e: abs(e["mean_z"]) * e["days"], reverse=True
    )
    out["top_events"] = [
        {k: e[k] for k in ("start", "end", "days", "direction", "mean_z", "text", "caveat")}
        for e in events[:3]
    ]
    return out
