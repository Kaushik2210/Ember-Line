import { describe, expect, it } from "vitest";
import { COLS, cellOfDate, dateOfCell, doyLabel, reconstructedShare, scaleMax, valueColor } from "@/lib/calendar";

describe("calendar cells", () => {
  it("maps columns to dates, skipping 29 February in leap years", () => {
    expect(dateOfCell(2019, 0)).toBe("2019-01-01");
    expect(dateOfCell(2019, 59)).toBe("2019-03-01");
    expect(dateOfCell(2020, 58)).toBe("2020-02-28");
    expect(dateOfCell(2020, 59)).toBe("2020-03-01"); // 29 Feb has no column
    expect(dateOfCell(2020, 364)).toBe("2020-12-31");
    expect(dateOfCell(2019, 364)).toBe("2019-12-31");
  });

  it("round-trips every day of a leap and a normal year", () => {
    for (const year of [2019, 2020]) {
      for (let c = 0; c < COLS; c++) {
        expect(cellOfDate(dateOfCell(year, c))).toEqual({ year, col: c });
      }
    }
  });

  it("puts 29 February on the 28 February cell", () => {
    expect(cellOfDate("2020-02-29")).toEqual({ year: 2020, col: 58 });
  });
});

describe("colour scale", () => {
  it("uses the 99th percentile of log1p across matrices", () => {
    const m = [[0, 1, 10, 100, null], [1000, 5, 5, 5, 5]];
    expect(scaleMax(m)).toBeCloseTo(Math.log1p(1000));
    expect(scaleMax([[null, 0]])).toBe(1);
    expect(scaleMax([[1, 2]], [[3000]])).toBeCloseTo(Math.log1p(3000));
  });

  it("distinguishes missing, zero and positive values", () => {
    const max = Math.log1p(100);
    expect(valueColor(null, max)).toBeNull();
    expect(valueColor(0, max)).toBe("#1a222c");
    expect(valueColor(-3, max)).toBe("#1a222c");
    const low = valueColor(1, max);
    const high = valueColor(100, max);
    expect(low).toMatch(/^#[0-9a-f]{6}$/i);
    expect(high).not.toBe(low);
    expect(valueColor(1e6, max)).toBe(high); // clamped at the top of the scale
  });

  it("counts reconstructed days, ignoring missing ones", () => {
    expect(reconstructedShare([1, 1, 0, null])).toBeCloseTo(2 / 3);
    expect(reconstructedShare([null, null])).toBe(0);
    expect(reconstructedShare([0, 0, 0])).toBe(0);
  });
});

describe("day-of-year labels", () => {
  it("names days on the 365-day calendar", () => {
    expect(doyLabel(1)).toBe("1 Jan");
    expect(doyLabel(60)).toBe("1 Mar");
    expect(doyLabel(305)).toBe("1 Nov");
    expect(doyLabel(365)).toBe("31 Dec");
  });
  it("clamps out-of-range input", () => {
    expect(doyLabel(0)).toBe("1 Jan");
    expect(doyLabel(999)).toBe("31 Dec");
  });
});
