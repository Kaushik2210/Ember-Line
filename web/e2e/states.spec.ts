import { expect, test } from "@playwright/test";

// The honest states: what a visitor sees when the data service is down. Nothing is invented and there is a way forward.

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort("connectionrefused"));
});

test("landing says the service is unreachable and still offers the workspace", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/data service is not reachable/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("link", { name: /Explore the record/ })).toBeVisible();
  await expect(page.getByText(/Computed from NASA FIRMS data/)).toHaveCount(0);
});

test("atlas explains the outage and retries on request", async ({ page }) => {
  await page.goto("/atlas");
  await expect(page.getByRole("alert")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.getByText(/robust standard deviations/)).toHaveCount(0);
});

test("workspace shows an error with a way to run again instead of a blank screen", async ({ page }) => {
  await page.goto("/explore?r=punjab-haryana&s=2012-01-20&e=2024-12-31");
  await expect(page.getByRole("alert").first()).toBeVisible({ timeout: 60_000 });
});
