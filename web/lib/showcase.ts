"use client";

import { useQuery } from "@tanstack/react-query";
import { API_URL } from "./api";
import type { BBox, CvRow, Markers } from "./types";

export interface Findings {
  metric: string;
  synthetic: boolean;
  years: [number, number] | null;
  overlap: { days: number; modis_total: number; viirs_total: number; ratio: number | null };
  overpass: {
    n_modis: number;
    n_viirs: number;
    modis_seen_by_viirs: number | null;
    viirs_seen_by_modis: number | null;
  } | null;
  normalization: {
    chosen: string;
    n_weeks: number;
    years: [number, number];
    before: Quality | null;
    after: Quality | null;
    scale_baseline: Quality | null;
    band_factor: number | null;
    level: number;
    cv: CvRow[];
  } | null;
  reconstructed_share: number | null;
  busiest_day: string | null;
  top_season: { season: string; z: number; text: string } | null;
  top_events: { start: string; end: string; days: number; direction: "high" | "low"; mean_z: number; text: string; caveat: string }[];
  segments: Markers[];
  notes: string[];
}

export interface Quality {
  r2_log: number | null;
  mae_log: number | null;
  bias_rel: number | null;
  spearman: number | null;
  coverage: number | null;
}

export interface ShowcaseEntry {
  id: string;
  name: string;
  bbox: BBox;
  blurb: string;
  start: string;
  end: string;
  state: "ready" | "computing" | "unavailable";
  job_id: string | null;
  findings: Findings | null;
  reason: string | null;
}

/** Fetches the per-region findings and keeps polling while any region is still being computed. */
export function useShowcase() {
  return useQuery({
    queryKey: ["showcase"],
    queryFn: async (): Promise<ShowcaseEntry[]> => {
      const res = await fetch(`${API_URL}/api/showcase`);
      if (!res.ok) throw new Error(`showcase ${res.status}`);
      return (await res.json()) as ShowcaseEntry[];
    },
    refetchInterval: (q) => (q.state.data?.some((e) => e.state === "computing") ? 4000 : false),
    staleTime: 60_000,
    retry: 1,
  });
}

export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "n/a" : `${(100 * v).toFixed(digits)}%`;

/** "+3%" or "−42%": a real minus sign, and an explicit plus, so direction reads at a glance. */
export const signedPct = (v: number | null | undefined, digits = 0) => {
  if (v == null) return "n/a";
  const s = (100 * Math.abs(v)).toFixed(digits);
  return `${v < 0 ? "−" : "+"}${s}%`;
};

/** The region to feature: Punjab and Haryana if it is ready, otherwise the first ready region. */
export function featured(entries: ShowcaseEntry[] | undefined): ShowcaseEntry | null {
  const ready = (entries ?? []).filter((e) => e.state === "ready" && e.findings && !e.findings.synthetic);
  return ready.find((e) => e.id === "punjab-haryana") ?? ready[0] ?? null;
}

export interface ProofStat {
  value: string;
  label: string;
  detail: string;
}

/** Three headline statistics, each only when the data supports it. The words follow the numbers. */
export function proofStats(f: Findings): ProofStat[] {
  const out: ProofStat[] = [];
  const r = f.overlap.ratio;
  if (r != null && f.overlap.days > 0) {
    const more = r >= 1;
    out.push({
      value: `${(more ? r : 1 / r).toFixed(1)}×`,
      label: `${more ? "more" : "less"} fire radiative power in VIIRS than in MODIS`,
      detail: `Summed over the ${f.overlap.days.toLocaleString("en-GB")} days both sensors were observing this region.`,
    });
  }
  const n = f.normalization;
  if (n?.before?.bias_rel != null && n.after?.bias_rel != null) {
    out.push({
      value: `${signedPct(n.before.bias_rel)} → ${signedPct(n.after.bias_rel)}`,
      label: "MODIS bias against VIIRS, before and after normalising",
      detail: `Measured on years the model never saw (leave-one-year-out, ${n.n_weeks.toLocaleString("en-GB")} weeks).`,
    });
  }
  if (f.years) {
    const span = f.years[1] - f.years[0] + 1;
    const rec = f.reconstructed_share;
    out.push({
      value: `${span} years`,
      label: "of one consistent record",
      detail:
        rec != null && rec > 0
          ? `${pct(rec)} of the days are reconstructed from MODIS into VIIRS-equivalent units, with uncertainty bands.`
          : "Every day is observed by VIIRS.",
    });
  }
  return out;
}

/** Link into the Explore workspace for a region, preset to its default period and its busiest day. */
export function exploreLink(e: ShowcaseEntry, tab = "calendar"): string {
  const p = new URLSearchParams({ r: e.id, s: e.start, e: e.end, tab });
  if (e.findings?.busiest_day) p.set("day", e.findings.busiest_day);
  if (e.job_id && e.state === "ready") p.set("job", e.job_id);
  return `/explore?${p}`;
}
