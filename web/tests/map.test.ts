import { describe, expect, it } from "vitest";
import { LAYERS, imageryFor, tileUrl } from "@/lib/gibs";
import { SENSOR_RGB, countBySensor, toBuffers } from "@/lib/hotspotBuffers";
import type { HotspotCollection } from "@/lib/types";

const pt = (lon: number, lat: number, sensor: "modis" | "viirs", extra = {}) => ({
  type: "Feature" as const,
  geometry: { type: "Point" as const, coordinates: [lon, lat] as [number, number] },
  properties: { sensor, ...extra },
});

describe("GIBS tiles", () => {
  it("builds a MapLibre template with the verified matrix set and row/col order", () => {
    const u = tileUrl(LAYERS.modis, "2019-11-01");
    expect(u).toBe(
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2019-11-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
    );
  });
  it("the base layer has no time dimension", () => {
    expect(tileUrl(LAYERS.base, "2019-11-01")).toContain("/default/default/GoogleMapsCompatible_Level8/");
  });
  it("falls back to Terra imagery on the VIIRS side before VIIRS imagery exists", () => {
    expect(imageryFor("viirs", "2014-05-01")).toMatchObject({ fallback: true, layer: LAYERS.modis });
    expect(imageryFor("viirs", "2015-11-24")).toMatchObject({ fallback: false, layer: LAYERS.viirs });
    expect(imageryFor("modis", "2001-01-01").fallback).toBe(false);
    expect(imageryFor("viirs", null).fallback).toBe(false);
  });
});

describe("hotspot buffers", () => {
  const fc: HotspotCollection = {
    type: "FeatureCollection",
    properties: { aggregated: false, total: 3 },
    features: [pt(75.1, 30.2, "modis"), pt(75.2, 30.3, "viirs"), pt(75.3, 30.4, "viirs")],
  };

  it("packs positions, radii and colours per point", () => {
    const b = toBuffers(fc);
    expect(b.length).toBe(3);
    expect(Array.from(b.positions.slice(0, 2)).map((x) => Number(x.toFixed(2)))).toEqual([75.1, 30.2]);
    expect(b.radii[0]).toBe(500); // MODIS: half of a 1 km pixel
    expect(b.radii[1]).toBeCloseTo(187.5); // VIIRS: half of a 375 m pixel
    expect(Array.from(b.colors.slice(0, 3))).toEqual([...SENSOR_RGB.modis]);
    expect(Array.from(b.colors.slice(4, 7))).toEqual([...SENSOR_RGB.viirs]);
  });

  it("can restrict to one sensor, keeping features for picking", () => {
    const b = toBuffers(fc, "viirs");
    expect(b.length).toBe(2);
    expect(b.features.every((f) => f.properties.sensor === "viirs")).toBe(true);
  });

  it("sizes aggregated cells by their width and shades by count", () => {
    const agg: HotspotCollection = {
      type: "FeatureCollection",
      properties: { aggregated: true, total: 110, cell_deg: 0.1 },
      features: [
        pt(75, 30, "modis", { count: 10, cell_deg: 0.1 }),
        pt(75.1, 30, "modis", { count: 100, cell_deg: 0.1 }),
      ],
    };
    const b = toBuffers(agg);
    expect(b.aggregated).toBe(true);
    expect(b.radii[0]).toBeCloseTo(5550);
    expect(b.colors[3]).toBeLessThan(b.colors[7]); // fewer detections, more transparent
    expect(b.colors[7]).toBeLessThanOrEqual(255);
  });

  it("handles an empty day", () => {
    const empty: HotspotCollection = { type: "FeatureCollection", properties: { aggregated: false, total: 0 }, features: [] };
    expect(toBuffers(empty).length).toBe(0);
    expect(countBySensor(empty)).toEqual({ modis: 0, viirs: 0 });
    expect(countBySensor(undefined)).toEqual({ modis: 0, viirs: 0 });
  });

  it("counts detections by sensor, summing aggregated cells", () => {
    expect(countBySensor(fc)).toEqual({ modis: 1, viirs: 2 });
    const agg: HotspotCollection = {
      type: "FeatureCollection",
      properties: { aggregated: true, total: 12 },
      features: [pt(0, 0, "modis", { count: 4 }), pt(0, 1, "viirs", { count: 8 })],
    };
    expect(countBySensor(agg)).toEqual({ modis: 4, viirs: 8 });
  });
});
