"""Data-quality timeline: documented events that affect the MODIS/VIIRS fire record.

Only facts confirmed against NASA pages are listed, each with its source. Where a source gives
no date the event is marked "undated" instead of guessing one. Anything not verified is left out.
`verified` records when the sources were last checked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import polars as pl

Precision = Literal["day", "month", "year", "undated"]
VERIFIED = "2026-10-26"

FAQ_MODIS = "https://forum.earthdata.nasa.gov/viewtopic.php?t=5191"
FAQ_VIIRS = "https://forum.earthdata.nasa.gov/viewtopic.php?t=5189"
FIRMS_VIIRS = (
    "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html"
)
TERRA_DRIFT = "https://terra.nasa.gov/about/terras-orbit-changes/terra-orbital-drift-information"
MODIS_LAND_NEWS = "https://modis-land.gsfc.nasa.gov/news.html"
C61 = "https://www.earthdata.nasa.gov/data/catalog/lancemodis-mcd14dl-6.1nrt"


@dataclass(frozen=True)
class Annotation:
    when: str  # ISO date, "YYYY-MM", "YYYY" or "undated"
    precision: Precision
    kind: str  # launch | coverage | orbit | algorithm
    title: str
    detail: str
    affects: tuple[str, ...]  # "modis" and/or "viirs"
    source: str

    @property
    def start(self) -> date | None:
        """First day the event could apply, for placing it on a timeline."""
        if self.precision == "undated":
            return None
        parts = [int(p) for p in self.when.split("-")]
        return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)


EVENTS: list[Annotation] = [
    Annotation(
        "1999-12-18",
        "day",
        "launch",
        "Terra launched",
        "MODIS began flying on Terra (10:30 local equator crossing).",
        ("modis",),
        FAQ_MODIS,
    ),
    Annotation(
        "2000-11",
        "month",
        "coverage",
        "Terra active-fire record begins",
        "NASA describes high quality active fire observations from Terra as available starting "
        "November 2000. Until Aqua, MODIS fire data come from one satellite, with fewer overpasses.",
        ("modis",),
        FAQ_MODIS,
    ),
    Annotation(
        "2002-05-04",
        "day",
        "launch",
        "Aqua launched",
        "Second MODIS on Aqua (13:30 local equator crossing).",
        ("modis",),
        FAQ_MODIS,
    ),
    Annotation(
        "2002-07-04",
        "day",
        "coverage",
        "Aqua active-fire record begins",
        "High quality active fire observations from Aqua start on this date. From here MODIS "
        "samples the day twice at different local times (Terra morning, Aqua afternoon).",
        ("modis",),
        FAQ_MODIS,
    ),
    Annotation(
        "2011-10-28",
        "day",
        "launch",
        "VIIRS launched on Suomi NPP",
        "First VIIRS sensor, with 375 m I-band channels used for active fire detection.",
        ("viirs",),
        FAQ_VIIRS,
    ),
    Annotation(
        "2012-01-20",
        "day",
        "coverage",
        "Suomi NPP VIIRS fire record begins in FIRMS",
        "FIRMS lists S-NPP VIIRS 375 m active fire temporal coverage as starting 20 January 2012. "
        "This is the start of the overlap with MODIS used to fit the normalisation.",
        ("viirs",),
        FIRMS_VIIRS,
    ),
    Annotation(
        "2015",
        "year",
        "algorithm",
        "VIIRS 375 m fire radiative power uses 750 m data from 2015",
        "FIRMS states that FRP retrievals combine 375 m and 750 m data and that starting in 2015 "
        "the algorithm incorporated the M13 channel. FRP may not be homogeneous across this change; "
        "the source gives the year only.",
        ("viirs",),
        FIRMS_VIIRS,
    ),
    Annotation(
        "2017-11-18",
        "day",
        "launch",
        "VIIRS launched on NOAA-20",
        "Second VIIRS, flying in the same 13:30 orbit family as Suomi NPP.",
        ("viirs",),
        FAQ_VIIRS,
    ),
    Annotation(
        "2020-02-27",
        "day",
        "orbit",
        "Terra's last inclination maneuver; orbit drift begins",
        "After the final maneuver on this date Terra was allowed to drift to an earlier equator "
        "crossing than 10:30. NASA expects the impact on science to be minimal, but the morning "
        "sampling time of Terra-MODIS fire detections is no longer fixed after this point.",
        ("modis",),
        TERRA_DRIFT,
    ),
    Annotation(
        "undated",
        "undated",
        "algorithm",
        "MODIS Collection 6.1 processing",
        "FIRMS near-real-time MODIS data use Collection 6.1. NASA says C6.1 contains no change to "
        "the science algorithm; changes improve the calibration of the Level 1B inputs. The "
        "source page gives no switch-over date, so none is placed on the timeline.",
        ("modis",),
        C61,
    ),
]


def annotations_for(
    start: date, end: date, sensors: tuple[str, ...] = ("modis", "viirs")
) -> list[Annotation]:
    """Events inside [start, end] for the given sensors; undated ones are always included."""
    out = []
    for e in EVENTS:
        if not set(e.affects) & set(sensors):
            continue
        d = e.start
        if d is None or start <= d <= end:
            out.append(e)
    return sorted(out, key=lambda e: (e.start is None, e.start or date.max))


def platform_coverage(df: pl.DataFrame) -> pl.DataFrame:
    """First and last day, and detection count, per platform actually present in the data."""
    if df.height == 0:
        return pl.DataFrame(
            schema={
                "sensor": pl.Utf8,
                "platform": pl.Utf8,
                "first": pl.Date,
                "last": pl.Date,
                "detections": pl.UInt32,
            }
        )
    return (
        df.group_by("sensor", "platform")
        .agg(
            pl.col("local_date").min().alias("first"),
            pl.col("local_date").max().alias("last"),
            pl.len().alias("detections"),
        )
        .sort("first")
    )
