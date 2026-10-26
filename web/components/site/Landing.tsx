"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { formatDay } from "@/lib/day";
import { exploreLink, featured, proofStats, useShowcase } from "@/lib/showcase";
import { HeroMap } from "./HeroMap";
import { SiteFooter, SiteHeader } from "./SiteShell";

const QUESTIONS = [
  {
    n: "1",
    title: "Select an area and period",
    body: "Pick a preset region, draw a box, or upload a shape. Any period from 2000 to the latest data FIRMS provides.",
    tab: "calendar",
  },
  {
    n: "2",
    title: "Explore historical hotspots",
    body: "Slide between what MODIS saw and what VIIRS saw on the same day, over NASA satellite imagery, and step through time.",
    tab: "calendar",
  },
  {
    n: "3",
    title: "Find seasonal patterns and unusual periods",
    body: "Typical fire seasons for each region, and the seasons and weeks that stand out. Each year is compared only with the others.",
    tab: "seasonality",
  },
  {
    n: "4",
    title: "Normalize so comparisons are meaningful",
    body: "See why the sensors disagree, how the correction works, and how well it holds on years the model never saw.",
    tab: "agreement",
  },
] as const;

export function Landing() {
  const showcase = useShowcase();
  const entry = featured(showcase.data);
  const f = entry?.findings ?? null;
  const stats = f ? proofStats(f) : [];
  const computing = showcase.data?.some((e) => e.state === "computing");
  const start = entry ? exploreLink(entry) : "/explore";

  return (
    <div className="bg-bg text-ink">
      <section className="relative isolate flex min-h-[88dvh] flex-col overflow-hidden">
        <HeroMap entry={entry} />
        <div aria-hidden className="absolute inset-0 bg-gradient-to-r from-bg via-bg/85 to-bg/10" />
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-bg to-transparent" />
        <SiteHeader overlay current="/" />

        <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center px-4 pb-10 pt-24 sm:px-6">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">MODIS and VIIRS, harmonized</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
            One consistent record of fire, from two sensors.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
            Satellites disagree about how much is burning. EMBERLINE turns the two NASA fire records into one calendar of burning
            activity you can compare across sensors and decades, with the uncertainty shown.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href={start}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-medium text-bg hover:opacity-90"
            >
              Explore the record <ArrowRight aria-hidden className="size-4" />
            </Link>
            <Link
              href="/method"
              className="inline-flex min-h-11 items-center rounded-lg border border-line bg-panel/70 px-5 text-sm font-medium text-ink backdrop-blur hover:border-[var(--border-strong)]"
            >
              How it works
            </Link>
          </div>

          <div className="mt-12 max-w-4xl" aria-live="polite">
            {stats.length > 0 && entry && f ? (
              <>
                <ul className="grid gap-3 sm:grid-cols-3">
                  {stats.map((s) => (
                    <li key={s.label} className="rounded-xl border border-line bg-panel/80 p-4 backdrop-blur">
                      <p className="num text-2xl font-semibold text-ink sm:text-3xl">{s.value}</p>
                      <p className="mt-1 text-sm text-ink">{s.label}</p>
                      <p className="mt-2 text-xs leading-relaxed text-faint">{s.detail}</p>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-faint">
                  Computed from NASA FIRMS data for {entry.name}
                  {f.years ? `, ${f.years[0]} to ${f.years[1]}` : ""}
                  {f.busiest_day ? `. Map: detections on ${formatDay(f.busiest_day)}, MODIS in amber and VIIRS in blue.` : "."}
                </p>
              </>
            ) : showcase.isLoading || computing ? (
              <div role="status" className="grid gap-3 sm:grid-cols-3" aria-label="Computing findings">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-32 animate-pulse rounded-xl border border-line bg-panel/60" />
                ))}
              </div>
            ) : (
              <p className="max-w-xl rounded-xl border border-line bg-panel/80 p-4 text-sm text-muted backdrop-blur">
                {showcase.isError
                  ? "The data service is not reachable right now, so live findings cannot be shown. The workspace will work again once it is back."
                  : "Live findings appear once a region's NASA data has been downloaded. You can already run your own analysis in the workspace."}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight">Four questions, one workspace</h2>
        <p className="mt-2 max-w-2xl text-muted">The challenge asks for a consistent calendar of burning activity from two sensor records. This is how each part is answered.</p>
        <ol className="mt-8 grid gap-4 sm:grid-cols-2">
          {QUESTIONS.map((q) => (
            <li key={q.n}>
              <Link
                href={`/explore?tab=${q.tab}`}
                className="group block h-full rounded-xl border border-line bg-panel p-5 transition-colors duration-150 hover:border-[var(--border-strong)]"
              >
                <span className="num text-xs text-faint">{q.n}</span>
                <h3 className="mt-1 text-base font-semibold text-ink">{q.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{q.body}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-viirs group-hover:underline">
                  Open in the workspace <ArrowRight aria-hidden className="size-3.5" />
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="border-t border-line bg-panel">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-10 sm:px-6">
          <div>
            <h2 className="text-lg font-semibold">Six places where the sensors tell different stories</h2>
            <p className="mt-1 max-w-xl text-sm text-muted">From crop-residue burning in Punjab to the Australian Black Summer and the 2023 Canadian season, each with what the data show.</p>
          </div>
          <Link href="/atlas" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-line px-5 text-sm font-medium hover:border-[var(--border-strong)]">
            Browse the atlas <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}
