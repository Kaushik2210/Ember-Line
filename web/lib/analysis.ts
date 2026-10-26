"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { ApiError, followJob, getRegions, getResult, postAnalyze } from "./api";
import { useExploreStore } from "./store";
import type { AnalyzeRequest, BBox, Region } from "./types";
import { type ExploreParams, parseBox, useExploreParams, viirsClasses } from "./urlState";

export function useRegions() {
  return useQuery({ queryKey: ["regions"], queryFn: getRegions, staleTime: Infinity });
}

export interface Area {
  bbox: BBox | null;
  name: string;
  region: Region | null;
  custom: boolean;
}

/** The area being analysed: an uploaded shape, a drawn box, or a preset, in that order. */
export function resolveArea(p: ExploreParams, regions: Region[] | undefined, geojson: unknown): Area {
  const region = regions?.find((r) => r.id === p.r) ?? null;
  if (geojson) return { bbox: null, name: "Uploaded shape", region: null, custom: true };
  const box = parseBox(p.box);
  if (box) return { bbox: box, name: "Custom box", region: null, custom: true };
  return { bbox: region?.bbox ?? null, name: region?.name ?? "Choose a region", region, custom: false };
}

export function resolvePeriod(p: ExploreParams, region: Region | null): { start: string; end: string } {
  return {
    start: p.s ?? region?.default_start ?? "2012-06-01",
    end: p.e ?? region?.default_end ?? "2024-12-31",
  };
}

export function buildRequest(p: ExploreParams, regions: Region[] | undefined, geojson: unknown): AnalyzeRequest {
  const area = resolveArea(p, regions, geojson);
  const { start, end } = resolvePeriod(p, area.region);
  const req: AnalyzeRequest = {
    start,
    end,
    metric: p.m,
    model: p.mod,
    quality_policy: { modis_min_conf: p.conf, viirs_classes: viirsClasses(p.vc), daynight: p.dn },
    grid: { kind: p.gk, size_deg: p.gs, h3_res: p.gr },
  };
  if (geojson) req.geojson = geojson;
  else if (area.custom && area.bbox) req.bbox = area.bbox;
  else req.region_id = p.r;
  if (p.syn) req.synthetic = true;
  return req;
}

/** Start an analysis, stream its stages into the store, and put the job id in the URL. */
export function useRun() {
  const [p, setP] = useExploreParams();
  const regions = useRegions().data;
  const geojson = useExploreStore((s) => s.geojson);
  const qc = useQueryClient();

  return useCallback(async () => {
    const st = useExploreStore.getState();
    st.setRunning();
    try {
      const job = await postAnalyze(buildRequest(p, regions, geojson));
      await setP({ job: job.job_id });
      if (job.status !== "done") {
        st.addStage("Queued");
        const last = await followJob(job.job_id, (e) => {
          if (e.stage !== "done" && e.stage !== "error") useExploreStore.getState().addStage(e.stage);
        }).done;
        if (last.stage === "error") throw new ApiError(last.error ?? "The analysis failed.", 422);
      }
      await qc.invalidateQueries({ queryKey: ["result", job.job_id] });
      useExploreStore.getState().setDone();
    } catch (e) {
      useExploreStore
        .getState()
        .setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    }
  }, [p, regions, geojson, setP, qc]);
}

export function useResult() {
  const [{ job }] = useExploreParams();
  const phase = useExploreStore((s) => s.phase);
  return useQuery({
    queryKey: ["result", job],
    queryFn: () => getResult(job as string),
    enabled: !!job && phase !== "running" && phase !== "error",
    staleTime: Infinity,
    retry: false,
  });
}
