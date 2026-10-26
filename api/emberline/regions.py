"""Curated demo regions. Bboxes are (west, south, east, north) in degrees.

Narratives describe why a region is interesting; they contain no computed numbers.
Findings shown in the UI are computed from data, never taken from here.
"""

from __future__ import annotations

from pydantic import BaseModel

BBox = tuple[float, float, float, float]


class Region(BaseModel):
    id: str
    name: str
    bbox: BBox
    blurb: str
    default_start: str
    default_end: str


REGIONS: list[Region] = [
    Region(
        id="punjab-haryana",
        name="Punjab & Haryana, India",
        bbox=(73.8, 28.4, 77.6, 32.5),
        blurb=(
            "Crop-residue burning peaks in October and November, mostly as many small fires. "
            "The early-afternoon overpass can miss the evening burn peak, so the sensors diverge."
        ),
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
    Region(
        id="eastern-australia",
        name="Eastern Australia (NSW / Victoria)",
        bbox=(140.9, -39.2, 153.7, -28.1),
        blurb="Home of the 2019-20 Black Summer fires, the headline anomaly.",
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
    Region(
        id="para-mato-grosso",
        name="Pará / Mato Grosso, Brazil",
        bbox=(-62.0, -16.0, -48.0, -3.0),
        blurb="The Amazon arc of deforestation, with a strong dry-season burning cycle.",
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
    Region(
        id="california",
        name="California, USA",
        bbox=(-124.5, 32.5, -114.1, 42.0),
        blurb="Large wildfires in 2018 and 2020, where the two sensors tend to agree better.",
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
    Region(
        id="savanna-belt",
        name="Central African Republic / South Sudan",
        bbox=(14.4, 2.2, 34.0, 12.0),
        blurb="Part of the savanna belt that burns widely and regularly every dry season.",
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
    Region(
        id="canada-boreal",
        name="Western Canada (boreal)",
        bbox=(-125.0, 49.0, -95.0, 61.0),
        blurb="Boreal forest across BC, Alberta, Saskatchewan and the NWT, incl. the 2023 season.",
        default_start="2000-11-01",
        default_end="2025-12-31",
    ),
]


def get_region(region_id: str) -> Region:
    for r in REGIONS:
        if r.id == region_id:
            return r
    raise KeyError(region_id)
