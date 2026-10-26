from datetime import date
from pathlib import Path

from emberline.data.cache import ParquetCache
from emberline.data.schema import normalize_firms_csv
from emberline.data.store import HotspotStore

FIX = Path(__file__).parent / "fixtures"
BBOX = (73.0, 28.0, 78.0, 31.0)


def _fill(tmp_path: Path) -> HotspotStore:
    cache = ParquetCache(tmp_path)
    modis = normalize_firms_csv((FIX / "modis_sp_sample.csv").read_text(), "MODIS_SP")
    viirs = normalize_firms_csv((FIX / "viirs_snpp_sp_sample.csv").read_text(), "VIIRS_SNPP_SP")
    cache.write(modis, "MODIS_SP", "70_20_80_30", date(2019, 11, 1))
    cache.write(viirs, "VIIRS_SNPP_SP", "70_20_80_30", date(2019, 11, 1))
    # the same rows again under a neighbouring tile, like a tile-boundary duplicate
    cache.write(modis, "MODIS_SP", "70_30_80_40", date(2019, 11, 1))
    return HotspotStore(tmp_path)


def test_empty_store(tmp_path: Path) -> None:
    store = HotspotStore(tmp_path)
    assert store.query(BBOX, date(2019, 1, 1), date(2019, 12, 31)).height == 0
    assert store.coverage().height == 0


def test_query_filters_and_dedupes(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    df = store.query(BBOX, date(2019, 11, 1), date(2019, 11, 1))
    assert df.group_by("sensor").len().sort("sensor").rows() == [("modis", 2), ("viirs", 2)]


def test_query_source_filter(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    df = store.query(BBOX, date(2019, 11, 1), date(2019, 11, 1), sources=["VIIRS_SNPP_SP"])
    assert set(df["sensor"]) == {"viirs"}


def test_bbox_and_date_filter(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    assert store.query((0, 0, 1, 1), date(2019, 11, 1), date(2019, 11, 1)).height == 0
    assert store.query(BBOX, date(2020, 1, 1), date(2020, 2, 1)).height == 0


def test_synthetic_is_isolated(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    assert store.query(BBOX, date(2019, 11, 1), date(2019, 11, 1), synthetic=True).height == 0
    assert not store.has_data(synthetic=True)


def test_coverage(tmp_path: Path) -> None:
    cov = _fill(tmp_path).coverage()
    assert cov["source"].to_list() == ["MODIS_SP", "VIIRS_SNPP_SP"]
    assert cov["rows"].to_list() == [2, 2]
