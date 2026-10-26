import type { Map as MlMap } from "maplibre-gl";
import type { HotspotBuffers } from "./hotspotBuffers";

/** Metres per CSS pixel at a latitude and MapLibre zoom (512 px tiles). */
export function metersPerPixel(lat: number, zoom: number): number {
  return (40_075_016.686 * Math.cos((lat * Math.PI) / 180)) / (512 * 2 ** zoom);
}

/** Copy a map's WebGL canvas. Must happen inside a render event, while the frame is still valid. */
export function snapshot(map: MlMap): Promise<HTMLCanvasElement> {
  return new Promise((resolve) => {
    map.once("render", () => {
      const src = map.getCanvas();
      const c = document.createElement("canvas");
      c.width = src.width;
      c.height = src.height;
      c.getContext("2d")?.drawImage(src, 0, 0);
      resolve(c);
    });
    map.triggerRepaint();
  });
}

/** Draw hotspots on a 2D canvas through the map's own projection, matching what the map shows. */
export function drawHotspots(ctx: CanvasRenderingContext2D, map: MlMap, b: HotspotBuffers | null, scale: number): void {
  if (!b) return;
  const mpp = metersPerPixel(map.getCenter().lat, map.getZoom());
  const minR = (b.aggregated ? 3 : 2.2) * scale;
  const w = map.getCanvas().width;
  const h = map.getCanvas().height;
  for (let i = 0; i < b.length; i++) {
    const p = map.project([b.positions[2 * i], b.positions[2 * i + 1]]);
    const x = p.x * scale;
    const y = p.y * scale;
    if (x < -50 || y < -50 || x > w + 50 || y > h + 50) continue;
    const r = Math.min(60 * scale, Math.max(minR, (b.radii[i] / mpp) * scale));
    ctx.fillStyle = `rgba(${b.colors[4 * i]},${b.colors[4 * i + 1]},${b.colors[4 * i + 2]},${b.colors[4 * i + 3] / 255})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
}

export interface ExportInput {
  mode: "compare" | "overlay";
  left: MlMap | null;
  right: MlMap;
  leftBuffers: HotspotBuffers | null;
  rightBuffers: HotspotBuffers | null;
  /** Divider position, 0..1 from the left. */
  slider: number;
  dayLabel: string;
}

/** A single image of what is on screen: imagery, hotspots, divider and labels. */
export async function composeMapImage(inp: ExportInput): Promise<HTMLCanvasElement> {
  const rightCanvas = await snapshot(inp.right);
  const scale = rightCanvas.width / inp.right.getContainer().clientWidth;
  const out = document.createElement("canvas");
  out.width = rightCanvas.width;
  out.height = rightCanvas.height;
  const ctx = out.getContext("2d");
  if (!ctx) return out;
  const W = out.width;
  const H = out.height;
  const compare = inp.mode === "compare" && inp.left;
  if (compare && inp.left) {
    const leftCanvas = await snapshot(inp.left);
    ctx.drawImage(leftCanvas, 0, 0);
    drawHotspots(ctx, inp.left, inp.leftBuffers, scale);
    ctx.save();
    ctx.beginPath();
    ctx.rect(inp.slider * W, 0, W, H);
    ctx.clip();
    ctx.drawImage(rightCanvas, 0, 0);
    drawHotspots(ctx, inp.right, inp.rightBuffers, scale);
    ctx.restore();
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.fillRect(inp.slider * W - 1, 0, 2, H);
  } else {
    ctx.drawImage(rightCanvas, 0, 0);
    drawHotspots(ctx, inp.right, inp.rightBuffers, scale);
  }
  const tag = (text: string, x: number, color: string, align: CanvasTextAlign) => {
    ctx.font = `${12 * scale}px sans-serif`;
    const w = ctx.measureText(text).width + 16 * scale;
    const left = align === "left" ? x : x - w;
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(left, 10 * scale, w, 22 * scale);
    ctx.fillStyle = color;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(text, left + 8 * scale, 21 * scale);
  };
  if (compare) {
    tag("MODIS", 10 * scale, "#e69f00", "left");
    tag("VIIRS", W - 10 * scale, "#56b4e9", "right");
  }
  tag(inp.dayLabel, W / 2 + (compare ? 0 : 0) + 40 * scale, "#ffffff", "right");
  return out;
}
