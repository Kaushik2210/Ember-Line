export type Sensor = "modis" | "viirs" | "harmonized";

export const SENSORS: Record<Sensor, { label: string; detail: string; colorVar: string }> = {
  modis: { label: "MODIS", detail: "1 km, Terra + Aqua", colorVar: "var(--modis)" },
  viirs: { label: "VIIRS", detail: "375 m, SNPP + NOAA-20", colorVar: "var(--viirs)" },
  harmonized: { label: "Harmonized", detail: "VIIRS-equivalent units", colorVar: "var(--harmonized)" },
};
