"""The showcase endpoint on a store that holds real-source-named data for one region."""

import json
import time
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from emberline.config import Settings
from emberline.data.cache import ParquetCache
from emberline.data.chunking import date_chunks
from emberline.data.coverage import save_availability
from emberline.data.firms import Availability
from emberline.data.synthetic import generate_synthetic
from emberline.main import create_app
from emberline.regions import REGIONS, get_region

START, END = date(2012, 1, 1), date(2018, 12, 31)


@pytest.fixture(scope="module")
def store_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Synthetic detections stored under the real source names, so the real-data path is exercised."""
    root = tmp_path_factory.mktemp("showcase")
    region = get_region("punjab-haryana")
    df = generate_synthetic(region.bbox, START, END, seed=5)
    df = df.filter((pl.col("sensor") == "modis") | (pl.col("local_date") >= date(2014, 1, 1)))
    df = df.with_columns(
        pl.when(pl.col("sensor") == "modis")
        .then(pl.lit("MODIS_SP"))
        .otherwise(pl.lit("VIIRS_SNPP_SP"))
        .alias("source"),
        pl.lit(False).alias("synthetic"),
    )
    cache = ParquetCache(root)
    tile = "73.8_28.4_77.6_32.5"
    for src in ("MODIS_SP", "VIIRS_SNPP_SP"):
        part = df.filter(pl.col("source") == src)
        first = date(2012, 1, 1) if src == "MODIS_SP" else date(2014, 1, 1)
        for ch in date_chunks(first, END):
            sel = part.filter(pl.col("local_date").is_between(ch.start, ch.end))
            cache.write(sel, src, tile, ch.start)
    save_availability(
        root,
        {
            "MODIS_SP": Availability("MODIS_SP", START, END),
            "VIIRS_SNPP_SP": Availability("VIIRS_SNPP_SP", date(2014, 1, 1), END),
        },
    )
    return root


@pytest.fixture()
def client(store_root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for r in REGIONS:  # short default periods keep the test quick
        monkeypatch.setattr(r, "default_start", "2012-01-01")
        monkeypatch.setattr(r, "default_end", "2018-12-31")
    return TestClient(create_app(Settings(firms_map_key="", data_dir=store_root)))


def poll(c: TestClient, region: str = "punjab-haryana", timeout: float = 180.0) -> dict:  # type: ignore[type-arg]
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = {r["id"]: r for r in c.get("/api/showcase").json()}
        if rows[region]["state"] in ("ready", "unavailable"):
            return rows  # type: ignore[no-any-return]
        time.sleep(0.5)
    raise AssertionError("showcase did not settle")


def test_a_cached_region_is_ready_with_computed_findings(client: TestClient) -> None:
    with client:
        rows = poll(client)
    p = rows["punjab-haryana"]
    assert p["state"] == "ready" and p["job_id"] and p["reason"] is None
    f = p["findings"]
    json.dumps(f, allow_nan=False)
    assert f["synthetic"] is False  # real source names, not the synthetic path
    assert f["overlap"]["ratio"] and f["normalization"]["chosen"]
    assert f["years"][0] == 2012


def test_regions_without_data_are_unavailable_with_a_reason_and_nothing_is_downloaded(
    client: TestClient,
) -> None:
    with client:
        rows = poll(client)
        # settle every region, then check the others
        for _ in range(240):
            rows = {r["id"]: r for r in client.get("/api/showcase").json()}
            if all(r["state"] != "computing" for r in rows.values()):
                break
            time.sleep(0.5)
    others = [r for k, r in rows.items() if k != "punjab-haryana"]
    assert others and all(r["state"] == "unavailable" for r in others), {
        r["id"]: (r["state"], r["reason"]) for r in others
    }
    assert all(r["reason"] for r in others)
    assert all(r["findings"] is None for r in others)
    assert len(rows) == len(REGIONS)


def test_listing_has_the_preset_details(client: TestClient) -> None:
    with client:
        rows = client.get("/api/showcase").json()
    assert {r["id"] for r in rows} == {r.id for r in REGIONS}
    assert all({"name", "bbox", "blurb", "start", "end", "state"} <= set(r) for r in rows)
