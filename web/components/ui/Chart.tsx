"use client";

import type { EChartsOption } from "echarts";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { ImageDown } from "lucide-react";
import { useRef } from "react";
import { useChartColors } from "@/lib/chartTheme";
import { saveFile } from "@/lib/download";
import echarts from "@/lib/echarts";

type Props = {
  option: EChartsOption;
  height?: number;
  /** Plain-language description for screen readers. */
  label: string;
  /** When set, a button saves the chart as a PNG with this file name. */
  filename?: string;
  onClick?: (params: unknown) => void;
};

/** A themed ECharts canvas. Respects reduced motion by turning animation off. */
export function Chart({ option, height = 240, label, filename, onClick }: Props) {
  const ref = useRef<ReactEChartsCore>(null);
  const c = useChartColors();
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const save = () => {
    const inst = ref.current?.getEchartsInstance();
    if (!inst || !filename) return;
    saveFile(inst.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: c.panel }), `${filename}.png`);
  };

  return (
    <div role="img" aria-label={label} className="group relative">
      <ReactEChartsCore
        ref={ref}
        echarts={echarts}
        option={reduce ? { ...option, animation: false } : option}
        style={{ height, width: "100%" }}
        notMerge
        lazyUpdate
        opts={{ renderer: "canvas" }}
        onEvents={onClick ? { click: onClick } : undefined}
      />
      {filename && (
        <button
          type="button"
          onClick={save}
          aria-label="Save chart as PNG"
          title="Save as PNG"
          className="absolute right-1 top-0 grid size-7 place-items-center rounded-md bg-panel/80 text-faint opacity-0 transition-opacity duration-150 hover:text-ink focus-visible:opacity-100 group-hover:opacity-100 pointer-coarse:size-11 pointer-coarse:opacity-100"
        >
          <ImageDown aria-hidden className="size-4" />
        </button>
      )}
    </div>
  );
}
