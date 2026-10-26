import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AtlasGrid } from "@/components/site/AtlasGrid";
import { Landing } from "@/components/site/Landing";
import type { Findings, ShowcaseEntry } from "@/lib/showcase";

vi.mock("next/link", () => ({ default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => <a href={href} {...rest}>{children}</a> }));
vi.mock("next/dynamic", () => ({ default: () => () => null }));
vi.mock("@/components/explore/ThemeToggle", () => ({ ThemeToggle: () => null }));

afterEach(cleanup);
beforeEach(() => vi.restoreAllMocks());

const findings: Findings = {
  metric: "frp_sum_mw",
  synthetic: false,
  years: [2000, 2025],
  overlap: { days: 5095, modis_total: 100, viirs_total: 170, ratio: 1.7 },
  overpass: { n_modis: 1000, n_viirs: 4000, modis_seen_by_viirs: 0.33, viirs_seen_by_modis: 0.14 },
  normalization: {
    chosen: "quantile", n_weeks: 727, years: [2012, 2025],
    before: { r2_log: 0.77, mae_log: 0.91, bias_rel: -0.41, spearman: 0.95, coverage: 0.9 },
    after: { r2_log: 0.89, mae_log: 0.51, bias_rel: 0.01, spearman: 0.96, coverage: 0.9 },
    scale_baseline: null, band_factor: 3.1, level: 0.9, cv: [],
  },
  reconstructed_share: 0.45,
  busiest_day: "2016-11-07",
  top_season: { season: "2024-25", z: -3.5, text: "2024-25 was 3.5 robust standard deviations below the median of the other 23 fire years." },
  top_events: [],
  segments: [
    { start_doy: 290, peak_doy: 303, end_doy: 312, length_days: 23, total: 75 },
    { start_doy: 122, peak_doy: 129, end_doy: 136, length_days: 15, total: 25 },
  ],
  notes: [],
};

const entry = (id: string, state: ShowcaseEntry["state"], extra: Partial<ShowcaseEntry> = {}): ShowcaseEntry => ({
  id, name: `Region ${id}`, bbox: [0, 0, 1, 1], blurb: `Story of ${id}.`, start: "2000-11-01", end: "2025-12-31",
  state, job_id: state === "ready" ? `job-${id}` : null, findings: state === "ready" ? findings : null, reason: null, ...extra,
});

function mockApi(rows: ShowcaseEntry[] | "down") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => (rows === "down" ? Promise.reject(new Error("offline")) : new Response(JSON.stringify(rows), { status: 200 }))),
  );
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Atlas", () => {
  it("shows computed findings for a ready region and a deep link into the workspace", async () => {
    mockApi([entry("a", "ready")]);
    wrap(<AtlasGrid />);
    await waitFor(() => expect(screen.getByText("Region a")).toBeTruthy());
    expect(screen.getByText(/2 burning seasons/)).toBeTruthy();
    expect(screen.getByText(/peaks around 30 Oct and peaks around 9 May/)).toBeTruthy();
    expect(screen.getByText(/33% of MODIS detections are also seen by VIIRS/)).toBeTruthy();
    expect(screen.getByText(/2024-25 was 3.5 robust standard deviations below/)).toBeTruthy();
    const link = screen.getByRole("link", { name: /Open in the workspace/ }) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toContain("/explore?r=a");
    expect(link.getAttribute("href")).toContain("day=2016-11-07");
  });

  it("invents nothing for a region whose data is missing, and says why in plain words", async () => {
    mockApi([entry("b", "unavailable", { reason: "Data for MODIS_SP is not cached yet." })]);
    wrap(<AtlasGrid />);
    await waitFor(() => expect(screen.getByText("Region b")).toBeTruthy());
    expect(screen.getByText(/has not been downloaded yet/)).toBeTruthy();
    expect(screen.queryByText(/What the data show/)).toBeNull();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.getByText("Data for MODIS_SP is not cached yet.")).toBeTruthy(); // technical detail is available
  });

  it("says a region is being computed while it is", async () => {
    mockApi([entry("c", "computing")]);
    wrap(<AtlasGrid />);
    expect(await screen.findByText(/Computing this region/)).toBeTruthy();
  });

  it("explains an unreachable service and offers a retry", async () => {
    mockApi("down");
    wrap(<AtlasGrid />);
    // the hook retries once before giving up, so allow for that delay
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy(), { timeout: 5000 });
    expect(screen.getByText(/not reachable/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("words a region where VIIRS records less than MODIS correctly", async () => {
    mockApi([entry("d", "ready")]);
    const rows = [{ ...entry("d", "ready"), findings: { ...findings, overlap: { ...findings.overlap, ratio: 0.7 } } }];
    mockApi(rows);
    wrap(<AtlasGrid />);
    await waitFor(() => expect(screen.getByText(/1.4× less/)).toBeTruthy());
    expect(screen.getByText(/fire radiative power than MODIS does/)).toBeTruthy();
  });
});

describe("Landing", () => {
  it("shows the three computed statistics and where they come from", async () => {
    mockApi([entry("punjab-haryana", "ready")]);
    wrap(<Landing />);
    await waitFor(() => expect(screen.getByText("1.7×")).toBeTruthy());
    expect(screen.getByText("−41% → +1%")).toBeTruthy();
    expect(screen.getByText("26 years")).toBeTruthy();
    expect(screen.getByText(/Computed from NASA FIRMS data for Region punjab-haryana, 2000 to 2025/)).toBeTruthy();
  });

  it("shows no statistics, and says so, when no region is ready", async () => {
    mockApi([entry("a", "unavailable")]);
    wrap(<Landing />);
    await waitFor(() => expect(screen.getByText(/Live findings appear once a region/)).toBeTruthy());
    expect(screen.queryByText(/×/)).toBeNull();
  });

  it("explains an unreachable service without fabricating anything", async () => {
    mockApi("down");
    wrap(<Landing />);
    await waitFor(() => expect(screen.getByText(/data service is not reachable/)).toBeTruthy(), { timeout: 5000 });
    expect(screen.getByRole("link", { name: /Explore the record/ })).toBeTruthy(); // the workspace link still works
  });

  it("never features synthetic findings", async () => {
    mockApi([{ ...entry("a", "ready"), findings: { ...findings, synthetic: true } }]);
    wrap(<Landing />);
    await waitFor(() => expect(screen.getByText(/Live findings appear once a region/)).toBeTruthy());
  });
});
