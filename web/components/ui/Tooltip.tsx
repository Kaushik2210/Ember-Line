"use client";
import { useId, useState } from "react";

/** Shown on hover or focus; Escape dismisses it without moving focus. */
export function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const id = useId();
  const [dismissed, setDismissed] = useState(false);
  const reset = () => setDismissed(false);
  return (
    <span
      className="group relative inline-flex"
      aria-describedby={id}
      onKeyDown={(e) => e.key === "Escape" && setDismissed(true)}
      onMouseLeave={reset}
      onBlur={reset}
    >
      {children}
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md border border-line bg-raised px-2 py-1 text-xs text-ink ${
          dismissed ? "hidden" : "hidden group-focus-within:block group-hover:block"
        }`}
      >
        {text}
      </span>
    </span>
  );
}
