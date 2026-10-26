from datetime import date
from pathlib import Path

import httpx
import respx

from emberline.data.cache import ParquetCache
from emberline.data.firms import FirmsClient
from emberline.data.ingest import ingest
from emberline.data.limiter import RateLimiter
from emberline.data.store import HotspotStore

FIX = Path(__file__).parent / "fixtures"
AVAIL = "data_id,min_date,max_date\nMODIS_SP,2000-11-01,2019-11-15\nVIIRS_SNPP_SP,2012-01-20,2026-06-30\n"
BBOX = (74.0, 31.0, 77.0, 32.0)  # one 10-degree tile


async def _nosleep(_: float) -> None:
    return None


def mock_api() -> respx.Route:
    respx.get(url__regex=r".*/data_availability/.*").mock(
        return_value=httpx.Response(200, text=AVAIL)
    )
    return respx.get(url__regex=r".*/api/area/csv/.*").mock(
        return_value=httpx.Response(200, text=(FIX / "modis_sp_sample.csv").read_text())
    )


def client(http: httpx.AsyncClient) -> FirmsClient:
    return FirmsClient("K", http=http, limiter=RateLimiter(1000), sleep=_nosleep)


@respx.mock
async def test_fetches_each_chunk_once_and_is_idempotent(tmp_path: Path) -> None:
    area = mock_api()
    cache = ParquetCache(tmp_path)
    async with httpx.AsyncClient() as http:
        c = client(http)
        first = await ingest(c, cache, ["MODIS_SP"], BBOX, date(2019, 10, 1), date(2019, 10, 30))
        n = area.call_count
        second = await ingest(c, cache, ["MODIS_SP"], BBOX, date(2019, 10, 1), date(2019, 10, 30))
    assert first["MODIS_SP"].fetched == n >= 3
    assert second["MODIS_SP"].fetched == 0
    assert second["MODIS_SP"].from_cache == n
    assert area.call_count == n  # nothing new requested


@respx.mock
async def test_clips_to_availability(tmp_path: Path) -> None:
    area = mock_api()
    async with httpx.AsyncClient() as http:
        stats = await ingest(
            client(http),
            ParquetCache(tmp_path),
            ["MODIS_SP"],
            BBOX,
            date(2019, 12, 1),
            date(2020, 1, 31),
        )
    assert area.call_count == 0
    assert stats["MODIS_SP"].unavailable > 0 and stats["MODIS_SP"].fetched == 0


@respx.mock
async def test_tail_chunk_is_partial_and_refetched(tmp_path: Path) -> None:
    area = mock_api()
    cache = ParquetCache(tmp_path)
    async with httpx.AsyncClient() as http:
        c = client(http)
        s1 = await ingest(c, cache, ["MODIS_SP"], BBOX, date(2019, 11, 10), date(2019, 11, 15))
        calls_after_first = area.call_count
        s2 = await ingest(c, cache, ["MODIS_SP"], BBOX, date(2019, 11, 10), date(2019, 11, 15))
    assert s1["MODIS_SP"].partial == 1
    assert area.call_count == calls_after_first + 1  # partial chunk fetched again
    assert s2["MODIS_SP"].partial == 1


@respx.mock
async def test_unknown_source_skipped_and_data_queryable(tmp_path: Path) -> None:
    mock_api()
    cache = ParquetCache(tmp_path)
    async with httpx.AsyncClient() as http:
        out = await ingest(
            client(http), cache, ["MODIS_SP", "NOPE"], BBOX, date(2019, 10, 28), date(2019, 11, 2)
        )
    assert list(out) == ["MODIS_SP"]
    df = HotspotStore(tmp_path).query(BBOX, date(2019, 11, 1), date(2019, 11, 1))
    assert df.height == 2


@respx.mock
async def test_max_requests_caps_work(tmp_path: Path) -> None:
    area = mock_api()
    async with httpx.AsyncClient() as http:
        await ingest(
            client(http),
            ParquetCache(tmp_path),
            ["MODIS_SP"],
            BBOX,
            date(2019, 1, 1),
            date(2019, 6, 30),
            max_requests=2,
        )
    assert area.call_count == 2
