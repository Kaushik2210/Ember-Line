"""Calendar-complete daily and weekly series from `grid.daily_series` output.

A day with no detections has no row, so naive sums mix up "nothing burned" with "this sensor
was not observing". Here each sensor is zero-filled only inside its own observed period
(first to last day it has any data in the loaded record); outside it the value is null.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

METRICS = ("det_count", "active_1km", "frp_sum_mw")


def sensor_periods(ds: pl.DataFrame) -> dict[str, tuple[date, date]]:
    g = ds.group_by("sensor").agg(
        pl.col("local_date").min().alias("lo"), pl.col("local_date").max().alias("hi")
    )
    return {r["sensor"]: (r["lo"], r["hi"]) for r in g.iter_rows(named=True)}


def calendar_series(
    ds: pl.DataFrame,
    metric: str,
    start: date | None = None,
    end: date | None = None,
    daynight: str | None = None,
    periods: dict[str, tuple[date, date]] | None = None,
    observed: dict[str, list[date]] | None = None,
) -> pl.DataFrame:
    """Daily values per sensor, columns: local_date, modis, viirs (null where not observed).

    `daynight` None sums day and night. `periods` overrides each sensor's observed period
    (e.g. the availability range reported by FIRMS) when the loaded record is shorter.
    `observed` lists, per sensor, the exact days that were downloaded (see data.coverage); a day
    outside it is null even inside the sensor's period, so a failed download is a gap, not zeros.
    """
    if metric not in METRICS:
        raise ValueError(f"unknown metric {metric}")
    if ds.height == 0:
        return pl.DataFrame(
            schema={"local_date": pl.Date, "modis": pl.Float64, "viirs": pl.Float64}
        )
    periods = periods or sensor_periods(ds)
    if observed:
        periods = {
            **periods,
            **{k: (min(v), max(v)) for k, v in observed.items() if v},
        }
    src = ds if daynight is None else ds.filter(pl.col("daynight") == daynight)
    lo = start or min(p[0] for p in periods.values())
    hi = end or max(p[1] for p in periods.values())
    days = pl.DataFrame({"local_date": pl.date_range(lo, hi, "1d", eager=True)})
    out = days
    for sensor in ("modis", "viirs"):
        vals = (
            src.filter(pl.col("sensor") == sensor)
            .group_by("local_date")
            .agg(pl.col(metric).sum().cast(pl.Float64).alias(sensor))
        )
        out = out.join(vals, on="local_date", how="left")
        if observed is not None and sensor in observed:
            seen = pl.Series(observed[sensor], dtype=pl.Date)
            out = out.with_columns(
                pl.when(pl.col("local_date").is_in(seen.implode()))
                .then(pl.col(sensor).fill_null(0.0))
                .otherwise(None)
                .alias(sensor)
            )
        elif sensor in periods:
            plo, phi = periods[sensor]
            out = out.with_columns(
                pl.when(pl.col("local_date").is_between(plo, phi))
                .then(pl.col(sensor).fill_null(0.0))
                .otherwise(None)
                .alias(sensor)
            )
        else:
            out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias(sensor))
    return out.sort("local_date")


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly(daily: pl.DataFrame) -> pl.DataFrame:
    """Sum calendar days into Monday-start weeks. A week is kept only if all 7 days were observed
    by the sensor; otherwise that sensor's value for the week is null (partial weeks bias sums)."""
    w = daily.with_columns(pl.col("local_date").dt.truncate("1w").alias("week"))
    aggs = []
    for s in ("modis", "viirs"):
        aggs.append(pl.when(pl.col(s).count() == 7).then(pl.col(s).sum()).otherwise(None).alias(s))
    return w.group_by("week").agg(*aggs).sort("week")


def weekly_pairs(daily: pl.DataFrame) -> pl.DataFrame:
    """Weeks where both sensors have a complete value: the overlap used to fit normalisation."""
    return weekly(daily).drop_nulls(["modis", "viirs"])
