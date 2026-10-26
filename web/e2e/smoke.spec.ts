import { expect, test } from "@playwright/test";
import { readyPreset, waitForWorkspace } from "./helpers";

test("landing, then the workspace, a preset and the calendar", async ({ page, request }) => {
  await readyPreset(request); // make sure the region is computed so the path is not a cold start
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /One consistent record of fire/ })).toBeVisible();

  await expect(page.getByText(/Computed from NASA FIRMS data/)).toBeVisible({ timeout: 60_000 }); // the link deep-links once findings load
  await page.getByRole("link", { name: /Explore the record/ }).click();
  await expect(page).toHaveURL(/\/explore\?.*r=punjab-haryana/);
  await waitForWorkspace(page);

  // the calendar is drawn: a canvas with painted pixels, one row per year
  const cal = page.getByRole("img", { name: /Daily calendar heatmap/ });
  await expect(cal).toBeVisible();
  const painted = await cal.evaluate((c: HTMLCanvasElement) => {
    const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++;
    return n;
  });
  expect(painted).toBeGreaterThan(10_000);

  // the other views answer too
  for (const name of ["Seasonality", "Unusual periods", "Sensor agreement", "Data quality"]) {
    await page.getByRole("tab", { name }).click();
    await expect(page.getByRole("tab", { name, selected: true })).toBeVisible();
    await expect(page.getByRole("tabpanel")).not.toBeEmpty();
  }
});

test("a workspace link reproduces the view", async ({ page, request }) => {
  const url = await readyPreset(request, "agreement");
  await page.goto(url);
  await waitForWorkspace(page);
  await expect(page.getByRole("tab", { name: "Sensor agreement", selected: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Before and after normalising" })).toBeVisible();
});
