from datetime import date
from pathlib import Path

import polars as pl
import pytest

from emberline.data.schema import COMMON_SCHEMA
from emberline.data.store import HotspotStore
from emberline.data.synthetic import generate_synthetic, write_synthetic

BBOX = (74.0, 29.0, 77.0, 32.0)
START, END = date(2014, 1, 1), date(2018, 12, 31)


@pytest.fixture(scope="module")
def df() -> pl.DataFrame:
    return generate_synthetic(BBOX, START, END, seed=1)


def test_schema_and_flagging(df: pl.DataFrame) -> None:
    assert df.schema == COMMON_SCHEMA
    assert df["synthetic"].all()
    assert df["source"].str.starts_with("SYNTHETIC_").all()


def test_deterministic_per_seed(df: pl.DataFrame) -> None:
    again = generate_synthetic(BBOX, START, END, seed=1)
    assert again.equals(df)
    assert not generate_synthetic(BBOX, START, END, seed=2).equals(df)


def test_inside_bbox_and_period(df: pl.DataFrame) -> None:
    assert df["longitude"].min() > BBOX[0] - 0.1 and df["longitude"].max() < BBOX[2] + 0.1
    assert df["latitude"].min() > BBOX[1] - 0.1 and df["latitude"].max() < BBOX[3] + 0.1
    assert df["local_date"].min() >= START and df["local_date"].max() <= END


def test_viirs_sees_more_than_modis(df: pl.DataFrame) -> None:
    counts = dict(df.group_by("sensor").len().iter_rows())
    assert counts["viirs"] > 1.5 * counts["modis"]


def test_overpass_times_differ_by_platform(df: pl.DataFrame) -> None:
    med = dict(df.group_by("platform").agg(pl.col("local_solar_hour").median()).iter_rows())
    assert med["Terra"] == pytest.approx(10.5, abs=0.3)
    assert med["Aqua"] == pytest.approx(13.5, abs=0.3)
    assert med["SNPP"] == pytest.approx(13.5, abs=0.3)


def test_has_a_seasonal_cycle(df: pl.DataFrame) -> None:
    by_month = df.group_by(pl.col("local_date").dt.month().alias("m")).len().sort("m")
    counts = dict(by_month.iter_rows())
    assert counts[7] > 5 * counts[1]


def test_confidence_scheme_per_sensor(df: pl.DataFrame) -> None:
    modis = df.filter(pl.col("sensor") == "modis")
    viirs = df.filter(pl.col("sensor") == "viirs")
    assert modis["conf_num"].is_not_null().all() and modis["conf_class"].is_null().all()
    assert viirs["conf_num"].is_null().all()
    assert set(viirs["conf_class"].unique()) <= {"l", "n", "h"}


def test_write_and_read_back_isolated_from_real(df: pl.DataFrame, tmp_path: Path) -> None:
    write_synthetic(tmp_path, df)
    store = HotspotStore(tmp_path)
    got = store.query(BBOX, START, END, synthetic=True)
    assert got.height > 0 and got["synthetic"].all()
    assert store.query(BBOX, START, END, synthetic=False).height == 0
