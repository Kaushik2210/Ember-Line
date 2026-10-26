"use client";
import { useId } from "react";

export function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const id = useId();
  return (
    <span className="group relative inline-flex" aria-describedby={id}>
      {children}
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-line bg-raised px-2 py-1 text-xs text-ink group-focus-within:block group-hover:block"
      >
        {text}
      </span>
    </span>
  );
}
