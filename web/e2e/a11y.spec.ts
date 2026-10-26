import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { readyPreset, waitForWorkspace } from "./helpers";

// Automated accessibility audit (axe, WCAG 2.1 A and AA) of every page and workspace tab.
// Map canvases are excluded: they are decorative to axe and covered by the text alternatives beside them.

async function audit(page: import("@playwright/test").Page) {
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .exclude(".maplibregl-canvas, canvas")
    .analyze();
  return r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length}x ${v.nodes[0]?.target.join(" ")}`);
}

for (const [name, path] of [
  ["landing", "/"],
  ["atlas", "/atlas"],
  ["method", "/method"],
  ["about", "/about"],
] as const) {
  test(`axe: ${name}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => undefined);
    await page.waitForTimeout(1000);
    expect(await audit(page)).toEqual([]);
  });
}

for (const tab of ["calendar", "seasonality", "anomalies", "agreement", "quality"] as const) {
  test(`axe: workspace ${tab}`, async ({ page, request }) => {
    await page.goto(await readyPreset(request, tab));
    await waitForWorkspace(page);
    await page.waitForTimeout(1500);
    expect(await audit(page)).toEqual([]);
  });
}
