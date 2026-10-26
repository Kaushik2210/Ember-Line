"use client";

import type { EChartsOption } from "echarts";
import { MapPin } from "lucide-react";
import { useMemo } from "react";
import { axisStyle, baseOption, useChartColors } from "@/lib/chartTheme";
import type { AnomalyEvent, ResultPayload } from "@/lib/types";
import { useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";
import { Chart } from "@/components/ui/Chart";

const UNIT: Record<string, string> = { frp_sum_mw: "MW", active_1km: "footprints", det_count: "detections" };

export function AnomaliesTab({ result }: { result: ResultPayload }) {
  const c = useChartColors();
  const [, setP] = useExploreParams();
  const h = result.harmonized;
  const { events, seasons } = result.anomalies;
  const unit = UNIT[result.meta.metric] ?? "";

  const ranked = useMemo(
    () => [...events].sort((a, b) => Math.abs(b.mean_z) * b.days - Math.abs(a.mean_z) * a.days).slice(0, 12),
    [events],
  );

  const timeline = useMemo<EChartsOption | null>(() => {
    if (!h) return null;
    const a = axisStyle(c);
    return {
      ...baseOption(c),
      grid: { left: 52, right: 16, top: 12, bottom: 28 },
      tooltip: { ...baseOption(c).tooltip, trigger: "axis" },
      xAxis: { type: "category", data: h.dates, ...a, splitLine: { show: false }, axisLabel: { ...a.axisLabel, formatter: (v: string) => v.slice(0, 4), interval: 364 } },
      yAxis: { type: "value", name: unit, ...a },
      series: [
        {
          name: "Harmonized",
          type: "line",
          data: h.value,
          symbol: "none",
          sampling: "lttb",
          lineStyle: { color: c.harmonized, width: 1 },
          markArea: {
            silent: true,
            data: events.map((e) => [
              { xAxis: e.start, itemStyle: { color: e.direction === "high" ? c.hot : c.cool, opacity: 0.28 } },
              { xAxis: e.end },
            ]),
          },
        },
      ],
    } as EChartsOption;
  }, [h, events, c, unit]);

  const seasonBars = useMemo<EChartsOption | null>(() => {
    if (!seasons.length) return null;
    const top = seasons.slice(0, 8);
    const a = axisStyle(c);
    return {
      ...baseOption(c),
      grid: { left: 64, right: 24, top: 8, bottom: 24 },
      tooltip: { ...baseOption(c).tooltip, trigger: "item", formatter: (q: unknown) => { const i = (q as { dataIndex: number }).dataIndex; return top[i].text; } },
      xAxis: { type: "value", name: "robust SD vs other years", nameLocation: "middle", nameGap: 22, ...a },
      yAxis: { type: "category", data: top.map((s) => s.season), inverse: true, ...a, splitLine: { show: false } },
      series: [
        {
          type: "bar",
          data: top.map((s) => ({ value: Number(s.z.toFixed(2)), itemStyle: { color: s.z >= 0 ? c.hot : c.cool } })),
          barWidth: 12,
          label: { show: true, position: "right", color: c.muted, fontSize: 10, formatter: (q: unknown) => `${(q as { value: number }).value > 0 ? "+" : ""}${(q as { value: number }).value}` },
        },
      ],
    } as EChartsOption;
  }, [seasons, c]);

  if (!h || !timeline) {
    return <p className="p-4 text-sm text-muted">Unusual periods need a harmonized record of at least three years.</p>;
  }

  return (
    <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-col gap-4">
        <div>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Timeline</h3>
          <Chart option={timeline} height={200} label="Daily harmonized activity over the whole record, with unusually high periods shaded red and unusually low periods shaded blue." />
          <p className="mt-1 text-xs text-faint">
            <span style={{ color: c.hot }}>Red</span> is unusually active and <span style={{ color: c.cool }}>blue</span> unusually quiet for that time of year. Each year is compared with the others, never with itself.
          </p>
        </div>
        {seasonBars && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Most unusual seasons</h3>
            <Chart option={seasonBars} height={Math.min(8, seasons.length) * 24 + 40} label="Fire seasons ranked by how far their total is from the other years." />
          </div>
        )}
      </div>

      <div className="min-w-0">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Sustained unusual periods</h3>
        {ranked.length === 0 ? (
          <p className="text-sm text-muted">No sustained unusual periods were found at this threshold (more than 2.5 robust standard deviations for 3 or more days).</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {ranked.map((e) => (
              <EventRow key={`${e.start}-${e.direction}`} e={e} onShow={() => void setP({ day: e.start })} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function EventRow({ e, onShow }: { e: AnomalyEvent; onShow: () => void }) {
  const high = e.direction === "high";
  return (
    <li className="rounded-lg border border-line p-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs leading-relaxed text-ink">
          <span className={high ? "text-hot" : "text-cool"} aria-label={high ? "Unusually high" : "Unusually low"}>
            {high ? "▲ " : "▼ "}
          </span>
          {e.text.replace(/ Less reliable:.*$/, "")}
        </p>
        <Button size="sm" variant="ghost" className="shrink-0 border border-line" onClick={onShow} aria-label={`Show ${e.start} on the map`}>
          <MapPin aria-hidden className="size-3.5" /> Map
        </Button>
      </div>
      {e.caveat && <p className="mt-1.5 text-xs text-modis">{e.caveat}</p>}
    </li>
  );
}
