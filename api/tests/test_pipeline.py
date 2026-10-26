from datetime import date
from pathlib import Path

import polars as pl
import pytest

from emberline.data.store import HotspotStore
from emberline.data.synthetic import generate_synthetic, write_synthetic
from emberline.pipeline import AnalysisError, run_analysis

BBOX = (74.0, 29.0, 77.0, 32.0)
START, END = date(2010, 1, 1), date(2020, 12, 31)
VIIRS_FROM = date(2014, 1, 1)


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> HotspotStore:
    root = tmp_path_factory.mktemp("syn")
    df = generate_synthetic(BBOX, START, END, seed=3)
    # VIIRS only flies from 2014 here, so 2010-2013 must be reconstructed from MODIS
    df = df.filter((pl.col("sensor") == "modis") | (pl.col("local_date") >= VIIRS_FROM))
    write_synthetic(root, df)
    return HotspotStore(root)


@pytest.fixture(scope="module")
def analysis(store: HotspotStore):  # type: ignore[no-untyped-def]
    stages: list[str] = []
    a = run_analysis(store, BBOX, START, END, synthetic=True, progress=stages.append)
    a.stages = stages  # type: ignore[attr-defined]
    return a


def test_stages_are_reported(analysis) -> None:  # type: ignore[no-untyped-def]
    s = analysis.stages
    assert s[0] == "Loading hotspots"
    assert any(x.startswith("Matching overpasses") for x in s)
    assert "Fitting normalisation models" in s and "Harmonising the record" in s


def test_synthetic_is_flagged_in_notes(analysis) -> None:  # type: ignore[no-untyped-def]
    assert analysis.synthetic
    assert any("SYNTHETIC" in n for n in analysis.notes)


def test_normalisation_beats_raw(analysis) -> None:  # type: ignore[no-untyped-def]
    cv = {r["model"]: r for r in analysis.norm.cv.iter_rows(named=True)}
    chosen = cv[analysis.norm.chosen]
    assert chosen["mae_log"] < cv["raw"]["mae_log"]
    assert abs(chosen["bias_rel"]) < abs(cv["raw"]["bias_rel"])


def test_reconstruction_covers_the_modis_only_years(analysis) -> None:  # type: ignore[no-untyped-def]
    h = analysis.harmonized
    early = h.filter(pl.col("local_date") < VIIRS_FROM)
    late = h.filter(pl.col("local_date") >= VIIRS_FROM)
    assert early["reconstructed"].all() and not late["reconstructed"].any()
    rec = early.drop_nulls("harmonized")
    assert rec.height > 0.9 * early.height
    assert (rec["lo"] <= rec["harmonized"]).all() and (rec["harmonized"] <= rec["hi"]).all()
    assert any("reconstructed" in n for n in analysis.notes)


def test_overpass_summary_and_tables(analysis) -> None:  # type: ignore[no-untyped-def]
    o = analysis.overpass
    assert o["n_modis_eval"] > 0 and o["n_viirs_eval"] > 0
    assert 0 <= o["modis_corroborated_by_viirs"] <= 1
    # VIIRS sees small fires MODIS cannot, so fewer VIIRS pixels are corroborated
    assert o["viirs_corroborated_by_modis"] < o["modis_corroborated_by_viirs"]
    assert analysis.frp_ratio["median_viirs_over_modis"] > 0
    assert analysis.overpass_tables["by_frp"].height > 0
    assert analysis.overpass_tables["by_daynight"].height > 0


def test_seasonality_and_extreme_year_found(analysis) -> None:  # type: ignore[no-untyped-def]
    assert analysis.markers is not None
    assert analysis.markers.start_doy < analysis.markers.peak_doy < analysis.markers.end_doy
    assert analysis.climatology is not None and analysis.climatology.height == 365
    # the generator injects an extreme season in start.year + 3 (a reconstructed year)
    assert analysis.seasons["season"][0] == "2013"
    assert analysis.seasons["z"][0] > 3
    assert any(e.start.year == 2013 and e.direction == "high" for e in analysis.events)


def test_quality_counts(analysis) -> None:  # type: ignore[no-untyped-def]
    c = analysis.counts
    assert c["raw"] >= c["kept"] > 0
    assert c["modis_kept"] > 0 and c["viirs_kept"] > 0


