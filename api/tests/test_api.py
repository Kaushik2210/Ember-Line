import csv
import io
import json
import time
from collections.abc import Iterator
from datetime import date

import pytest
from conftest import BBOX, END, START
from fastapi.testclient import TestClient

from emberline.config import Settings
from emberline.data.store import HotspotStore
from emberline.main import create_app

BODY = {
    "bbox": list(BBOX),
    "start": START.isoformat(),
    "end": END.isoformat(),
    "synthetic": True,
}


@pytest.fixture(scope="module")
def client(store: HotspotStore) -> Iterator[TestClient]:
    app = create_app(
        Settings(firms_map_key="", data_dir=store.root, web_origin="http://localhost:3000")
    )
    with TestClient(app) as c:
        yield c


def wait_done(c: TestClient, job_id: str, timeout: float = 120.0) -> dict:  # type: ignore[type-arg]
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = c.get(f"/api/jobs/{job_id}").json()
        if s["status"] in ("done", "error"):
            return s  # type: ignore[no-any-return]
        time.sleep(0.2)
    raise AssertionError("job did not finish")


@pytest.fixture(scope="module")
def job(client: TestClient) -> str:
    r = client.post("/api/analyze", json=BODY)
    assert r.status_code == 202
    jid = r.json()["job_id"]
    assert wait_done(client, jid)["status"] == "done"
    return jid  # type: ignore[no-any-return]


def test_health_regions_availability(client: TestClient) -> None:
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["firms_key_configured"] is False
    regions = client.get("/api/regions").json()
    assert len(regions) == 8 and {"id", "name", "bbox", "blurb"} <= set(regions[0])
    assert "sources" in client.get("/api/availability").json()


def test_openapi_docs_are_enabled(client: TestClient) -> None:
    assert client.get("/api/openapi.json").status_code == 200
    paths = client.get("/api/openapi.json").json()["paths"]
    assert {"/api/analyze", "/api/jobs/{job_id}/result", "/api/hotspots", "/api/export"} <= set(
        paths
    )


def test_job_result_is_json_with_the_expected_sections(client: TestClient, job: str) -> None:
    r = client.get(f"/api/jobs/{job}/result")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    p = r.json()
    for key in (
        "meta",
        "harmonized",
        "calendar",
        "seasonality",
        "anomalies",
        "validation",
        "quality",
    ):
        assert key in p
    assert p["synthetic"] is True and any("SYNTHETIC" in n for n in p["quality"]["notes"])


def test_same_request_is_idempotent_and_served_from_cache(client: TestClient, job: str) -> None:
    r = client.post("/api/analyze", json=BODY)
    assert r.json()["job_id"] == job and r.json()["cached"] is True
    other = client.post("/api/analyze", json={**BODY, "metric": "active_1km"})
    assert other.json()["job_id"] != job


