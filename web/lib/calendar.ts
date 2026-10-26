import { interpolateInferno } from "d3-scale-chromatic";
import { addDays } from "./day";
import type { Matrix } from "./types";

export const COLS = 365;

const isLeap = (y: number) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;

/**
 * Date of a calendar cell. The matrices have 365 columns and drop 29 February, so in a leap year
 * every cell after 28 February is one day later in the real calendar.
 */
export function dateOfCell(year: number, col: number): string {
  const shift = isLeap(year) && col >= 59 ? 1 : 0;
  return addDays(`${year}-01-01`, col + shift);
}

/** Inverse of dateOfCell. 29 February maps to the cell for 28 February. */
export function cellOfDate(iso: string): { year: number; col: number } {
  const year = Number(iso.slice(0, 4));
  const days = Math.round((Date.UTC(year, +iso.slice(5, 7) - 1, +iso.slice(8, 10)) - Date.UTC(year, 0, 1)) / 86_400_000);
  const col = isLeap(year) && days >= 60 ? days - 1 : isLeap(year) && days === 59 ? 58 : days;
  return { year, col: Math.min(COLS - 1, col) };
}

/** 99th percentile of log1p over every finite value, so a few huge days do not wash out the scale. */
export function scaleMax(...matrices: Matrix[]): number {
  const v: number[] = [];
  for (const m of matrices) for (const row of m) for (const x of row) if (x != null && x > 0) v.push(Math.log1p(x));
  if (v.length === 0) return 1;
  v.sort((a, b) => a - b);
  return Math.max(1e-6, v[Math.min(v.length - 1, Math.floor(0.99 * v.length))]);
}

/** Perceptual inferno ramp on log1p. Zero is a dark neutral so it differs from missing data. */
export function valueColor(x: number | null, logMax: number, zero = "#1a222c"): string | null {
  if (x == null) return null;
  if (x <= 0) return zero;
  const t = Math.min(1, Math.log1p(x) / logMax);
  return interpolateInferno(0.12 + 0.88 * t);
}

/** Share of days in a row that were reconstructed (not observed by VIIRS), ignoring missing days. */
export function reconstructedShare(row: (number | null)[]): number {
  let n = 0;
  let r = 0;
  for (const x of row) {
    if (x == null) continue;
    n++;
    r += x > 0.5 ? 1 : 0;
  }
  return n === 0 ? 0 : r / n;
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "5 Nov" for a 1-based day of year on the 365-day calendar (29 February has no day number). */
export function doyLabel(doy: number): string {
  const d = dateOfCell(2021, Math.min(COLS, Math.max(1, doy)) - 1);
  return `${Number(d.slice(8, 10))} ${MONTH_NAMES[Number(d.slice(5, 7)) - 1]}`;
}
