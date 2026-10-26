"""Hotspots for the map as GeoJSON, capped, and aggregated on the server when there are too many."""

from __future__ import annotations

from datetime import date
from typing import Any

import polars as pl

from emberline.data.store import HotspotStore

MAX_FEATURES = 50_000
MAX_DAYS = 7
BBox = tuple[float, float, float, float]
_CELL_STEPS = (0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)


def _points(df: pl.DataFrame) -> list[dict[str, Any]]:
    cols = [
        "longitude",
        "latitude",
        "sensor",
        "platform",
        "frp",
        "daynight",
        "acq_utc",
        "conf_num",
        "conf_class",
    ]
    rows = df.select(cols).iter_rows()
    feats = []
    for lon, lat, sensor, platform, frp, dn, t, cnum, cclass in rows:
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                "properties": {
                    "sensor": sensor,
                    "platform": platform,
                    "frp": None if frp is None else round(frp, 2),
                    "daynight": dn,
                    "time": t.isoformat(timespec="minutes") + "Z",
                    "confidence": cclass
                    if cclass is not None
                    else (None if cnum is None else int(cnum)),
                },
            }
        )
    return feats


def _aggregate(df: pl.DataFrame, cap: int) -> tuple[list[dict[str, Any]], float]:
    """Smallest cell size from a fixed ladder that gives at most `cap` cells (per sensor)."""
    for step in _CELL_STEPS:
        g = (
            df.with_columns(
                (pl.col("longitude") / step).floor().cast(pl.Int64).alias("ix"),
                (pl.col("latitude") / step).floor().cast(pl.Int64).alias("iy"),
            )
            .group_by("sensor", "ix", "iy")
            .agg(pl.len().alias("n"), pl.col("frp").sum().alias("frp_sum"))
        )
        if g.height <= cap or step == _CELL_STEPS[-1]:
            break
    feats = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round((ix + 0.5) * step, 5), round((iy + 0.5) * step, 5)],
            },
            "properties": {
                "sensor": sensor,
                "count": n,
                "frp_sum": round(frp or 0.0, 1),
                "cell_deg": step,
            },
        }
        for sensor, ix, iy, n, frp in g.iter_rows()
    ]
    return feats, step


def hotspots_geojson(
    store: HotspotStore,
    bbox: BBox,
    start: date,
    end: date,
    sensors: tuple[str, ...] = ("modis", "viirs"),
    synthetic: bool = False,
    max_features: int = MAX_FEATURES,
) -> dict[str, Any]:
    if (end - start).days + 1 > MAX_DAYS:
        raise ValueError(f"Ask for at most {MAX_DAYS} days of hotspots at a time.")
    max_features = min(max_features, MAX_FEATURES)
    df = store.query(bbox, start, end, synthetic=synthetic)
    df = df.filter(pl.col("sensor").is_in(list(sensors)))
    if df.height <= max_features:
        return {
            "type": "FeatureCollection",
            "features": _points(df),
            "properties": {"aggregated": False, "total": df.height},
        }
    feats, step = _aggregate(df, max_features)
    return {
        "type": "FeatureCollection",
        "features": feats,
        "properties": {"aggregated": True, "cell_deg": step, "total": df.height},
    }
