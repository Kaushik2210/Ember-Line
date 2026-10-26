"use client";

import type { Map as MlMap } from "maplibre-gl";
import { useCallback, useImperativeHandle, useMemo, useRef } from "react";
import { imageryFor } from "@/lib/gibs";
import { toBuffers } from "@/lib/hotspotBuffers";
import { composeMapImage } from "@/lib/mapExport";
import { useExploreStore } from "@/lib/store";
import type { BBox, HotspotCollection, HotspotFeature } from "@/lib/types";
import { SensorMap } from "./SensorMap";

export interface CompareHandle {
  /** PNG data URL of the current view, hotspots and labels included. */
  exportCanvas: (dayLabel: string) => Promise<HTMLCanvasElement | null>;
}

type Props = {
  handleRef?: React.Ref<CompareHandle>;
  mode: "compare" | "overlay";
  day: string | null;
  hotspots: HotspotCollection | undefined;
  showModis: boolean;
  showViirs: boolean;
  area: BBox | null;
  drawing: boolean;
  onDrawEnd: (b: BBox) => void;
  onPick: (f: HotspotFeature | null) => void;
};

/**
 * Two synchronised maps, MODIS on the left and VIIRS on the right, divided by a draggable slider
 * (the top map is clipped, so each side of the divider shows one sensor). In overlay mode a single
 * map shows both sensors together.
 */
export function CompareMap({ handleRef, mode, day, hotspots, showModis, showViirs, area, drawing, onDrawEnd, onPick }: Props) {
  const slider = useExploreStore((s) => s.slider);
  const setSlider = useExploreStore((s) => s.setSlider);
  const box = useRef<HTMLDivElement>(null);
  const maps = useRef<Partial<Record<"a" | "b", MlMap>>>({});
  const syncing = useRef(false);

  const modisBuf = useMemo(() => (hotspots && showModis ? toBuffers(hotspots, "modis") : null), [hotspots, showModis]);
  const viirsBuf = useMemo(() => (hotspots && showViirs ? toBuffers(hotspots, "viirs") : null), [hotspots, showViirs]);
  const bothBuf = useMemo(() => {
    if (!hotspots) return null;
    const keep = hotspots.features.filter((f) => (f.properties.sensor === "modis" ? showModis : showViirs));
    return toBuffers({ ...hotspots, features: keep });
  }, [hotspots, showModis, showViirs]);

  const follow = useCallback((from: "a" | "b") => {
    return (m: MlMap) => {
      if (syncing.current) return;
      const other = maps.current[from === "a" ? "b" : "a"];
      if (!other) return;
      syncing.current = true;
      other.jumpTo({ center: m.getCenter(), zoom: m.getZoom() });
      syncing.current = false;
    };
  }, []);
  const followA = useMemo(() => follow("a"), [follow]);
  const followB = useMemo(() => follow("b"), [follow]);

  const dragTo = (clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (r) setSlider((clientX - r.left) / r.width);
  };

  useImperativeHandle(
    handleRef,
    () => ({
      exportCanvas: async (dayLabel: string) => {
        const right = maps.current.b;
        if (!right) return null;
        return composeMapImage({
          mode,
          left: maps.current.a ?? null,
          right,
          leftBuffers: modisBuf,
          rightBuffers: mode === "compare" ? viirsBuf : bothBuf,
          slider,
          dayLabel,
        });
      },
    }),
    [mode, modisBuf, viirsBuf, bothBuf, slider],
  );

  const viirsImagery = imageryFor("viirs", day);
  const compare = mode === "compare";

  return (
    <div ref={box} className="absolute inset-0 overflow-hidden bg-bg" role="region" aria-label="Map of fire detections">
      {compare && (
        <SensorMap
          sensor="modis"
          day={day}
          buffers={modisBuf}
          area={area}
          drawing={false}
          onPick={onPick}
          onReady={(m) => {
            maps.current.a = m;
          }}
          onMove={followA}
        />
      )}
      <div
        className="absolute inset-0"
        style={compare ? { clipPath: `inset(0 0 0 ${slider * 100}%)` } : undefined}
      >
        <SensorMap
          sensor="viirs"
          day={day}
          buffers={compare ? viirsBuf : bothBuf}
          area={area}
          drawing={drawing}
          onDrawEnd={onDrawEnd}
          onPick={onPick}
          onReady={(m) => {
            maps.current.b = m;
          }}
          onMove={followB}
        />
      </div>

      {compare && (
        <>
          <div aria-hidden className="pointer-events-none absolute left-3 top-[4.5rem] rounded-md sm:top-3 bg-black/55 px-2 py-1 text-xs font-medium text-modis backdrop-blur">
            MODIS
          </div>
          <div aria-hidden className="pointer-events-none absolute right-14 top-[4.5rem] rounded-md sm:top-3 bg-black/55 px-2 py-1 text-xs font-medium text-viirs backdrop-blur">
            VIIRS{viirsImagery.fallback ? " · Terra imagery" : ""}
          </div>
          <div
            role="slider"
            tabIndex={0}
            aria-label="Compare MODIS and VIIRS"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(slider * 100)}
            aria-valuetext={`${Math.round(slider * 100)}% MODIS, ${100 - Math.round(slider * 100)}% VIIRS`}
            className="group absolute inset-y-0 z-10 -ml-3 w-6 cursor-ew-resize touch-none outline-offset-[-2px]"
            style={{ left: `${slider * 100}%` }}
            onPointerDown={(e) => {
              e.currentTarget.setPointerCapture(e.pointerId);
              dragTo(e.clientX);
            }}
            onPointerMove={(e) => {
              if (e.currentTarget.hasPointerCapture(e.pointerId)) dragTo(e.clientX);
            }}
            onKeyDown={(e) => {
              const step = e.shiftKey ? 0.1 : 0.02;
              if (e.key === "ArrowLeft") setSlider(slider - step);
              else if (e.key === "ArrowRight") setSlider(slider + step);
              else if (e.key === "Home") setSlider(0);
              else if (e.key === "End") setSlider(1);
              else return;
              e.preventDefault();
            }}
          >
            <span aria-hidden className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-white/80" />
            <span
              aria-hidden
              className="absolute left-1/2 top-1/2 grid size-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-white/70 bg-black/60 text-[10px] text-white backdrop-blur group-focus-visible:ring-2 group-focus-visible:ring-[var(--focus)]"
            >
              ◂▸
            </span>
          </div>
        </>
      )}
    </div>
  );
}
