"""Date and spatial chunking so each FIRMS request is small and cache keys are stable.

Date chunks sit on a fixed 5-day grid anchored at 2000-01-01, so overlapping requests
from different analyses reuse the same cache entries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

# The live FIRMS area API answers "Invalid day range. Expects [1..5]" above 5 days
# (the public docs say 10), so 5 is what is verified to work.
MAX_DAY_RANGE = 5
_EPOCH = date(2000, 1, 1)

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class DateChunk:
    start: date
    days: int

    @property
    def end(self) -> date:
        return self.start + timedelta(days=self.days - 1)


def date_chunks(start: date, end: date) -> list[DateChunk]:
    """Grid-aligned chunks covering [start, end] inclusive. Edge chunks may extend outside."""
    if end < start:
        return []
    first = (start - _EPOCH).days // MAX_DAY_RANGE
    last = (end - _EPOCH).days // MAX_DAY_RANGE
    return [
        DateChunk(_EPOCH + timedelta(days=i * MAX_DAY_RANGE), MAX_DAY_RANGE)
        for i in range(first, last + 1)
    ]


def clip_chunk(chunk: DateChunk, lo: date, hi: date) -> DateChunk | None:
    """Clip a chunk to the available [lo, hi] range, or None if nothing is left."""
    s, e = max(chunk.start, lo), min(chunk.end, hi)
    if e < s:
        return None
    return DateChunk(s, (e - s).days + 1)


@dataclass(frozen=True)
class Tile:
    west: float
    south: float
    east: float
    north: float

    @property
    def key(self) -> str:
        return f"{self.west:g}_{self.south:g}_{self.east:g}_{self.north:g}"

    @property
    def bbox(self) -> BBox:
        return (self.west, self.south, self.east, self.north)


def tiles_for(bbox: BBox, size_deg: float = 10.0) -> list[Tile]:
    """Split a bbox into tiles on a fixed global grid, each clipped to the bbox.

    Grid-aligned splitting keeps tile keys stable between overlapping bboxes. A tile that
    is only partly inside the bbox is requested in full so its cache entry is reusable.
    """
    w, s, e, n = bbox
    if not (w < e and s < n):
        raise ValueError("bbox must satisfy west < east and south < north")
    x0, x1 = math.floor(w / size_deg), math.ceil(e / size_deg)
    y0, y1 = math.floor(s / size_deg), math.ceil(n / size_deg)
    return [
        Tile(i * size_deg, j * size_deg, (i + 1) * size_deg, (j + 1) * size_deg)
        for i in range(x0, x1)
        for j in range(y0, y1)
    ]
