"""Markdown validation report for one analysed region. Every figure comes from the Analysis."""

from __future__ import annotations

import polars as pl

from emberline.pipeline import Analysis
from emberline.science.anomalies import describe_event, describe_season
from emberline.science.series import METRICS, calendar_series, weekly_pairs


def md(df: pl.DataFrame, floats: int = 3) -> str:
    if df.height == 0:
        return "_(none)_"
    rows = []
    for r in df.iter_rows():
        rows.append(
            [
                f"{v:,.{floats}f}"
                if isinstance(v, float)
                else f"{v:,}"
                if isinstance(v, int) and not isinstance(v, bool)
                else str(v)
                for v in r
            ]
        )
    out = ["| " + " | ".join(df.columns) + " |", "|" + "|".join("---" for _ in df.columns) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def raw_mismatch(a: Analysis) -> str:
    """Yearly totals per sensor over weeks where both sensors observed, for each metric."""
    blocks = []
    for m in METRICS:
        cs = calendar_series(a.ds, m, a.start, a.end, observed=a.observed)
        pairs = weekly_pairs(cs)
        if pairs.height == 0:
            continue
        by_year = (
            pairs.with_columns(pl.col("week").dt.year().alias("year"))
            .group_by("year")
            .agg(pl.col("modis").sum(), pl.col("viirs").sum(), pl.len().alias("weeks"))
            .with_columns((pl.col("viirs") / pl.col("modis")).alias("viirs/modis"))
            .sort("year")
        )
        tot = float(pairs["viirs"].to_numpy().sum() / pairs["modis"].to_numpy().sum())
        blocks.append(
            f"**{m}**: VIIRS / MODIS over all overlap weeks = {tot:.2f}\n\n{md(by_year, 2)}"
        )
    return "\n\n".join(blocks)


def report(a: Analysis, name: str, coverage: pl.DataFrame) -> str:
    L: list[str] = [f"# Validation report: {name}\n"]
    L.append(
        f"Period {a.start} to {a.end}. Metric: `{a.metric}`. Grid: {a.grid.kind} "
        f"({a.grid.size_deg:g} deg). Day/night: {a.policy.daynight}."
    )
    if a.synthetic:
        L.append("\n**SYNTHETIC DATA: not real observations.**")
    L.append("\n## Data\n")
    L.append(md(coverage, 0))
    c = a.counts
    L.append(
        f"\nQuality policy kept {c['kept']:,} of {c['raw']:,} detections "
        f"(MODIS {c['modis_kept']:,}, VIIRS {c['viirs_kept']:,}); "
        f"{c['persistent_cells']} persistent heat-source cells masked."
    )
    L.append("\n## 1. The sensors disagree (raw, before normalisation)\n")
    L.append(raw_mismatch(a))
    o = a.overpass
    if o:
        L.append("\n## 2. Coincident overpasses: Aqua-MODIS vs SNPP-VIIRS\n")
        L.append(
            f"Pairs within 750 m and 30 min. {o['n_modis_eval']:,.0f} MODIS and "
            f"{o['n_viirs_eval']:,.0f} VIIRS detections were co-observed "
            f"({o['modis_not_coobserved']:,.0f} MODIS / {o['viirs_not_coobserved']:,.0f} VIIRS "
            f"excluded because the other sensor had no detection nearby in that window).\n"
        )
        L.append(
            f"- MODIS detections also seen by VIIRS: **{o['modis_corroborated_by_viirs']:.1%}**"
        )
        L.append(
            f"- VIIRS detections also seen by MODIS: **{o['viirs_corroborated_by_modis']:.1%}**"
        )
        if a.frp_ratio:
            r = a.frp_ratio
            L.append(
                f"- FRP of matched fires, VIIRS (summed over its pixels) / MODIS: median "
                f"{r['median_viirs_over_modis']:.2f} (P10 {r['p10']:.2f}, P90 {r['p90']:.2f}, "
                f"n={r['n_pairs']:,.0f})"
            )
        titles = (
            ("by_frp", "by FRP (MW)"),
            ("by_daynight", "by day/night"),
            ("by_scan", "by MODIS pixel size (km)"),
        )
        for k, title in titles:
            t = a.overpass_tables.get(k)
            if t is not None and t.height:
                shown = t.drop([x for x in t.columns if x.endswith("_i")])
                L.append(f"\n{title}:\n\n{md(shown)}")
    if a.norm:
        n = a.norm
        L.append("\n## 3. Normalisation (leave-one-year-out cross-validation)\n")
        L.append(
            f"{n.n_weeks} overlapping weeks, years {n.years[0]}-{n.years[-1]}. "
            f"Chosen model: **{n.chosen}**. `raw` and `scale` are baselines, not candidates.\n"
        )
        L.append(md(n.cv.drop("selectable")))
        L.append(
            f"\nInterval half-width in log1p units: {n.q:.3f} at {n.level:.0%} nominal coverage."
        )
    if a.harmonized is not None:
        h = a.harmonized
        rec = h.filter(pl.col("reconstructed") & pl.col("harmonized").is_not_null())
        L.append("\n## 4. Harmonised record\n")
        L.append(f"{h.height:,} days, of which {rec.height:,} reconstructed from MODIS.")
    if a.markers:
        m = a.markers
        L.append("\n## 5. Seasonality\n")
        L.append(
            f"Fire season (10% / 50% / 90% of cumulative activity): day of year "
            f"{m.start_doy} / {m.peak_doy} / {m.end_doy}, about {m.length_days} days long."
        )
    if a.seasons is not None and a.seasons.height:
        L.append("\n## 6. Most unusual seasons\n")
        for r in a.seasons.head(5).iter_rows(named=True):
            L.append(f"- {describe_season(str(r['season']), float(r['z']), a.seasons.height)}")
    if a.events:
        L.append("\n## 7. Sustained unusual periods\n")
        top = sorted(a.events, key=lambda e: abs(e.mean_z) * e.days, reverse=True)[:8]
        L += [f"- {describe_event(e)}" for e in top]
    L.append("\n## Notes\n")
    L += [f"- {x}" for x in a.notes]
    return "\n".join(L) + "\n"
