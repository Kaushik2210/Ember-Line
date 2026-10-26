"use client";

import { useResult } from "@/lib/analysis";
import { METRIC_NAME, modisSplit, overlapTotals, scanTrend } from "@/lib/why";
import type { ResultPayload } from "@/lib/types";
import { Drawer } from "@/components/ui/Drawer";

const pct = (v: number) => `${Math.round(v * 100)}%`;

function Item({ title, children, here }: { title: string; children: React.ReactNode; here?: string | null }) {
  return (
    <section className="border-b border-line p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-muted">{children}</p>
      {here && (
        <p className="mt-2 rounded-lg bg-raised p-2.5 text-xs leading-relaxed text-ink">
          <span className="font-medium text-harmonized">In this analysis: </span>
          {here}
        </p>
      )}
    </section>
  );
}

function reasons(r: ResultPayload | undefined) {
  const policy = r?.meta.quality_policy as { modis_min_conf?: number; viirs_classes?: string[] } | undefined;
  const o = r ? overlapTotals(r.daily) : null;
  const split = r ? modisSplit(r.quality.platforms) : null;
  const scan = r ? scanTrend(r.validation.tables.by_scan) : null;
  const ov = r?.validation.overpass;
  const metric = r ? (METRIC_NAME[r.meta.metric] ?? r.meta.metric) : "";
  const classes = (policy?.viirs_classes ?? []).map((c) => ({ l: "low", n: "nominal", h: "high" })[c] ?? c).join(" and ");
  return {
    size:
      o?.ratio != null && o.days > 0
        ? `Over the ${o.days.toLocaleString("en-GB")} days both sensors were observing, VIIRS recorded ${o.ratio.toFixed(1)} times the ${metric} that MODIS did.${ov && ov.viirs_unseen_by_modis != null ? ` Of the VIIRS detections MODIS could have seen, ${pct(ov.viirs_unseen_by_modis)} had no MODIS partner.` : ""}`
        : null,
    time: split
      ? `Aqua (afternoon) supplied ${pct(split.aqua)} of the MODIS detections here and Terra (morning) ${pct(split.terra)}.`
      : null,
    scan: scan
      ? `MODIS detections with the smallest pixels (${scan.small.label} km) were also seen by VIIRS ${pct(scan.small.rate)} of the time; for the larger pixels (${scan.large.label} km), ${pct(scan.large.rate)}.`
      : null,
    conf: policy?.modis_min_conf != null ? `MODIS confidence of at least ${policy.modis_min_conf} and VIIRS confidence ${classes || "set by the policy"} were kept.` : null,
    nonfire: r ? `${r.quality.counts.persistent_cells ?? 0} persistent heat-source cells were removed from this analysis.` : null,
  };
}

export function WhyDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const result = useResult().data;
  const here = reasons(result);
  return (
    <Drawer open={open} title="Why the sensors differ" onClose={onClose}>
      <div className="border-b border-line p-4 text-sm text-muted">
        MODIS (1 km, on Terra and Aqua) and VIIRS (375 m, on Suomi NPP) both detect fires from space, but they do not see the same things. EMBERLINE turns the two into one comparable record by correcting for the differences below.
        {!result && <span className="mt-2 block text-xs text-faint">Run an analysis to see these explained with this region&apos;s own numbers.</span>}
      </div>
      <Item title="VIIRS sees smaller fires" here={here.size}>
        VIIRS&apos;s 375 m pixels respond to small and low-intensity fires that fall below what MODIS&apos;s 1 km pixels can detect (NASA FIRMS and Earthdata). In regions with many small fires, such as agricultural burning, VIIRS has far more detections.
      </Item>
      <Item title="They pass at different times of day" here={here.time}>
        Terra crosses the equator in the morning and Aqua in the afternoon; Suomi NPP&apos;s VIIRS crosses at about 13:30 local time (NASA). Fires have a daily cycle, so each satellite samples a different part of it. A fire that burns mostly in the evening can be missed by all of them.
      </Item>
      <Item title="Pixels grow toward the edge of the scan" here={here.scan}>
        MODIS pixels get larger away from the centre of the swath (FIRMS reports the actual pixel size as scan and track). Larger pixels dilute a small fire, so the same fire is easier to detect near nadir. VIIRS pixels grow off-nadir too.
      </Item>
      <Item title="Confidence is scored differently" here={here.conf}>
        MODIS gives a number from 0 to 100, which NASA also sorts into low, nominal and high classes. VIIRS gives only the classes. The quality policy maps both onto one rule, which you can change under Quality policy.
      </Item>
      <Item title="Different measurements, one shared quantity">
        MODIS reports brightness temperatures in channels 21 and 31; VIIRS in its I4 and I5 channels. Both report fire radiative power (FRP, in megawatts), which is the most physically comparable quantity, so it is the default measure here. Raw detection counts are shown only to demonstrate the mismatch.
      </Item>
      <Item title="Not everything hot is a fire" here={here.nonfire}>
        FIRMS marks each detection as presumed vegetation fire, active volcano, other static land source (such as gas flares and industry) or offshore. EMBERLINE keeps vegetation fire and also masks places that burn on a large share of days across a long record.
      </Item>
      <Item title="Before Aqua there was only Terra">
        Until Aqua&apos;s fire record began in July 2002, MODIS fire data come from one satellite with fewer overpasses. Those years are calibrated with their own model so they are not mistaken for quiet years.
      </Item>
    </Drawer>
  );
}
