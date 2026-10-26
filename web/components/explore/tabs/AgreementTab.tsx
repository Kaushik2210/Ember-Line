"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";
import { axisStyle, baseOption, useChartColors } from "@/lib/chartTheme";
import type { CvRow, ResultPayload, TableRow, WeeklyPair } from "@/lib/types";
import { Chart } from "@/components/ui/Chart";
import { MetricPill } from "@/components/ui/MetricPill";

const UNIT: Record<string, string> = { frp_sum_mw: "MW", active_1km: "footprints", det_count: "detections" };
const pct = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "n/a" : `${(100 * v).toFixed(0)}%`);
const num = (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "n/a" : v.toFixed(d));

export function AgreementTab({ result }: { result: ResultPayload }) {
  const c = useChartColors();
  const norm = result.validation.normalization;
  const ov = result.validation.overpass;
  const unit = UNIT[result.meta.metric] ?? "";

  const scatter = (pairs: WeeklyPair[], which: "before" | "after"): EChartsOption => {
    const a = axisStyle(c);
    const xs = pairs.map((p) => (which === "before" ? p.modis : p.predicted)).filter((v): v is number => v != null && v > 0);
    const ys = pairs.map((p) => p.viirs).filter((v) => v > 0);
    const hi = Math.max(1, ...xs, ...ys);
    const data = pairs
      .map((p) => [which === "before" ? p.modis : p.predicted, p.viirs, p.week] as const)
      .filter(([x, y]) => x != null && x > 0 && y > 0);
    return {
      ...baseOption(c),
      grid: { left: 54, right: 12, top: 12, bottom: 38 },
      tooltip: { ...baseOption(c).tooltip, trigger: "item", formatter: (q: unknown) => { const d = (q as { data: [number, number, string] }).data; return `Week of ${d[2]}<br/>${which === "before" ? "MODIS" : "Normalised"}: ${Math.round(d[0]).toLocaleString("en-GB")}<br/>VIIRS: ${Math.round(d[1]).toLocaleString("en-GB")}`; } },
      xAxis: { type: "log", min: 1, max: hi * 1.3, name: which === "before" ? `MODIS weekly (${unit})` : `Normalised MODIS weekly (${unit})`, nameLocation: "middle", nameGap: 24, ...a },
      yAxis: { type: "log", min: 1, max: hi * 1.3, name: `VIIRS weekly (${unit})`, nameLocation: "middle", nameGap: 40, ...a },
      series: [
        { type: "line", data: [[1, 1], [hi * 1.3, hi * 1.3]], symbol: "none", lineStyle: { color: c.faint, type: "dashed", width: 1 }, silent: true, tooltip: { show: false } },
        { type: "scatter", data, symbolSize: 5, itemStyle: { color: which === "before" ? c.modis : c.harmonized, opacity: 0.65 } },
      ],
    } as EChartsOption;
  };

  const cvBy = useMemo(() => Object.fromEntries((norm?.cv ?? []).map((r) => [r.model, r])) as Record<string, CvRow>, [norm]);
  const raw = cvBy.raw;
  const best = norm ? cvBy[norm.chosen] : undefined;

  const bars = (rows: TableRow[], key: string, title: string) => {
    if (!rows.length) return null;
    const a = axisStyle(c);
    const opt = {
      ...baseOption(c),
      grid: { left: 42, right: 8, top: 22, bottom: 40 },
      legend: { top: 0, right: 0, textStyle: { color: c.muted, fontSize: 10 }, itemWidth: 10, itemHeight: 8 },
      tooltip: { ...baseOption(c).tooltip, trigger: "axis", valueFormatter: (v: unknown) => pct(v as number) },
      xAxis: { type: "category", data: rows.map((r) => String(r[key])), ...a, splitLine: { show: false } },
      yAxis: { type: "value", min: 0, max: 1, ...a, axisLabel: { ...a.axisLabel, formatter: (v: number) => `${Math.round(v * 100)}%` } },
      series: [
        { name: "MODIS seen by VIIRS", type: "bar", data: rows.map((r) => r.modis_corroborated ?? null), itemStyle: { color: c.modis }, barMaxWidth: 16 },
        { name: "VIIRS seen by MODIS", type: "bar", data: rows.map((r) => r.viirs_corroborated ?? null), itemStyle: { color: c.viirs }, barMaxWidth: 16 },
      ],
    } as EChartsOption;
    return (
      <div className="min-w-0">
        <h4 className="mb-1 text-xs font-medium text-muted">{title}</h4>
        <Chart option={opt} height={170} label={`${title}: share of detections the other sensor also saw.`} />
      </div>
    );
  };

  const nM = ov.n_modis_eval ?? 0;
  const nV = ov.n_viirs_eval ?? 0;
  const mSeen = Math.round((ov.modis_corroborated_by_viirs ?? 0) * nM);
  const vSeen = Math.round((ov.viirs_corroborated_by_modis ?? 0) * nV);

  return (
    <div className="flex flex-col gap-6 p-4">
      <section aria-labelledby="norm-h">
        <h3 id="norm-h" className="mb-1 text-sm font-semibold text-ink">Before and after normalising</h3>
        {norm && norm.pairs.length > 0 ? (
          <>
            <p className="mb-3 text-xs text-muted">
              Each dot is one week. On the right, every week is predicted by a model that never saw that week&apos;s year (leave-one-year-out), so the improvement is not self-flattery. The dashed line is perfect agreement.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <Chart option={scatter(norm.pairs, "before")} height={240} label="Weekly MODIS against weekly VIIRS before normalising, on log axes." />
              <Chart option={scatter(norm.pairs, "after")} height={240} label="Weekly normalised MODIS against weekly VIIRS on held-out years, on log axes." />
            </div>
            {raw && best && (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-xs">
                  <caption className="sr-only">Agreement before and after normalising</caption>
                  <thead>
                    <tr className="text-muted">
                      <th className="py-1 pr-3 font-medium">Measure</th>
                      <th className="py-1 pr-3 font-medium">Before (raw MODIS)</th>
                      <th className="py-1 font-medium">After ({norm.chosen})</th>
                    </tr>
                  </thead>
                  <tbody className="num text-ink">
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">Bias</td><td>{pct(raw.bias_rel)}</td><td>{pct(best.bias_rel)}</td></tr>
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">R² (log scale)</td><td>{num(raw.r2_log)}</td><td>{num(best.r2_log)}</td></tr>
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">Mean error (log scale)</td><td>{num(raw.mae_log)}</td><td>{num(best.mae_log)}</td></tr>
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">Mean error ({unit})</td><td>{raw.mae_raw != null ? Math.round(raw.mae_raw).toLocaleString("en-GB") : "n/a"}</td><td>{best.mae_raw != null ? Math.round(best.mae_raw).toLocaleString("en-GB") : "n/a"}</td></tr>
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">Rank correlation</td><td>{num(raw.spearman)}</td><td>{num(best.spearman)}</td></tr>
                    <tr className="border-t border-line"><td className="py-1.5 pr-3 font-sans text-muted">Held-out weeks inside the {pct(norm.level)} band</td><td>n/a</td><td>{pct(best.coverage)}</td></tr>
                  </tbody>
                </table>
              </div>
            )}
            <div className="mt-3 flex flex-wrap gap-1.5">
              <MetricPill label="Chosen model" value={norm.chosen} />
              <MetricPill label="Weeks" value={String(norm.n_weeks)} />
              <MetricPill label="Years" value={`${norm.years[0]}–${norm.years[norm.years.length - 1]}`} />
              {norm.interval_halfwidth_log1p != null && <MetricPill label="Band width" value={`×${(Math.expm1(norm.interval_halfwidth_log1p) + 1).toFixed(1)}`} tone="warn" />}
            </div>
            <p className="mt-2 text-xs text-faint">
              A wide band is an honest result: the sensors&apos; weekly totals differ by more than a fixed factor, so a harmonized value is an estimate with a range.
            </p>
            <details className="mt-3">
              <summary className="min-h-9 cursor-pointer text-xs font-medium text-muted hover:text-ink">All models compared</summary>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[480px] text-left text-xs">
                  <thead><tr className="text-muted"><th className="py-1 pr-3 font-medium">Model</th><th className="font-medium">R² log</th><th className="font-medium">Error log</th><th className="font-medium">Bias</th><th className="font-medium">Rank corr.</th><th className="font-medium">Coverage</th></tr></thead>
                  <tbody className="num text-ink">
                    {norm.cv.map((r) => (
                      <tr key={r.model} className="border-t border-line">
                        <td className="py-1.5 pr-3 font-sans">{r.model}{r.model === norm.chosen ? " (chosen)" : !r.selectable ? " (baseline)" : ""}</td>
                        <td>{num(r.r2_log)}</td><td>{num(r.mae_log)}</td><td>{pct(r.bias_rel)}</td><td>{num(r.spearman)}</td><td>{pct(r.coverage)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        ) : (
          <p className="text-sm text-muted">No normalisation was fitted for this run, so there is nothing to compare.</p>
        )}
      </section>

      <section aria-labelledby="ov-h">
        <h3 id="ov-h" className="mb-1 text-sm font-semibold text-ink">Coincident overpasses: Aqua-MODIS and Suomi NPP VIIRS</h3>
        {nM > 0 ? (
          <>
            <p className="mb-3 text-xs text-muted">
              The two satellites pass the same place within about half an hour. Detections within 750 m of each other count as the same fire. Only detections the other sensor could have seen are counted ({nM.toLocaleString("en-GB")} MODIS, {nV.toLocaleString("en-GB")} VIIRS).
            </p>
            <div className="grid gap-4 md:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
              <table className="w-full self-start text-left text-xs">
                <caption className="sr-only">Detections seen and not seen by the other sensor</caption>
                <thead>
                  <tr className="text-muted"><th className="py-1 pr-3 font-medium"> </th><th className="font-medium">Also seen</th><th className="font-medium">Missed</th></tr>
                </thead>
                <tbody className="num text-ink">
                  <tr className="border-t border-line"><th scope="row" className="py-2 pr-3 text-left font-sans font-medium" style={{ color: c.modis }}>MODIS detections</th><td>{mSeen.toLocaleString("en-GB")} ({pct(ov.modis_corroborated_by_viirs)})</td><td>{(nM - mSeen).toLocaleString("en-GB")} ({pct(ov.modis_unseen_by_viirs)})</td></tr>
                  <tr className="border-t border-line"><th scope="row" className="py-2 pr-3 text-left font-sans font-medium" style={{ color: c.viirs }}>VIIRS detections</th><td>{vSeen.toLocaleString("en-GB")} ({pct(ov.viirs_corroborated_by_modis)})</td><td>{(nV - vSeen).toLocaleString("en-GB")} ({pct(ov.viirs_unseen_by_modis)})</td></tr>
                </tbody>
                <tfoot>
                  {result.validation.frp_ratio.median_viirs_over_modis != null && (
                    <tr className="border-t border-line"><td colSpan={3} className="pt-2 font-sans text-xs text-muted">Matched fires: VIIRS reports a median of <span className="num text-ink">{num(result.validation.frp_ratio.median_viirs_over_modis)}×</span> the MODIS radiative power (10th–90th percentile {num(result.validation.frp_ratio.p10)}–{num(result.validation.frp_ratio.p90)}).</td></tr>
                  )}
                </tfoot>
              </table>
              <div className="grid gap-4 sm:grid-cols-2">
                {bars(result.validation.tables.by_frp, "frp_bin", "By fire power (MW)")}
                {bars(result.validation.tables.by_daynight, "daynight", "Day and night")}
                {bars(result.validation.tables.by_scan, "scan_bin", "By MODIS pixel size (km)")}
              </div>
            </div>
            <p className="mt-2 text-xs text-faint">
              VIIRS sees many small, cool fires that MODIS cannot, so far fewer VIIRS detections have a MODIS partner. Agreement rises with fire power, and MODIS pixels grow toward the edge of its scan.
            </p>
          </>
        ) : (
          <p className="text-sm text-muted">No coincident overpasses could be matched for this region and period.</p>
        )}
      </section>
    </div>
  );
}
