"use client";

import { Check, Loader2, Play, RotateCcw } from "lucide-react";
import { resolveArea, useRegions, useResult, useRun } from "@/lib/analysis";
import { useExploreStore } from "@/lib/store";
import { useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";

/** The run button plus live stage names, and a clear error with retry. */
export function RunPanel() {
  const run = useRun();
  const [p] = useExploreParams();
  const regions = useRegions().data;
  const { phase, stages, error, geojson } = useExploreStore();
  const result = useResult();
  const area = resolveArea(p, regions, geojson);
  const running = phase === "running";
  const hasResult = !!result.data && phase !== "running";

  return (
    <div className="border-t border-line bg-panel p-4">
      <Button variant="primary" className="w-full" disabled={running || !area.bbox && !geojson} onClick={() => void run()}>
        {running ? <Loader2 aria-hidden className="size-4 animate-spin" /> : hasResult ? <RotateCcw aria-hidden className="size-4" /> : <Play aria-hidden className="size-4" />}
        {running ? "Analysing…" : hasResult ? "Run again" : "Run analysis"}
      </Button>

      <div aria-live="polite" className="mt-3">
        {running && (
          <ol className="flex flex-col gap-1.5" aria-label="Analysis progress">
            {stages.map((s, i) => {
              const last = i === stages.length - 1;
              return (
                <li key={`${s}-${i}`} className="flex items-center gap-2 text-xs">
                  {last ? <Loader2 aria-hidden className="size-3.5 shrink-0 animate-spin text-harmonized" /> : <Check aria-hidden className="size-3.5 shrink-0 text-faint" />}
                  <span className={last ? "text-ink" : "text-faint"}>{s}</span>
                </li>
              );
            })}
          </ol>
        )}
        {phase === "error" && error && (
          <div role="alert" className="rounded-lg border border-hot/40 bg-hot/10 p-3 text-xs text-ink">
            <p className="font-medium">The analysis did not finish</p>
            <p className="mt-1 text-muted">{error}</p>
            <Button size="sm" className="mt-2" onClick={() => void run()}>
              Try again
            </Button>
          </div>
        )}
        {result.isError && phase !== "running" && phase !== "error" && (
          <p role="alert" className="text-xs text-muted">
            This saved analysis could not be loaded. Run it again.
          </p>
        )}
        {phase === "idle" && !hasResult && !result.isLoading && (
          <p className="text-xs text-faint">Pick a region and period, then run. Nothing is computed until you do.</p>
        )}
      </div>
    </div>
  );
}
