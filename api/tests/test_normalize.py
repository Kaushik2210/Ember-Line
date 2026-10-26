from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from emberline.science.normalize import (
    EXTRAPOLATION_WIDEN,
    HuberLogLog,
    IsotonicMap,
    QuantileMapping,
    TheilSenLogLog,
    fit_normalizer,
    harmonize,
    season_of,
)


def make_pairs(n_years: int = 9, seed: int = 0) -> pl.DataFrame:
    """Weekly pairs with a known relation: VIIRS = 0.4 * MODIS^0.92 with multiplicative noise."""
    rng = np.random.default_rng(seed)
    weeks = [date(2012, 1, 2) + timedelta(weeks=i) for i in range(52 * n_years)]
    doy = np.array([w.timetuple().tm_yday for w in weeks])
    x = np.exp(4.0 * np.cos(2 * np.pi * (doy - 200) / 365.25)) * rng.lognormal(0, 0.4, len(weeks))
    y = 0.4 * x**0.92 * rng.lognormal(0, 0.15, len(weeks))
    return pl.DataFrame({"week": weeks, "modis": x, "viirs": y})


@pytest.fixture(scope="module")
def pairs() -> pl.DataFrame:
    return make_pairs()


@pytest.fixture(scope="module")
def result(pairs: pl.DataFrame):  # type: ignore[no-untyped-def]
    return fit_normalizer(pairs, metric="test")


def test_cv_table_has_models_and_baselines(result) -> None:  # type: ignore[no-untyped-def]
    assert set(result.cv["model"]) == {"huber", "theilsen", "quantile", "isotonic", "raw", "scale"}
    assert result.chosen in {"huber", "theilsen", "quantile", "isotonic"}
    assert result.years == list(range(2012, 2021))


def test_chosen_beats_baselines(result) -> None:  # type: ignore[no-untyped-def]
    cv = {r["model"]: r for r in result.cv.iter_rows(named=True)}
    best = cv[result.chosen]
    assert best["mae_log"] < cv["raw"]["mae_log"]
    assert best["mae_log"] < cv["scale"]["mae_log"]
    assert best["r2_log"] > 0.9
    assert abs(best["bias_rel"]) < 0.15
    assert abs(cv["raw"]["bias_rel"]) > 0.5  # without normalisation MODIS is far off VIIRS


def test_interval_coverage_close_to_nominal(result) -> None:  # type: ignore[no-untyped-def]
    cov = result.cv.filter(pl.col("model") == result.chosen)["coverage"][0]
    assert 0.8 <= cov <= 1.0


def test_predictions_recover_truth(pairs: pl.DataFrame, result) -> None:  # type: ignore[no-untyped-def]
    weeks = pairs["week"].to_list()
    val, lo, hi = result.predict_weekly(pairs["modis"].to_numpy(), weeks)
    truth = pairs["viirs"].to_numpy()
    assert np.median(np.abs(val - truth) / truth) < 0.2
    assert np.all(lo <= val) and np.all(val <= hi)
    inside = ((truth >= lo) & (truth <= hi)).mean()
    assert inside > 0.8


