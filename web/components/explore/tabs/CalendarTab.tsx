"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { COLS, cellOfDate, dateOfCell, reconstructedShare, scaleMax, valueColor } from "@/lib/calendar";
import { formatDay } from "@/lib/day";
import type { Matrix, ResultPayload } from "@/lib/types";
import { type CalendarView, useExploreParams } from "@/lib/urlState";
import { Segmented } from "@/components/ui/Segmented";
import { useChartColors } from "@/lib/chartTheme";

const LEFT = 52; // year labels
const TOP = 18; // month labels
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_COL = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

const UNIT: Record<string, string> = { frp_sum_mw: "MW", active_1km: "burning 1 km footprints", det_count: "detections" };

interface Tip {
  x: number;
  y: number;
  year: number;
  col: number;
}

export function CalendarTab({ result }: { result: ResultPayload }) {
  const [p, setP] = useExploreParams();
  const c = useChartColors();
  const cal = result.calendar;
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(900);
  const [tip, setTip] = useState<Tip | null>(null);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const matrices = useMemo(
    () => (cal ? { harmonized: cal.harmonized, modis: cal.modis, viirs: cal.viirs } : null),
    [cal],
  );
  // one scale for all three views, so switching between them shows the disagreement shrinking
  const logMax = useMemo(() => (matrices ? scaleMax(matrices.harmonized, matrices.modis, matrices.viirs) : 1), [matrices]);

  const rows = cal?.years.length ?? 0;
  const rowH = rows > 18 ? 12 : 16;
  const cellW = Math.max(2, (width - LEFT - 8) / COLS);
  const W = LEFT + cellW * COLS + 8;
  const H = TOP + rowH * rows + 4;
  const view: CalendarView = p.view;
  const matrix: Matrix | null = matrices ? matrices[view] : null;
  const selected = p.day ? cellOfDate(p.day) : null;

  useEffect(() => {
    const cv = canvas.current;
    if (!cv || !matrix || !cal) return;
    const dpr = window.devicePixelRatio || 1;
    cv.width = W * dpr;
    cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);
    ctx.font = "10px var(--font-jetbrains), monospace";
    ctx.textBaseline = "middle";
    // month ticks
    ctx.fillStyle = c.faint;
    ctx.textAlign = "left";
    MONTH_COL.forEach((col, m) => ctx.fillText(MONTHS[m], LEFT + col * cellW, 8));
    cal.years.forEach((year, r) => {
      const y = TOP + r * rowH;
      ctx.fillStyle = c.muted;
      ctx.textAlign = "right";
      ctx.fillText(String(year), LEFT - 14, y + rowH / 2);
      // marker for how the year was built: cyan = observed by VIIRS, amber = reconstructed from MODIS
      const share = reconstructedShare(cal.reconstructed[r]);
      const hasData = cal.harmonized[r].some((v) => v != null);
      if (view === "harmonized" && hasData) {
        ctx.fillStyle = share > 0.5 ? c.modis : c.viirs;
        ctx.fillRect(LEFT - 10, y + 1, 4, rowH - 2);
      }
      const row = matrix[r];
      for (let col = 0; col < COLS; col++) {
        const color = valueColor(row[col], logMax, c.raised);
        if (color === null) {
          ctx.fillStyle = c.line;
          ctx.fillRect(LEFT + col * cellW, y + rowH / 2 - 0.5, Math.max(1, cellW - 0.5), 1);
          continue;
        }
        ctx.fillStyle = color;
        ctx.fillRect(LEFT + col * cellW, y, Math.ceil(cellW) - (cellW > 3 ? 0.5 : 0), rowH - 1);
      }
    });
    if (selected) {
      const r = cal.years.indexOf(selected.year);
      if (r >= 0) {
        ctx.strokeStyle = c.ink;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(LEFT + selected.col * cellW - 1, TOP + r * rowH - 1, Math.max(cellW, 3) + 2, rowH + 1);
      }
    }
  }, [cal, matrix, view, W, H, cellW, rowH, logMax, c, selected]);

  if (!cal || !matrix) {
    return <p className="p-4 text-sm text-muted">The calendar needs a fitted normalisation, which this run did not produce. See the Data quality tab for why.</p>;
  }

  const hit = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const col = Math.floor((e.clientX - r.left - LEFT) / cellW);
    const row = Math.floor((e.clientY - r.top - TOP) / rowH);
    if (col < 0 || col >= COLS || row < 0 || row >= rows) return null;
    return { year: cal.years[row], col, row, x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const tipData = tip
    ? (() => {
        const row = cal.years.indexOf(tip.year);
        const val = cal.harmonized[row][tip.col];
        return {
          day: dateOfCell(tip.year, tip.col),
          shown: matrix[row][tip.col],
          lo: cal.lo[row][tip.col],
          hi: cal.hi[row][tip.col],
          rec: (cal.reconstructed[row][tip.col] ?? 0) > 0.5,
          harmonized: val,
          modis: cal.modis[row][tip.col],
          viirs: cal.viirs[row][tip.col],
        };
      })()
    : null;
  const unit = UNIT[result.meta.metric] ?? "";
  const fmt = (v: number | null) => (v == null ? "no data" : v < 10 ? v.toFixed(1) : Math.round(v).toLocaleString("en-GB"));

  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="w-full max-w-sm">
          <Segmented<CalendarView>
            label="Series shown"
            value={view}
            options={[
              { value: "modis", label: "Raw MODIS" },
              { value: "viirs", label: "Raw VIIRS" },
              { value: "harmonized", label: "Harmonized" },
            ]}
            onChange={(v) => void setP({ view: v })}
          />
        </div>
        <Legend max={Math.expm1(logMax)} unit={unit} />
      </div>

      <div ref={wrap} className="relative overflow-x-auto">
        <canvas
          ref={canvas}
          style={{ width: W, height: H }}
          className="block cursor-crosshair"
          role="img"
          aria-label={`Daily calendar heatmap, one row per year, showing ${view === "harmonized" ? "the harmonized series" : `raw ${view.toUpperCase()}`}. Select a day to show it on the map.`}
          onPointerMove={(e) => {
            const h = hit(e);
            setTip(h ? { x: h.x, y: h.y, year: h.year, col: h.col } : null);
          }}
          onPointerLeave={() => setTip(null)}
          onClick={(e) => {
            const h = hit(e);
            if (h) void setP({ day: dateOfCell(h.year, h.col) });
          }}
        />
        {tip && tipData && (
          <div
            role="tooltip"
            className="pointer-events-none absolute z-10 w-56 rounded-lg border border-line bg-raised p-2.5 text-xs shadow-xl"
            style={{ left: Math.min(tip.x + 12, Math.max(0, W - 230)), top: tip.y + 14 }}
          >
            <p className="font-medium text-ink">{formatDay(tipData.day)}</p>
            <dl className="mt-1 flex flex-col gap-0.5">
              <div className="flex justify-between gap-3">
                <dt className="text-muted">{view === "harmonized" ? "Harmonized" : view === "modis" ? "MODIS" : "VIIRS"}</dt>
                <dd className="num text-ink">{fmt(tipData.shown)} {tipData.shown != null ? unit : ""}</dd>
              </div>
              {view === "harmonized" && tipData.rec && tipData.lo != null && tipData.hi != null && (
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">90% band</dt>
                  <dd className="num text-ink">{fmt(tipData.lo)} – {fmt(tipData.hi)}</dd>
                </div>
              )}
              {view === "harmonized" && tipData.harmonized != null && (
                <p className="mt-1 text-faint">{tipData.rec ? "Reconstructed from MODIS" : "Observed by VIIRS"}</p>
              )}
            </dl>
          </div>
        )}
      </div>

      <p className="text-xs text-faint">
        Colour is log-scaled and shared by all three views.{" "}
        {view === "harmonized" && (
          <>
            The bar beside each year is <span style={{ color: c.viirs }}>cyan</span> where VIIRS observed it and{" "}
            <span style={{ color: c.modis }}>amber</span> where it is reconstructed from MODIS, with wider uncertainty.{" "}
          </>
        )}
        A thin line means no data. Click a day to show it on the map.
      </p>

      <table className="sr-only">
        <caption>Total per year, {view}</caption>
        <thead>
          <tr><th>Year</th><th>Total ({unit})</th></tr>
        </thead>
        <tbody>
          {cal.years.map((y, i) => (
            <tr key={y}><td>{y}</td><td>{Math.round(matrix[i].reduce<number>((s, v) => s + (v ?? 0), 0))}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Legend({ max, unit }: { max: number; unit: string }) {
  const stops = Array.from({ length: 12 }, (_, i) => valueColor(Math.expm1((i / 11) * Math.log1p(max)), Math.log1p(max)) ?? "#000");
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.expm1(t * Math.log1p(max)));
  return (
    <div className="flex items-center gap-2" aria-hidden>
      <div className="h-2.5 w-40 rounded-sm" style={{ background: `linear-gradient(90deg, ${stops.join(",")})` }} />
      <span className="num text-[10px] text-faint">0</span>
      <span className="num text-[10px] text-faint">{Math.round(ticks[4]).toLocaleString("en-GB")} {unit}</span>
    </div>
  );
}
