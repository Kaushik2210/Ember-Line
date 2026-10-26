import type {
  AnalyzeRequest,
  AvailabilityInfo,
  BBox,
  HotspotCollection,
  JobEvent,
  JobStatus,
  Region,
  ResultPayload,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** An error whose message is safe to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the EMBERLINE server. Check that it is running and try again.", 0);
  }
  if (!res.ok) {
    let detail = `The server answered ${res.status}.`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((d: { msg?: string }) => d.msg)
          .filter(Boolean)
          .join(" ");
      }
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const getRegions = () => request<Region[]>("/api/regions");
export const getAvailability = () => request<AvailabilityInfo>("/api/availability");

export const postAnalyze = (body: AnalyzeRequest) =>
  request<JobStatus>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getJob = (id: string) => request<JobStatus>(`/api/jobs/${id}`);
export const getResult = (id: string) => request<ResultPayload>(`/api/jobs/${id}/result`);

export function getHotspots(
  bbox: BBox,
  start: string,
  end: string,
  opts: { sensors?: string[]; synthetic?: boolean; maxFeatures?: number } = {},
): Promise<HotspotCollection> {
  const p = new URLSearchParams({
    bbox: bbox.join(","),
    start,
    end,
    sensors: (opts.sensors ?? ["modis", "viirs"]).join(","),
    synthetic: String(opts.synthetic ?? false),
    max_features: String(opts.maxFeatures ?? 50000),
  });
  return request<HotspotCollection>(`/api/hotspots?${p}`);
}

export type ExportFormat = "csv" | "geojson" | "methods";
export const exportUrl = (jobId: string, format: ExportFormat) =>
  `${API_URL}/api/export?job_id=${encodeURIComponent(jobId)}&format=${format}`;

/**
 * Follow a job's progress over server-sent events. Calls onEvent for every stage and resolves
 * with the final status ("done" or "error"). The returned function stops listening.
 */
export function followJob(
  jobId: string,
  onEvent: (e: JobEvent) => void,
): { done: Promise<JobEvent>; close: () => void } {
  const es = new EventSource(`${API_URL}/api/jobs/${jobId}/events`);
  const done = new Promise<JobEvent>((resolve, reject) => {
    const handle = (ev: MessageEvent<string>) => {
      const e = JSON.parse(ev.data) as JobEvent;
      onEvent(e);
      if (e.stage === "done" || e.stage === "error") {
        es.close();
        resolve(e);
      }
    };
    es.addEventListener("progress", handle as EventListener);
    es.addEventListener("done", handle as EventListener);
    es.addEventListener("error", ((ev: MessageEvent<string>) => {
      if (typeof ev.data === "string" && ev.data) handle(ev);
    }) as EventListener);
    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        reject(new ApiError("The progress stream was interrupted.", 0));
      }
    };
  });
  return { done, close: () => es.close() };
}
