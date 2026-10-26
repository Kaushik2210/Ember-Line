"""Normalisation: map the MODIS record onto VIIRS-equivalent units, with uncertainty.

Models are fitted on weekly totals over the overlap period (both sensors flying), in
log1p space so that the heavy-tailed, zero-heavy totals behave:
    u = log1p(MODIS weekly metric)  ->  v = log1p(VIIRS weekly metric)

Candidates:
  huber       log-log line, Huber loss (robust to outlier weeks)
  theilsen    log-log line, Theil-Sen (median of pairwise slopes)
  quantile    seasonal quantile mapping: match the MODIS CDF to the VIIRS CDF per season
  isotonic    monotone non-decreasing step fit
Baselines for context only (never selected): `raw` (use MODIS as is) and `scale`
(one multiplicative factor).

Selection is by leave-one-year-out cross-validation: each year is predicted by a model fitted
on the other years. Intervals are cross-conformal: the (1-alpha) quantile of the absolute
out-of-fold residuals of the other years, so coverage is checked on data the model never saw.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import HuberRegressor, TheilSenRegressor

SEASONS = {
    12: 0,
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 2,
    9: 3,
    10: 3,
    11: 3,
}  # DJF MAM JJA SON
EXTRAPOLATION_WIDEN = 1.5  # interval multiplier where MODIS exceeds the range seen when fitting
MIN_WEEKS = 40


def season_of(weeks: list[date]) -> np.ndarray:
    return np.array([SEASONS[w.month] for w in weeks], dtype=np.int64)


def _slope_one_tail(u: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Outside the fitted range keep the edge offset (a constant ratio in log space)."""
    out = np.interp(u, xs, ys)
    out = np.where(u > xs[-1], ys[-1] + (u - xs[-1]), out)
    return np.asarray(np.where(u < xs[0], np.maximum(ys[0] + (u - xs[0]), 0.0), out))


class Model(ABC):
    name: str

    @abstractmethod
    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model: ...

    @abstractmethod
    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray: ...


class RawBaseline(Model):
    name = "raw"

    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model:
        return self

    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray:
        return u.copy()


class ScaleBaseline(Model):
    name = "scale"

    def __init__(self) -> None:
        self.shift = 0.0

    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model:
        self.shift = float(np.median(v - u))
        return self

    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray:
        return np.asarray(np.maximum(u + self.shift, 0.0))


class _Linear(Model):
    reg: Any

    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model:
        self.reg.fit(u.reshape(-1, 1), v)
        return self

    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray:
        return np.asarray(np.maximum(self.reg.predict(u.reshape(-1, 1)), 0.0))

    @property
    def coef(self) -> tuple[float, float]:
        return float(self.reg.intercept_), float(self.reg.coef_[0])


class HuberLogLog(_Linear):
    name = "huber"

    def __init__(self) -> None:
        self.reg = HuberRegressor(epsilon=1.35, alpha=0.0, max_iter=500)


class TheilSenLogLog(_Linear):
    name = "theilsen"

    def __init__(self) -> None:
        self.reg = TheilSenRegressor(random_state=0)


