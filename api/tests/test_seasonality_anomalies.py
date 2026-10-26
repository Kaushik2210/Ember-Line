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
    season_segments,
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


def test_season_labels_follow_the_peak_or_straddle_new_year() -> None:
    # northern-style season peaking in July: named by the peak's calendar year
    north = season_totals(make_daily(range(2000, 2006)))
    assert north.height > 0 and all(s.isdigit() for s in north["season"])
    # austral-style season centred on 1 January: named like 2019-20
    days = [date(2000, 1, 1) + timedelta(days=i) for i in range(6 * 365 + 2)]
    doy = np.array([d.timetuple().tm_yday for d in days])
    dist = np.minimum(doy, 365 - doy)  # distance to 1 January
    v = 50 * np.exp(-0.5 * (dist / 25.0) ** 2) + 0.01
    south = season_totals(pl.DataFrame({"local_date": days, "harmonized": v}))
    assert south.height > 0 and all("-" in s for s in south["season"])


def test_two_burning_seasons_are_separated() -> None:
    doy = np.arange(365)
    bump = lambda c, w, h: h * np.exp(-0.5 * ((doy - c) / w) ** 2)  # noqa: E731
    prof = bump(110, 12, 40) + bump(305, 14, 100) + 0.1  # Apr-May and Oct-Nov, like Punjab
    segs = season_segments(prof)
    assert len(segs) == 2
    big, small = segs
    assert big.total > small.total  # largest first
    assert 290 < big.peak_doy < 320 and 95 < small.peak_doy < 125
    assert all(m.start_doy < m.peak_doy < m.end_doy for m in segs)
    # one merged season would span both; the segments are each much shorter
    merged = season_markers(prof)
    assert merged is not None and merged.length_days > 2 * max(m.length_days for m in segs)


def test_one_season_and_wrapping_season_and_empty() -> None:
    doy = np.arange(365)
    one = 80 * np.exp(-0.5 * ((doy - 200) / 30.0) ** 2) + 0.1
    assert len(season_segments(one)) == 1
    dist = np.minimum(doy, 365 - doy)  # centred on 1 January
    wrap = season_segments(80 * np.exp(-0.5 * (dist / 20.0) ** 2) + 0.1)
    assert len(wrap) == 1 and wrap[0].start_doy > wrap[0].end_doy  # straddles new year
    assert season_segments(np.zeros(365)) == []
    assert season_segments(np.r_[np.zeros(300), np.ones(3), np.zeros(62)]) == []  # too short


def test_tiny_events_in_quiet_periods_are_dropped_by_the_materiality_floor() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(6)]
    sc = pl.DataFrame(
        {"local_date": dates, "z": [5.0] * 6, "baseline": [0.1] * 6, "harmonized": [2.0] * 6}
    )
    assert len(flag_events(sc)) == 1  # a big z score...
    assert flag_events(sc, min_excess=50.0) == []  # ...but only ~11 units above baseline
    assert len(flag_events(sc, min_excess=5.0)) == 1


def test_describe_event_appends_a_caveat_when_there_is_one() -> None:
    from dataclasses import replace

    ev = flag_events(
        loyo_zscores(make_daily(extreme_year=2008, burst=(date(2004, 7, 10), 6, 8.0)))
    )[0]
    assert ev.caveat == "" and not describe_event(ev).endswith(" ")
    flagged = replace(ev, caveat="Less reliable: test.")
    assert describe_event(flagged).endswith("Less reliable: test.")
