import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { horizontalOverflow, readyPreset, waitForWorkspace } from "./helpers";

// Visual QA: screenshots of every page and workspace tab at the project's two reference sizes, plus a
// check that nothing overflows sideways. Images go to qa-screenshots/<project>/ (not committed).

const DIR = "qa-screenshots";

test.beforeAll(() => mkdirSync(DIR, { recursive: true }));

async function settle(page: import("@playwright/test").Page) {
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => undefined);
  await page.waitForTimeout(1500); // map tiles and charts finish painting
}

for (const [name, path] of [
  ["landing", "/"],
  ["atlas", "/atlas"],
  ["method", "/method"],
  ["about", "/about"],
] as const) {
  test(`site page: ${name}`, async ({ page }, info) => {
    await page.goto(path);
    if (name === "landing" || name === "atlas") {
      // wait for computed findings rather than a skeleton
      await expect(page.locator("[aria-label='Computing findings'], [aria-label='Loading regions']")).toHaveCount(0, { timeout: 240_000 });
    }
    await settle(page);
    await page.screenshot({ path: `${DIR}/${info.project.name}-${name}.png`, fullPage: true });
    expect(await horizontalOverflow(page), "horizontal overflow").toBeNull();
  });
}

for (const tab of ["calendar", "seasonality", "anomalies", "agreement", "quality"] as const) {
  test(`workspace tab: ${tab}`, async ({ page, request }, info) => {
    await page.goto(await readyPreset(request, tab));
    await waitForWorkspace(page);
    await settle(page);
    await page.screenshot({ path: `${DIR}/${info.project.name}-explore-${tab}.png` });
    expect(await horizontalOverflow(page), "horizontal overflow").toBeNull();
  });
}

test("workspace: why drawer and export menu", async ({ page, request }, info) => {
  await page.goto(await readyPreset(request));
  await waitForWorkspace(page);
  await page.getByRole("button", { name: /Why they differ/ }).click();
  await expect(page.getByRole("dialog", { name: "Why the sensors differ" })).toBeVisible();
  await settle(page);
  await page.screenshot({ path: `${DIR}/${info.project.name}-explore-why.png` });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: /Export/ }).click();
  await expect(page.getByRole("menu", { name: "Export" })).toBeVisible();
  await page.screenshot({ path: `${DIR}/${info.project.name}-explore-export.png` });
});

test("workspace: controls", async ({ page, request }, info) => {
  await page.goto(await readyPreset(request));
  await waitForWorkspace(page);
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Open controls" }).click();
    await expect(page.getByRole("dialog", { name: "Controls" })).toBeVisible();
  }
  await page.getByRole("button", { name: /Quality policy/ }).click();
  await settle(page);
  await page.screenshot({ path: `${DIR}/${info.project.name}-explore-controls.png` });
});
