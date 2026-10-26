"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useRef, useState } from "react";
import { ImageDown } from "lucide-react";
import { CREDIT, canvasToPng, saveFile } from "@/lib/download";
import { formatDay } from "@/lib/day";
import type { CompareHandle } from "./map/CompareMap";
import { getHotspots } from "@/lib/api";
import { resolveArea, resolvePeriod, useRegions, useResult } from "@/lib/analysis";
import { clampDay, defaultDay } from "@/lib/day";
import { countBySensor } from "@/lib/hotspotBuffers";
import { useExploreStore } from "@/lib/store";
import type { HotspotFeature } from "@/lib/types";
import { formatBox, useExploreParams } from "@/lib/urlState";
import { Segmented } from "@/components/ui/Segmented";
import { HotspotInspector } from "./map/HotspotInspector";
import { TimeScrubber } from "./map/TimeScrubber";

// MapLibre needs the browser, so the map is loaded on the client only
const CompareMap = dynamic(() => import("./map/CompareMap").then((m) => m.CompareMap), {
  ssr: false,
  loading: () => <div className="absolute inset-0 animate-pulse bg-raised" aria-label="Loading map" />,
});

export function MapPane() {
  const [p, setP] = useExploreParams();
  const regions = useRegions().data;
  const { geojson, drawing, setDrawing, setGeojson } = useExploreStore();
  const result = useResult();
  const [mode, setMode] = useState<"compare" | "overlay">("compare");
  const [picked, setPicked] = useState<HotspotFeature | null>(null);
  const mapHandle = useRef<CompareHandle>(null);

  const savePng = async () => {
    const canvas = await mapHandle.current?.exportCanvas(day ? formatDay(day) : "");
    if (canvas) saveFile(canvasToPng(canvas, "#0b0f14", CREDIT), `emberline-map-${day ?? "view"}.png`);
  };

  const area = resolveArea(p, regions, geojson);
  const { start, end } = resolvePeriod(p, area.region);
  const bbox = area.bbox ?? result.data?.bbox ?? null;
  const day = p.day ? clampDay(p.day, start, end) : defaultDay(result.data);

  const hotspots = useQuery({
    queryKey: ["hotspots", bbox, day, p.syn],
    queryFn: () => getHotspots(bbox as NonNullable<typeof bbox>, day as string, day as string, { synthetic: !!p.syn }),
    enabled: !!bbox && !!day,
    staleTime: 300_000,
    placeholderData: keepPreviousData,
    retry: 1,
  });

  const counts = countBySensor(hotspots.data);
  const setDay = (d: string) => {
    setPicked(null);
    void setP({ day: d });
  };

  return (
    <section aria-label="Map" className="relative grid min-h-0 grid-rows-[minmax(0,1fr)_auto]">
      <div className="relative min-h-0 overflow-hidden">
        <CompareMap
          handleRef={mapHandle}
          mode={drawing ? "overlay" : mode}
          day={day}
          hotspots={hotspots.data}
          showModis={p.sens.includes("modis")}
          showViirs={p.sens.includes("viirs")}
          area={bbox}
          drawing={drawing}
          onPick={setPicked}
          onDrawEnd={(b) => {
            setDrawing(false);
            setGeojson(null);
            void setP({ box: formatBox(b), job: null, day: null });
          }}
        />

        <div className="pointer-events-none absolute inset-x-3 top-3 z-10 flex justify-center">
          <div className="pointer-events-auto flex items-center gap-1.5">
            <div className="w-56">
            <Segmented
              label="Map mode"
              value={mode}
              options={[
                { value: "compare", label: "Compare" },
                { value: "overlay", label: "Overlay" },
              ]}
              onChange={setMode}
              className="bg-panel/90 backdrop-blur"
            />
            </div>
            <button
              type="button"
              onClick={() => void savePng()}
              aria-label="Save map as PNG"
              title="Save map as PNG"
              className="grid size-9 place-items-center rounded-lg border border-line bg-panel/90 text-muted backdrop-blur hover:text-ink pointer-coarse:size-11"
            >
              <ImageDown aria-hidden className="size-4" />
            </button>
          </div>
        </div>

        <div className="pointer-events-none absolute bottom-3 right-3 z-10 flex flex-col items-end gap-1.5" aria-live="polite">
          {drawing && (
            <p className="pointer-events-auto rounded-md bg-panel/95 px-2.5 py-1.5 text-xs text-ink shadow">Drag on the map to draw a box. <button className="underline" onClick={() => setDrawing(false)}>Cancel</button></p>
          )}
          {hotspots.isFetching && (
            <p className="flex items-center gap-1.5 rounded-md bg-panel/90 px-2.5 py-1.5 text-xs text-muted shadow">
              <Loader2 aria-hidden className="size-3.5 animate-spin" /> Loading detections
            </p>
          )}
          {hotspots.data && !hotspots.isFetching && (
            <p className="num rounded-md bg-panel/90 px-2.5 py-1.5 text-xs text-ink shadow">
              <span className="text-modis">MODIS {counts.modis.toLocaleString("en-GB")}</span>
              <span className="mx-1.5 text-faint">·</span>
              <span className="text-viirs">VIIRS {counts.viirs.toLocaleString("en-GB")}</span>
            </p>
          )}
          {hotspots.data?.properties.aggregated && (
            <p className="max-w-64 rounded-md bg-panel/90 px-2.5 py-1.5 text-right text-xs text-muted shadow">
              {hotspots.data.properties.total.toLocaleString("en-GB")} detections grouped into {hotspots.data.properties.cell_deg}° cells. Draw a smaller box to see individual points.
            </p>
          )}
        </div>

        {!bbox && (
          <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center">
            <p className="rounded-lg bg-panel/95 px-4 py-3 text-sm text-muted shadow">Choose a region to see detections.</p>
          </div>
        )}
        {bbox && !day && (
          <div className="pointer-events-none absolute inset-x-0 top-14 z-10 flex justify-center">
            <p className="rounded-lg bg-panel/95 px-4 py-2 text-xs text-muted shadow">Run the analysis to pick a day, or choose one with the scrubber below.</p>
          </div>
        )}
        {hotspots.isError && (
          <div role="alert" className="absolute inset-x-0 top-14 z-10 flex justify-center">
            <p className="rounded-lg border border-hot/40 bg-panel/95 px-4 py-2 text-xs text-ink shadow">
              Detections could not be loaded.{" "}
              <button className="underline" onClick={() => void hotspots.refetch()}>Retry</button>
            </p>
          </div>
        )}
        {hotspots.data && hotspots.data.features.length === 0 && !hotspots.isFetching && (
          <div className="pointer-events-none absolute inset-x-0 top-14 z-10 flex justify-center">
            <p className="rounded-lg bg-panel/95 px-4 py-2 text-xs text-muted shadow">No detections on this day in this area. Try another day.</p>
          </div>
        )}

        {picked && <HotspotInspector feature={picked} onClose={() => setPicked(null)} />}
      </div>

      <TimeScrubber start={start} end={end} day={day} onDay={setDay} disabled={!bbox} />
    </section>
  );
}