def test_no_data_is_a_friendly_error(tmp_path: Path) -> None:
    with pytest.raises(AnalysisError, match="No hotspot data"):
        run_analysis(HotspotStore(tmp_path), BBOX, START, END, synthetic=True)


def test_missing_sensor_is_a_friendly_error(tmp_path: Path) -> None:
    df = generate_synthetic(BBOX, START, date(2012, 12, 31), seed=1).filter(
        pl.col("sensor") == "modis"
    )
    write_synthetic(tmp_path, df)
    with pytest.raises(AnalysisError, match="VIIRS"):
        run_analysis(HotspotStore(tmp_path), BBOX, START, date(2012, 12, 31), synthetic=True)


def test_short_record_degrades_gracefully(tmp_path: Path) -> None:
    df = generate_synthetic(BBOX, date(2018, 1, 1), date(2018, 12, 31), seed=1)
    write_synthetic(tmp_path, df)
    a = run_analysis(
        HotspotStore(tmp_path), BBOX, date(2018, 1, 1), date(2018, 12, 31), synthetic=True
    )
    assert a.norm is None and a.harmonized is None
    assert any("Normalisation not fitted" in n for n in a.notes)


def test_report_renders_every_section_from_computed_numbers(analysis, store) -> None:  # type: ignore[no-untyped-def]
    from emberline.report import report

    text = report(analysis, "Test region", store.coverage(synthetic=True))
    for heading in (
        "SYNTHETIC DATA",
        "## 1. The sensors disagree",
        "## 2. Coincident overpasses",
        "## 3. Normalisation",
        "## 4. Harmonised record",
        "## 5. Seasonality",
        "## 6. Most unusual seasons",
        "## Notes",
    ):
        assert heading in text, heading
    assert analysis.norm.chosen in text
    assert "VIIRS / MODIS over all overlap weeks" in text
    assert "nan" not in text.lower().replace("nominal", "")


def test_md_does_not_put_separators_in_years() -> None:
    from emberline.report import md

    t = md(pl.DataFrame({"year": [2012], "weeks": [31], "frp": [1234.5], "n": [12345]}))
    assert "| 2012 |" in t and "12,345" in t and "1,234.500" in t


def test_terra_only_note_needs_a_real_gap() -> None:
    from emberline.pipeline import _data_notes

    def frame(terra_first: date, aqua_first: date) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "sensor": ["modis", "modis"],
                "platform": ["Terra", "Aqua"],
                "local_date": [terra_first, aqua_first],
            }
        )

    daily = pl.DataFrame({"local_date": [date(2012, 6, 1)], "modis": [1.0], "viirs": [1.0]})
    counts = {"persistent_cells": 0}
    quiet = _data_notes(frame(date(2012, 6, 1), date(2012, 6, 2)), daily, counts, False)
    assert not any("Terra" in n for n in quiet)
    real = _data_notes(frame(date(2001, 1, 1), date(2002, 7, 4)), daily, counts, False)
    assert any("Terra alone before 2002-07-04" in n for n in real)


def test_timeline_comes_from_data_and_synthetic_has_no_nasa_events(analysis) -> None:  # type: ignore[no-untyped-def]
    assert analysis.platforms.height >= 2
    assert set(analysis.platforms["sensor"]) == {"modis", "viirs"}
    # synthetic data must not be annotated with real satellite history
    assert analysis.annotations == []


def test_real_run_gets_documented_events(tmp_path: Path) -> None:
    # real-source naming on tiny hand-made data is not needed: check the selection logic
    from emberline.annotations import annotations_for

    titles = [e.title for e in annotations_for(date(2012, 1, 1), date(2024, 1, 1))]
    assert "Terra's last inclination maneuver; orbit drift begins" in titles


def test_stl_is_computed_on_the_harmonised_weekly_series(analysis) -> None:  # type: ignore[no-untyped-def]
    s = analysis.stl
    assert s is not None and s.height > 104
    assert set(s.columns) == {"week", "trend", "seasonal", "resid"}
    assert (
        s["seasonal"].max() - s["seasonal"].min() > 1.0
    )  # clear yearly cycle in the synthetic data
