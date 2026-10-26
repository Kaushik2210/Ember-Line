import { type APIRequestContext, type Page, expect } from "@playwright/test";

export const API = process.env.E2E_API_URL ?? "http://localhost:8000";

interface ShowcaseRow {
  id: string;
  state: string;
  start: string;
  end: string;
  job_id: string | null;
  findings: { busiest_day: string | null; synthetic: boolean } | null;
}

/** The workspace URL for the first ready real region, waiting for the API to finish computing it. */
export async function readyPreset(request: APIRequestContext, tab = "calendar"): Promise<string> {
  const t0 = Date.now();
  while (Date.now() - t0 < 200_000) {
    const rows = (await (await request.get(`${API}/api/showcase`)).json()) as ShowcaseRow[];
    const ready = rows.find((r) => r.id === "punjab-haryana" && r.state === "ready" && r.findings && !r.findings.synthetic);
    if (ready) {
      const p = new URLSearchParams({ r: ready.id, s: ready.start, e: ready.end, tab });
      if (ready.findings?.busiest_day) p.set("day", ready.findings.busiest_day);
      if (ready.job_id) p.set("job", ready.job_id);
      return `/explore?${p}`;
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error("Punjab and Haryana never became ready: is its data downloaded?");
}

/** Wait until the workspace has loaded a result and drawn the calendar. */
export async function waitForWorkspace(page: Page): Promise<void> {
  await expect(page.getByRole("tab", { selected: true })).toBeVisible();
  // the controls live in a drawer on phones, so wait for the result itself: the calendar or a tab panel with content
  await expect(page.getByRole("tabpanel")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("img", { name: /Daily calendar heatmap/ }).or(page.getByRole("heading").first())).toBeVisible({ timeout: 120_000 });
}

/** Resolve once the page has no horizontal overflow, and report the widest offender if it does. */
export async function horizontalOverflow(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const w = document.documentElement.clientWidth;
    if (document.documentElement.scrollWidth <= w + 1) return null;
    const bad = [...document.querySelectorAll("body *")]
      .map((e) => ({ e, r: e.getBoundingClientRect() }))
      .filter(({ e, r }) => r.right > w + 1 && r.width > 0 && !e.closest("[role=tablist], .overflow-x-auto, canvas, .maplibregl-map"))
      .sort((a, b) => b.r.right - a.r.right)[0];
    return bad ? `${bad.e.tagName}.${String(bad.e.className).slice(0, 80)} right=${Math.round(bad.r.right)} > ${w}` : "document wider than viewport";
  });
}
