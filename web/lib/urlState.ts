"use client";

import {
  parseAsArrayOf,
  parseAsFloat,
  parseAsInteger,
  parseAsString,
  parseAsStringEnum,
  useQueryStates,
} from "nuqs";
import type { BBox, DayNight, Metric, ModelChoice } from "./types";

export const TABS = ["calendar", "seasonality", "anomalies", "agreement", "quality"] as const;
export type Tab = (typeof TABS)[number];
export const VIEWS = ["harmonized", "modis", "viirs"] as const;
export type CalendarView = (typeof VIEWS)[number];
export const SENSORS = ["modis", "viirs"] as const;

export const DEFAULT_REGION = "punjab-haryana";

/** Everything that defines what the user is looking at lives in the URL, so a link reproduces it. */
export const parsers = {
  r: parseAsString.withDefault(DEFAULT_REGION),
  box: parseAsString, // custom area "west,south,east,north"; overrides the preset
  s: parseAsString, // start (ISO date); null means the region's default
  e: parseAsString,
  m: parseAsStringEnum<Metric>(["frp_sum_mw", "active_1km", "det_count"]).withDefault("frp_sum_mw"),
  mod: parseAsStringEnum<ModelChoice>(["auto", "huber", "theilsen", "quantile", "isotonic"]).withDefault("auto"),
  dn: parseAsStringEnum<DayNight>(["both", "D", "N"]).withDefault("both"),
  conf: parseAsInteger.withDefault(30),
  vc: parseAsStringEnum(["nh", "h", "lnh"]).withDefault("nh"),
  gk: parseAsStringEnum(["regular", "h3"]).withDefault("regular"),
  gs: parseAsFloat.withDefault(0.25),
  gr: parseAsInteger.withDefault(5),
  sens: parseAsArrayOf(parseAsStringEnum([...SENSORS])).withDefault([...SENSORS]),
  tab: parseAsStringEnum<Tab>([...TABS]).withDefault("calendar"),
  view: parseAsStringEnum<CalendarView>([...VIEWS]).withDefault("harmonized"),
  day: parseAsString,
  yr: parseAsInteger,
  job: parseAsString,
  syn: parseAsStringEnum(["1"]), // development only: use SYNTHETIC data
};

export function useExploreParams() {
  return useQueryStates(parsers, { history: "replace", shallow: true });
}

export type ExploreParams = ReturnType<typeof useExploreParams>[0];

export function parseBox(s: string | null): BBox | null {
  if (!s) return null;
  const v = s.split(",").map(Number);
  if (v.length !== 4 || v.some((x) => !Number.isFinite(x))) return null;
  const [w, so, e, n] = v;
  if (!(w < e && so < n)) return null;
  return [w, so, e, n];
}

export function formatBox(b: BBox): string {
  return b.map((x) => Number(x.toFixed(3))).join(",");
}

const VIIRS_CLASSES: Record<string, string[]> = { nh: ["n", "h"], h: ["h"], lnh: ["l", "n", "h"] };
export const viirsClasses = (code: string) => VIIRS_CLASSES[code] ?? VIIRS_CLASSES.nh;
