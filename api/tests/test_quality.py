import math
from datetime import date, datetime, timedelta

import polars as pl

from emberline.data.schema import COMMON_SCHEMA, add_time_columns
from emberline.science.quality import QualityPolicy, apply_quality, persistent_cells


def rows(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source": "X",
        "sensor": "modis",
        "platform": "Aqua",
        "latitude": 30.0,
        "longitude": 75.0,
        "acq_utc": datetime(2020, 1, 1, 8),
        "daynight": "D",
        "frp": 5.0,
        "conf_num": 60.0,
        "conf_class": None,
        "bright_primary": 320.0,
        "bright_secondary": 300.0,
        "scan": 1.0,
        "track": 1.0,
        "fire_type": 0,
        "synthetic": False,
        "local_solar_hour": 0.0,
        "local_date": None,
    }
    base.update(kw)
    return base


def frame(items: list[dict[str, object]]) -> pl.DataFrame:
    df = pl.DataFrame(items, schema=COMMON_SCHEMA)
    return add_time_columns(df)


def test_modis_confidence_threshold() -> None:
    df = frame([rows(conf_num=29.0), rows(conf_num=30.0), rows(conf_num=90.0)])
    out = apply_quality(df, QualityPolicy(persistent_mask=False))
    assert out["conf_num"].to_list() == [30.0, 90.0]


def test_viirs_drops_low_confidence() -> None:
    v = {"sensor": "viirs", "platform": "SNPP", "conf_num": None}
    df = frame([rows(conf_class="l", **v), rows(conf_class="n", **v), rows(conf_class="h", **v)])
    out = apply_quality(df, QualityPolicy(persistent_mask=False))
    assert sorted(out["conf_class"].to_list()) == ["h", "n"]


def test_fire_type_filter_keeps_null() -> None:
    df = frame([rows(fire_type=0), rows(fire_type=2), rows(fire_type=None)])
    out = apply_quality(df, QualityPolicy(persistent_mask=False))
    assert out["fire_type"].to_list() == [0, None]
    strict = apply_quality(df, QualityPolicy(persistent_mask=False, keep_null_type=False))
    assert strict["fire_type"].to_list() == [0]


def test_day_night_selection() -> None:
    df = frame([rows(daynight="D"), rows(daynight="N")])
    out = apply_quality(df, QualityPolicy(persistent_mask=False, daynight="N"))
    assert out["daynight"].to_list() == ["N"]


def _flare_and_fires() -> pl.DataFrame:
    start = datetime(2020, 1, 1, 8)
    items = []
    for d in range(100):  # a flare active every day at one cell
        items.append(rows(latitude=31.0, longitude=76.0, acq_utc=start + timedelta(days=d)))
    for d in range(0, 100, 10):  # ordinary fires: one cell each, active on 1 day
        items.append(
            rows(latitude=30.0 + d / 1000, longitude=75.0, acq_utc=start + timedelta(days=d))
        )
    return frame(items)


def test_persistent_mask_finds_the_flare_only() -> None:
    df = _flare_and_fires()
    m = persistent_cells(df, cell_deg=0.02, min_frac=0.10)
    assert m.height == 1
    assert m["cx"][0] == math.floor(76.0 / 0.02) and m["cy"][0] == math.floor(31.0 / 0.02)


def test_apply_quality_removes_persistent_source() -> None:
    df = _flare_and_fires()
    out = apply_quality(df, QualityPolicy())
    assert out.height == 10
    assert (out["latitude"] < 31.0).all()
    assert apply_quality(df, QualityPolicy(persistent_mask=False)).height == 110


def test_empty_input() -> None:
    empty = pl.DataFrame(schema=COMMON_SCHEMA)
    assert apply_quality(empty).height == 0
    assert persistent_cells(empty).height == 0


def test_dates_cover_expected_span() -> None:
    df = _flare_and_fires()
    assert df["local_date"].min() == date(2020, 1, 1)
