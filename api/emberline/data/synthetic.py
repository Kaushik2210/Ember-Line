"""SYNTHETIC hotspot generator for development and automated tests only.

Every row has synthetic=True and source SYNTHETIC_*. The UI must show a visible banner
whenever this data is used. Numbers produced here are never real observations.

The generator draws a latent set of "true" fires per day, then lets each sensor detect
them with its own sensitivity and overpass time:
  * VIIRS (375 m) detects smaller / cooler fires than MODIS (1 km), so it sees more fires.
  * Terra passes ~10:30 local, Aqua and SNPP ~13:30; fire activity follows a diurnal cycle
    peaking mid-afternoon, so the overpass time changes what each sensor catches.
Overpass times here are modelling assumptions, not measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from emberline.data.schema import COMMON_SCHEMA, add_time_columns

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class SensorModel:
    source: str
    sensor: str
    platform: str
    overpass_hour: float  # local solar time of the daytime pass
    frp_threshold_mw: float  # FRP at which detection probability is 50%
    pixel_deg: float


MODELS = [
    SensorModel("SYNTHETIC_MODIS", "modis", "Terra", 10.5, 6.0, 0.01),
    SensorModel("SYNTHETIC_MODIS", "modis", "Aqua", 13.5, 6.0, 0.01),
    SensorModel("SYNTHETIC_VIIRS", "viirs", "SNPP", 13.5, 1.0, 0.004),
]


def _diurnal(hour: np.ndarray) -> np.ndarray:
    """Relative fire activity by local hour: peak ~15:00, small night floor."""
    d = np.minimum(np.abs(hour - 15.0), 24 - np.abs(hour - 15.0))
    return np.asarray(0.08 + 0.92 * np.exp(-0.5 * (d / 3.5) ** 2))


def generate_synthetic(bbox: BBox, start: date, end: date, seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    w, s, e, n = bbox
    n_days = (end - start).days + 1
    days = np.arange(n_days)
    doy = np.array([(start + timedelta(days=int(i))).timetuple().tm_yday for i in days])

    # fire season peaks mid-year; a couple of anomalous seasons are injected
    season = np.exp(2.2 * np.cos(2 * np.pi * (doy - 200) / 365.25))
    year_idx = np.array([(start + timedelta(days=int(i))).year for i in days])
    extreme = np.isin(year_idx, [start.year + 3]) * 2.5 + 1.0
    lam = 6.0 * season * extreme * rng.lognormal(0, 0.35, n_days)
    n_fires = rng.poisson(lam)

    centres = np.column_stack([rng.uniform(w, e, 40), rng.uniform(s, n, 40)])
    frames: list[pl.DataFrame] = []
    total = int(n_fires.sum())
    if total == 0:
        return pl.DataFrame(schema=COMMON_SCHEMA)

    day_of = np.repeat(days, n_fires)
    c = centres[rng.integers(0, len(centres), total)]
    lon = np.clip(c[:, 0] + rng.normal(0, 0.25, total), w, e)
    lat = np.clip(c[:, 1] + rng.normal(0, 0.25, total), s, n)
    frp = rng.lognormal(np.log(3.0), 1.1, total)  # heavy-tailed true FRP, MW
    # fire timing offset: how long after the nominal peak this fire stays active
    shift = rng.normal(0, 1.5, total)

    for m in MODELS:
        act = _diurnal(np.full(total, m.overpass_hour) - shift)
        p = 1.0 / (1.0 + np.exp(-2.2 * (np.log(frp * act / m.frp_threshold_mw))))
        hit = rng.random(total) < p
        k = int(hit.sum())
        if k == 0:
            continue
        hour = m.overpass_hour + rng.normal(0, 0.4, k)
        base_dt = np.array(
            [
                datetime.combine(start, datetime.min.time()) + timedelta(days=int(i))
                for i in day_of[hit]
            ],
            dtype="datetime64[us]",
        )
        # local solar time -> UTC: subtract lon/15 hours
        utc_offset_us = ((hour - lon[hit] / 15.0) * 3.6e9).astype("int64")
        acq_utc = base_dt + utc_offset_us.astype("timedelta64[us]")
        meas = frp[hit] * act[hit] ** 0.5 * rng.lognormal(0, 0.2, k)
        if m.sensor == "modis":
            conf_num = np.clip(rng.normal(40 + 12 * np.log1p(meas), 12, k), 0, 100).round()
            conf_class = [None] * k
            b1 = 305 + 6 * np.log1p(meas) + rng.normal(0, 2, k)
        else:
            conf_num = np.full(k, np.nan)
            q = rng.random(k)
            conf_class = list(np.where(q < 0.1, "l", np.where(q < 0.85, "n", "h")))
            b1 = 330 + 4 * np.log1p(meas) + rng.normal(0, 2, k)
        frames.append(
            pl.DataFrame(
                {
                    "source": m.source,
                    "sensor": m.sensor,
                    "platform": m.platform,
                    "latitude": lat[hit] + rng.normal(0, m.pixel_deg / 3, k),
                    "longitude": lon[hit] + rng.normal(0, m.pixel_deg / 3, k),
                    "acq_utc": acq_utc,
                    "daynight": "D",
                    "frp": meas,
                    "conf_num": conf_num,
                    "conf_class": conf_class,
                    "bright_primary": b1,
                    "bright_secondary": b1 - 20,
                    "scan": rng.uniform(1.0, 2.0, k)
                    if m.sensor == "modis"
                    else rng.uniform(0.4, 0.8, k),
                    "track": rng.uniform(1.0, 1.5, k)
                    if m.sensor == "modis"
                    else rng.uniform(0.4, 0.6, k),
                    "fire_type": 0,
                    "synthetic": True,
                }
            ).with_columns(
                pl.col("conf_num").fill_nan(None),
                pl.col("conf_class").cast(pl.Utf8),
                pl.col("acq_utc").cast(pl.Datetime("us")),
            )
        )

    df = pl.concat(frames)
    df = df.with_columns(
        pl.lit(0.0).alias("local_solar_hour"), pl.lit(None, dtype=pl.Date).alias("local_date")
    )
    df = add_time_columns(df)
    return df.select(list(COMMON_SCHEMA)).cast(COMMON_SCHEMA).sort("acq_utc")


def write_synthetic(root: Path, df: pl.DataFrame) -> list[Path]:
    """Store under <root>/synthetic/ in the same hive layout the DuckDB store reads."""
    out: list[Path] = []
    for src in df["source"].unique().to_list():
        p = Path(root) / "synthetic" / f"src={src}" / "tile=all" / "chunk=all.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        df.filter(pl.col("source") == src).write_parquet(p, compression="zstd")
        out.append(p)
    return out
