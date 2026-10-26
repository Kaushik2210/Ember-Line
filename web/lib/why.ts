import type { ResultPayload, TableRow } from "./types";

/** Totals over the days both sensors were observing, and their ratio (VIIRS divided by MODIS). */
export function overlapTotals(daily: ResultPayload["daily"]): { modis: number; viirs: number; ratio: number | null; days: number } {
  let modis = 0;
  let viirs = 0;
  let days = 0;
  for (let i = 0; i < daily.dates.length; i++) {
    const m = daily.modis[i];
    const v = daily.viirs[i];
    if (m == null || v == null) continue;
    modis += m;
    viirs += v;
    days++;
  }
  return { modis, viirs, ratio: modis > 0 ? viirs / modis : null, days };
}

/** Share of MODIS detections that came from each satellite, from the platforms present in the data. */
export function modisSplit(platforms: ResultPayload["quality"]["platforms"]): { terra: number; aqua: number } | null {
  const t = platforms.find((p) => p.platform === "Terra")?.detections ?? 0;
  const a = platforms.find((p) => p.platform === "Aqua")?.detections ?? 0;
  const tot = t + a;
  return tot > 0 ? { terra: t / tot, aqua: a / tot } : null;
}

/** Corroboration rate for the largest and smallest MODIS pixel-size bins that have enough detections. */
export function scanTrend(rows: TableRow[], minCount = 50): { small: { label: string; rate: number }; large: { label: string; rate: number } } | null {
  const usable = rows
    .filter((r) => Number(r.n_modis) >= minCount && typeof r.modis_corroborated === "number")
    .sort((a, b) => Number(a.scan_bin_i ?? 0) - Number(b.scan_bin_i ?? 0));
  if (usable.length < 2) return null;
  const s = usable[0];
  const l = usable[usable.length - 1];
  return {
    small: { label: String(s.scan_bin), rate: s.modis_corroborated as number },
    large: { label: String(l.scan_bin), rate: l.modis_corroborated as number },
  };
}

export const METRIC_NAME: Record<string, string> = {
  frp_sum_mw: "fire radiative power",
  active_1km: "burning 1 km footprints",
  det_count: "raw detections",
};
