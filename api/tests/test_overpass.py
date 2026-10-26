from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from emberline.data.schema import COMMON_SCHEMA, add_time_columns
from emberline.science.overpass import (
    _nearest_within,
    _points,
    combine_summaries,
    match_coincident,
)

T0 = datetime(2020, 1, 1, 8, 0)
M_PER_DEG_LAT = 111_195.0


def det(
    sensor: str,
    lat: float,
    lon: float,
    minutes: float = 0.0,
    frp: float = 5.0,
    scan: float = 1.0,
    daynight: str = "D",
) -> dict[str, object]:
    return {
        "source": "X",
        "sensor": sensor,
        "platform": "Aqua" if sensor == "modis" else "SNPP",
        "latitude": lat,
        "longitude": lon,
        "acq_utc": T0 + timedelta(minutes=minutes),
        "daynight": daynight,
        "frp": frp,
        "conf_num": 60.0,
        "conf_class": None,
        "bright_primary": 320.0,
        "bright_secondary": 300.0,
        "scan": scan,
        "track": 1.0,
        "fire_type": 0,
        "synthetic": False,
        "local_solar_hour": 0.0,
        "local_date": None,
    }


def frame(items: list[dict[str, object]]) -> pl.DataFrame:
    return add_time_columns(pl.DataFrame(items, schema=COMMON_SCHEMA))


def north(metres: float) -> float:
    return metres / M_PER_DEG_LAT


def test_nearest_within_respects_distance_and_time() -> None:
    m = frame([det("modis", 30.0, 75.0)])
    t0 = np.datetime64(T0, "us")
    mp = _points(m, t0, 1.0)

    def run(dlat_m: float, dt_min: float) -> int:
        v = frame([det("viirs", 30.0 + north(dlat_m), 75.0, dt_min)])
        idx, _ = _nearest_within(_points(v, t0, 1.0), mp, 750.0, 10.0)
        return int(idx[0])

    assert run(300, 3) == 0
    assert run(740, 9.5) == 0
    assert run(800, 0) == -1  # too far
    assert run(300, 11) == -1  # too late
    assert run(300, -11) == -1  # too early


def test_matches_nearest_of_two_modis() -> None:
    m = frame([det("modis", 30.0, 75.0), det("modis", 30.0 + north(600), 75.0)])
    v = frame([det("viirs", 30.0 + north(500), 75.0, 1)])
    r = match_coincident(m, v)
    assert r.pairs.height == 1
    assert r.pairs["mi"][0] == 1  # the 100 m neighbour, not the 500 m one


def test_corroboration_and_frp_ratio_many_to_one() -> None:
    m = frame([det("modis", 30.0, 75.0, frp=10.0)])
    v = frame(
        [
            det("viirs", 30.0 + north(d), 75.0, 2, frp=f)
            for d, f in [(100, 1.0), (200, 2.0), (300, 3.0)]
        ]
    )
    r = match_coincident(m, v)
    assert r.summary["modis_corroborated_by_viirs"] == 1.0
    assert r.summary["viirs_corroborated_by_modis"] == 1.0
    assert r.frp_ratio["median_viirs_over_modis"] == pytest.approx(0.6)  # (1+2+3)/10
    assert r.pairs["n_viirs_px"][0] == 3


def test_omission_modis_misses_small_viirs_fires() -> None:
    # one shared fire, plus VIIRS-only small fires inside the same pass area
    m = frame([det("modis", 30.0, 75.0, frp=20.0)])
    v = frame(
        [det("viirs", 30.0 + north(100), 75.0, 1, frp=3.0)]
        + [det("viirs", 30.0 + 0.05 * i, 75.2, 1, frp=0.8) for i in range(1, 4)]
    )
    r = match_coincident(m, v)
    assert r.summary["viirs_corroborated_by_modis"] == pytest.approx(0.25)
    assert r.summary["viirs_unseen_by_modis"] == pytest.approx(0.75)
    assert r.summary["modis_corroborated_by_viirs"] == 1.0


def test_commission_modis_detection_viirs_did_not_see() -> None:
    m = frame([det("modis", 30.0, 75.0), det("modis", 30.1, 75.0)])
    v = frame([det("viirs", 30.0 + north(100), 75.0, 1)])
    r = match_coincident(m, v)
    assert r.summary["modis_corroborated_by_viirs"] == pytest.approx(0.5)
    assert r.summary["modis_unseen_by_viirs"] == pytest.approx(0.5)


def test_not_coobserved_detections_are_excluded_not_counted_as_misses() -> None:
    # second MODIS detection is 2 degrees (~220 km) from anything VIIRS saw
    m = frame([det("modis", 30.0, 75.0), det("modis", 32.0, 75.0)])
    v = frame([det("viirs", 30.0 + north(100), 75.0, 1)])
    r = match_coincident(m, v)
    assert r.summary["modis_not_coobserved"] == 1.0
    assert r.summary["modis_corroborated_by_viirs"] == 1.0


def test_breakdown_tables() -> None:
    m = frame(
        [
            det("modis", 30.0, 75.0, frp=2.0, daynight="D"),
            det("modis", 30.0 + 0.05, 75.0, frp=30.0, daynight="N", scan=2.5),
        ]
    )
    v = frame(
        [
            det("viirs", 30.0 + north(100), 75.0, 1, frp=1.0, daynight="D"),
            det("viirs", 30.05 + north(100), 75.0, 1, frp=9.0, daynight="N"),
        ]
    )
    r = match_coincident(m, v)
    assert set(r.by_daynight["daynight"]) == {"D", "N"}
    assert r.by_frp.height == 3  # union of MODIS and VIIRS FRP bins present
    assert r.by_scan.height == 2


def test_empty_inputs() -> None:
    empty = pl.DataFrame(schema=COMMON_SCHEMA)
    r = match_coincident(empty, frame([det("viirs", 30.0, 75.0)]))
    assert r.summary["n_modis"] == 0.0 and r.by_frp.height == 0


def test_combine_summaries_weights_by_coobserved_counts() -> None:
    a = {
        "n_modis": 10.0,
        "n_viirs": 10.0,
        "modis_not_coobserved": 0.0,
        "viirs_not_coobserved": 0.0,
        "n_modis_eval": 10.0,
        "n_viirs_eval": 10.0,
        "modis_corroborated_by_viirs": 1.0,
        "viirs_corroborated_by_modis": 0.5,
    }
    b = {
        "n_modis": 30.0,
        "n_viirs": 30.0,
        "modis_not_coobserved": 5.0,
        "viirs_not_coobserved": 5.0,
        "n_modis_eval": 30.0,
        "n_viirs_eval": 30.0,
        "modis_corroborated_by_viirs": 0.0,
        "viirs_corroborated_by_modis": 0.1,
    }
    c = combine_summaries([a, b])
    assert c["n_modis"] == 40.0 and c["modis_not_coobserved"] == 5.0
    assert c["modis_corroborated_by_viirs"] == pytest.approx(0.25)
    assert c["viirs_corroborated_by_modis"] == pytest.approx((5 + 3) / 40)
    assert c["modis_unseen_by_viirs"] == pytest.approx(0.75)
    assert combine_summaries([])["n_modis"] == 0.0


def test_summary_reports_coobserved_counts() -> None:
    m = frame([det("modis", 30.0, 75.0), det("modis", 32.0, 75.0)])
    v = frame([det("viirs", 30.0 + north(100), 75.0, 1)])
    r = match_coincident(m, v)
    assert r.summary["n_modis_eval"] == 1.0 and r.summary["n_viirs_eval"] == 1.0
