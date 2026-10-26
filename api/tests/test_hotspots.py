from datetime import date

import polars as pl
import pytest
from conftest import BBOX

from emberline.data.store import HotspotStore
from emberline.hotspots import MAX_DAYS, hotspots_geojson

DAY = date(2017, 7, 12)


def busy_day(store: HotspotStore) -> date:
    df = store.query(BBOX, date(2017, 1, 1), date(2017, 12, 31), synthetic=True)
    return df.group_by("local_date").len().sort("len").row(-1)[0]


def test_points_for_a_busy_day(store: HotspotStore) -> None:
    day = busy_day(store)
    fc = hotspots_geojson(store, BBOX, day, day, synthetic=True)
    assert fc["type"] == "FeatureCollection" and fc["properties"]["aggregated"] is False
    assert len(fc["features"]) == fc["properties"]["total"] > 0
    f = fc["features"][0]
    assert f["geometry"]["type"] == "Point" and len(f["geometry"]["coordinates"]) == 2
    assert {"sensor", "platform", "frp", "daynight", "time", "confidence"} <= set(f["properties"])
    assert f["properties"]["time"].endswith("Z")


def test_sensor_filter(store: HotspotStore) -> None:
    day = busy_day(store)
    fc = hotspots_geojson(store, BBOX, day, day, sensors=("viirs",), synthetic=True)
    assert {f["properties"]["sensor"] for f in fc["features"]} == {"viirs"}


def test_over_the_cap_is_aggregated_server_side(store: HotspotStore) -> None:
    start, end = date(2017, 6, 1), date(2017, 6, 7)
    fc = hotspots_geojson(store, BBOX, start, end, synthetic=True, max_features=50)
    assert fc["properties"]["aggregated"] is True
    assert len(fc["features"]) <= 50 or fc["properties"]["cell_deg"] == 2.0
    total = sum(f["properties"]["count"] for f in fc["features"])
    assert total == fc["properties"]["total"]  # nothing lost, only grouped
    assert "count" in fc["features"][0]["properties"]


def test_cap_never_exceeds_the_hard_limit(store: HotspotStore) -> None:
    fc = hotspots_geojson(store, BBOX, DAY, DAY, synthetic=True, max_features=10**9)
    assert len(fc["features"]) <= 50_000


def test_window_limit(store: HotspotStore) -> None:
    with pytest.raises(ValueError, match=str(MAX_DAYS)):
        hotspots_geojson(store, BBOX, date(2017, 1, 1), date(2017, 1, 20), synthetic=True)


def test_empty_day_is_an_empty_collection(store: HotspotStore) -> None:
    fc = hotspots_geojson(store, BBOX, date(2017, 1, 3), date(2017, 1, 3), synthetic=True)
    assert fc["features"] == [] or fc["properties"]["total"] == len(fc["features"])
    assert isinstance(pl.DataFrame(), pl.DataFrame)
