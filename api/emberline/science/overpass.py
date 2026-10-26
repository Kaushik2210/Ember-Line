"""Coincident-overpass analysis: Aqua-MODIS vs SNPP-VIIRS space-time matching.

Aqua and Suomi-NPP cross the same area within minutes of each other (both ~13:30 local), so
detections that are close in space and time describe the same fires. Matching them shows what
each sensor catches that the other misses, free of overpass-time differences.

Matching rule: a VIIRS detection is matched to the nearest MODIS detection within `max_dist_m`
and `max_dt_min` (default 750 m, 30 min). Measured on Punjab/Haryana data, SNPP detections trail
Aqua detections of the same place by a median of ~16 min (IQR about -10 to +28), so a 10 min window
would discard most true coincidences; see docs/DECISIONS.md. Several VIIRS pixels can fall in one MODIS pixel, so
the relation is many-to-one; a MODIS pixel is "corroborated" if at least one VIIRS pixel matched.

Co-observation: a detection can only be judged by the other sensor if that sensor was looking.
FIRMS has no swath masks, so as a proxy a detection counts only if the other sensor has any
detection within `cooccur_km` and `max_dt_min` (a box, not a circle). Detections without that
are reported as `not_coobserved` and excluded from the rates. In very quiet scenes this proxy
is conservative, and it can bias rates toward busy scenes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from scipy.spatial import cKDTree

EARTH_R_M = 6_371_000.0
SCAN_BINS = [1.0, 1.5, 2.0, 3.0, 99.0]  # MODIS along-scan pixel size (km): grows off-nadir
FRP_BINS = [0.0, 5.0, 10.0, 20.0, 50.0, 1e9]


def _xyz(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return EARTH_R_M * np.column_stack(
        [np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
    )


def _points(df: pl.DataFrame, t0: np.datetime64, m_per_min: float) -> np.ndarray:
    minutes = (df["acq_utc"].to_numpy() - t0) / np.timedelta64(1, "m")
    xyz = _xyz(df["latitude"].to_numpy(), df["longitude"].to_numpy())
    return np.column_stack([xyz, minutes * m_per_min])


def _nearest_within(
    src: np.ndarray, dst: np.ndarray, max_dist_m: float, max_dt_min: float, k: int = 16
) -> tuple[np.ndarray, np.ndarray]:
    """For each src point, index of the nearest dst point within distance and time limits.

    Returns (index, distance_m); index is -1 where nothing qualifies. Time is the 4th axis,
    scaled so max_dt_min equals max_dist_m, then a Chebyshev query prunes candidates and the
    exact Euclidean distance on the sphere decides.
    """
    idx = np.full(len(src), -1, dtype=np.int64)
    dist = np.full(len(src), np.inf)
    if len(src) == 0 or len(dst) == 0:
        return idx, dist
    scale = max_dist_m / max_dt_min
    s, d = src.copy(), dst.copy()
    s[:, 3] *= scale
    d[:, 3] *= scale
    tree = cKDTree(d)
    kk = min(k, len(d))
    _, cand = tree.query(s, k=kk, p=np.inf, distance_upper_bound=max_dist_m * (1 + 1e-9))
    cand = cand.reshape(len(s), kk)
    valid = cand < len(d)
    for j in range(kk):
        c = cand[:, j]
        ok = valid[:, j]
        cj = np.where(ok, c, 0)
        d3 = np.linalg.norm(src[:, :3] - dst[cj, :3], axis=1)
        dt = np.abs(src[:, 3] - dst[cj, 3])  # minutes
        good = ok & (d3 <= max_dist_m) & (dt <= max_dt_min) & (d3 < dist)
        idx[good] = c[good]
        dist[good] = d3[good]
    return idx, dist


def _coobserved(a: np.ndarray, b: np.ndarray, cooccur_km: float, max_dt_min: float) -> np.ndarray:
    """True where `b` has any point within a cooccur_km / max_dt_min box of each `a` point."""
    out = np.zeros(len(a), dtype=bool)
    if len(a) == 0 or len(b) == 0:
        return out
    r = cooccur_km * 1000.0
    scale = r / max_dt_min
    s, d = a.copy(), b.copy()
    s[:, 3] *= scale
    d[:, 3] *= scale
    dd, _ = cKDTree(d).query(s, k=1, p=np.inf, distance_upper_bound=r)
    return np.asarray(np.isfinite(dd))


@dataclass
class MatchResult:
    summary: dict[str, float]
    frp_ratio: dict[str, float]
    by_scan: pl.DataFrame
    by_frp: pl.DataFrame
    by_daynight: pl.DataFrame
    pairs: pl.DataFrame = field(repr=False, default_factory=pl.DataFrame)


def _bin(df: pl.DataFrame, col: str, edges: list[float], name: str) -> pl.DataFrame:
    """Add `name` (readable label) and `name_i` (ordering index) for `col` binned at `edges`."""
    inner = edges[1:-1]
    idx = np.digitize(df[col].to_numpy(), inner)
    labels = [f"<{inner[0]:g}"]
    labels += [f"{a:g}-{b:g}" for a, b in zip(inner, inner[1:], strict=False)]
    labels.append(f">={inner[-1]:g}")
    return df.with_columns(
        pl.Series(f"{name}_i", idx, dtype=pl.Int64),
        pl.Series(name, [labels[k] for k in idx], dtype=pl.Utf8),
    )


def _rate_table(df: pl.DataFrame, key: str, rate: str) -> pl.DataFrame:
    keys = [key, f"{key}_i"] if f"{key}_i" in df.columns else [key]
    return (
        df.group_by(keys)
        .agg(pl.len().alias("n"), pl.col(rate).mean().alias("matched_rate"))
        .sort(keys[-1])
    )


def _mean(s: pl.Series) -> float:
    v = s.cast(pl.Float64).mean()
    return float(v) if isinstance(v, int | float) else float("nan")


def match_coincident(
    modis: pl.DataFrame,
    viirs: pl.DataFrame,
    max_dist_m: float = 750.0,
    max_dt_min: float = 30.0,
    cooccur_km: float = 25.0,
) -> MatchResult:
    """Match Aqua-MODIS (or any MODIS input) against SNPP-VIIRS. Inputs are common-schema frames."""
    empty_tbl = pl.DataFrame()
    if modis.height == 0 or viirs.height == 0:
        return MatchResult(
            {"n_modis": float(modis.height), "n_viirs": float(viirs.height)},
            {},
            empty_tbl,
            empty_tbl,
            empty_tbl,
        )

    t0_np = np.minimum(modis["acq_utc"].to_numpy().min(), viirs["acq_utc"].to_numpy().min())
    m_per_min = 1.0  # time axis in minutes; scaled inside the helpers
    mp, vp = _points(modis, t0_np, m_per_min), _points(viirs, t0_np, m_per_min)

    # spatial-temporal match, VIIRS -> nearest MODIS
    vi_to_mo, _ = _nearest_within(vp, mp, max_dist_m, max_dt_min)
    v_matched = vi_to_mo >= 0
    m_corroborated = np.zeros(len(mp), dtype=bool)
    m_corroborated[vi_to_mo[v_matched]] = True

    # co-observation proxy
    m_coobs = _coobserved(mp, vp, cooccur_km, max_dt_min)
    v_coobs = _coobserved(vp, mp, cooccur_km, max_dt_min)

    m = modis.with_columns(pl.Series("matched", m_corroborated), pl.Series("coobs", m_coobs))
    v = viirs.with_columns(pl.Series("matched", v_matched), pl.Series("coobs", v_coobs))
    m_eval, v_eval = m.filter(pl.col("coobs")), v.filter(pl.col("coobs"))

    # FRP ratio per corroborated MODIS pixel: sum of matched VIIRS FRP / MODIS FRP
    vfrp = (
        pl.DataFrame({"mi": vi_to_mo[v_matched], "vfrp": viirs["frp"].to_numpy()[v_matched]})
        .group_by("mi")
        .agg(pl.col("vfrp").sum(), pl.len().alias("n_viirs_px"))
    )
    pairs = (
        pl.DataFrame(
            {
                "mi": np.arange(len(mp)),
                "modis_frp": modis["frp"].to_numpy(),
                "scan": modis["scan"].to_numpy(),
                "daynight": modis["daynight"].to_numpy(),
            }
        )
        .join(vfrp, on="mi", how="inner")
        .filter((pl.col("modis_frp") > 0) & (pl.col("vfrp") > 0))
        .with_columns((pl.col("vfrp") / pl.col("modis_frp")).log10().alias("log10_ratio"))
    )
    lr = pairs["log10_ratio"].to_numpy()
    ratio = (
        {
            "n_pairs": float(len(lr)),
            "median_viirs_over_modis": float(10 ** np.median(lr)),
            "p10": float(10 ** np.percentile(lr, 10)),
            "p90": float(10 ** np.percentile(lr, 90)),
        }
        if len(lr)
        else {}
    )

    n_m, n_v = m_eval.height, v_eval.height
    summary = {
        "n_modis": float(modis.height),
        "n_viirs": float(viirs.height),
        "modis_not_coobserved": float(modis.height - n_m),
        "viirs_not_coobserved": float(viirs.height - n_v),
        "n_modis_eval": float(n_m),  # co-observed counts: weights for combining periods
        "n_viirs_eval": float(n_v),
        # share of co-observed MODIS pixels that VIIRS also saw / VIIRS pixels MODIS also saw
        "modis_corroborated_by_viirs": _mean(m_eval["matched"]) if n_m else float("nan"),
        "viirs_corroborated_by_modis": _mean(v_eval["matched"]) if n_v else float("nan"),
    }
    # omission/commission of each sensor relative to the other
    summary["modis_unseen_by_viirs"] = 1.0 - summary["modis_corroborated_by_viirs"]
    summary["viirs_unseen_by_modis"] = 1.0 - summary["viirs_corroborated_by_modis"]

    m_eval = _bin(_bin(m_eval, "scan", SCAN_BINS, "scan_bin"), "frp", FRP_BINS, "frp_bin")
    v_eval = _bin(v_eval, "frp", FRP_BINS, "frp_bin")
    by_frp = (
        _rate_table(m_eval, "frp_bin", "matched")
        .rename({"n": "n_modis", "matched_rate": "modis_corroborated"})
        .join(
            _rate_table(v_eval, "frp_bin", "matched").rename(
                {"n": "n_viirs", "matched_rate": "viirs_corroborated"}
            ),
            on=["frp_bin", "frp_bin_i"],
            how="full",
            coalesce=True,
        )
        .sort("frp_bin_i")
    )
    by_dn = (
        _rate_table(m_eval, "daynight", "matched")
        .rename({"n": "n_modis", "matched_rate": "modis_corroborated"})
        .join(
            _rate_table(v_eval, "daynight", "matched").rename(
                {"n": "n_viirs", "matched_rate": "viirs_corroborated"}
            ),
            on="daynight",
            how="full",
            coalesce=True,
        )
        .sort("daynight")
    )
    by_scan = _rate_table(m_eval, "scan_bin", "matched").rename(
        {"n": "n_modis", "matched_rate": "modis_corroborated"}
    )
    return MatchResult(summary, ratio, by_scan, by_frp, by_dn, pairs)


def combine_summaries(parts: list[dict[str, float]]) -> dict[str, float]:
    """Merge summaries of several matches (e.g. one per year), weighting rates by co-observed counts."""
    parts = [p for p in parts if p.get("n_modis_eval") is not None]
    out: dict[str, float] = {}
    for key in (
        "n_modis",
        "n_viirs",
        "modis_not_coobserved",
        "viirs_not_coobserved",
        "n_modis_eval",
        "n_viirs_eval",
    ):
        out[key] = sum(p.get(key, 0.0) for p in parts)
    for rate, weight in (
        ("modis_corroborated_by_viirs", "n_modis_eval"),
        ("viirs_corroborated_by_modis", "n_viirs_eval"),
    ):
        w = [(p[rate], p[weight]) for p in parts if p.get(weight, 0) > 0 and p[rate] == p[rate]]
        tot = sum(x for _, x in w)
        out[rate] = sum(r * x for r, x in w) / tot if tot else float("nan")
    out["modis_unseen_by_viirs"] = 1.0 - out["modis_corroborated_by_viirs"]
    out["viirs_unseen_by_modis"] = 1.0 - out["viirs_corroborated_by_modis"]
    return out
