from datetime import date
from pathlib import Path

from emberline.data.cache import ParquetCache
from emberline.data.schema import COMMON_SCHEMA, normalize_firms_csv

FIX = Path(__file__).parent / "fixtures"


def test_roundtrip(tmp_path: Path) -> None:
    cache = ParquetCache(tmp_path)
    df = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    assert not cache.has("MODIS_SP", "70_20_80_30", date(2019, 11, 1))
    cache.write(df, "MODIS_SP", "70_20_80_30", date(2019, 11, 1))
    assert cache.has("MODIS_SP", "70_20_80_30", date(2019, 11, 1))
    back = cache.read("MODIS_SP", "70_20_80_30", date(2019, 11, 1))
    assert back.equals(df)


def test_empty_chunk_is_cached_with_schema(tmp_path: Path) -> None:
    import polars as pl

    cache = ParquetCache(tmp_path)
    cache.write(pl.DataFrame(schema=COMMON_SCHEMA), "MODIS_SP", "t", date(2020, 1, 1))
    assert cache.has("MODIS_SP", "t", date(2020, 1, 1))
    assert cache.read("MODIS_SP", "t", date(2020, 1, 1)).schema == COMMON_SCHEMA


def test_missing_read_is_empty(tmp_path: Path) -> None:
    assert ParquetCache(tmp_path).read("MODIS_SP", "t", date(2020, 1, 1)).height == 0


def test_no_temp_files_left(tmp_path: Path) -> None:
    cache = ParquetCache(tmp_path)
    df = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    cache.write(df, "MODIS_SP", "t", date(2020, 1, 1))
    assert not list(tmp_path.rglob("*.tmp"))


def test_partial_chunk_is_not_reported_complete(tmp_path: Path) -> None:
    cache = ParquetCache(tmp_path)
    df = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    cache.write(df, "MODIS_SP", "t", date(2026, 7, 31), partial_days=1)
    assert not cache.has("MODIS_SP", "t", date(2026, 7, 31))
    assert cache.path("MODIS_SP", "t", date(2026, 7, 31), 1).is_file()
