"""Which days of which sensor were actually downloaded, versus merely "no detections".

A day with no hotspots and a day that was never fetched look identical in the data. Both the
cache layout (one file per source, tile and 5-day chunk) and FIRMS's availability ranges are
used to tell them apart, so a failed chunk becomes a gap (null) and not a run of zeros.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from emberline.data.chunking import MAX_DAY_RANGE
from emberline.data.firms import Availability

BBox = tuple[float, float, float, float]
_CHUNK = re.compile(r"chunk=(\d{4}-\d{2}-\d{2})(?:~(\d+)d)?\.parquet$")
_EPS = 1e-9


def save_availability(root: Path, avail: dict[str, Availability]) -> Path:
    p = Path(root) / "availability.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {k: [v.min_date.isoformat(), v.max_date.isoformat()] for k, v in avail.items()}
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(p)
    return p


def load_availability(root: Path) -> dict[str, tuple[date, date]]:
    p = Path(root) / "availability.json"
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {k: (date.fromisoformat(a), date.fromisoformat(b)) for k, (a, b) in raw.items()}


def _tile_bbox(name: str) -> BBox | None:
    try:
        w, s, e, n = (float(x) for x in name.removeprefix("tile=").split("_"))
    except ValueError:
        return None
    return (w, s, e, n)


def _chunk_days(path: Path) -> list[date]:
    m = _CHUNK.search(path.name)
    if not m:
        return []
    start = date.fromisoformat(m.group(1))
    n = int(m.group(2)) if m.group(2) else MAX_DAY_RANGE
    return [start + timedelta(days=i) for i in range(n)]


def observed_dates(
    root: Path,
    source: str,
    bbox: BBox,
    avail: dict[str, tuple[date, date]] | None = None,
) -> list[date]:
    """Sorted days for which `source` was downloaded over `bbox`, clipped to its availability.

    Uses tiles that fully contain the bbox; if there are none (grid tiling), a day counts only
    if every tile intersecting the bbox has it.
    """
    w, s, e, n = bbox
    src_dir = Path(root) / "raw" / f"src={source}"
    if not src_dir.is_dir():
        return []
    containing: list[set[date]] = []
    intersecting: list[set[date]] = []
    for tile_dir in src_dir.glob("tile=*"):
        tb = _tile_bbox(tile_dir.name)
        if tb is None:
            continue
        tw, ts, te, tn = tb
        days = {d for f in tile_dir.glob("chunk=*.parquet") for d in _chunk_days(f)}
        if tw <= w + _EPS and ts <= s + _EPS and te >= e - _EPS and tn >= n - _EPS:
            containing.append(days)
        elif tw < e and te > w and ts < n and tn > s:
            intersecting.append(days)
    if containing:
        days = set().union(*containing)
    elif intersecting:
        days = set.intersection(*intersecting)
    else:
        return []
    if avail and source in avail:
        lo, hi = avail[source]
        days = {d for d in days if lo <= d <= hi}
    return sorted(days)


def containing_tile(root: Path, source: str, bbox: BBox) -> BBox | None:
    """The cached tile (as a bbox) that fully contains `bbox` and holds the most chunks, if any.

    Extending an existing tile fills only what is missing, instead of re-downloading a whole new
    tile for a sub-area that is already mostly on disk."""
    w, s, e, n = bbox
    src_dir = Path(root) / "raw" / f"src={source}"
    if not src_dir.is_dir():
        return None
    best: tuple[int, BBox] | None = None
    for tile_dir in src_dir.glob("tile=*"):
        tb = _tile_bbox(tile_dir.name)
        if tb is None:
            continue
        tw, ts, te, tn = tb
        if tw <= w + _EPS and ts <= s + _EPS and te >= e - _EPS and tn >= n - _EPS:
            count = sum(1 for _ in tile_dir.glob("chunk=*.parquet"))
            if best is None or count > best[0]:
                best = (count, tb)
    return best[1] if best else None
