import { expect, test } from "@playwright/test";

// Stepping days while tiles load, and switching Overlay and back to Compare, must not log errors.
test("map: console is clean through the main interactions", async ({ page }) => {
  const problems: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") problems.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

  await page.goto("/explore?r=punjab-haryana&s=2019-10-01&e=2019-11-30&day=2019-11-02");
  await expect(page.getByRole("region", { name: "Map of fire detections" })).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(6000);

  // step days quickly, which reloads imagery while tiles are still loading
  for (let i = 0; i < 6; i++) {
    await page.getByRole("button", { name: "Next day" }).click();
    await page.waitForTimeout(150);
  }
  await page.waitForTimeout(3000);
  await expect(page.locator("[data-sensor]")).toHaveCount(2);

  // overlay and back to compare
  await page.getByRole("radio", { name: "Overlay" }).click().catch(() => page.getByText("Overlay").click());
  await page.waitForTimeout(1500);
  await page.getByText("Compare", { exact: true }).click();
  await page.waitForTimeout(2500);

  expect(problems).toEqual([]);
});
