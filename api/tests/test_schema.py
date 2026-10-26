from datetime import date, datetime
from pathlib import Path

import polars as pl
import pytest

from emberline.data.schema import COMMON_SCHEMA, add_time_columns, normalize_firms_csv

FIX = Path(__file__).parent / "fixtures"


def test_modis_normalised() -> None:
    df = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    assert df.schema == COMMON_SCHEMA
    row = df.row(0, named=True)
    assert row["sensor"] == "modis" and row["platform"] == "Terra"
    assert row["conf_num"] == 55 and row["conf_class"] is None
    assert row["bright_primary"] == 315.8 and row["bright_secondary"] == 299.1
    assert row["acq_utc"] == datetime(2019, 11, 1, 6, 6)
    assert row["fire_type"] == 0 and row["synthetic"] is False


def test_viirs_normalised() -> None:
    df = normalize_firms_csv((FIX / "viirs_snpp_sp_sample.csv").read_text(), "VIIRS_SNPP_SP")
    row = df.row(0, named=True)
    assert row["sensor"] == "viirs" and row["platform"] == "SNPP"
    assert row["conf_class"] == "n" and row["conf_num"] is None
    assert row["bright_primary"] == 334.23 and row["bright_secondary"] == 290.39
    assert row["acq_utc"] == datetime(2019, 11, 1, 7, 43)


def test_empty_and_header_only() -> None:
    assert normalize_firms_csv("", "MODIS_SP").schema == COMMON_SCHEMA
    header = (FIX / "modis_sp_sample.csv").read_text().splitlines()[0]
    assert normalize_firms_csv(header + "\n", "MODIS_SP").height == 0


def test_unknown_source() -> None:
    with pytest.raises(ValueError):
        normalize_firms_csv("a\n1\n", "NOPE")


def test_local_solar_time_basic() -> None:
    # 06:06 UTC at 75.9793E -> +5.065 h -> ~11:11 local, same day
    df = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    row = df.row(0, named=True)
    assert row["local_solar_hour"] == pytest.approx(6 + 6 / 60 + 75.9793 / 15)
    assert row["local_date"] == date(2019, 11, 1)


def test_local_date_rolls_over_both_ways() -> None:
    df = pl.DataFrame(
        {
            "acq_utc": [datetime(2020, 1, 1, 22, 0), datetime(2020, 1, 1, 1, 0)],
            "longitude": [150.0, -120.0],  # +10 h -> next day 08:00 ; -8 h -> prev day 17:00
        }
    )
    out = add_time_columns(df)
    assert out["local_date"].to_list() == [date(2020, 1, 2), date(2019, 12, 31)]
    assert out["local_solar_hour"].to_list() == pytest.approx([8.0, 17.0])
