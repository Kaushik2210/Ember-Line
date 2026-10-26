"use client";

import { useEffect, useState } from "react";

export interface ChartColors {
  ink: string;
  muted: string;
  faint: string;
  line: string;
  panel: string;
  raised: string;
  modis: string;
  viirs: string;
  harmonized: string;
  hot: string;
  cool: string;
}

// Dark defaults, used until the real CSS values are read in the browser.
const FALLBACK: ChartColors = {
  ink: "#e8edf3",
  muted: "#9aa7b5",
  faint: "#6b7886",
  line: "rgba(255,255,255,0.08)",
  panel: "#11171e",
  raised: "#1a222c",
  modis: "#e69f00",
  viirs: "#56b4e9",
  harmonized: "#b8a6ff",
  hot: "#ff5a4d",
  cool: "#5b8bb8",
};

const VARS: Record<keyof ChartColors, string> = {
  ink: "--text",
  muted: "--text-muted",
  faint: "--text-faint",
  line: "--border",
  panel: "--panel",
  raised: "--raised",
  modis: "--modis",
  viirs: "--viirs",
  harmonized: "--harmonized",
  hot: "--anomaly-high",
  cool: "--anomaly-low",
};

function read(): ChartColors {
  const cs = getComputedStyle(document.documentElement);
  const out = { ...FALLBACK };
  (Object.keys(VARS) as (keyof ChartColors)[]).forEach((k) => {
    const v = cs.getPropertyValue(VARS[k]).trim();
    if (v) out[k] = v;
  });
  return out;
}

/** Chart colours taken from the design tokens, refreshed when the theme changes. */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(FALLBACK);
  useEffect(() => {
    setColors(read());
    const obs = new MutationObserver(() => setColors(read()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onMq = () => setColors(read());
    mq.addEventListener("change", onMq);
    return () => {
      obs.disconnect();
      mq.removeEventListener("change", onMq);
    };
  }, []);
  return colors;
}

/** Axis, grid and text defaults shared by every chart. */
export function baseOption(c: ChartColors) {
  return {
    backgroundColor: "transparent",
    textStyle: { color: c.muted, fontFamily: "var(--font-inter), system-ui, sans-serif", fontSize: 11 },
    animationDuration: 200,
    animationEasing: "cubicOut" as const,
    aria: { enabled: true },
    tooltip: {
      backgroundColor: c.raised,
      borderColor: c.line,
      borderWidth: 1,
      textStyle: { color: c.ink, fontSize: 12 },
      extraCssText: "border-radius:8px;",
    },
  };
}

export const axisStyle = (c: ChartColors) => ({
  axisLine: { lineStyle: { color: c.line } },
  axisTick: { lineStyle: { color: c.line } },
  axisLabel: { color: c.faint, fontSize: 10 },
  splitLine: { lineStyle: { color: c.line } },
  nameTextStyle: { color: c.faint, fontSize: 10 },
});
