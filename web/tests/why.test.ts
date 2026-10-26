import { describe, expect, it } from "vitest";
import { modisSplit, overlapTotals, scanTrend } from "@/lib/why";

describe("overlap totals", () => {
  it("sums only the days both sensors observed", () => {
    const daily = {
      dates: ["a", "b", "c", "d"],
      modis: [10, 20, null, 30],
      viirs: [null, 50, 70, 90],
    };
    expect(overlapTotals(daily)).toEqual({ modis: 50, viirs: 140, ratio: 2.8, days: 2 });
  });
  it("has no ratio when MODIS saw nothing", () => {
    expect(overlapTotals({ dates: ["a"], modis: [0], viirs: [5] }).ratio).toBeNull();
    expect(overlapTotals({ dates: [], modis: [], viirs: [] }).days).toBe(0);
  });
});

describe("platform split", () => {
  it("is the share of MODIS detections from each satellite", () => {
    const s = modisSplit([
      { sensor: "modis", platform: "Terra", first: "", last: "", detections: 25 },
      { sensor: "modis", platform: "Aqua", first: "", last: "", detections: 75 },
      { sensor: "viirs", platform: "SNPP", first: "", last: "", detections: 500 },
    ]);
    expect(s).toEqual({ terra: 0.25, aqua: 0.75 });
    expect(modisSplit([])).toBeNull();
  });
});

describe("scan trend", () => {
  const rows = [
    { scan_bin: "<1.5", scan_bin_i: 0, n_modis: 1000, modis_corroborated: 0.35 },
    { scan_bin: "1.5-2", scan_bin_i: 1, n_modis: 300, modis_corroborated: 0.27 },
    { scan_bin: ">=3", scan_bin_i: 3, n_modis: 10, modis_corroborated: 0.1 },
  ];
  it("compares the smallest and largest bins with enough detections", () => {
    expect(scanTrend(rows)).toEqual({ small: { label: "<1.5", rate: 0.35 }, large: { label: "1.5-2", rate: 0.27 } });
  });
  it("needs at least two usable bins", () => {
    expect(scanTrend(rows.slice(0, 1))).toBeNull();
    expect(scanTrend([])).toBeNull();
  });
});