@pytest.mark.parametrize(
    "model", [HuberLogLog(), TheilSenLogLog(), QuantileMapping(), IsotonicMap()]
)
def test_each_model_is_monotone_and_sane(pairs: pl.DataFrame, model) -> None:  # type: ignore[no-untyped-def]
    u = np.log1p(pairs["modis"].to_numpy())
    v = np.log1p(pairs["viirs"].to_numpy())
    season = season_of(pairs["week"].to_list())
    m = type(model)().fit(u, v, season)
    grid = np.linspace(0, u.max() * 1.2, 80)
    one_season = np.full(len(grid), 2)
    pred = m.predict(grid, one_season)
    assert np.all(np.diff(pred) >= -1e-9), f"{model.name} not monotone"
    assert np.all(pred >= 0)
    mid = np.argsort(u)[len(u) // 2]
    assert abs(m.predict(u[[mid]], season[[mid]])[0] - v[mid]) < 1.5


def test_quantile_mapping_matches_distribution() -> None:
    rng = np.random.default_rng(3)
    u = rng.uniform(0, 5, 400)
    v = 0.5 * u
    season = np.zeros(400, dtype=np.int64)
    m = QuantileMapping().fit(u, v, season)
    out = m.predict(u, season)
    assert np.allclose(np.sort(out), np.sort(v), atol=0.05)


def test_extrapolation_widens_the_band(result) -> None:  # type: ignore[no-untyped-def]
    w = [date(2030, 7, 1)]
    inside = result.predict_weekly(np.array([result.fit_u_max * 0 + 10.0]), w)
    beyond = result.predict_weekly(np.array([np.expm1(result.fit_u_max) * 5]), w)
    ratio_in = np.log1p(inside[2][0]) - np.log1p(inside[1][0])
    ratio_out = np.log1p(beyond[2][0]) - np.log1p(beyond[1][0])
    assert ratio_out == pytest.approx(ratio_in * EXTRAPOLATION_WIDEN, rel=0.05)


def test_validation_of_inputs() -> None:
    with pytest.raises(ValueError, match="at least 40"):
        fit_normalizer(make_pairs().head(20))
    two_years = make_pairs(n_years=2)
    with pytest.raises(ValueError, match="3 distinct years"):
        fit_normalizer(two_years)


def daily_frame(modis_start: date, viirs_start: date, end: date, seed: int = 1) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    days = [modis_start + timedelta(days=i) for i in range((end - modis_start).days + 1)]
    doy = np.array([d.timetuple().tm_yday for d in days])
    m = np.exp(2.5 * np.cos(2 * np.pi * (doy - 200) / 365.25)) * rng.lognormal(0, 0.3, len(days))
    v = [0.4 * a**0.92 if d >= viirs_start else None for a, d in zip(m, days, strict=True)]
    return pl.DataFrame({"local_date": days, "modis": m, "viirs": v}, strict=False).with_columns(
        pl.col("viirs").cast(pl.Float64)
    )


def test_harmonize_flags_reconstruction_and_passes_viirs_through(
    pairs: pl.DataFrame, result
) -> None:  # type: ignore[no-untyped-def]
    d = daily_frame(date(2009, 1, 5), date(2012, 1, 2), date(2013, 12, 29))
    h = harmonize(d, result)
    assert h.height == d.height
    early, late = (
        h.filter(pl.col("local_date") < date(2012, 1, 2)),
        h.filter(pl.col("local_date") >= date(2012, 1, 2)),
    )
    assert early["reconstructed"].all() and not late["reconstructed"].any()
    assert (late["harmonized"] == late["viirs_raw"]).all()
    assert (late["lo"] == late["hi"]).all()
    rec = early.drop_nulls("harmonized")
    assert rec.height > 0.95 * early.height  # only a possible partial week at the edges is null
    assert (rec["lo"] <= rec["harmonized"]).all() and (rec["harmonized"] <= rec["hi"]).all()


def test_harmonize_weekly_total_equals_model_and_keeps_daily_shape(result) -> None:  # type: ignore[no-untyped-def]
    d = daily_frame(date(2009, 1, 5), date(2030, 1, 1), date(2009, 3, 1))
    h = harmonize(d, result)
    week = h.filter(pl.col("local_date").is_between(date(2009, 1, 12), date(2009, 1, 18)))
    w_modis = float(week["modis_raw"].sum())
    expected, _, _ = result.predict_weekly(np.array([w_modis]), [date(2009, 1, 12)])
    assert float(week["harmonized"].sum()) == pytest.approx(float(expected[0]), rel=1e-9)
    ratio = (week["harmonized"] / week["modis_raw"]).to_numpy()
    assert np.allclose(ratio, ratio[0])  # same factor every day: MODIS's within-week shape kept


def test_harmonize_zero_modis_week_spreads_uniformly(result) -> None:  # type: ignore[no-untyped-def]
    days = [date(2009, 1, 5) + timedelta(days=i) for i in range(14)]
    d = pl.DataFrame(
        {"local_date": days, "modis": [0.0] * 14, "viirs": [None] * 14},
        schema={"local_date": pl.Date, "modis": pl.Float64, "viirs": pl.Float64},
    )
    h = harmonize(d, result)
    first = h.filter(pl.col("local_date") < date(2009, 1, 12))["harmonized"]
    expected, _, _ = result.predict_weekly(np.array([0.0]), [date(2009, 1, 5)])
    assert first.n_unique() == 1  # no MODIS pattern to follow: spread evenly
    assert first[0] == pytest.approx(float(expected[0]) / 7)


def test_force_uses_the_named_model_but_still_scores_all(pairs: pl.DataFrame) -> None:
    forced = fit_normalizer(pairs, force="isotonic")
    assert forced.chosen == "isotonic" and forced.model.name == "isotonic"
    assert set(forced.cv["model"]) == {"huber", "theilsen", "quantile", "isotonic", "raw", "scale"}
    with pytest.raises(ValueError, match="unknown model"):
        fit_normalizer(pairs, force="raw")  # baselines cannot be selected
