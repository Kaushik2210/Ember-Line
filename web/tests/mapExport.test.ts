import { describe, expect, it } from "vitest";
import { metersPerPixel } from "@/lib/mapExport";

describe("map scale", () => {
  it("is about 78 km per pixel at zoom 0 on the equator with 512 px tiles", () => {
    expect(metersPerPixel(0, 0)).toBeCloseTo(78_271.5, 0);
  });
  it("halves with every zoom level", () => {
    expect(metersPerPixel(30, 5) / metersPerPixel(30, 6)).toBeCloseTo(2, 6);
  });
  it("shrinks toward the poles", () => {
    expect(metersPerPixel(60, 4)).toBeCloseTo(metersPerPixel(0, 4) / 2, 3);
  });
});