def test_progress_events_are_streamed_and_end_with_done(client: TestClient, job: str) -> None:
    with client.stream("GET", f"/api/jobs/{job}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        text = "".join(r.iter_text())
    assert "event: done" in text
    datas = [json.loads(line[5:]) for line in text.splitlines() if line.startswith("data:")]
    assert datas and datas[-1]["status"] == "done"


def test_progress_has_stage_names_for_a_fresh_run(client: TestClient) -> None:
    body = {**BODY, "model": "isotonic"}  # a different request, so it runs and streams live
    jid = client.post("/api/analyze", json=body).json()["job_id"]
    with client.stream("GET", f"/api/jobs/{jid}/events") as r:
        text = "".join(r.iter_text())
    stages = [json.loads(x[5:])["stage"] for x in text.splitlines() if x.startswith("data:")]
    assert "Loading hotspots" in stages and "Fitting normalisation models" in stages
    assert stages[-1] == "done"
    res = client.get(f"/api/jobs/{jid}/result").json()
    assert res["validation"]["normalization"]["chosen"] == "isotonic"


def test_polygon_request_runs(client: TestClient) -> None:
    ring = [[74.0, 29.0], [76.0, 29.0], [76.0, 32.0], [74.0, 32.0], [74.0, 29.0]]
    body = {k: v for k, v in BODY.items() if k != "bbox"}
    body["geojson"] = {"type": "Polygon", "coordinates": [ring]}
    jid = client.post("/api/analyze", json=body).json()["job_id"]
    assert wait_done(client, jid)["status"] == "done"
    assert client.get(f"/api/jobs/{jid}/result").json()["bbox"] == [74.0, 29.0, 76.0, 32.0]


def test_friendly_validation_errors(client: TestClient) -> None:
    both = client.post("/api/analyze", json={**BODY, "region_id": "california"})
    assert both.status_code == 422 and "exactly one" in both.text
    none = client.post("/api/analyze", json={k: v for k, v in BODY.items() if k != "bbox"})
    assert none.status_code == 422
    big = client.post("/api/analyze", json={**BODY, "bbox": [-100, -50, 100, 50]})
    assert big.status_code == 422 and "square degrees" in big.json()["detail"]
    short = client.post("/api/analyze", json={**BODY, "end": "2010-03-01"})
    assert short.status_code == 422 and "at least one year" in short.json()["detail"]
    unknown = client.post(
        "/api/analyze",
        json={**{k: v for k, v in BODY.items() if k != "bbox"}, "region_id": "atlantis"},
    )
    assert unknown.status_code == 422
    assert client.get("/api/jobs/doesnotexist/result").status_code == 404
    assert client.get("/api/jobs/doesnotexist").status_code == 404


def test_missing_real_data_ends_in_a_clear_error_not_a_crash(client: TestClient) -> None:
    jid = client.post("/api/analyze", json={**BODY, "synthetic": False}).json()["job_id"]
    s = wait_done(client, jid)
    assert s["status"] == "error" and "cached" in s["error"]
    r = client.get(f"/api/jobs/{jid}/result")
    assert r.status_code == 422 and "cached" in r.json()["detail"]


def test_hotspots_endpoint(client: TestClient, store: HotspotStore) -> None:
    df = store.query(BBOX, date(2017, 1, 1), date(2017, 12, 31), synthetic=True)
    day = df.group_by("local_date").len().sort("len").row(-1)[0]
    r = client.get(
        "/api/hotspots",
        params={"bbox": ",".join(map(str, BBOX)), "start": day.isoformat(), "synthetic": "true"},
    )
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/geo+json")
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and fc["features"]
    agg = client.get(
        "/api/hotspots",
        params={
            "bbox": ",".join(map(str, BBOX)),
            "start": "2017-06-01",
            "end": "2017-06-07",
            "synthetic": "true",
            "max_features": 100,
        },
    )
    assert agg.status_code == 200
    assert agg.json()["properties"]["aggregated"] is True
    assert len(agg.json()["features"]) <= 100


def test_hotspots_bad_input(client: TestClient) -> None:
    assert (
        client.get("/api/hotspots", params={"bbox": "1,2,3", "start": "2017-01-01"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/hotspots", params={"bbox": "-100,-50,100,50", "start": "2017-01-01"}
        ).status_code
        == 422
    )
    too_long = {"bbox": ",".join(map(str, BBOX)), "start": "2017-01-01", "end": "2017-02-01"}
    assert client.get("/api/hotspots", params=too_long).status_code == 422


def test_exports(client: TestClient, job: str) -> None:
    c = client.get("/api/export", params={"job_id": job, "format": "csv"})
    assert c.status_code == 200 and "attachment" in c.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(c.text)))
    assert rows[0] == ["date", "harmonized", "lo", "hi", "reconstructed", "modis_raw", "viirs_raw"]
    assert len(rows) > 3000
    assert {r[4] for r in rows[1:]} <= {"0", "1"}
    g = client.get("/api/export", params={"job_id": job, "format": "geojson"}).json()
    assert g["type"] == "FeatureCollection" and g["features"][0]["geometry"]["type"] == "Polygon"
    assert "FIRMS" in g["features"][0]["properties"]["acknowledgment"]
    m = client.get("/api/export", params={"job_id": job, "format": "methods"}).json()
    assert (
        m["quality_policy"]["modis_min_conf"] == 30 and "versions" in m and m["synthetic"] is True
    )
    assert client.get("/api/export", params={"job_id": job, "format": "pdf"}).status_code == 422
    assert client.get("/api/export", params={"job_id": "nope", "format": "csv"}).status_code == 404


def test_cors_is_locked_to_the_web_origin(client: TestClient) -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_results_survive_a_restart(store: HotspotStore, job: str) -> None:
    app = create_app(Settings(firms_map_key="", data_dir=store.root))
    with TestClient(app) as fresh:  # new process state: only the disk cache remains
        s = fresh.get(f"/api/jobs/{job}").json()
        assert s["status"] == "done" and s["cached"] is True
        assert fresh.get(f"/api/jobs/{job}/result").json()["synthetic"] is True
