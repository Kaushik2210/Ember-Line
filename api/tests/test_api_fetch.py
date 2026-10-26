"""Live-fetch stage of an analysis job, with the FIRMS API mocked."""

import json
import time
from datetime import date
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from emberline.config import Settings
from emberline.data.coverage import load_availability
from emberline.main import create_app

AVAIL = (
    "data_id,min_date,max_date\n"
    "MODIS_SP,2000-11-01,2026-07-31\n"
    "VIIRS_SNPP_SP,2012-01-20,2026-06-30\n"
)
BODY = {"bbox": [10.1, 5.2, 11.3, 6.4], "start": "2018-01-01", "end": "2019-06-30"}


def wait(c: TestClient, jid: str) -> dict:  # type: ignore[type-arg]
    t0 = time.time()
    while time.time() - t0 < 60:
        s = c.get(f"/api/jobs/{jid}").json()
        if s["status"] in ("done", "error"):
            return s  # type: ignore[no-any-return]
        time.sleep(0.1)
    raise AssertionError("timeout")


def mock_firms(rows: str = "") -> tuple[respx.Route, respx.Route]:
    respx.get(url__regex=r".*mapkey_status.*").mock(
        return_value=httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":0}')
    )
    av = respx.get(url__regex=r".*data_availability.*").mock(
        return_value=httpx.Response(200, text=AVAIL)
    )
    area = respx.get(url__regex=r".*/api/area/csv/.*").mock(
        return_value=httpx.Response(200, text="latitude,longitude,acq_date,acq_time\n")
    )
    return av, area


@respx.mock
def test_uncached_area_is_fetched_with_progress_then_reported_cleanly(tmp_path: Path) -> None:
    av, area = mock_firms()
    app = create_app(Settings(firms_map_key="TESTKEY", data_dir=tmp_path))
    with TestClient(app) as c:
        jid = c.post("/api/analyze", json=BODY).json()["job_id"]
        s = wait(c, jid)
        with c.stream("GET", f"/api/jobs/{jid}/events") as r:
            text = "".join(r.iter_text())
    stages = [json.loads(x[5:])["stage"] for x in text.splitlines() if x.startswith("data:")]
    assert any(st.startswith("Fetching MODIS_SP") for st in stages)
    assert any(st.startswith("Fetching VIIRS_SNPP_SP") for st in stages)
    assert area.call_count > 10
    assert (
        s["status"] == "error" and "No hotspot data" in s["error"]
    )  # the mock returns no hotspots
    assert load_availability(tmp_path)["MODIS_SP"][0] == date(2000, 11, 1)  # saved for offline use


@respx.mock
def test_second_run_does_not_refetch_cached_chunks(tmp_path: Path) -> None:
    _, area = mock_firms()
    app = create_app(Settings(firms_map_key="TESTKEY", data_dir=tmp_path))
    with TestClient(app) as c:
        wait(c, c.post("/api/analyze", json=BODY).json()["job_id"])
        first = area.call_count
        other = {**BODY, "metric": "active_1km"}  # a different job over the same data
        wait(c, c.post("/api/analyze", json=other).json()["job_id"])
    assert area.call_count == first


@respx.mock
def test_a_box_inside_a_cached_area_needs_no_download(tmp_path: Path) -> None:
    _, area = mock_firms()
    app = create_app(Settings(firms_map_key="TESTKEY", data_dir=tmp_path))
    with TestClient(app) as c:
        wait(c, c.post("/api/analyze", json=BODY).json()["job_id"])
        calls = area.call_count
        inside = {**BODY, "bbox": [10.4, 5.5, 10.9, 6.0]}
        wait(c, c.post("/api/analyze", json=inside).json()["job_id"])
    assert area.call_count == calls


@respx.mock
def test_request_cap_stops_a_huge_fetch(tmp_path: Path) -> None:
    _, area = mock_firms()
    app = create_app(Settings(firms_map_key="TESTKEY", data_dir=tmp_path))
    big = {**BODY, "start": "2005-01-01", "end": "2025-12-31"}  # thousands of requests
    with TestClient(app) as c:
        s = wait(c, c.post("/api/analyze", json=big).json()["job_id"])
    assert s["status"] == "error" and "limit" in s["error"] and "preset" in s["error"]
    assert area.call_count == 0


@respx.mock
def test_no_key_and_no_cache_explains_how_to_get_data(tmp_path: Path) -> None:
    app = create_app(Settings(firms_map_key="", data_dir=tmp_path))
    with TestClient(app) as c:
        s = wait(c, c.post("/api/analyze", json=BODY).json()["job_id"])
    assert s["status"] == "error"
    assert "not cached" in s["error"] or "No hotspot data" in s["error"]


@respx.mock
def test_firms_failure_becomes_a_friendly_error(tmp_path: Path) -> None:
    respx.get(url__regex=r".*data_availability.*").mock(
        return_value=httpx.Response(200, text=AVAIL)
    )
    respx.get(url__regex=r".*mapkey_status.*").mock(
        return_value=httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":0}')
    )
    respx.get(url__regex=r".*/api/area/csv/.*").mock(return_value=httpx.Response(404, text="gone"))
    app = create_app(Settings(firms_map_key="TESTKEY", data_dir=tmp_path))
    with TestClient(app) as c:
        s = wait(c, c.post("/api/analyze", json=BODY).json()["job_id"])
    # chunk failures are skipped (retried next run); the job then reports there is no data
    assert s["status"] == "error" and "TESTKEY" not in json.dumps(s)
