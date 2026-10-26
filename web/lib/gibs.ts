// NASA GIBS WMTS (no key). Layer ids, tile matrix sets, formats and time ranges below were read from
// the live GetCapabilities document (epsg3857/best), not assumed.
//   MODIS_Terra_CorrectedReflectance_TrueColor   jpeg  GoogleMapsCompatible_Level9  daily from 2000-02-24
//   VIIRS_SNPP_CorrectedReflectance_TrueColor    jpeg  GoogleMapsCompatible_Level9  daily from 2015-11-24
//   BlueMarble_ShadedRelief_Bathymetry           jpeg  GoogleMapsCompatible_Level8  no time dimension
// The *_Thermal_Anomalies layers are vector tiles (MVT), so they are not drawn here; hotspots come from
// our own FIRMS-derived data instead.

const BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";

export interface GibsLayer {
  id: string;
  matrixSet: string;
  maxZoom: number;
  ext: "jpg";
  /** First day with imagery (ISO), null when the layer has no time dimension. */
  first: string | null;
  label: string;
}

export const LAYERS = {
  modis: {
    id: "MODIS_Terra_CorrectedReflectance_TrueColor",
    matrixSet: "GoogleMapsCompatible_Level9",
    maxZoom: 9,
    ext: "jpg",
    first: "2000-02-24",
    label: "Terra MODIS true colour",
  },
  viirs: {
    id: "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    matrixSet: "GoogleMapsCompatible_Level9",
    maxZoom: 9,
    ext: "jpg",
    first: "2015-11-24",
    label: "Suomi NPP VIIRS true colour",
  },
  base: {
    id: "BlueMarble_ShadedRelief_Bathymetry",
    matrixSet: "GoogleMapsCompatible_Level8",
    maxZoom: 8,
    ext: "jpg",
    first: null,
    label: "Blue Marble",
  },
} as const satisfies Record<string, GibsLayer>;

/** MapLibre tile template. GIBS orders tiles {z}/{row}/{col}, which MapLibre calls {z}/{y}/{x}. */
export function tileUrl(layer: GibsLayer, day: string | null): string {
  const time = layer.first === null ? "default" : (day ?? "default");
  return `${BASE}/${layer.id}/default/${time}/${layer.matrixSet}/{z}/{y}/{x}.${layer.ext}`;
}

/**
 * The imagery layer to show on a sensor's side of the map for a day. VIIRS imagery only exists from
 * 2015-11-24, so earlier days fall back to Terra, and the caller is told so it can say so.
 */
export function imageryFor(sensor: "modis" | "viirs", day: string | null): { layer: GibsLayer; fallback: boolean } {
  const want = LAYERS[sensor];
  if (day && want.first && day < want.first) return { layer: LAYERS.modis, fallback: true };
  return { layer: want, fallback: false };
}
