"use client";

import { ExternalLink } from "lucide-react";
import { useChartColors } from "@/lib/chartTheme";
import type { Annotation, PlatformRow, ResultPayload } from "@/lib/types";

const PLATFORM_LABEL: Record<string, string> = { Terra: "Terra MODIS", Aqua: "Aqua MODIS", SNPP: "Suomi NPP VIIRS" };

const ms = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const annotationDate = (a: Annotation): string | null =>
  a.precision === "undated" ? null : a.precision === "year" ? `${a.when}-07-01` : a.precision === "month" ? `${a.when}-15` : a.when;

function Timeline({ platforms, annotations }: { platforms: PlatformRow[]; annotations: Annotation[] }) {
  const c = useChartColors();
  if (platforms.length === 0) return null;
  const dated = annotations.filter((a) => annotationDate(a));
  const all = [...platforms.flatMap((p) => [p.first, p.last]), ...dated.map((a) => annotationDate(a) as string)];
  const lo = Math.min(...all.map(ms));
  const hi = Math.max(...all.map(ms));
  const W = 640;
  const L = 112;
  const R = 12;
  const rowH = 26;
  const top = 22;
  const x = (iso: string) => L + ((ms(iso) - lo) / Math.max(1, hi - lo)) * (W - L - R);
  const y0 = new Date(lo).getUTCFullYear();
  const y1 = new Date(hi).getUTCFullYear();
  const step = y1 - y0 > 18 ? 5 : y1 - y0 > 9 ? 2 : 1;
  const years: number[] = [];
  for (let y = Math.ceil(y0 / step) * step; y <= y1; y += step) years.push(y);
  const H = top + platforms.length * rowH + 8;
  const color = (sensor: string) => (sensor === "modis" ? c.modis : c.viirs);

  return (
    <div className="overflow-x-auto">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Timeline of when each satellite contributes data, with documented events marked." className="min-w-[560px]">
        {years.map((yr) => (
          <g key={yr}>
            <line x1={x(`${yr}-01-01`)} x2={x(`${yr}-01-01`)} y1={top - 4} y2={H - 4} stroke={c.line} />
            <text x={x(`${yr}-01-01`) + 3} y={12} fill={c.faint} fontSize={10} fontFamily="var(--font-jetbrains), monospace">{yr}</text>
          </g>
        ))}
        {platforms.map((p, i) => (
          <g key={p.platform}>
            <text x={L - 8} y={top + i * rowH + rowH / 2 + 3} textAnchor="end" fill={c.muted} fontSize={11}>{PLATFORM_LABEL[p.platform] ?? p.platform}</text>
            <rect x={x(p.first)} y={top + i * rowH + 5} width={Math.max(3, x(p.last) - x(p.first))} height={rowH - 10} rx={3} fill={color(p.sensor)} opacity={0.85}>
              <title>{`${PLATFORM_LABEL[p.platform] ?? p.platform}: ${p.first} to ${p.last}, ${p.detections.toLocaleString("en-GB")} detections in this record`}</title>
            </rect>
          </g>
        ))}
        {dated.map((a) => {
          const d = annotationDate(a) as string;
          return (
            <g key={a.title}>
              <line x1={x(d)} x2={x(d)} y1={top - 4} y2={H - 4} stroke={c.ink} strokeDasharray="2 3" opacity={0.55} />
              <circle cx={x(d)} cy={top - 4} r={3} fill={c.ink}>
                <title>{`${a.when}: ${a.title}`}</title>
              </circle>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function QualityTab({ result }: { result: ResultPayload }) {
  const q = result.quality;
  const counts = q.counts;
  const terra = result.validation.normalization_terra_only;
  const kept = counts.raw ? Math.round((100 * counts.kept) / counts.raw) : null;

  return (
    <div className="grid gap-5 p-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-col gap-5">
        <section>
          <h3 className="mb-2 text-sm font-semibold text-ink">Which satellites contribute when</h3>
          <Timeline platforms={q.platforms} annotations={q.annotations} />
          <p className="mt-1 text-xs text-faint">Bars show the first to last detection in this record. Dots mark documented events (listed on the right).</p>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-semibold text-ink">What the quality policy did</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs sm:grid-cols-4">
            {[
              ["Detections loaded", counts.raw],
              ["Kept", counts.kept],
              ["MODIS kept", counts.modis_kept],
              ["VIIRS kept", counts.viirs_kept],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt className="text-muted">{k}</dt>
                <dd className="num text-ink">{typeof v === "number" ? v.toLocaleString("en-GB") : "n/a"}</dd>
              </div>
            ))}
          </dl>
          {kept != null && <p className="mt-2 text-xs text-muted">{kept}% of detections passed. {counts.persistent_cells} persistent heat-source cells (flares, industry, volcanoes) were removed.</p>}
        </section>
        {terra && (
          <section className="rounded-lg border border-line p-3">
            <h3 className="text-sm font-semibold text-ink">Before Aqua, Terra reported alone</h3>
            <p className="mt-1 text-xs text-muted">
              With one satellite, MODIS sees far fewer detections, which would read as quiet years. A separate model ({terra.chosen}) calibrated on Terra&apos;s own overlap with VIIRS is used for those weeks
              {terra.used_before ? ` (before ${terra.used_before})` : ""}, and events found there are flagged as less reliable.
            </p>
          </section>
        )}
        <section>
          <h3 className="mb-2 text-sm font-semibold text-ink">Notes for this run</h3>
          <ul className="flex flex-col gap-1.5 text-xs text-muted">
            {q.notes.map((n, i) => (
              <li key={i} className={n.startsWith("SYNTHETIC") ? "font-medium text-hot" : undefined}>{n}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="min-w-0">
        <h3 className="mb-2 text-sm font-semibold text-ink">Documented events</h3>
        <p className="mb-2 text-xs text-faint">Only facts stated by NASA pages are listed. Where a source gives no date, the event is shown as undated.</p>
        <ol className="flex flex-col gap-2">
          {q.annotations.map((a) => (
            <li key={a.title} className="rounded-lg border border-line p-2.5">
              <p className="text-xs font-medium text-ink">
                <span className="num text-faint">{a.when}</span> · {a.title}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted">{a.detail}</p>
              <a href={a.source} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex min-h-6 items-center gap-1 text-xs text-viirs hover:underline">
                Source <ExternalLink aria-hidden className="size-3" />
              </a>
            </li>
          ))}
        </ol>
        {q.annotations.length === 0 && <p className="text-xs text-muted">No documented events fall in this period.</p>}
      </section>
    </div>
  );
}
