import { describe, expect, it } from "vitest";
import { buildRequest, resolveArea, resolvePeriod } from "@/lib/analysis";
import type { Region } from "@/lib/types";
import { type ExploreParams, formatBox, parseBox, viirsClasses } from "@/lib/urlState";

const REGIONS: Region[] = [
  {
    id: "punjab-haryana",
    name: "Punjab & Haryana, India",
    bbox: [73.8, 28.4, 77.6, 32.5],
    blurb: "",
    default_start: "2012-06-01",
    default_end: "2024-12-31",
  },
];

const base = {
  r: "punjab-haryana", box: null, s: null, e: null, m: "frp_sum_mw", mod: "auto", dn: "both",
  conf: 30, vc: "nh", gk: "regular", gs: 0.25, gr: 5, sens: ["modis", "viirs"], tab: "calendar",
  view: "harmonized", day: null, yr: null, job: null, syn: null,
} as unknown as ExploreParams;

describe("box parsing", () => {
  it("round-trips a box", () => {
    expect(parseBox("73.8,28.4,77.6,32.5")).toEqual([73.8, 28.4, 77.6, 32.5]);
    expect(formatBox([73.80001, 28.4, 77.6, 32.5123456])).toBe("73.8,28.4,77.6,32.512");
  });
  it("rejects malformed boxes", () => {
    expect(parseBox(null)).toBeNull();
    expect(parseBox("1,2,3")).toBeNull();
    expect(parseBox("a,b,c,d")).toBeNull();
    expect(parseBox("10,0,5,5")).toBeNull(); // west must be less than east
  });
});

describe("VIIRS confidence choice", () => {
  it("maps codes to classes and falls back to nominal+high", () => {
    expect(viirsClasses("nh")).toEqual(["n", "h"]);
    expect(viirsClasses("h")).toEqual(["h"]);
    expect(viirsClasses("lnh")).toEqual(["l", "n", "h"]);
    expect(viirsClasses("zzz")).toEqual(["n", "h"]);
  });
});

describe("analysis request", () => {
  it("uses the preset by id and its default period", () => {
    const req = buildRequest(base, REGIONS, null);
    expect(req.region_id).toBe("punjab-haryana");
    expect(req.bbox).toBeUndefined();
    expect(req.start).toBe("2012-06-01");
    expect(req.end).toBe("2024-12-31");
    expect(req.quality_policy).toMatchObject({ modis_min_conf: 30, viirs_classes: ["n", "h"], daynight: "both" });
    expect(req.synthetic).toBeUndefined();
  });

  it("a drawn box overrides the preset, an uploaded shape overrides both", () => {
    const boxed = { ...base, box: "10,5,12,7" } as ExploreParams;
    expect(buildRequest(boxed, REGIONS, null)).toMatchObject({ bbox: [10, 5, 12, 7] });
    expect(buildRequest(boxed, REGIONS, null).region_id).toBeUndefined();
    const shape = { type: "Polygon", coordinates: [] };
    const req = buildRequest(boxed, REGIONS, shape);
    expect(req.geojson).toBe(shape);
    expect(req.bbox).toBeUndefined();
    expect(req.region_id).toBeUndefined();
  });

  it("explicit dates and options from the URL win", () => {
    const p = { ...base, s: "2015-01-01", e: "2020-12-31", m: "active_1km", mod: "isotonic", syn: "1" } as ExploreParams;
    const req = buildRequest(p, REGIONS, null);
    expect(req).toMatchObject({ start: "2015-01-01", end: "2020-12-31", metric: "active_1km", model: "isotonic", synthetic: true });
  });

  it("describes the area being analysed", () => {
    expect(resolveArea(base, REGIONS, null).name).toBe("Punjab & Haryana, India");
    expect(resolveArea({ ...base, box: "1,2,3,4" } as ExploreParams, REGIONS, null)).toMatchObject({ custom: true, name: "Custom box" });
    expect(resolveArea(base, REGIONS, { x: 1 })).toMatchObject({ custom: true, bbox: null });
    expect(resolveArea(base, undefined, null).bbox).toBeNull();
    expect(resolvePeriod(base, null)).toEqual({ start: "2012-06-01", end: "2024-12-31" });
  });
});
