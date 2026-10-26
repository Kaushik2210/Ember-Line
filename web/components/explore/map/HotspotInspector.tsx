"use client";

import { X } from "lucide-react";
import type { HotspotFeature } from "@/lib/types";
import { SensorBadge } from "@/components/ui/SensorBadge";

const PLATFORM: Record<string, string> = { Terra: "Terra", Aqua: "Aqua", SNPP: "Suomi NPP" };

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-6 text-xs">
      <dt className="text-muted">{k}</dt>
      <dd className="num text-ink">{v}</dd>
    </div>
  );
}

/** Details of the clicked detection, or of the clicked cell when the server has grouped them. */
export function HotspotInspector({ feature, onClose }: { feature: HotspotFeature; onClose: () => void }) {
  const p = feature.properties;
  const [lon, lat] = feature.geometry.coordinates;
  const cell = p.count !== undefined;
  return (
    <div role="dialog" aria-label="Detection details" className="absolute bottom-3 left-3 z-20 w-60 rounded-xl border border-line bg-panel/95 p-3 shadow-xl backdrop-blur">
      <div className="mb-2 flex items-center justify-between">
        <SensorBadge sensor={p.sensor} />
        <button type="button" onClick={onClose} aria-label="Close details" className="grid size-7 place-items-center rounded-md text-muted hover:text-ink pointer-coarse:size-11">
          <X aria-hidden className="size-4" />
        </button>
      </div>
      <dl className="flex flex-col gap-1">
        {cell ? (
          <>
            <Row k="Detections in cell" v={String(p.count)} />
            <Row k="Summed FRP" v={`${p.frp_sum?.toLocaleString("en-GB")} MW`} />
            <Row k="Cell size" v={`${p.cell_deg}°`} />
          </>
        ) : (
          <>
            {p.platform && <Row k="Satellite" v={PLATFORM[p.platform] ?? p.platform} />}
            <Row k="FRP" v={p.frp == null ? "n/a" : `${p.frp} MW`} />
            {p.time && <Row k="Time (UTC)" v={p.time.replace("T", " ").replace("Z", "")} />}
            {p.daynight && <Row k="Pass" v={p.daynight === "D" ? "Day" : "Night"} />}
            {p.confidence != null && <Row k="Confidence" v={String(p.confidence)} />}
          </>
        )}
        <Row k="Position" v={`${lat.toFixed(3)}, ${lon.toFixed(3)}`} />
      </dl>
    </div>
  );
}
