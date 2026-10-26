"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { doyLabel } from "@/lib/calendar";
import { type ShowcaseEntry, exploreLink, pct, signedPct, useShowcase } from "@/lib/showcase";

function Ready({ e }: { e: ShowcaseEntry }) {
  const f = e.findings!;
  const n = f.normalization;
  const seasons = f.segments;
  const ev = f.top_events[0];
  return (
    <div className="mt-4 flex flex-col gap-3 text-sm">
      <p className="text-xs uppercase tracking-wide text-faint">What the data show</p>
      <ul className="flex flex-col gap-2.5 text-muted">
        {seasons.length > 0 && (
          <li>
            <span className="text-ink">{seasons.length > 1 ? `${seasons.length} burning seasons. ` : "One burning season. "}</span>
            {seasons.map((s) => `peaks around ${doyLabel(s.peak_doy)}`).join(" and ")}.
          </li>
        )}
        {f.overlap.ratio != null && (
          <li>
            <span className="text-ink">
              VIIRS records {f.overlap.ratio >= 1 ? `${f.overlap.ratio.toFixed(1)}× the` : `${(1 / f.overlap.ratio).toFixed(1)}× less`}
            </span>{" "}
            fire radiative power {f.overlap.ratio >= 1 ? "that MODIS does" : "than MODIS does"} on the same days.
          </li>
        )}
        {f.overpass?.modis_seen_by_viirs != null && f.overpass.viirs_seen_by_modis != null && (
          <li>
            When both satellites pass together, {pct(f.overpass.modis_seen_by_viirs)} of MODIS detections are also seen by VIIRS, but only{" "}
            {pct(f.overpass.viirs_seen_by_modis)} of VIIRS detections are seen by MODIS.
          </li>
        )}
        {n?.before?.bias_rel != null && n.after?.bias_rel != null && (
          <li>
            Normalising ({n.chosen.replace("theilsen", "Theil–Sen")}) moves MODIS bias from <span className="num text-ink">{signedPct(n.before.bias_rel)}</span> to{" "}
            <span className="num text-ink">{signedPct(n.after.bias_rel)}</span> against VIIRS, on years held out of the fit.
          </li>
        )}
        {f.top_season && <li>{f.top_season.text}</li>}
        {ev && (
          <li>
            {ev.text.replace(/ Less reliable:.*$/, "")}
            {ev.caveat ? <span className="text-modis"> {ev.caveat}</span> : null}
          </li>
        )}
      </ul>
    </div>
  );
}

function Card({ e }: { e: ShowcaseEntry }) {
  return (
    <article className="flex flex-col rounded-xl border border-line bg-panel p-5">
      <h2 className="text-lg font-semibold text-ink">{e.name}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted">{e.blurb}</p>

      {e.state === "ready" && e.findings && <Ready e={e} />}
      {e.state === "computing" && (
        <p role="status" className="mt-4 flex items-center gap-2 text-sm text-muted">
          <Loader2 aria-hidden className="size-4 animate-spin" /> Computing this region&apos;s findings from the NASA record…
        </p>
      )}
      {e.state === "unavailable" && (
        <div className="mt-4 rounded-lg border border-line bg-raised p-3 text-sm text-muted">
          <p>The NASA data for this region has not been downloaded yet, so there are no findings to show. You can still open it in the workspace.</p>
          {e.reason && (
            <details className="mt-2 text-xs text-faint">
              <summary className="cursor-pointer">Details</summary>
              <p className="mt-1">{e.reason}</p>
            </details>
          )}
        </div>
      )}

      <div className="mt-auto pt-5">
        <Link
          href={exploreLink(e)}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-line px-4 text-sm font-medium text-ink hover:border-[var(--border-strong)] pointer-coarse:min-h-11"
        >
          Open in the workspace <ArrowRight aria-hidden className="size-4" />
        </Link>
      </div>
    </article>
  );
}

export function AtlasGrid() {
  const q = useShowcase();
  if (q.isLoading) {
    return (
      <div role="status" aria-label="Loading regions" className="grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-72 animate-pulse rounded-xl border border-line bg-panel" />
        ))}
      </div>
    );
  }
  if (q.isError || !q.data) {
    return (
      <p role="alert" className="rounded-xl border border-line bg-panel p-5 text-sm text-muted">
        The data service is not reachable, so the case studies cannot be shown.{" "}
        <button className="text-ink underline" onClick={() => void q.refetch()}>
          Retry
        </button>
      </p>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {q.data.map((e) => (
        <Card key={e.id} e={e} />
      ))}
    </div>
  );
}
