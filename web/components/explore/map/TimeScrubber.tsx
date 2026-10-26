"use client";

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useEffect } from "react";
import { addDays, clampDay, daysBetween, formatDay } from "@/lib/day";
import { useExploreStore } from "@/lib/store";

type Props = {
  start: string;
  end: string;
  day: string | null;
  onDay: (d: string) => void;
  disabled?: boolean;
};

const PLAY_MS = 450;

export function TimeScrubber({ start, end, day, onDay, disabled }: Props) {
  const playing = useExploreStore((s) => s.playing);
  const setPlaying = useExploreStore((s) => s.setPlaying);
  const total = Math.max(1, daysBetween(start, end));
  const index = day ? daysBetween(start, clampDay(day, start, end)) : 0;
  const step = (n: number) => day && onDay(clampDay(addDays(day, n), start, end));

  // `[` and `]` step a day, as in the keyboard shortcuts of the brief
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "SELECT", "TEXTAREA"].includes(t.tagName)) return;
      if (e.key === "[") step(-1);
      else if (e.key === "]") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // playback advances one day at a time and stops at the end
  useEffect(() => {
    if (!playing || !day || disabled) return;
    if (day >= end) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => onDay(addDays(day, 1)), PLAY_MS);
    return () => clearTimeout(t);
  }, [playing, day, end, onDay, setPlaying, disabled]);

  return (
    <div className="flex items-center gap-2 border-t border-line bg-panel px-3 py-2">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setPlaying(!playing)}
        aria-label={playing ? "Pause playback" : "Play through days"}
        className="grid size-9 shrink-0 place-items-center rounded-lg border border-line bg-raised text-ink hover:border-[var(--border-strong)] disabled:opacity-50 pointer-coarse:size-11"
      >
        {playing ? <Pause aria-hidden className="size-4" /> : <Play aria-hidden className="size-4" />}
      </button>
      <button type="button" disabled={disabled} onClick={() => step(-1)} aria-label="Previous day" className="grid size-9 shrink-0 place-items-center rounded-lg text-muted hover:text-ink disabled:opacity-50 pointer-coarse:size-11">
        <ChevronLeft aria-hidden className="size-4" />
      </button>
      <input
        type="range"
        min={0}
        max={total}
        value={index}
        disabled={disabled}
        aria-label="Day"
        aria-valuetext={day ? formatDay(day) : "no day selected"}
        onChange={(e) => onDay(addDays(start, Number(e.target.value)))}
        className="h-6 min-w-0 flex-1 accent-[var(--harmonized)]"
      />
      <button type="button" disabled={disabled} onClick={() => step(1)} aria-label="Next day" className="grid size-9 shrink-0 place-items-center rounded-lg text-muted hover:text-ink disabled:opacity-50 pointer-coarse:size-11">
        <ChevronRight aria-hidden className="size-4" />
      </button>
      <time className="num w-28 shrink-0 text-right text-xs text-ink" dateTime={day ?? undefined}>
        {day ? formatDay(day) : "No day"}
      </time>
    </div>
  );
}
