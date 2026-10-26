"""Request limits and region geometry (bbox or uploaded GeoJSON).

Limits exist to keep one request from exhausting the FIRMS budget or the server. Every
rejection carries a message a user can act on.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np

BBox = tuple[float, float, float, float]

MAX_BBOX_AREA_DEG2 = 800.0  # about 28 x 28 degrees; the largest demo region is 360
MAX_PERIOD_DAYS = 27 * 366  # the whole MODIS record
MIN_PERIOD_DAYS = 365
MAX_FETCH_DAYS = 3 * 366  # longest period fetched live for a region that is not cached
MAX_GEOJSON_VERTICES = 20_000


class GuardrailError(ValueError):
    """The request is outside what the service accepts. The message says what to change."""


def check_bbox(bbox: BBox) -> BBox:
    w, s, e, n = bbox
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise GuardrailError(
            "The box must satisfy -180 <= west < east <= 180 and -90 <= south < north <= 90."
        )
    area = (e - w) * (n - s)
    if area > MAX_BBOX_AREA_DEG2:
        raise GuardrailError(
            f"That area is {area:,.0f} square degrees; the limit is {MAX_BBOX_AREA_DEG2:,.0f}. "
            f"Choose a smaller region."
        )
    return bbox


def check_period(start: date, end: date, earliest: date | None = None) -> None:
    if end < start:
        raise GuardrailError("The end date is before the start date.")
    days = (end - start).days + 1
    if days < MIN_PERIOD_DAYS:
        raise GuardrailError(
            "Choose at least one year: the harmonisation needs full seasons to compare."
        )
    if days > MAX_PERIOD_DAYS:
        raise GuardrailError(f"The period is {days:,} days; the limit is {MAX_PERIOD_DAYS:,}.")
    if earliest and start < earliest:
        raise GuardrailError(f"No MODIS fire data exist before {earliest.isoformat()}.")


def _rings(geom: dict[str, Any]) -> list[np.ndarray]:
    t = geom.get("type")
    if t == "Polygon":
        polys = [geom["coordinates"]]
    elif t == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        raise GuardrailError(f"Unsupported geometry type {t!r}: upload a Polygon or MultiPolygon.")
    rings = [np.asarray(p[0], dtype=float)[:, :2] for p in polys if p]  # outer rings only
    if not rings or any(r.shape[0] < 4 for r in rings):
        raise GuardrailError("A polygon needs at least 3 distinct vertices.")
    return rings


def geometry_from_geojson(obj: dict[str, Any]) -> list[np.ndarray]:
    """Outer rings of every polygon in a Geometry, Feature or FeatureCollection.

    Holes are ignored (a hole counts as inside the region). Vertex count is capped.
    """
    t = obj.get("type")
    if t == "FeatureCollection":
        geoms = [f["geometry"] for f in obj.get("features", []) if f.get("geometry")]
    elif t == "Feature":
        geoms = [obj["geometry"]]
    else:
        geoms = [obj]
    if not geoms:
        raise GuardrailError("The GeoJSON contains no geometry.")
    rings = [r for g in geoms for r in _rings(g)]
    if sum(len(r) for r in rings) > MAX_GEOJSON_VERTICES:
        raise GuardrailError(f"The shape has too many vertices (limit {MAX_GEOJSON_VERTICES:,}).")
    for r in rings:
        if not np.isfinite(r).all():
            raise GuardrailError("The GeoJSON has non-numeric coordinates.")
    return rings


def bbox_of(rings: list[np.ndarray]) -> BBox:
    allp = np.vstack(rings)
    return (
        float(allp[:, 0].min()),
        float(allp[:, 1].min()),
        float(allp[:, 0].max()),
        float(allp[:, 1].max()),
    )


def points_in_rings(lat: np.ndarray, lon: np.ndarray, rings: list[np.ndarray]) -> np.ndarray:
    """Even-odd ray casting for many points against the union of outer rings."""
    inside = np.zeros(len(lat), dtype=bool)
    for ring in rings:
        x, y = ring[:, 0], ring[:, 1]
        hit = np.zeros(len(lat), dtype=bool)
        for i in range(len(ring) - 1):
            x1, y1, x2, y2 = x[i], y[i], x[i + 1], y[i + 1]
            if y1 == y2:
                continue
            crosses = ((y1 > lat) != (y2 > lat)) & (lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1)
            hit ^= crosses
        inside |= hit
    return inside
