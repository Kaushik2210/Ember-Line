import { defineConfig } from "@playwright/test";

const WEB = process.env.E2E_WEB_URL ?? "http://localhost:3000";

// Software WebGL so MapLibre and deck.gl draw in headless Chromium.
const launchOptions = {
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"],
};

export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  outputDir: "./e2e/.results",
  use: { baseURL: WEB, launchOptions, trace: "off", screenshot: "only-on-failure", reducedMotion: "no-preference" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true } },
  ],
  // Reuses servers that are already running; starts them otherwise.
  webServer: [
    { command: "npm run dev", url: WEB, reuseExistingServer: true, timeout: 120_000 },
    {
      command: "uv run --project ../api uvicorn emberline.main:app --app-dir ../api --port 8000",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
