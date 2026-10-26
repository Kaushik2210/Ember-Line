import { describe, expect, it } from "vitest";
import { fileName } from "@/lib/download";

describe("file names", () => {
  it("are lowercase, dash-separated and path-safe", () => {
    expect(fileName("EMBERLINE", "Punjab & Haryana, India", "calendar")).toBe("emberline-punjab-haryana-india-calendar");
    expect(fileName("a/b\\c", "..", "x")).toBe("a-b-c-..-x");
  });
  it("skips empty parts", () => {
    expect(fileName("emberline", null, undefined, "", 2019)).toBe("emberline-2019");
    expect(fileName()).toBe("");
  });
});
