"use client";

import Link from "next/link";
import { type Findings, exploreLink, featured, pct, signedPct, useShowcase } from "@/lib/showcase";

const n2 = (v: number | null | undefined) => (v == null ? "n/a" : v.toFixed(2));

function CvTable({ f }: { f: NonNullable<Findings["normalization"]> }) {
  return (
    <div className="my-4 overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <caption className="sr-only">Cross-validated error of each normalisation model</caption>
        <thead>
          <tr className="text-xs text-muted">
            <th className="py-1.5 pr-4 font-medium">Model</th>
            <th className="pr-4 font-medium">R² (log)</th>
            <th className="pr-4 font-medium">Error (log)</th>
            <th className="pr-4 font-medium">Bias</th>
            <th className="pr-4 font-medium">Rank corr.</th>
            <th className="font-medium">Coverage</th>
          </tr>
        </thead>
        <tbody className="num text-ink">
          {f.cv.map((r) => (
            <tr key={r.model} className="border-t border-line">
              <td className="py-2 pr-4 font-sans">
                {r.model}
                {r.model === f.chosen ? " (chosen)" : !r.selectable ? " (baseline)" : ""}
              </td>
              <td className="pr-4">{n2(r.r2_log)}</td>
              <td className="pr-4">{n2(r.mae_log)}</td>
              <td className="pr-4">{signedPct(r.bias_rel)}</td>
              <td className="pr-4">{n2(r.spearman)}</td>
              <td>{pct(r.coverage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Validation numbers for the featured region, computed from the cached record when it is available. */
export function MethodLive() {
  const q = useShowcase();
  const e = featured(q.data);
  const f = e?.findings;
  if (q.isLoading || q.data?.some((x) => x.state === "computing")) {
    return <p role="status" className="my-4 text-sm text-faint">Computing validation results from the NASA record…</p>;
  }
  if (!e || !f || !f.normalization) {
    return (
      <p className="my-4 rounded-lg border border-line bg-panel p-4 text-sm text-muted">
        Validation results are computed from a region&apos;s downloaded record and are not available right now. They appear here, with the
        figures and the exact period, as soon as a region&apos;s data is on disk.
      </p>
    );
  }
  const n = f.normalization;
  return (
    <div>
      <p>
        Results for <strong>{e.name}</strong>, {e.start} to {e.end}, measure: {f.metric === "frp_sum_mw" ? "fire radiative power" : f.metric}. Computed by the pipeline described above, not typed in.
      </p>
      <CvTable f={n} />
      <ul>
        <li>
          {n.n_weeks.toLocaleString("en-GB")} overlapping weeks between {n.years[0]} and {n.years[1]}. Chosen model: <strong>{n.chosen}</strong>.
        </li>
        {n.before?.bias_rel != null && n.after?.bias_rel != null && (
          <li>
            Bias of MODIS against VIIRS: {signedPct(n.before.bias_rel)} before, {signedPct(n.after.bias_rel)} after, on years held out of each fit.
          </li>
        )}
        {n.band_factor != null && (
          <li>
            The {pct(n.level)} prediction band is about ×{n.band_factor.toFixed(1)} wide on a weekly total. That is the honest uncertainty of reconstructing one sensor from the other, not a rounding.
          </li>
        )}
        {f.overpass?.modis_seen_by_viirs != null && f.overpass.viirs_seen_by_modis != null && (
          <li>
            Coincident overpasses ({f.overpass.n_modis.toLocaleString("en-GB")} MODIS and {f.overpass.n_viirs.toLocaleString("en-GB")} VIIRS detections co-observed): {pct(f.overpass.modis_seen_by_viirs)} of MODIS detections have a VIIRS partner, {pct(f.overpass.viirs_seen_by_modis)} of VIIRS detections have a MODIS partner.
          </li>
        )}
        {f.overlap.ratio != null && (
          <li>
            Over {f.overlap.days.toLocaleString("en-GB")} days both sensors observed, VIIRS recorded {f.overlap.ratio.toFixed(2)}× the MODIS total of this measure.
          </li>
        )}
      </ul>
      <p>
        <Link href={exploreLink(e, "agreement")}>Open this analysis in the workspace</Link>. The full console report is{" "}
        <a href="https://github.com/Kaushik2210/Ember-Line/blob/main/docs/validation/punjab-haryana.md" target="_blank" rel="noopener noreferrer">
          in the repository
        </a>
        .
      </p>
    </div>
  );
}
