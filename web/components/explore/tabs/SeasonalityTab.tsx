"use client";

import type { EChartsOption } from "echarts";
import { useMemo, useState } from "react";
import { dateOfCell } from "@/lib/calendar";
import { axisStyle, baseOption, useChartColors } from "@/lib/chartTheme";
import type { Markers, ResultPayload } from "@/lib/types";
import { useExploreParams } from "@/lib/urlState";
import { Chart } from "@/components/ui/Chart";
import { Select } from "@/components/ui/Field";
import { Switch } from "@/components/ui/Field";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_START = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
const UNIT: Record<string, string> = { frp_sum_mw: "MW", active_1km: "footprints", det_count: "detections" };

const doyLabel = (doy: number) => {
  const d = dateOfCell(2021, doy - 1);
  return `${Number(d.slice(8, 10))} ${MONTHS[Number(d.slice(5, 7)) - 1]}`;
};

/** Latest year with nearly a full year of harmonized data. */
function latestCompleteYear(cal: NonNullable<ResultPayload["calendar"]>): number {
  for (let i = cal.years.length - 1; i >= 0; i--) {
    if (cal.harmonized[i].filter((v) => v != null).length >= 330) return cal.years[i];
  }
  return cal.years[cal.years.length - 1];
}

function seasonText(m: Markers) {
  return `${doyLabel(m.start_doy)} – ${doyLabel(m.peak_doy)} (peak) – ${doyLabel(m.end_doy)}`;
}

