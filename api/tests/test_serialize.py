import json
import math
from datetime import date

import numpy as np
import polars as pl

from emberline.pipeline import Analysis
from emberline.serialize import ACKNOWLEDGMENT, clean, methods_card, result_payload


def test_clean_handles_non_json_values() -> None:
    out = clean(
        {
            "nan": float("nan"),
            "inf": float("inf"),
            "np": np.float64(1.23456789),
            "i": np.int64(3),
            "d": date(2020, 1, 2),
            "arr": np.array([1.0, np.nan]),
            "ser": pl.Series([1.5, None]),
            "t": (1, 2),
            "zero": 0.0,
        }
    )
    assert out["nan"] is None and out["inf"] is None
    assert out["np"] == 1.235 and out["i"] == 3 and out["d"] == "2020-01-02"
    assert out["arr"] == [1.0, None] and out["ser"] == [1.5, None] and out["t"] == [1, 2]
    assert out["zero"] == 0.0
    json.dumps(out, allow_nan=False)  # strict JSON: must not raise


def test_payload_is_strict_json(analysis: Analysis) -> None:
    p = result_payload(analysis)
    text = json.dumps(p, allow_nan=False)
    assert "NaN" not in text and "Infinity" not in text
    assert len(text) < 8_000_000  # stays small enough to ship to a browser


def test_payload_sections(analysis: Analysis) -> None:
    p = result_payload(analysis)
    assert p["synthetic"] is True
    assert p["bbox"] == list(analysis.bbox)
    assert len(p["daily"]["dates"]) == len(p["daily"]["modis"]) == len(p["daily"]["viirs"])
    h = p["harmonized"]
    n = len(h["dates"])
    assert n == len(h["value"]) == len(h["lo"]) == len(h["hi"]) == len(h["reconstructed"])
    assert set(h["reconstructed"]) <= {0, 1} and 1 in h["reconstructed"]
    cal = p["calendar"]
    assert cal["days_per_year"] == 365 and len(cal["years"]) == len(cal["harmonized"])
    assert all(len(row) == 365 for row in cal["harmonized"])
    for key in ("lo", "hi", "modis", "viirs", "reconstructed"):
        assert len(cal[key]) == len(cal["years"])
    s = p["seasonality"]
    assert len(s["climatology"]["median"]) == 365 and s["markers"]["peak_doy"] > 0
    assert set(s["stl"]) == {"week", "trend", "seasonal", "resid"}


def test_validation_and_anomaly_text(analysis: Analysis) -> None:
    p = result_payload(analysis)
    v = p["validation"]
    norm = v["normalization"]
    assert norm["chosen"] == analysis.norm.chosen  # type: ignore[union-attr]
    assert {r["model"] for r in norm["cv"]} >= {"huber", "raw", "scale"}
    assert 0 <= v["overpass"]["modis_corroborated_by_viirs"] <= 1
    assert v["tables"]["by_frp"] and "frp_bin_i" not in v["tables"]["by_frp"][0]
    seasons = p["anomalies"]["seasons"]
    assert seasons[0]["season"] == "2013" and "robust standard deviations" in seasons[0]["text"]
    assert all("text" in e and e["direction"] in ("high", "low") for e in p["anomalies"]["events"])


def test_methods_card_is_reproducibility_info(analysis: Analysis) -> None:
    m = methods_card(analysis)
    assert m["quality_policy"]["modis_min_conf"] == 30
    assert m["grid"]["kind"] == "regular" and m["metric"] == "frp_sum_mw"
    assert m["model"]["chosen"] == analysis.norm.chosen  # type: ignore[union-attr]
    assert m["sources"]["modis"] == "SYNTHETIC_MODIS"
    assert {"python", "polars", "numpy", "scikit-learn", "statsmodels"} <= set(m["versions"])
    assert m["acknowledgment"] == ACKNOWLEDGMENT and "FIRMS" in ACKNOWLEDGMENT
    assert m["run_utc"].endswith("+00:00")


def test_no_nan_leaks_into_the_calendar(analysis: Analysis) -> None:
    cal = result_payload(analysis)["calendar"]["harmonized"]
    flat = [v for row in cal for v in row if v is not None]
    assert flat and all(math.isfinite(v) for v in flat)


def test_every_calendar_matrix_shares_one_year_axis(analysis: Analysis) -> None:
    cal = result_payload(analysis)["calendar"]
    n = len(cal["years"])
    for key in ("harmonized", "lo", "hi", "modis", "viirs", "reconstructed"):
        assert len(cal[key]) == n, key
    first = cal["years"].index(2010)  # VIIRS does not exist yet in 2010 here
    assert all(v is None for v in cal["viirs"][first])
    assert any(v is not None for v in cal["modis"][first])
    assert cal["years"] == sorted(cal["years"])


def test_normalisation_pairs_expose_out_of_fold_predictions(analysis: Analysis) -> None:
    norm = result_payload(analysis)["validation"]["normalization"]
    pairs = norm["pairs"]
    assert len(pairs) == norm["n_weeks"]
    assert {"week", "modis", "viirs", "predicted", "lo", "hi"} <= set(pairs[0])
    assert all(p["lo"] <= p["predicted"] <= p["hi"] for p in pairs if p["predicted"] is not None)
    inside = sum(p["lo"] <= p["viirs"] <= p["hi"] for p in pairs) / len(pairs)
    assert inside > 0.8  # held-out weeks fall inside the nominal 90% band most of the time
