import type { HotspotCollection, HotspotFeature } from "./types";

// Colours per sensor, matching the design tokens (Okabe-Ito safe): MODIS amber, VIIRS sky blue.
export const SENSOR_RGB = { modis: [230, 159, 0], viirs: [86, 180, 233] } as const;

export interface HotspotBuffers {
  length: number;
  positions: Float32Array; // lon, lat pairs
  radii: Float32Array; // metres
  colors: Uint8ClampedArray; // r, g, b, a
  /** Source features by index, for picking. */
  features: HotspotFeature[];
  aggregated: boolean;
}

// Half a nominal pixel at nadir. Real pixels grow off-nadir, so these are lower bounds.
const PIXEL_RADIUS_M = { modis: 500, viirs: 187.5 } as const;

/**
 * Pack hotspots into typed arrays for deck.gl (binary attributes), so tens of thousands of points
 * are drawn without one object per point. When the server aggregated into cells, each point is a
 * cell: sized to the cell and shaded by how much it holds.
 */
export function toBuffers(fc: HotspotCollection, sensor?: "modis" | "viirs"): HotspotBuffers {
  const features = sensor ? fc.features.filter((f) => f.properties.sensor === sensor) : fc.features;
  const n = features.length;
  const positions = new Float32Array(n * 2);
  const radii = new Float32Array(n);
  const colors = new Uint8ClampedArray(n * 4);
  const aggregated = fc.properties.aggregated;
  const maxCount = aggregated ? Math.max(1, ...features.map((f) => f.properties.count ?? 1)) : 1;

  features.forEach((f, i) => {
    const [lon, lat] = f.geometry.coordinates;
    positions[2 * i] = lon;
    positions[2 * i + 1] = lat;
    const rgb = SENSOR_RGB[f.properties.sensor];
    colors[4 * i] = rgb[0];
    colors[4 * i + 1] = rgb[1];
    colors[4 * i + 2] = rgb[2];
    if (aggregated) {
      radii[i] = ((f.properties.cell_deg ?? 0.1) * 111_000) / 2;
      // denser cells are more opaque; sqrt keeps sparse cells visible
      colors[4 * i + 3] = 70 + 150 * Math.sqrt((f.properties.count ?? 1) / maxCount);
    } else {
      radii[i] = PIXEL_RADIUS_M[f.properties.sensor];
      colors[4 * i + 3] = 215;
    }
  });
  return { length: n, positions, radii, colors, features, aggregated };
}

export function countBySensor(fc: HotspotCollection | undefined): { modis: number; viirs: number } {
  const out = { modis: 0, viirs: 0 };
  if (!fc) return out;
  for (const f of fc.features) out[f.properties.sensor] += f.properties.count ?? 1;
  return out;
}
