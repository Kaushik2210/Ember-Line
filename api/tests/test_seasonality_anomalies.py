from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from emberline.science.anomalies import (
    describe_event,
    describe_season,
    flag_events,
    loyo_zscores,
    rank_seasons,
    season_totals,
)
from emberline.science.seasonality import (
    climatology,
    doy_matrix,
    season_markers,
    stl_decompose,
)


def make_daily(
    years: range = range(2000, 2013),
    seed: int = 0,
    extreme_year: int | None = None,
    burst: tuple[date, int, float] | None = None,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    first, last = date(years[0], 1, 1), date(years[-1], 12, 31)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    doy = np.array([d.timetuple().tm_yday for d in days])
    base = 80 * np.exp(-0.5 * ((doy - 200) / 35.0) ** 2)  # one season peaking mid-July
    v = base * rng.lognormal(0, 0.25, len(days))
    if extreme_year:
        v = np.where([d.year == extreme_year for d in days], v * 6, v)
    if burst:
        start, n, factor = burst
        for i, d in enumerate(days):
            if start <= d < start + timedelta(days=n):
                v[i] *= factor
    return pl.DataFrame({"local_date": days, "harmonized": v})


@pytest.fixture(scope="module")
def daily() -> pl.DataFrame:
    return make_daily(extreme_year=2008, burst=(date(2004, 7, 10), 6, 8.0))


def test_doy_matrix_shape_and_alignment() -> None:
    d = make_daily(range(2000, 2005))
    mat, years = doy_matrix(d)
    assert mat.shape == (5, 365) and years == list(range(2000, 2005))
    # 1 March is column index 59 in leap and non-leap years alike
    for y_i, y in enumerate(years):
        expect = d.filter(pl.col("local_date") == date(y, 3, 1))["harmonized"][0]
        assert mat[y_i, 59] == pytest.approx(expect)


def test_climatology_quantiles_ordered_and_peaks_in_july() -> None:
    mat, _ = doy_matrix(make_daily())
    c = climatology(mat)
    assert (c["p10"] <= c["p25"]).all() and (c["p25"] <= c["median"]).all()
    assert (c["median"] <= c["p75"]).all() and (c["p75"] <= c["p90"]).all()
    peak = int(c["median"].arg_max())
    assert 185 <= peak + 1 <= 215


def test_leave_one_year_out_excludes_that_year() -> None:
    mat, years = doy_matrix(make_daily(extreme_year=2008))
    i = years.index(2008)
    with_it = climatology(mat)["median"].max()
    without = climatology(mat, exclude_row=i)["median"].max()
    assert without <= with_it


def test_season_markers_order_and_straddling_new_year() -> None:
    mat, _ = doy_matrix(make_daily())
    m = season_markers(np.nanmedian(mat, axis=0))
    assert m is not None
    assert m.start_doy < m.peak_doy < m.end_doy
    assert 150 < m.peak_doy < 250
    # a season centred on 1 January (southern summer): start must be in the old year
    prof = np.zeros(365)
    prof[[*range(335, 365), *range(0, 40)]] = 1.0
    s = season_markers(prof)
    assert s is not None and s.start_doy > 300 and s.end_doy < 100
    assert s.length_days == pytest.approx(0.8 * 70, abs=4)
    assert season_markers(np.zeros(365)) is None


def test_stl_has_components_and_needs_two_periods() -> None:
    weeks = [date(2010, 1, 4) + timedelta(weeks=i) for i in range(52 * 4)]
    y = 50 + 40 * np.sin(2 * np.pi * np.arange(len(weeks)) / 52)
    out = stl_decompose(pl.DataFrame({"week": weeks, "value": y}))
    assert set(out.columns) == {"week", "trend", "seasonal", "resid"}
    assert out["seasonal"].abs().max() > 0.5
    with pytest.raises(ValueError):
        stl_decompose(pl.DataFrame({"week": weeks[:60], "value": y[:60]}))


def test_burst_is_flagged_as_sustained_high_event(daily: pl.DataFrame) -> None:
    ev = flag_events(loyo_zscores(daily))
    hits = [e for e in ev if e.direction == "high" and e.start <= date(2004, 7, 15) <= e.end]
    assert hits, "the injected 6-day burst should be found"
    assert hits[0].days >= 3 and hits[0].peak_z > 2.5 and hits[0].excess > 0


def test_extreme_year_stands_out_and_is_not_its_own_baseline(daily: pl.DataFrame) -> None:
    scores = loyo_zscores(daily)
    y2008 = scores.filter(pl.col("local_date").dt.year() == 2008)
    ordinary = scores.filter(pl.col("local_date").dt.year() == 2001)
    assert y2008["z"].median() > 3
    assert abs(ordinary["z"].median()) < 1.5


def test_no_events_in_clean_series() -> None:
    assert flag_events(loyo_zscores(make_daily(seed=5)), threshold=4.0) == []


def test_single_day_spike_is_not_an_event() -> None:
    d = make_daily(burst=(date(2006, 7, 10), 1, 50.0))
    ev = flag_events(loyo_zscores(d), min_days=3)
    assert not [e for e in ev if e.start <= date(2006, 7, 10) <= e.end]


def test_gap_bridging_and_validation() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(8)]
    z = [3, 3, 0, 3, 3, 0, 0, 0]
    sc = pl.DataFrame({"local_date": dates, "z": z, "baseline": [1.0] * 8, "harmonized": [5.0] * 8})
    one = flag_events(sc, max_gap=1)
    assert len(one) == 1 and one[0].days == 5
    assert flag_events(sc, max_gap=0) == []  # two runs of 2 days, each below min_days
    with pytest.raises(ValueError):
        flag_events(sc, max_gap=3)


def test_needs_three_years() -> None:
    with pytest.raises(ValueError):
        loyo_zscores(make_daily(range(2000, 2002)))


def test_rank_seasons_puts_extreme_year_first(daily: pl.DataFrame) -> None:
    ranked = rank_seasons(season_totals(daily))
    assert ranked["season"][0] == "2008"
    assert ranked["z"][0] > 3
    assert ranked["rank"].to_list() == sorted(ranked["rank"].to_list())


def test_descriptions_are_plain_language(daily: pl.DataFrame) -> None:
    ev = flag_events(loyo_zscores(daily))[0]
    text = describe_event(ev)
    assert "robust standard deviations" in text and "other years" in text
    assert "2008" in describe_season("2008", 4.1, 13)
    assert "12 fire years" in describe_season("2008", 4.1, 13)
