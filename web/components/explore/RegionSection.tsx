"use client";

import { Search, Square, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { resolveArea, useRegions } from "@/lib/analysis";
import { useExploreStore } from "@/lib/store";
import { formatBox, parseBox, useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";
import { Section } from "@/components/ui/Section";

const MAX_UPLOAD_BYTES = 2_000_000;

export function RegionSection({ searchRef }: { searchRef: React.RefObject<HTMLInputElement | null> }) {
  const [p, setP] = useExploreParams();
  const regions = useRegions();
  const { geojson, geojsonName, setGeojson, drawing, setDrawing } = useExploreStore();
  const [query, setQuery] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const area = resolveArea(p, regions.data, geojson);
  const list = (regions.data ?? []).filter((r) => r.name.toLowerCase().includes(query.trim().toLowerCase()));

  const pick = (id: string) => {
    setGeojson(null);
    void setP({ r: id, box: null, s: null, e: null, job: null, day: null });
  };

  const onFile = async (file: File | undefined) => {
    setUploadError(null);
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError("That file is over 2 MB. Simplify the shape and try again.");
      return;
    }
    try {
      const obj = JSON.parse(await file.text()) as { type?: string };
      if (!obj || typeof obj.type !== "string") throw new Error("not GeoJSON");
      setGeojson(obj, file.name);
      void setP({ box: null, job: null, day: null });
    } catch {
      setUploadError("That file is not valid GeoJSON. Upload a Polygon or MultiPolygon.");
    }
  };

  const box = parseBox(p.box);

  return (
    <Section title="Region" summary={area.name} defaultOpen>
      <div className="relative">
        <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-faint" />
        <input
          ref={searchRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search regions   /"
          aria-label="Search regions"
          className="h-9 w-full rounded-lg border border-line bg-raised pl-9 pr-3 text-sm text-ink pointer-coarse:h-11"
        />
      </div>

      <ul className="flex flex-col gap-1.5" aria-label="Preset regions">
        {regions.isLoading && <li className="h-14 animate-pulse rounded-lg bg-raised" aria-label="Loading regions" />}
        {regions.isError && (
          <li className="rounded-lg border border-line p-3 text-xs text-muted">
            Regions could not be loaded.{" "}
            <button className="text-ink underline" onClick={() => void regions.refetch()}>
              Retry
            </button>
          </li>
        )}
        {list.map((r) => {
          const on = !area.custom && p.r === r.id;
          return (
            <li key={r.id}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => pick(r.id)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-left transition-colors duration-150 pointer-coarse:min-h-11",
                  on ? "border-harmonized bg-raised" : "border-line hover:border-[var(--border-strong)]",
                )}
              >
                <span className="block text-sm font-medium text-ink">{r.name}</span>
                {on && <span className="mt-1 block text-xs text-muted">{r.blurb}</span>}
              </button>
            </li>
          );
        })}
        {regions.data && list.length === 0 && <li className="px-1 text-xs text-muted">No region matches “{query}”.</li>}
      </ul>

      <div className="flex gap-2">
        <Button size="sm" variant={drawing ? "primary" : "secondary"} onClick={() => setDrawing(!drawing)} className="flex-1">
          <Square aria-hidden className="size-3.5" />
          {drawing ? "Drawing: drag on map" : "Draw box"}
        </Button>
        <Button size="sm" onClick={() => fileRef.current?.click()} className="flex-1">
          <Upload aria-hidden className="size-3.5" />
          Upload GeoJSON
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept=".geojson,.json,application/geo+json,application/json"
          className="sr-only"
          aria-label="Upload a GeoJSON shape"
          onChange={(e) => {
            void onFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
      {uploadError && (
        <p role="alert" className="text-xs text-hot">
          {uploadError}
        </p>
      )}

      {(box !== null || geojson !== null) && (
        <div className="flex items-start justify-between gap-2 rounded-lg border border-line bg-raised p-3">
          <div className="min-w-0 text-xs">
            <p className="font-medium text-ink">{geojson ? (geojsonName ?? "Uploaded shape") : "Custom box"}</p>
            <p className="num mt-0.5 break-all text-muted">{geojson ? "Not part of the share link" : formatBox(box as NonNullable<typeof box>)}</p>
          </div>
          <button
            type="button"
            aria-label="Clear custom area"
            onClick={() => {
              setGeojson(null);
              void setP({ box: null, job: null });
            }}
            className="rounded-md p-1 text-muted hover:text-ink pointer-coarse:size-11"
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>
      )}
    </Section>
  );
}
