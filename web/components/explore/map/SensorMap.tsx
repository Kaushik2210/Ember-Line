"use client";

import { ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { LAYERS, imageryFor, tileUrl } from "@/lib/gibs";
import type { HotspotBuffers } from "@/lib/hotspotBuffers";
import type { BBox, HotspotFeature } from "@/lib/types";

// the worker file is copied to /public by scripts/copy-maplibre-worker.mjs
if (typeof window !== "undefined") maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

type MlMap = maplibregl.Map;
type StyleSpecification = maplibregl.StyleSpecification;

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const ATTRIBUTION = "Imagery: NASA GIBS / ESDIS. Hotspots: NASA FIRMS";

function styleFor(sensor: "modis" | "viirs", day: string | null): StyleSpecification {
  const img = imageryFor(sensor, day).layer;
  return {
    version: 8,
    sources: {
      base: { type: "raster", tiles: [tileUrl(LAYERS.base, null)], tileSize: 256, maxzoom: LAYERS.base.maxZoom, attribution: ATTRIBUTION },
      imagery: { type: "raster", tiles: [tileUrl(img, day)], tileSize: 256, maxzoom: img.maxZoom },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#0b0f14" } },
      { id: "base", type: "raster", source: "base", paint: { "raster-opacity": 0.9 } },
      { id: "imagery", type: "raster", source: "imagery" },
    ],
  };
}

function bboxFeature(b: BBox | null) {
  const [w, s, e, n] = b ?? [0, 0, 0, 0];
  return {
    type: "FeatureCollection" as const,
    features: b ? [{ type: "Feature" as const, properties: {}, geometry: { type: "Polygon" as const, coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } }] : [],
  };
}

type Props = {
  sensor: "modis" | "viirs";
  day: string | null;
  buffers: HotspotBuffers | null;
  area: BBox | null;
  drawing: boolean;
  /** False freezes the map (no pan or zoom) and hides the controls, for decorative use. */
  interactive?: boolean;
  /** Padding in pixels around the area when framing it; lets a page keep one side of the map free. */
  framePadding?: maplibregl.PaddingOptions;
  /** False keeps the camera where it is when the area changes (a follower map is moved by its partner). */
  fit?: boolean;
  /** Drawn rectangle as [west, south, east, north]. */
  onDrawEnd?: (b: BBox) => void;
  onPick?: (f: HotspotFeature | null) => void;
  onReady?: (map: MlMap) => void;
  onRemove?: (map: MlMap) => void;
  onMove?: (map: MlMap) => void;
};

export function SensorMap({ sensor, day, buffers, area, drawing, interactive = true, framePadding, fit = true, onDrawEnd, onPick, onReady, onRemove, onMove }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const loaded = useRef(false);
  const cb = useRef({ onPick, onDrawEnd, onMove, onReady, onRemove });
  cb.current = { onPick, onDrawEnd, onMove, onReady, onRemove };

  // create once
  useEffect(() => {
    if (!el.current) return;
    const map = new maplibregl.Map({
      container: el.current,
      style: styleFor(sensor, day),
      center: [78, 25],
      zoom: 3,
      maxZoom: 12,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
      interactive,
    });
    if (interactive) {
      map.touchZoomRotate.disableRotation();
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    }
    const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
    map.addControl(overlay as unknown as maplibregl.IControl);
    mapRef.current = map;
    overlayRef.current = overlay;
    loaded.current = false;
    map.on("move", () => cb.current.onMove?.(map));
    map.on("load", () => {
      map.addSource("area", { type: "geojson", data: bboxFeature(null) });
      map.addLayer({ id: "area-line", type: "line", source: "area", paint: { "line-color": "#ffffff", "line-width": 1.5, "line-dasharray": [2, 2], "line-opacity": 0.85 } });
      map.addSource("draw", { type: "geojson", data: bboxFeature(null) });
      map.addLayer({ id: "draw-fill", type: "fill", source: "draw", paint: { "fill-color": "#b8a6ff", "fill-opacity": 0.2 } });
      map.addLayer({ id: "draw-line", type: "line", source: "draw", paint: { "line-color": "#b8a6ff", "line-width": 2 } });
      loaded.current = true;
      cb.current.onReady?.(map);
    });
    return () => {
      loaded.current = false;
      cb.current.onRemove?.(map);
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
    // the map is created once; later changes are applied by the effects below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // imagery follows the selected day
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("imagery") as maplibregl.RasterTileSource | undefined;
      const img = imageryFor(sensor, day).layer;
      src?.setTiles([tileUrl(img, day)]);
    };
    // isStyleLoaded() is false while tiles are loading, and "load" only fires once, so track it ourselves
    if (loaded.current) apply();
    else map.once("load", apply);
  }, [sensor, day]);

  // hotspots
  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;
    if (!buffers || buffers.length === 0) {
      overlay.setProps({ layers: [] });
      return;
    }
    overlay.setProps({
      layers: [
        new ScatterplotLayer({
          id: `hotspots-${sensor}`,
          data: {
            length: buffers.length,
            attributes: {
              getPosition: { value: buffers.positions, size: 2 },
              getRadius: { value: buffers.radii, size: 1 },
              getFillColor: { value: buffers.colors, size: 4 },
            },
          },
          radiusUnits: "meters",
          radiusMinPixels: buffers.aggregated ? 3 : 2.2,
          radiusMaxPixels: 60,
          stroked: false,
          pickable: true,
          autoHighlight: true,
          onClick: (info) => {
            const f = info.index >= 0 ? buffers.features[info.index] : null;
            cb.current.onPick?.(f ?? null);
          },
        }),
      ],
    });
  }, [buffers, sensor]);

  // frame the analysed area
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const go = () => {
      (map.getSource("area") as maplibregl.GeoJSONSource | undefined)?.setData(bboxFeature(area));
      if (area && fit) {
        map.fitBounds([[area[0], area[1]], [area[2], area[3]]], { padding: framePadding ?? 48, duration: prefersReducedMotion() ? 0 : 600 });
      }
    };
    if (loaded.current) go();
    else map.once("load", go);
  }, [area, framePadding, fit]);

  // drawing a box: drag on the map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !drawing) return;
    const canvas = map.getCanvasContainer();
    let start: maplibregl.LngLat | null = null;
    let last: maplibregl.LngLat | null = null;
    const draw = (a: maplibregl.LngLat, b: maplibregl.LngLat) => {
      const box: BBox = [Math.min(a.lng, b.lng), Math.min(a.lat, b.lat), Math.max(a.lng, b.lng), Math.max(a.lat, b.lat)];
      (map.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData(bboxFeature(box));
      return box;
    };
    const down = (e: maplibregl.MapMouseEvent | maplibregl.MapTouchEvent) => {
      e.preventDefault();
      start = last = e.lngLat;
    };
    const move = (e: maplibregl.MapMouseEvent | maplibregl.MapTouchEvent) => {
      if (!start) return;
      last = e.lngLat;
      draw(start, last);
    };
    // a touchend event carries no position, so the box ends where the finger last was
    const up = (e: maplibregl.MapMouseEvent | maplibregl.MapTouchEvent) => {
      if (!start) return;
      const box = draw(start, e.lngLat ?? last ?? start);
      start = last = null;
      (map.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData(bboxFeature(null));
      if (box[2] - box[0] > 0.05 && box[3] - box[1] > 0.05) cb.current.onDrawEnd?.(box);
    };
    map.dragPan.disable();
    canvas.style.cursor = "crosshair";
    map.on("mousedown", down);
    map.on("mousemove", move);
    map.on("mouseup", up);
    map.on("touchstart", down);
    map.on("touchmove", move);
    map.on("touchend", up);
    return () => {
      map.dragPan.enable();
      canvas.style.cursor = "";
      map.off("mousedown", down);
      map.off("mousemove", move);
      map.off("mouseup", up);
      map.off("touchstart", down);
      map.off("touchmove", move);
      map.off("touchend", up);
    };
  }, [drawing]);

  // MapLibre sets position: relative on its container, so the sizing wrapper is a separate element
  return (
    <div className="absolute inset-0">
      <div ref={el} className="h-full w-full" data-sensor={sensor} />
    </div>
  );
}
