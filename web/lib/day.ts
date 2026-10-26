import type { ResultPayload } from "./types";

const MS_DAY = 86_400_000;
const toMs = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));

export function addDays(iso: string, n: number): string {
  return new Date(toMs(iso) + n * MS_DAY).toISOString().slice(0, 10);
}

export function daysBetween(a: string, b: string): number {
  return Math.round((toMs(b) - toMs(a)) / MS_DAY);
}

export function clampDay(iso: string, lo: string, hi: string): string {
  return iso < lo ? lo : iso > hi ? hi : iso;
}

/**
 * The day to show first: the busiest day among those VIIRS actually observed, because that is where
 * the two sensors can be compared. Falls back to the busiest harmonised day, then null.
 */
export function defaultDay(result: ResultPayload | undefined): string | null {
  const h = result?.harmonized;
  if (!h) return null;
  let best = -1;
  let bestObserved = -1;
  h.value.forEach((v, i) => {
    if (v == null) return;
    if (best < 0 || v > (h.value[best] ?? -Infinity)) best = i;
    if (!h.reconstructed[i] && (bestObserved < 0 || v > (h.value[bestObserved] ?? -Infinity))) bestObserved = i;
  });
  const i = bestObserved >= 0 ? bestObserved : best;
  return i >= 0 ? h.dates[i] : null;
}

export function formatDay(iso: string): string {
  return new Date(toMs(iso)).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
