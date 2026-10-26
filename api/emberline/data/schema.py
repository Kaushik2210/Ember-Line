"""Common hotspot schema and normalisation of raw FIRMS CSV into it.

MODIS and VIIRS rows differ in column names and confidence scheme:
  MODIS: brightness / bright_t31, confidence 0-100
  VIIRS: bright_ti4 / bright_ti5, confidence l / n / h
Both are mapped to one table. FRP is the most directly comparable attribute.
"""

from __future__ import annotations

import io

import polars as pl

MODIS_SOURCES = {"MODIS_SP", "MODIS_NRT"}
VIIRS_PLATFORM_BY_SOURCE = {
    "VIIRS_SNPP_SP": "SNPP",
    "VIIRS_SNPP_NRT": "SNPP",
    "VIIRS_NOAA20_SP": "NOAA-20",
    "VIIRS_NOAA20_NRT": "NOAA-20",
    "VIIRS_NOAA21_SP": "NOAA-21",
    "VIIRS_NOAA21_NRT": "NOAA-21",
}
ALL_SOURCES = sorted(MODIS_SOURCES | set(VIIRS_PLATFORM_BY_SOURCE))

COMMON_SCHEMA: dict[str, pl.DataType] = {
    "source": pl.Utf8,
    "sensor": pl.Utf8,
    "platform": pl.Utf8,
    "latitude": pl.Float64,
    "longitude": pl.Float64,
    "acq_utc": pl.Datetime("us"),
    "local_solar_hour": pl.Float64,
    "local_date": pl.Date,
    "daynight": pl.Utf8,
    "frp": pl.Float64,
    "conf_num": pl.Float64,
    "conf_class": pl.Utf8,
    "bright_primary": pl.Float64,
    "bright_secondary": pl.Float64,
    "scan": pl.Float64,
    "track": pl.Float64,
    "fire_type": pl.Int64,
    "synthetic": pl.Boolean,
}


def sensor_of(source: str) -> str:
    if source in MODIS_SOURCES:
        return "modis"
    if source in VIIRS_PLATFORM_BY_SOURCE:
        return "viirs"
    raise ValueError(f"unknown FIRMS source: {source}")


def empty_frame() -> pl.DataFrame:
    return pl.DataFrame(schema=COMMON_SCHEMA)


def add_time_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Add local solar hour/date from a UTC timestamp and longitude (UTC + lon/15 h)."""
    utc_hour = (
        pl.col("acq_utc").dt.hour().cast(pl.Float64)
        + pl.col("acq_utc").dt.minute().cast(pl.Float64) / 60.0
    )
    shifted = utc_hour + pl.col("longitude") / 15.0
    return df.with_columns(
        (shifted % 24.0).alias("local_solar_hour"),
        (
            pl.col("acq_utc").dt.date() + pl.duration(days=(shifted / 24.0).floor().cast(pl.Int64))
        ).alias("local_date"),
    )


def normalize_firms_csv(text: str, source: str) -> pl.DataFrame:
    """Parse a FIRMS area CSV body into the common schema."""
    sensor = sensor_of(source)
    if not text.strip():
        return empty_frame()
    raw = pl.read_csv(io.StringIO(text), infer_schema_length=0)  # everything as str
    if raw.height == 0 or "acq_date" not in raw.columns:
        return empty_frame()

    modis = sensor == "modis"
    primary, secondary = ("brightness", "bright_t31") if modis else ("bright_ti4", "bright_ti5")
    cols = raw.columns

    def col(name: str) -> pl.Expr:
        return pl.col(name) if name in cols else pl.lit(None, dtype=pl.Utf8)

    platform = col("satellite") if modis else pl.lit(VIIRS_PLATFORM_BY_SOURCE[source])

    df = raw.select(
        pl.lit(source).alias("source"),
        pl.lit(sensor).alias("sensor"),
        platform.alias("platform"),
        col("latitude").cast(pl.Float64),
        col("longitude").cast(pl.Float64),
        (col("acq_date") + pl.lit(" ") + col("acq_time").str.zfill(4))
        .str.to_datetime("%Y-%m-%d %H%M", time_unit="us")
        .alias("acq_utc"),
        col("daynight"),
        col("frp").cast(pl.Float64),
        (
            col("confidence").cast(pl.Float64, strict=False)
            if modis
            else pl.lit(None, dtype=pl.Float64)
        ).alias("conf_num"),
        (pl.lit(None, dtype=pl.Utf8) if modis else col("confidence").str.to_lowercase()).alias(
            "conf_class"
        ),
        col(primary).cast(pl.Float64).alias("bright_primary"),
        col(secondary).cast(pl.Float64).alias("bright_secondary"),
        col("scan").cast(pl.Float64),
        col("track").cast(pl.Float64),
        col("type").cast(pl.Int64, strict=False).alias("fire_type"),
        pl.lit(False).alias("synthetic"),
    )
    df = add_time_columns(
        df.with_columns(
            pl.lit(0.0).alias("local_solar_hour"), pl.lit(None, dtype=pl.Date).alias("local_date")
        )
    )
    return df.select(list(COMMON_SCHEMA)).cast(COMMON_SCHEMA)  # type: ignore[arg-type]
