"use client";

import { Info, Menu, Share2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { resolveArea, useRegions, useResult } from "@/lib/analysis";
import { useExploreStore } from "@/lib/store";
import { useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { AnalyticsDock } from "./AnalyticsDock";
import { ExportMenu } from "./ExportMenu";
import { LeftRail } from "./LeftRail";
import { MapPane } from "./MapPane";
import { ThemeToggle } from "./ThemeToggle";
import { WhyDrawer } from "./WhyDrawer";

function isTyping(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
}

export function Workspace() {
  const searchRef = useRef<HTMLInputElement>(null);
  const [p] = useExploreParams();
  const regions = useRegions().data;
  const { geojson, whyOpen, setWhyOpen, setPlaying } = useExploreStore();
  const result = useResult();
  const [controlsOpen, setControlsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const area = resolveArea(p, regions, geojson);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      if (e.key === "/") {
        e.preventDefault();
        setControlsOpen(true);
        setTimeout(() => searchRef.current?.focus(), 0);
      } else if (e.key === " " && !(e.target as HTMLElement).closest("button, a, [role=radio]")) {
        e.preventDefault();
        setPlaying(!useExploreStore.getState().playing);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPlaying]);

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this link", window.location.href);
    }
  };

  return (
    <div className="flex h-dvh flex-col bg-bg text-ink">
      {result.data?.synthetic && (
        <div role="status" className="bg-hot px-4 py-1 text-center text-xs font-semibold text-white">
          SYNTHETIC DATA: generated for development, not real observations
        </div>
      )}
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)]">
        <header className="flex min-h-12 items-center gap-2 border-b border-line bg-panel px-3 sm:px-4">
          <Button variant="ghost" size="sm" className="lg:hidden" aria-label="Open controls" onClick={() => setControlsOpen(true)}>
            <Menu aria-hidden className="size-4" />
          </Button>
          <Link href="/" className="text-sm font-semibold tracking-wide text-ink">
            EMBERLINE
          </Link>
          <span aria-hidden className="text-faint">/</span>
          <h1 className="min-w-0 flex-1 truncate text-sm text-muted sm:flex-none">{area.name}</h1>
          <div className="ml-auto flex shrink-0 items-center gap-1">
            <Button variant="ghost" size="sm" aria-label="Why they differ" onClick={() => setWhyOpen(true)}>
              <Info aria-hidden className="size-4" />
              <span className="hidden sm:inline">Why they differ</span>
            </Button>
            <ExportMenu ready={!!result.data} />
            <Button variant="ghost" size="sm" aria-label={copied ? "Link copied" : "Share"} onClick={() => void share()} aria-live="polite">
              <Share2 aria-hidden className="size-4" />
              <span className="hidden sm:inline">{copied ? "Link copied" : "Share"}</span>
            </Button>
            <ThemeToggle />
          </div>
        </header>

        <div className="grid min-h-0 grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="hidden min-h-0 border-r border-line lg:block">
            <LeftRail searchRef={searchRef} />
          </div>
          <main className="grid min-h-0 grid-cols-[minmax(0,1fr)] grid-rows-[minmax(220px,1fr)_auto]">
            <MapPane />
            <AnalyticsDock />
          </main>
        </div>
      </div>

      <div className="lg:hidden">
        <Drawer open={controlsOpen} title="Controls" side="left" onClose={() => setControlsOpen(false)}>
          <LeftRail searchRef={searchRef} />
        </Drawer>
      </div>
      <WhyDrawer open={whyOpen} onClose={() => setWhyOpen(false)} />
    </div>
  );
}
