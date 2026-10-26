"use client";

import { cn } from "@/lib/cn";

type Option<T extends string> = { value: T; label: string; title?: string };

type Props<T extends string> = {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (v: T) => void;
  className?: string;
};

/** A row of mutually exclusive choices. Arrow keys move the selection, as in a native control. */
export function Segmented<T extends string>({ label, value, options, onChange, className }: Props<T>) {
  const move = (dir: 1 | -1) => {
    const i = options.findIndex((o) => o.value === value);
    onChange(options[(i + dir + options.length) % options.length].value);
  };
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("inline-flex w-full rounded-lg border border-line bg-raised p-0.5", className)}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          e.preventDefault();
          move(1);
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          e.preventDefault();
          move(-1);
        }
      }}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={on ? 0 : -1}
            title={o.title}
            onClick={() => onChange(o.value)}
            className={cn(
              "min-h-8 flex-1 rounded-md px-2 text-xs font-medium transition-colors duration-150 pointer-coarse:min-h-11",
              on ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
