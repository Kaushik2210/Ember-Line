"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useRef, useState } from "react";
import { useResult } from "@/lib/analysis";
import { cn } from "@/lib/cn";
import { useExploreStore } from "@/lib/store";
import { TABS, type Tab, useExploreParams } from "@/lib/urlState";
import { AgreementTab } from "./tabs/AgreementTab";
import { AnomaliesTab } from "./tabs/AnomaliesTab";
import { Provenance } from "./Provenance";
import { CalendarTab } from "./tabs/CalendarTab";
import { QualityTab } from "./tabs/QualityTab";
import { SeasonalityTab } from "./tabs/SeasonalityTab";

const LABEL: Record<Tab, string> = {
  calendar: "Harmonized calendar",
  seasonality: "Seasonality",
  anomalies: "Unusual periods",
  agreement: "Sensor agreement",
  quality: "Data quality",
};

function Skeleton() {
  return (
    <div role="status" aria-label="Loading results" className="flex flex-col gap-2 p-4">
      <div className="h-4 w-48 animate-pulse rounded bg-raised" />
      <div className="h-40 animate-pulse rounded-lg bg-raised" />
    </div>
  );
}

export function AnalyticsDock() {
  const [p, setP] = useExploreParams();
  const result = useResult();
  const { phase, stages } = useExploreStore();
  const [open, setOpen] = useState(true);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: React.KeyboardEvent, i: number) => {
    const last = TABS.length - 1;
    const next = e.key === "ArrowRight" ? (i === last ? 0 : i + 1) : e.key === "ArrowLeft" ? (i === 0 ? last : i - 1) : e.key === "Home" ? 0 : e.key === "End" ? last : null;
    if (next === null) return;
    e.preventDefault();
    void setP({ tab: TABS[next] });
    tabRefs.current[next]?.focus();
  };

  const data = result.data;
  let body: React.ReactNode;
  if (phase === "running") {
    body = (
      <div className="p-4">
        <Skeleton />
        <p className="px-4 text-xs text-muted">{stages[stages.length - 1] ?? "Starting"}…</p>
      </div>
    );
  } else if (data) {
    body = {
      calendar: <CalendarTab result={data} />,
      seasonality: <SeasonalityTab result={data} />,
      anomalies: <AnomaliesTab result={data} />,
      agreement: <AgreementTab result={data} />,
      quality: <QualityTab result={data} />,
    }[p.tab];
  } else if (result.isLoading) {
    body = <Skeleton />;
  } else if (result.isError) {
    body = (
      <div role="alert" className="p-4 text-sm text-muted">
        This saved analysis could not be loaded.{" "}
        <button className="text-ink underline" onClick={() => void result.refetch()}>
          Retry
        </button>{" "}
        or run it again from the controls.
      </div>
    );
  } else {
    body = (
      <div className="grid gap-3 p-4 text-sm text-muted sm:grid-cols-2">
        <p className="sm:col-span-2 text-ink">Run an analysis to see the harmonized record for this region.</p>
        <p>
          <span className="text-ink">Calendar.</span> Every day since the record began, with MODIS, VIIRS and the harmonized series side by side.
        </p>
        <p>
          <span className="text-ink">Seasonality and unusual periods.</span> Typical fire seasons, and the seasons and weeks that stand out against them.
        </p>
        <p>
          <span className="text-ink">Sensor agreement.</span> How well the two records match before and after normalising, validated on years the model never saw.
        </p>
        <p>
          <span className="text-ink">Data quality.</span> Which satellites contribute when, and what changed over time.
        </p>
      </div>
    );
  }

  return (
    <section aria-label="Analysis results" className={cn("flex min-h-0 flex-col border-t border-line bg-panel", open ? "max-h-[56dvh] lg:max-h-[48dvh]" : "")}>
      <div className="flex items-center gap-1 border-b border-line px-2">
        <div role="tablist" aria-label="Results" className="flex min-w-0 flex-1 gap-0.5 overflow-x-auto">
          {TABS.map((t, i) => {
            const on = p.tab === t;
            return (
              <button
                key={t}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                role="tab"
                id={`tab-${t}`}
                aria-selected={on}
                aria-controls={`panel-${t}`}
                tabIndex={on ? 0 : -1}
                onKeyDown={(e) => onKey(e, i)}
                onClick={() => {
                  void setP({ tab: t });
                  setOpen(true);
                }}
                className={cn(
                  "min-h-10 shrink-0 whitespace-nowrap border-b-2 px-3 text-xs font-medium transition-colors duration-150 pointer-coarse:min-h-11",
                  on ? "border-harmonized text-ink" : "border-transparent text-muted hover:text-ink",
                )}
              >
                {LABEL[t]}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-label={open ? "Collapse results" : "Expand results"}
          className="grid size-9 shrink-0 place-items-center rounded-lg text-muted hover:text-ink pointer-coarse:size-11"
        >
          {open ? <ChevronDown aria-hidden className="size-4" /> : <ChevronUp aria-hidden className="size-4" />}
        </button>
      </div>
      {open && (
        <div role="tabpanel" id={`panel-${p.tab}`} aria-labelledby={`tab-${p.tab}`} className="min-h-0 flex-1 overflow-auto">
          {body}
          {data && phase !== "running" && <Provenance result={data} />}
        </div>
      )}
    </section>
  );
}
