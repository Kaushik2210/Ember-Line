import { describe, expect, it } from "vitest";
import { addDays, clampDay, daysBetween, defaultDay, formatDay } from "@/lib/day";
import type { ResultPayload } from "@/lib/types";

describe("day arithmetic", () => {
  it("adds and counts days across month and leap boundaries", () => {
    expect(addDays("2019-12-31", 1)).toBe("2020-01-01");
    expect(addDays("2020-02-28", 1)).toBe("2020-02-29");
    expect(addDays("2020-03-01", -1)).toBe("2020-02-29");
    expect(daysBetween("2019-11-01", "2019-11-30")).toBe(29);
    expect(daysBetween("2020-01-01", "2019-01-01")).toBe(-365);
  });
  it("clamps into a range", () => {
    expect(clampDay("2010-01-01", "2012-06-01", "2020-01-01")).toBe("2012-06-01");
    expect(clampDay("2030-01-01", "2012-06-01", "2020-01-01")).toBe("2020-01-01");
    expect(clampDay("2015-01-01", "2012-06-01", "2020-01-01")).toBe("2015-01-01");
  });
  it("formats in UTC without shifting the date", () => {
    expect(formatDay("2019-11-01")).toBe("1 Nov 2019");
  });
});

function result(value: (number | null)[], reconstructed: number[]): ResultPayload {
  const dates = value.map((_, i) => addDays("2012-01-01", i));
  return { harmonized: { dates, value, reconstructed, lo: value, hi: value, modis_basis: null } } as unknown as ResultPayload;
}

describe("default day", () => {
  it("prefers the busiest day VIIRS observed over a bigger reconstructed one", () => {
    const r = result([100, 5, 40, 90], [1, 0, 0, 1]);
    expect(defaultDay(r)).toBe("2012-01-03");
  });
  it("falls back to the busiest harmonised day when nothing was observed", () => {
    expect(defaultDay(result([3, 9, 1], [1, 1, 1]))).toBe("2012-01-02");
  });
  it("skips missing days and handles no result", () => {
    expect(defaultDay(result([null, null, 4], [0, 0, 0]))).toBe("2012-01-03");
    expect(defaultDay(result([null, null], [0, 0]))).toBeNull();
    expect(defaultDay(undefined)).toBeNull();
  });
});
