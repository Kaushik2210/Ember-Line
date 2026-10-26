"""Shared fixtures: one synthetic region analysed once per test session."""

from datetime import date

import polars as pl
import pytest

from emberline.data.store import HotspotStore
from emberline.data.synthetic import generate_synthetic, write_synthetic
from emberline.pipeline import Analysis, run_analysis

BBOX = (74.0, 29.0, 77.0, 32.0)
START, END = date(2010, 1, 1), date(2020, 12, 31)
VIIRS_FROM = date(2014, 1, 1)


@pytest.fixture(scope="session")
def store(tmp_path_factory: pytest.TempPathFactory) -> HotspotStore:
    root = tmp_path_factory.mktemp("syn")
    df = generate_synthetic(BBOX, START, END, seed=3)
    # VIIRS only flies from 2014 here, so 2010-2013 must be reconstructed from MODIS
    df = df.filter((pl.col("sensor") == "modis") | (pl.col("local_date") >= VIIRS_FROM))
    write_synthetic(root, df)
    return HotspotStore(root)


@pytest.fixture(scope="session")
def analysis(store: HotspotStore) -> Analysis:
    stages: list[str] = []
    a = run_analysis(store, BBOX, START, END, synthetic=True, progress=stages.append)
    a.stages = stages  # type: ignore[attr-defined]
    return a
