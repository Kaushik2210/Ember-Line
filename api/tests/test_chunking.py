from datetime import date

import pytest

from emberline.data.chunking import clip_chunk, date_chunks, tiles_for


def test_chunks_cover_range_and_are_grid_aligned() -> None:
    chunks = date_chunks(date(2019, 11, 3), date(2019, 11, 27))
    assert chunks[0].start <= date(2019, 11, 3) <= chunks[0].end
    assert chunks[-1].start <= date(2019, 11, 27) <= chunks[-1].end
    assert all(c.days == 5 for c in chunks)
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert (b.start - a.start).days == 5


def test_same_day_in_different_requests_hits_same_chunk() -> None:
    a = date_chunks(date(2019, 11, 3), date(2019, 11, 5))
    b = date_chunks(date(2019, 10, 28), date(2019, 11, 9))
    assert a[0] in b


def test_empty_when_reversed() -> None:
    assert date_chunks(date(2020, 1, 2), date(2020, 1, 1)) == []


def test_clip() -> None:
    c = date_chunks(date(2019, 11, 3), date(2019, 11, 3))[0]
    clipped = clip_chunk(c, date(2019, 11, 3), date(2019, 11, 5))
    assert clipped is not None
    assert clipped.start == date(2019, 11, 3) and clipped.days == 3
    assert clip_chunk(c, date(2030, 1, 1), date(2030, 2, 1)) is None


def test_tiles_cover_bbox_and_are_stable() -> None:
    tiles = tiles_for((73.8, 28.4, 77.6, 32.5))
    assert {t.key for t in tiles} == {"70_20_80_30", "70_30_80_40"}
    again = tiles_for((74.0, 31.0, 76.0, 32.0))
    assert again[0].key == "70_30_80_40"


def test_tiles_negative_coordinates() -> None:
    tiles = tiles_for((-124.5, 32.5, -114.1, 42.0))
    assert min(t.west for t in tiles) == -130 and max(t.east for t in tiles) == -110


def test_bad_bbox() -> None:
    with pytest.raises(ValueError):
        tiles_for((10, 10, 5, 20))