export function SeasonalityTab({ result }: { result: ResultPayload }) {
  const c = useChartColors();
  const [p, setP] = useExploreParams();
  const [log, setLog] = useState(false);
  const clim = result.seasonality?.climatology;
  const cal = result.calendar;
  const year = p.yr ?? (cal ? latestCompleteYear(cal) : null);
  const unit = UNIT[result.meta.metric] ?? "";

  const option = useMemo<EChartsOption | null>(() => {
    if (!clim || !cal) return null;
    const x = clim.doy;
    const row = year != null ? cal.harmonized[cal.years.indexOf(year)] : null;
    const band = (lo: number[], hi: number[]) => hi.map((h, i) => Math.max(0, h - lo[i]));
    const a = axisStyle(c);
    const segs = result.seasonality?.segments ?? [];
    const total = segs.reduce((s, m) => s + m.total, 0) || 1;
    const floorFix = (arr: number[]) => (log ? arr.map((v) => (v > 0 ? v : null)) : arr);
    return {
      ...baseOption(c),
      grid: { left: 52, right: 16, top: 24, bottom: 28 },
      legend: {
        top: 0,
        right: 0,
        data: ["P10–P90", "Middle half (IQR)", "Typical (median)", ...(row ? [String(year)] : [])],
        textStyle: { color: c.muted, fontSize: 11 },
        itemWidth: 14,
        itemHeight: 8,
      },
      tooltip: { ...baseOption(c).tooltip, trigger: "axis" },
      xAxis: {
        type: "category",
        data: x,
        boundaryGap: false,
        ...a,
        splitLine: { show: false },
        axisLabel: { ...a.axisLabel, interval: 0, formatter: (v: string) => (MONTH_START.includes(Number(v) - 1) ? MONTHS[MONTH_START.indexOf(Number(v) - 1)] : "") },
        axisTick: { show: false },
      },
      yAxis: { type: log ? "log" : "value", min: log ? 1 : 0, name: unit, ...a },
      series: [
        { name: "P10", type: "line", data: floorFix(clim.p10), stack: "b1", symbol: "none", lineStyle: { opacity: 0 }, silent: true },
        { name: "P10–P90", type: "line", data: log ? floorFix(clim.p90) : band(clim.p10, clim.p90), stack: log ? undefined : "b1", symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: c.harmonized, opacity: 0.12 }, silent: true },
        { name: "P25", type: "line", data: floorFix(clim.p25), stack: "b2", symbol: "none", lineStyle: { opacity: 0 }, silent: true },
        { name: "Middle half (IQR)", type: "line", data: log ? floorFix(clim.p75) : band(clim.p25, clim.p75), stack: log ? undefined : "b2", symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: c.harmonized, opacity: 0.22 }, silent: true },
        { name: "Typical (median)", type: "line", data: floorFix(clim.median), symbol: "none", lineStyle: { color: c.harmonized, width: 2 }, z: 5 },
        ...(row
          ? [{ name: String(year), type: "line" as const, data: row.map((v) => (v != null && (!log || v > 0) ? v : null)), symbol: "none", lineStyle: { color: c.ink, width: 1.4 }, z: 6, connectNulls: false }]
          : []),
        {
          name: "Seasons",
          type: "line",
          data: [],
          markArea: {
            silent: true,
            itemStyle: { color: c.viirs, opacity: 0.07 },
            label: { color: c.faint, fontSize: 10, position: "insideTop" },
            data: segs.map((m, i) => [
              { xAxis: m.start_doy - 1, name: segs.length > 1 ? `Season ${i + 1} · ${Math.round((100 * m.total) / total)}%` : "Fire season" },
              { xAxis: m.end_doy - 1 },
            ]),
          },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: c.faint, type: "dashed", width: 1 },
            label: { show: false },
            data: segs.map((m) => ({ xAxis: m.peak_doy - 1 })),
          },
        },
      ],
    } as EChartsOption;
  }, [clim, cal, c, year, log, unit, result.seasonality?.segments]);

  const stl = result.seasonality?.stl;
  const stlOption = useMemo<EChartsOption | null>(() => {
    if (!stl) return null;
    const a = axisStyle(c);
    return {
      ...baseOption(c),
      grid: { left: 52, right: 16, top: 24, bottom: 24 },
      legend: { top: 0, right: 0, textStyle: { color: c.muted, fontSize: 11 } },
      tooltip: { ...baseOption(c).tooltip, trigger: "axis" },
      xAxis: { type: "category", data: stl.week, ...a, splitLine: { show: false }, axisLabel: { ...a.axisLabel, formatter: (v: string) => v.slice(0, 4), interval: 51 } },
      yAxis: { type: "value", ...a, name: "log1p" },
      series: [
        { name: "Trend", type: "line", data: stl.trend, symbol: "none", lineStyle: { color: c.harmonized, width: 2 } },
        { name: "Seasonal", type: "line", data: stl.seasonal, symbol: "none", lineStyle: { color: c.muted, width: 1 } },
      ],
    } as EChartsOption;
  }, [stl, c]);

  if (!clim || !cal || !option) {
    return <p className="p-4 text-sm text-muted">Seasonality needs at least three years of harmonized data.</p>;
  }
  const segs = result.seasonality?.segments ?? [];
  const markers = result.seasonality?.markers;
  const total = segs.reduce((s, m) => s + m.total, 0) || 1;

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-muted">
            Overlay year
            <Select value={year ?? ""} onChange={(e) => void setP({ yr: Number(e.target.value) })} className="w-24">
              {cal.years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </Select>
          </label>
          <div className="w-44">
            <Switch label="Log scale" checked={log} onChange={setLog} />
          </div>
        </div>
        <Chart
          option={option}
          height={260}
          label={`Typical seasonal cycle of harmonized activity with the 10th to 90th percentile range, and the year ${year} overlaid.`}
        />
        {stlOption && (
          <details className="mt-3">
            <summary className="min-h-9 cursor-pointer text-xs font-medium text-muted hover:text-ink">Long-term trend and seasonal component (STL)</summary>
            <Chart option={stlOption} height={180} label="STL decomposition: weekly trend and seasonal component on a log scale." />
          </details>
        )}
      </div>
      <aside className="flex flex-col gap-3 text-sm">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Fire season</h3>
        {segs.length > 1 ? (
          <>
            <p className="text-xs text-muted">This region burns in more than one season. Start, peak and end are the days when 10%, 50% and 90% of each season&apos;s activity has accumulated.</p>
            <ul className="flex flex-col gap-2">
              {segs.map((m, i) => (
                <li key={i} className="rounded-lg border border-line p-2.5">
                  <p className="text-xs font-medium text-ink">Season {i + 1} · {Math.round((100 * m.total) / total)}% of seasonal activity</p>
                  <p className="num mt-0.5 text-xs text-muted">{seasonText(m)}</p>
                  <p className="num text-xs text-faint">about {m.length_days} days</p>
                </li>
              ))}
            </ul>
          </>
        ) : markers ? (
          <div className="rounded-lg border border-line p-2.5">
            <p className="text-xs text-muted">Start, peak and end, at 10%, 50% and 90% of the year&apos;s activity:</p>
            <p className="num mt-1 text-xs text-ink">{seasonText(markers)}</p>
            <p className="num text-xs text-faint">about {markers.length_days} days</p>
          </div>
        ) : (
          <p className="text-xs text-muted">No clear season: activity is spread through the year or absent.</p>
        )}
        <p className="text-xs text-faint">The shaded ribbons are built from the whole record; the line is {year}. Values before VIIRS began are reconstructed from MODIS.</p>
      </aside>
    </div>
  );
}