class QuantileMapping(Model):
    name = "quantile"
    GRID = np.linspace(0.0, 1.0, 51)

    def __init__(self, min_per_season: int = 20) -> None:
        self.min_per_season = min_per_season
        self.maps: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self.pooled: tuple[np.ndarray, np.ndarray] | None = None

    def _build(self, u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return np.quantile(u, self.GRID), np.quantile(v, self.GRID)

    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model:
        self.pooled = self._build(u, v)
        self.maps = {
            s: self._build(u[season == s], v[season == s])
            for s in np.unique(season)
            if (season == s).sum() >= self.min_per_season
        }
        return self

    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray:
        assert self.pooled is not None
        out = np.empty_like(u, dtype=float)
        for s in np.unique(season):
            m = season == s
            xs, ys = self.maps.get(int(s), self.pooled)
            out[m] = _slope_one_tail(u[m], xs, ys)
        return out


class IsotonicMap(Model):
    name = "isotonic"

    def __init__(self) -> None:
        self.iso = IsotonicRegression(increasing=True, out_of_bounds="clip", y_min=0.0)
        self.lo = self.hi = 0.0
        self.xs = np.array([0.0])
        self.ys = np.array([0.0])

    def fit(self, u: np.ndarray, v: np.ndarray, season: np.ndarray) -> Model:
        self.iso.fit(u, v)
        grid = np.unique(u)
        self.xs, self.ys = grid, self.iso.predict(grid)
        return self

    def predict(self, u: np.ndarray, season: np.ndarray) -> np.ndarray:
        return _slope_one_tail(u, self.xs, self.ys)


def default_models() -> list[Model]:
    return [HuberLogLog(), TheilSenLogLog(), QuantileMapping(), IsotonicMap()]


def _fresh(m: Model) -> Model:
    return type(m)()


def _metrics(u_true: np.ndarray, v_hat: np.ndarray, v: np.ndarray) -> dict[str, float]:
    y, yhat = np.expm1(v), np.expm1(v_hat)
    ss_res, ss_tot = float(np.sum((v - v_hat) ** 2)), float(np.sum((v - v.mean()) ** 2))
    rho = spearmanr(y, yhat).statistic if np.ptp(yhat) > 0 and np.ptp(y) > 0 else float("nan")
    return {
        "r2_log": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "mae_log": float(np.mean(np.abs(v - v_hat))),
        "mae_raw": float(np.mean(np.abs(y - yhat))),
        "bias_rel": float((yhat.sum() - y.sum()) / y.sum()) if y.sum() > 0 else float("nan"),
        "spearman": float(rho),
    }


def _conformal_q(abs_res: np.ndarray, level: float) -> float:
    n = len(abs_res)
    if n == 0:
        return float("nan")
    k = min(1.0, np.ceil((n + 1) * level) / n)
    return float(np.quantile(abs_res, k))


@dataclass
class NormalizationResult:
    chosen: str
    model: Model
    cv: pl.DataFrame
    q: float  # (level) quantile of absolute log residuals for the chosen model
    level: float
    n_weeks: int
    years: list[int]
    fit_u_max: float
    metric: str = ""
    warnings: list[str] = field(default_factory=list)
    # weekly overlap with each week's out-of-fold prediction (the year was left out when fitting)
    pairs: pl.DataFrame = field(default_factory=pl.DataFrame)

    def predict_weekly(
        self, modis: np.ndarray, weeks: list[date]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(value, lo, hi) in VIIRS-equivalent units for weekly MODIS totals."""
        u = np.log1p(np.asarray(modis, dtype=float))
        v = self.model.predict(u, season_of(weeks))
        widen = np.where(u > self.fit_u_max, EXTRAPOLATION_WIDEN, 1.0)
        lo = np.maximum(np.expm1(v - self.q * widen), 0.0)
        hi = np.expm1(v + self.q * widen)
        return np.expm1(v), lo, hi


def fit_normalizer(
    pairs: pl.DataFrame,
    level: float = 0.9,
    models: list[Model] | None = None,
    min_weeks: int = MIN_WEEKS,
    metric: str = "",
    force: str | None = None,
) -> NormalizationResult:
    """Fit candidates on overlap weeks (columns: week, modis, viirs), pick the best by LOYO CV.

    `force` names a model to use instead of the best one; all candidates are still scored so
    the comparison stays visible."""
    if pairs.height < min_weeks:
        raise ValueError(f"need at least {min_weeks} overlapping weeks, have {pairs.height}")
    weeks = pairs["week"].to_list()
    u = np.log1p(pairs["modis"].to_numpy().astype(float))
    v = np.log1p(pairs["viirs"].to_numpy().astype(float))
    season = season_of(weeks)
    year = np.array([w.year for w in weeks])
    years = sorted(set(year.tolist()))
    if len(years) < 3:
        raise ValueError("need at least 3 distinct years for leave-one-year-out validation")

    candidates = (models or default_models()) + [RawBaseline(), ScaleBaseline()]
    oof: dict[str, np.ndarray] = {}
    for m in candidates:
        pred = np.full(len(u), np.nan)
        for y in years:
            te, tr = year == y, year != y
            fitted = _fresh(m).fit(u[tr], v[tr], season[tr])
            pred[te] = fitted.predict(u[te], season[te])
        oof[m.name] = pred

    rows = []
    for m in candidates:
        pred = oof[m.name]
        res = np.abs(v - pred)
        covered = []
        for y in years:  # cross-conformal: threshold from the other years' residuals
            q_other = _conformal_q(res[year != y], level)
            covered.append(res[year == y] <= q_other)
        rows.append(
            {
                "model": m.name,
                "selectable": m.name not in ("raw", "scale"),
                **_metrics(u, pred, v),
                "coverage": float(np.concatenate(covered).mean()),
            }
        )
    cv = pl.DataFrame(rows)
    selectable = cv.filter(pl.col("selectable")).sort("mae_log")
    if force is not None and force not in selectable["model"].to_list():
        raise ValueError(f"unknown model {force!r}; choose one of {selectable['model'].to_list()}")
    best = force or selectable.row(0, named=True)["model"]
    chosen = next(m for m in candidates if m.name == best)
    final = _fresh(chosen).fit(u, v, season)
    q = _conformal_q(np.abs(v - oof[best]), level)
    pred = oof[best]
    pairs_out = pl.DataFrame(
        {
            "week": weeks,
            "modis": pairs["modis"].to_numpy(),
            "viirs": pairs["viirs"].to_numpy(),
            "predicted": np.expm1(pred),
            "lo": np.maximum(np.expm1(pred - q), 0.0),
            "hi": np.expm1(pred + q),
        }
    )
    return NormalizationResult(
        chosen=best,
        model=final,
        cv=cv,
        q=q,
        level=level,
        n_weeks=len(u),
        years=years,
        fit_u_max=float(u.max()),
        metric=metric,
        pairs=pairs_out,
    )


def harmonize(daily: pl.DataFrame, result: NormalizationResult) -> pl.DataFrame:
    """VIIRS-equivalent daily series over the full record.

    Where VIIRS observed, its own values are used (`reconstructed` False, no band). Elsewhere
    the weekly MODIS total is mapped through the fitted model and spread over the days in
    proportion to MODIS's own daily pattern (uniformly if the week had no MODIS detections), with
    prediction bands (`reconstructed` True). Only complete weeks are reconstructed.

    Input columns: local_date, modis, viirs (null where a sensor was not observing).
    """
    d = daily.sort("local_date").with_columns(pl.col("local_date").dt.truncate("1w").alias("week"))
    wk = (
        d.group_by("week")
        .agg(pl.col("modis").count().alias("n_modis"), pl.col("modis").sum().alias("w_modis"))
        .sort("week")
    )
    full = wk.filter(pl.col("n_modis") == 7)
    val, lo, hi = result.predict_weekly(full["w_modis"].to_numpy(), full["week"].to_list())
    mapped = full.select("week", "w_modis").with_columns(
        pl.Series("w_val", val), pl.Series("w_lo", lo), pl.Series("w_hi", hi)
    )
    out = d.join(mapped, on="week", how="left")

    def spread(col: str) -> pl.Expr:
        share = (
            pl.when(pl.col("w_modis") > 0)
            .then(pl.col("modis") / pl.col("w_modis"))
            .otherwise(1 / 7)
        )
        return pl.col(col) * share

    out = out.with_columns(
        spread("w_val").alias("m_val"), spread("w_lo").alias("m_lo"), spread("w_hi").alias("m_hi")
    )
    observed = pl.col("viirs").is_not_null()
    return out.select(
        "local_date",
        pl.when(observed).then(pl.col("viirs")).otherwise(pl.col("m_val")).alias("harmonized"),
        pl.when(observed).then(pl.col("viirs")).otherwise(pl.col("m_lo")).alias("lo"),
        pl.when(observed).then(pl.col("viirs")).otherwise(pl.col("m_hi")).alias("hi"),
        (~observed).alias("reconstructed"),
        pl.col("modis").alias("modis_raw"),
        pl.col("viirs").alias("viirs_raw"),
    )


def harmonize_with_early(
    daily: pl.DataFrame,
    result: NormalizationResult,
    daily_early: pl.DataFrame,
    result_early: NormalizationResult,
    cutoff: date,
) -> pl.DataFrame:
    """Harmonise, using a separate model for the weeks before `cutoff`.

    Before Aqua flew, MODIS fire data come from Terra alone and carry roughly a third of the
    detections, so the two-satellite model would read those years as unusually quiet.
    `daily_early` has the same columns as `daily` but with MODIS counted from Terra only, and
    `result_early` is calibrated on that. `cutoff` is moved to the next Monday so weeks stay whole.
    Adds `modis_basis`: "terra" for the early weeks, "terra+aqua" afterwards.
    """
    cut = cutoff + timedelta(days=(7 - cutoff.weekday()) % 7)
    late = harmonize(daily, result).with_columns(pl.lit("terra+aqua").alias("modis_basis"))
    early = harmonize(daily_early, result_early).with_columns(pl.lit("terra").alias("modis_basis"))
    return pl.concat(
        [early.filter(pl.col("local_date") < cut), late.filter(pl.col("local_date") >= cut)]
    ).sort("local_date")
