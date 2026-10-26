"use client";

import type { ResultPayload } from "@/lib/types";

/** Where the numbers came from: sources, versions, parameters, run time and the NASA acknowledgment. */
export function Provenance({ result }: { result: ResultPayload }) {
  const m = result.meta;
  const policy = m.quality_policy as Record<string, unknown> | undefined;
  const grid = m.grid as { kind: string; size_deg: number; h3_res: number } | undefined;
  const run = new Date(m.run_utc).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" });
  return (
    <footer className="border-t border-line px-4 py-2 text-xs text-faint">
      <p>
        Data: {m.sources.modis} and {m.sources.viirs}. EMBERLINE {m.emberline_version}, run {run} UTC.{" "}
        <a href="/method" className="text-muted underline hover:text-ink">
          Method
        </a>
      </p>
      <details className="mt-1">
        <summary className="min-h-6 cursor-pointer text-muted hover:text-ink">Parameters and acknowledgment</summary>
        <dl className="mt-1.5 grid min-w-0 gap-x-6 gap-y-1 sm:grid-cols-2">
          <div><dt className="inline text-muted">Measure: </dt><dd className="num inline">{m.metric}</dd></div>
          <div><dt className="inline text-muted">Grid: </dt><dd className="num inline">{grid ? (grid.kind === "h3" ? `H3 resolution ${grid.h3_res}` : `regular ${grid.size_deg}°`) : "n/a"}</dd></div>
          <div><dt className="inline text-muted">Model: </dt><dd className="num inline">{m.model.chosen ?? "none"}, {m.model.validation}</dd></div>
          <div><dt className="inline text-muted">Interval: </dt><dd className="num inline">{m.model.interval ?? "n/a"}</dd></div>
          <div className="sm:col-span-2"><dt className="inline text-muted">Quality policy: </dt><dd className="num inline break-all">{policy ? JSON.stringify(policy) : "n/a"}</dd></div>
        </dl>
        <p className="mt-2 leading-relaxed">{m.acknowledgment}</p>
      </details>
    </footer>
  );
}
