"use client";

import type { EChartsOption } from "echarts";
import ReactEChartsCore from "echarts-for-react/lib/core";
import echarts from "@/lib/echarts";

type Props = {
  option: EChartsOption;
  height?: number;
  /** Plain-language description for screen readers. */
  label: string;
  onClick?: (params: unknown) => void;
};

/** A themed ECharts canvas. Respects reduced motion by turning animation off. */
export function Chart({ option, height = 240, label, onClick }: Props) {
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return (
    <div role="img" aria-label={label}>
      <ReactEChartsCore
        echarts={echarts}
        option={reduce ? { ...option, animation: false } : option}
        style={{ height, width: "100%" }}
        notMerge
        lazyUpdate
        opts={{ renderer: "canvas" }}
        onEvents={onClick ? { click: onClick } : undefined}
      />
    </div>
  );
}
