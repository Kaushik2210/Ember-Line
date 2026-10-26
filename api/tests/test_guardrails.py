from datetime import date

import numpy as np
import pytest

from emberline.guardrails import (
    MAX_BBOX_AREA_DEG2,
    GuardrailError,
    bbox_of,
    check_bbox,
    check_period,
    geometry_from_geojson,
    points_in_rings,
)

SQUARE = {"type": "Polygon", "coordinates": [[[74, 29], [77, 29], [77, 32], [74, 32], [74, 29]]]}


def test_bbox_accepts_demo_regions_and_rejects_bad_ones() -> None:
    assert check_bbox((14.4, 2.2, 34.0, 12.0)) == (14.4, 2.2, 34.0, 12.0)
    assert check_bbox((-125.0, 49.0, -95.0, 61.0))  # Canada, the biggest demo region
    with pytest.raises(GuardrailError, match="square degrees"):
        check_bbox((-100, -50, 100, 50))
    with pytest.raises(GuardrailError, match="west < east"):
        check_bbox((10, 0, 5, 5))
    with pytest.raises(GuardrailError):
        check_bbox((0, 0, 1, 95))
    assert (MAX_BBOX_AREA_DEG2) >= 360


def test_period_rules() -> None:
    check_period(date(2012, 1, 1), date(2020, 12, 31))
    with pytest.raises(GuardrailError, match="before the start"):
        check_period(date(2020, 1, 2), date(2020, 1, 1))
    with pytest.raises(GuardrailError, match="at least one year"):
        check_period(date(2020, 1, 1), date(2020, 3, 1))
    with pytest.raises(GuardrailError, match="limit"):
        check_period(date(1990, 1, 1), date(2026, 1, 1))
    with pytest.raises(GuardrailError, match="before 2000-11-01"):
        check_period(date(1999, 1, 1), date(2005, 1, 1), earliest=date(2000, 11, 1))


def test_geojson_forms_and_bbox() -> None:
    feat = {"type": "Feature", "properties": {}, "geometry": SQUARE}
    coll = {"type": "FeatureCollection", "features": [feat]}
    for obj in (SQUARE, feat, coll):
        assert bbox_of(geometry_from_geojson(obj)) == (74.0, 29.0, 77.0, 32.0)


def test_geojson_rejections() -> None:
    with pytest.raises(GuardrailError, match="Polygon"):
        geometry_from_geojson({"type": "Point", "coordinates": [1, 2]})
    with pytest.raises(GuardrailError, match="no geometry"):
        geometry_from_geojson({"type": "FeatureCollection", "features": []})
    with pytest.raises(GuardrailError, match="vertices"):
        geometry_from_geojson({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]})
    big = {"type": "Polygon", "coordinates": [[[i % 100, i % 50] for i in range(21_000)]]}
    with pytest.raises(GuardrailError, match="too many"):
        geometry_from_geojson(big)


def test_point_in_polygon() -> None:
    rings = geometry_from_geojson(SQUARE)
    lat = np.array([30.0, 33.0, 29.5, 28.0])
    lon = np.array([75.0, 75.0, 76.9, 75.0])
    assert points_in_rings(lat, lon, rings).tolist() == [True, False, True, False]


def test_point_in_concave_and_multipolygon() -> None:
    # an L shape: the notch (upper right) is outside
    el = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4], [0, 0]]],
    }
    r = geometry_from_geojson(el)
    assert points_in_rings(np.array([1.0, 3.0, 1.0]), np.array([1.0, 3.0, 3.0]), r).tolist() == [
        True,
        False,
        True,
    ]
    multi = {"type": "MultiPolygon", "coordinates": [SQUARE["coordinates"], el["coordinates"]]}
    rr = geometry_from_geojson(multi)
    assert len(rr) == 2
    assert points_in_rings(np.array([30.0, 1.0]), np.array([75.0, 1.0]), rr).all()
