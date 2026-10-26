"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useMemo } from "react";
import { getHotspots } from "@/lib/api";
import { toBuffers } from "@/lib/hotspotBuffers";
import type { ShowcaseEntry } from "@/lib/showcase";

const SensorMap = dynamic(() => import("@/components/explore/map/SensorMap").then((m) => m.SensorMap), { ssr: false });

/** Decorative map behind the hero: the real detections of a region's busiest day. Frozen, not clickable. */
export function HeroMap({ entry }: { entry: ShowcaseEntry | null }) {
  const day = entry?.findings?.busiest_day ?? null;
  const hotspots = useQuery({
    queryKey: ["hero-hotspots", entry?.id, day],
    queryFn: () => getHotspots(entry!.bbox, day as string, day as string),
    enabled: !!entry && !!day,
    staleTime: 600_000,
    placeholderData: keepPreviousData,
    retry: 1,
  });
  const buffers = useMemo(() => (hotspots.data ? toBuffers(hotspots.data) : null), [hotspots.data]);

  if (!entry || !day) return null;
  return (
    // the points fade out toward the text so the headline stays readable
    <div
      aria-hidden
      className="absolute inset-0"
      style={{
        maskImage: "linear-gradient(90deg, transparent 0%, transparent 30%, black 72%)",
        WebkitMaskImage: "linear-gradient(90deg, transparent 0%, transparent 30%, black 72%)",
      }}
    >
      <SensorMap sensor="viirs" day={day} buffers={buffers} area={entry.bbox} drawing={false} interactive={false} />
    </div>
  );
}
