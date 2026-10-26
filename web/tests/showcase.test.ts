import { describe, expect, it } from "vitest";
import { type Findings, type ShowcaseEntry, exploreLink, featured, pct, proofStats, signedPct } from "@/lib/showcase";

const base: Findings = {
  metric: "frp_sum_mw",
  synthetic: false,
  years: [2000, 2025],
  overlap: { days: 4800, modis_total: 100, viirs_total: 173, ratio: 1.73 },
  overpass: null,
  normalization: {
    chosen: "quantile",
    n_weeks: 734,
    years: [2012, 2025],
    before: { r2_log: 0.77, mae_log: 0.92, bias_rel: -0.423, spearman: 0.95, coverage: 0.9 },
    after: { r2_log: 0.89, mae_log: 0.51, bias_rel: 0.014, spearman: 0.96, coverage: 0.9 },
    scale_baseline: null,
    band_factor: 3.1,
    level: 0.9,
    cv: [],
  },
  reconstructed_share: 0.45,
  busiest_day: "2019-11-02",
  top_season: null,
  top_events: [],
  segments: [],
  notes: [],
};

const entry = (id: string, state: ShowcaseEntry["state"], f: Findings | null = null): ShowcaseEntry => ({
  id, name: id, bbox: [0, 0, 1, 1], blurb: "", start: "2012-06-01", end: "2024-12-31", state, job_id: `job-${id}`, findings: f, reason: null,
});

describe("number formatting", () => {
  it("uses real minus signs and explicit plus signs", () => {
    expect(signedPct(-0.423)).toBe("−42%");
    expect(signedPct(0.014)).toBe("+1%");
    expect(signedPct(0)).toBe("+0%");
    expect(signedPct(null)).toBe("n/a");
    expect(pct(0.456)).toBe("46%");
    expect(pct(0.4567, 1)).toBe("45.7%");
    expect(pct(undefined)).toBe("n/a");
  });
});

describe("proof statistics", () => {
  it("are computed from the findings", () => {
    const s = proofStats(base);
    expect(s).toHaveLength(3);
    expect(s[0].value).toBe("1.7×");
    expect(s[0].label).toContain("more fire radiative power in VIIRS");
    expect(s[1].value).toBe("−42% → +1%");
    expect(s[2].value).toBe("26 years");
    expect(s[2].detail).toContain("45%");
  });

  it("flip the wording when MODIS is the larger one", () => {
    const s = proofStats({ ...base, overlap: { ...base.overlap, ratio: 0.5 } });
    expect(s[0].value).toBe("2.0×");
    expect(s[0].label).toContain("less fire radiative power in VIIRS");
  });

  it("leave out what the data cannot support", () => {
    const s = proofStats({ ...base, normalization: null, overlap: { days: 0, modis_total: 0, viirs_total: 0, ratio: null }, years: null });
    expect(s).toEqual([]);
  });

  it("say so when nothing was reconstructed", () => {
    const s = proofStats({ ...base, reconstructed_share: 0 });
    expect(s[2].detail).toBe("Every day is observed by VIIRS.");
  });
});

describe("featured region", () => {
  it("prefers Punjab and Haryana, then any ready real region", () => {
    const list = [entry("california", "ready", base), entry("punjab-haryana", "ready", base)];
    expect(featured(list)?.id).toBe("punjab-haryana");
    expect(featured([entry("california", "ready", base)])?.id).toBe("california");
  });
  it("never features unavailable, computing or synthetic results", () => {
    expect(featured([entry("a", "unavailable"), entry("b", "computing"), entry("c", "ready", { ...base, synthetic: true })])).toBeNull();
    expect(featured(undefined)).toBeNull();
  });
});

describe("explore links", () => {
  it("preset the region, period, busiest day and finished job", () => {
    const url = exploreLink(entry("punjab-haryana", "ready", base));
    const p = new URL(url, "http://x").searchParams;
    expect(p.get("r")).toBe("punjab-haryana");
    expect(p.get("s")).toBe("2012-06-01");
    expect(p.get("day")).toBe("2019-11-02");
    expect(p.get("job")).toBe("job-punjab-haryana");
    expect(p.get("tab")).toBe("calendar");
  });
  it("omit the day and job when there are no findings", () => {
    const p = new URL(exploreLink(entry("x", "unavailable")), "http://x").searchParams;
    expect(p.has("day")).toBe(false);
    expect(p.has("job")).toBe(false);
  });
});
