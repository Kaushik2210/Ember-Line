import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { horizontalOverflow } from "./helpers";

// Layout at in-between sizes (tablet portrait and landscape, a large desktop). Nothing may overflow sideways.

const SIZES = [
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 768 },
  { name: "wide", width: 1920, height: 1080 },
] as const;

const PAGES = [
  ["landing", "/"],
  ["atlas", "/atlas"],
  ["method", "/method"],
  ["explore", "/explore?r=punjab-haryana&s=2019-10-01&e=2019-11-30&day=2019-11-02"],
] as const;

test.beforeAll(() => mkdirSync("qa-screenshots", { recursive: true }));

for (const size of SIZES) {
  for (const [name, path] of PAGES) {
    test(`${name} at ${size.name}`, async ({ page }) => {
      await page.setViewportSize({ width: size.width, height: size.height });
      await page.goto(path);
      await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => undefined);
      await page.waitForTimeout(3000);
      await page.screenshot({ path: `qa-screenshots/${size.name}-${name}.png`, fullPage: name !== "explore" });
      expect(await horizontalOverflow(page), "horizontal overflow").toBeNull();
    });
  }
}
