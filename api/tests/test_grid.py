from datetime import datetime

import h3
import polars as pl
import pytest

from emberline.data.schema import COMMON_SCHEMA, add_time_columns
from emberline.science.grid import GridSpec, assign_cells, cell_days, daily_series


def frame(items: list[dict[str, object]]) -> pl.DataFrame:
    base: dict[str, object] = {
        "source": "X",
        "sensor": "modis",
        "platform": "Aqua",
        "latitude": 30.005,
        "longitude": 75.005,
        "acq_utc": datetime(2020, 1, 1, 8),
        "daynight": "D",
        "frp": 1.0,
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
    df = pl.DataFrame([{**base, **i} for i in items], schema=COMMON_SCHEMA)
    return add_time_columns(df)


REG = GridSpec(kind="regular", size_deg=0.25)


def test_viirs_pixels_in_one_footprint_count_once_for_presence() -> None:
    # four VIIRS pixels inside one 0.01-degree footprint, one MODIS pixel in it too
    v = {"sensor": "viirs", "platform": "SNPP"}
    df = frame(
        [
            {**v, "latitude": 30.001, "longitude": 75.001, "frp": 1.0},
            {**v, "latitude": 30.003, "longitude": 75.003, "frp": 2.0},
            {**v, "latitude": 30.006, "longitude": 75.006, "frp": 3.0},
            {**v, "latitude": 30.008, "longitude": 75.008, "frp": 4.0},
            {"latitude": 30.005, "longitude": 75.005, "frp": 10.0},
        ]
    )
    cd = cell_days(df, REG).sort("sensor")
    modis, viirs = cd.row(0, named=True), cd.row(1, named=True)
    assert viirs["det_count"] == 4 and modis["det_count"] == 1  # raw counts disagree...
    assert viirs["active_1km"] == modis["active_1km"] == 1  # ...presence agrees
    assert viirs["frp_sum_mw"] == pytest.approx(10.0) and modis["frp_sum_mw"] == pytest.approx(10.0)
    assert viirs["cell_active"] == 1


def test_separate_footprints_counted_separately() -> None:
    df = frame(
        [{"latitude": 30.005}, {"latitude": 30.025}, {"latitude": 30.025, "longitude": 75.1}]
    )
    cd = cell_days(df, GridSpec(kind="regular", size_deg=0.25))
    assert cd["active_1km"].sum() == 3
    assert cd.height == 1  # all in one 0.25 degree cell on one day


def test_cells_split_on_grid_boundaries() -> None:
    df = frame([{"longitude": 75.10}, {"longitude": 75.40}])
    assert cell_days(df, GridSpec(kind="regular", size_deg=0.25)).height == 2
    assert cell_days(df, GridSpec(kind="regular", size_deg=0.5)).height == 1


def test_day_and_night_kept_apart() -> None:
    df = frame([{"daynight": "D"}, {"daynight": "N"}])
    assert cell_days(df, REG).height == 2


def test_h3_cells_valid_and_resolution() -> None:
    df = frame([{"latitude": 30.005, "longitude": 75.005}, {"latitude": 30.5, "longitude": 75.5}])
    g = assign_cells(df, GridSpec(kind="h3", h3_res=5))
    assert all(h3.is_valid_cell(c) and h3.get_resolution(c) == 5 for c in g["cell"])
    assert g["cell"][0] != g["cell"][1]
    assert h3.latlng_to_cell(30.005, 75.005, 5) == g["cell"][0]


def test_grid_spec_validation() -> None:
    with pytest.raises(ValueError):
        GridSpec(kind="regular", size_deg=0.001)
    with pytest.raises(ValueError):
        GridSpec(kind="h3", h3_res=9)


def test_daily_series_sums_over_cells() -> None:
    df = frame(
        [
            {"longitude": 75.10, "frp": 1.0},
            {"longitude": 75.40, "frp": 2.0},
            {"longitude": 75.40, "latitude": 31.0, "frp": 4.0},
        ]
    )
    ds = daily_series(cell_days(df, REG))
    assert ds.height == 1
    row = ds.row(0, named=True)
    assert row["det_count"] == 3 and row["frp_sum_mw"] == pytest.approx(7.0)
    assert row["cells_active"] == 3 and row["active_1km"] == 3


def test_empty_input() -> None:
    empty = pl.DataFrame(schema=COMMON_SCHEMA)
    assert cell_days(empty, REG).height == 0
