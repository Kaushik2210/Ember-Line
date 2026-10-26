from datetime import date

import polars as pl
import pytest

from emberline.science.series import calendar_series, sensor_periods, weekly, weekly_pairs


def ds(rows: list[tuple[str, date, str, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "local_date": d,
                "sensor": s,
                "daynight": dn,
                "det_count": 1,
                "active_1km": 1,
                "frp_sum_mw": v,
                "cells_active": 1,
            }
            for s, d, dn, v in rows
        ],
        schema={
            "local_date": pl.Date,
            "sensor": pl.Utf8,
            "daynight": pl.Utf8,
            "det_count": pl.Int64,
            "active_1km": pl.Int64,
            "frp_sum_mw": pl.Float64,
            "cells_active": pl.Int64,
        },
    )


def test_zero_fill_only_inside_each_sensors_period() -> None:
    d = ds(
        [
            ("modis", date(2020, 1, 1), "D", 5.0),
            ("modis", date(2020, 1, 10), "D", 7.0),
            ("viirs", date(2020, 1, 5), "D", 2.0),
            ("viirs", date(2020, 1, 8), "D", 3.0),
        ]
    )
    cs = calendar_series(d, "frp_sum_mw")
    assert cs.height == 10
    modis = dict(zip(cs["local_date"], cs["modis"], strict=True))
    viirs = dict(zip(cs["local_date"], cs["viirs"], strict=True))
    assert modis[date(2020, 1, 5)] == 0.0  # observed period, nothing detected
    assert viirs[date(2020, 1, 5)] == 2.0
    assert viirs[date(2020, 1, 2)] is None  # before VIIRS observed anything
    assert viirs[date(2020, 1, 9)] is None  # after


def test_periods_override_extends_zero_fill() -> None:
    d = ds([("modis", date(2020, 1, 3), "D", 5.0), ("viirs", date(2020, 1, 3), "D", 1.0)])
    cs = calendar_series(
        d,
        "frp_sum_mw",
        periods={
            "modis": (date(2020, 1, 1), date(2020, 1, 5)),
            "viirs": (date(2020, 1, 1), date(2020, 1, 5)),
        },
    )
    assert cs["viirs"].to_list() == [0.0, 0.0, 1.0, 0.0, 0.0]


def test_daynight_selection_and_unknown_metric() -> None:
    d = ds(
        [
            ("modis", date(2020, 1, 1), "D", 5.0),
            ("modis", date(2020, 1, 1), "N", 2.0),
            ("viirs", date(2020, 1, 1), "D", 1.0),
        ]
    )
    assert calendar_series(d, "frp_sum_mw")["modis"][0] == 7.0
    assert calendar_series(d, "frp_sum_mw", daynight="N")["modis"][0] == 2.0
    with pytest.raises(ValueError):
        calendar_series(d, "nope")


def test_weekly_requires_all_seven_days() -> None:
    # 2020-01-06 is a Monday. modis observed 06..16 (full weeks 06-12 and partial 13-16)
    rows = [("modis", date(2020, 1, 6 + i), "D", 1.0) for i in range(11)]
    rows += [("viirs", date(2020, 1, 6), "D", 1.0), ("viirs", date(2020, 1, 12), "D", 1.0)]
    w = weekly(
        calendar_series(ds(rows), "frp_sum_mw", start=date(2020, 1, 6), end=date(2020, 1, 16))
    )
    assert w["week"].to_list() == [date(2020, 1, 6), date(2020, 1, 13)]
    assert w["modis"].to_list() == [7.0, None]
    assert w["viirs"].to_list() == [2.0, None]


def test_weekly_pairs_drops_incomplete_overlap() -> None:
    rows = [("modis", date(2020, 1, 6 + i), "D", 2.0) for i in range(14)]
    rows += [("viirs", date(2020, 1, 6 + i), "D", 1.0) for i in range(7)]
    wp = weekly_pairs(calendar_series(ds(rows), "frp_sum_mw"))
    assert wp.height == 1 and wp["modis"][0] == 14.0 and wp["viirs"][0] == 7.0


def test_sensor_periods() -> None:
    d = ds([("modis", date(2020, 1, 1), "D", 1.0), ("modis", date(2020, 3, 1), "D", 1.0)])
    assert sensor_periods(d) == {"modis": (date(2020, 1, 1), date(2020, 3, 1))}
