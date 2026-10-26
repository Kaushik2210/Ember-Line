from datetime import date
from pathlib import Path

import polars as pl

from emberline.data.cache import ParquetCache
from emberline.data.coverage import load_availability, observed_dates, save_availability
from emberline.data.firms import Availability
from emberline.data.schema import COMMON_SCHEMA

EMPTY = pl.DataFrame(schema=COMMON_SCHEMA)
BBOX = (74.0, 29.0, 77.0, 32.0)


def put(cache: ParquetCache, src: str, tile: str, start: date, partial: int | None = None) -> None:
    cache.write(EMPTY, src, tile, start, partial_days=partial)


def test_empty_chunk_counts_as_observed(tmp_path: Path) -> None:
    c = ParquetCache(tmp_path)
    put(c, "MODIS_SP", "73_28_78_33", date(2020, 1, 1))
    days = observed_dates(tmp_path, "MODIS_SP", BBOX)
    assert days == [date(2020, 1, d) for d in range(1, 6)]


def test_missing_chunk_is_a_gap_not_zeros(tmp_path: Path) -> None:
    c = ParquetCache(tmp_path)
    put(c, "MODIS_SP", "73_28_78_33", date(2020, 1, 1))
    put(c, "MODIS_SP", "73_28_78_33", date(2020, 1, 11))  # 6..10 never fetched
    days = observed_dates(tmp_path, "MODIS_SP", BBOX)
    assert date(2020, 1, 8) not in days and date(2020, 1, 12) in days


def test_partial_chunk_covers_only_its_days(tmp_path: Path) -> None:
    put(ParquetCache(tmp_path), "MODIS_SP", "73_28_78_33", date(2020, 1, 1), partial=2)
    assert observed_dates(tmp_path, "MODIS_SP", BBOX) == [date(2020, 1, 1), date(2020, 1, 2)]


def test_clipped_to_availability(tmp_path: Path) -> None:
    put(ParquetCache(tmp_path), "VIIRS_SNPP_SP", "73_28_78_33", date(2012, 1, 16))
    av = {"VIIRS_SNPP_SP": (date(2012, 1, 20), date(2026, 6, 30))}
    assert observed_dates(tmp_path, "VIIRS_SNPP_SP", BBOX, av) == [date(2012, 1, 20)]


def test_other_regions_tiles_do_not_count(tmp_path: Path) -> None:
    put(ParquetCache(tmp_path), "MODIS_SP", "-125_49_-95_61", date(2020, 1, 1))
    assert observed_dates(tmp_path, "MODIS_SP", BBOX) == []
    assert observed_dates(tmp_path, "NOPE", BBOX) == []


def test_grid_tiles_need_every_tile(tmp_path: Path) -> None:
    c = ParquetCache(tmp_path)
    box = (74.0, 29.0, 77.0, 32.0)  # straddles the 30N tile edge
    put(c, "MODIS_SP", "70_20_80_30", date(2020, 1, 1))
    put(c, "MODIS_SP", "70_30_80_40", date(2020, 1, 1))
    put(c, "MODIS_SP", "70_30_80_40", date(2020, 1, 6))  # south tile missing for this chunk
    days = observed_dates(tmp_path, "MODIS_SP", box)
    assert days == [date(2020, 1, d) for d in range(1, 6)]


def test_availability_roundtrip(tmp_path: Path) -> None:
    av = {"MODIS_SP": Availability("MODIS_SP", date(2000, 11, 1), date(2026, 7, 31))}
    save_availability(tmp_path, av)
    assert load_availability(tmp_path) == {"MODIS_SP": (date(2000, 11, 1), date(2026, 7, 31))}
    assert load_availability(tmp_path / "nowhere") == {}
