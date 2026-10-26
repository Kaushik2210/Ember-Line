"use client";

import { Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { exportUrl, type ExportFormat } from "@/lib/api";
import { useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";

const ITEMS: { format: ExportFormat; label: string; hint: string }[] = [
  { format: "csv", label: "Daily series (CSV)", hint: "Harmonized values, bands, and raw MODIS and VIIRS" },
  { format: "geojson", label: "Summary (GeoJSON)", hint: "Region with seasons, unusual periods and acknowledgment" },
  { format: "methods", label: "Methods card (JSON)", hint: "Exact parameters and versions, to reproduce the run" },
];

/** Downloads of the finished analysis. Charts and the calendar have their own PNG buttons. */
export function ExportMenu({ ready }: { ready: boolean }) {
  const [{ job }] = useExploreParams();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={box} className="relative">
      <Button variant="ghost" size="sm" aria-label="Export" disabled={!ready || !job} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <Download aria-hidden className="size-4" />
        <span className="hidden sm:inline">Export</span>
      </Button>
      {open && job && (
        <ul role="menu" aria-label="Export" className="absolute right-0 top-full z-50 mt-1 w-72 rounded-xl border border-line bg-panel p-1 shadow-2xl">
          {ITEMS.map((it) => (
            <li key={it.format} role="none">
              <a
                role="menuitem"
                href={exportUrl(job, it.format)}
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2 hover:bg-raised pointer-coarse:py-3"
              >
                <span className="block text-sm text-ink">{it.label}</span>
                <span className="block text-xs text-faint">{it.hint}</span>
              </a>
            </li>
          ))}
          <li role="none" className="px-3 py-2 text-xs text-faint">Charts, the calendar and the map have their own PNG buttons.</li>
        </ul>
      )}
    </div>
  );
}
