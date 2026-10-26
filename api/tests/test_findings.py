import json
from datetime import date

from emberline.findings import busiest_observed_day, findings, overlap_totals
from emberline.pipeline import Analysis
from emberline.serialize import result_payload


def test_overlap_totals_only_count_days_both_sensors_observed() -> None:
    daily = {"modis": [10, 20, None, 30], "viirs": [None, 50, 70, 90]}
    assert overlap_totals(daily) == {"days": 2, "modis_total": 50, "viirs_total": 140, "ratio": 2.8}
    assert overlap_totals({"modis": [0], "viirs": [4]})["ratio"] is None
    assert overlap_totals({"modis": [], "viirs": []})["days"] == 0


def test_busiest_day_prefers_observed_over_reconstructed() -> None:
    p = {
        "harmonized": {
            "dates": ["2012-01-01", "2012-01-02", "2012-01-03"],
            "value": [100, 5, 40],
            "reconstructed": [1, 0, 0],
        }
    }
    assert busiest_observed_day(p) == "2012-01-03"
    assert busiest_observed_day({"harmonized": None}) is None


def test_findings_come_from_the_payload(analysis: Analysis) -> None:
    payload = result_payload(analysis)
    f = findings(payload)
    json.dumps(f, allow_nan=False)  # strict json: it is served over the api
    assert f["synthetic"] is True and f["metric"] == "frp_sum_mw"
    assert f["years"] == [2010, 2020]
    assert f["overlap"]["ratio"] and f["overlap"]["days"] > 1000
    n = f["normalization"]
    assert n["chosen"] == analysis.norm.chosen  # type: ignore[union-attr]
    assert n["after"]["mae_log"] < n["before"]["mae_log"]
    assert abs(n["after"]["bias_rel"]) < abs(n["before"]["bias_rel"])
    assert n["band_factor"] > 1 and n["n_weeks"] > 100
    assert f["overpass"]["modis_seen_by_viirs"] is not None
    assert 0 < f["reconstructed_share"] < 1  # VIIRS only exists from 2014 in the fixture
    assert f["top_season"]["season"] == "2013"
    assert date.fromisoformat(f["busiest_day"]).year >= 2014  # a day VIIRS observed
    assert f["segments"] and len(f["top_events"]) <= 3
    assert all("text" in e for e in f["top_events"])


def test_findings_degrade_when_nothing_was_fitted(analysis: Analysis) -> None:
    payload = result_payload(analysis)
    payload["validation"]["normalization"] = None
    payload["validation"]["overpass"] = {}
    payload["harmonized"] = None
    payload["anomalies"] = {"events": [], "seasons": []}
    f = findings(payload)
    assert f["normalization"] is None and f["overpass"] is None
    assert f["busiest_day"] is None and f["top_season"] is None and f["top_events"] == []
    assert f["reconstructed_share"] is None
