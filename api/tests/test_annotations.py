from datetime import date

import polars as pl

from emberline.annotations import EVENTS, annotations_for, platform_coverage


def test_every_event_cites_an_official_source() -> None:
    allowed = ("nasa.gov", "gsfc.nasa.gov", "eosdis.nasa.gov")
    for e in EVENTS:
        assert e.source.startswith("https://"), e.title
        assert any(host in e.source for host in allowed), f"{e.title}: {e.source}"
        assert e.detail and e.title


def test_dates_parse_and_match_their_precision() -> None:
    for e in EVENTS:
        d = e.start
        if e.precision == "undated":
            assert d is None and e.when == "undated"
        else:
            assert d is not None
            assert {"day": 3, "month": 2, "year": 1}[e.precision] == len(e.when.split("-"))


def test_known_dates_are_the_verified_ones() -> None:
    by_title = {e.title: e for e in EVENTS}
    assert by_title["Terra launched"].start == date(1999, 12, 18)
    assert by_title["Aqua launched"].start == date(2002, 5, 4)
    assert by_title["VIIRS launched on Suomi NPP"].start == date(2011, 10, 28)
    assert by_title["VIIRS launched on NOAA-20"].start == date(2017, 11, 18)


def test_window_and_sensor_filtering() -> None:
    mid = annotations_for(date(2012, 1, 1), date(2013, 12, 31))
    titles = [e.title for e in mid]
    assert "Suomi NPP VIIRS fire record begins in FIRMS" in titles
    assert "Terra launched" not in titles
    assert any(e.precision == "undated" for e in mid)  # undated notes always shown
    only_viirs = annotations_for(date(1990, 1, 1), date(2030, 1, 1), ("viirs",))
    assert only_viirs and all("viirs" in e.affects for e in only_viirs)
    starts = [e.start for e in mid if e.start]
    assert starts == sorted(starts)


def test_platform_coverage_comes_from_the_data() -> None:
    df = pl.DataFrame(
        {
            "sensor": ["modis", "modis", "viirs"],
            "platform": ["Terra", "Aqua", "SNPP"],
            "local_date": [date(2001, 1, 1), date(2002, 8, 1), date(2012, 2, 1)],
        }
    )
    pc = platform_coverage(df)
    assert pc["platform"].to_list() == ["Terra", "Aqua", "SNPP"]
    assert platform_coverage(df.head(0)).height == 0
