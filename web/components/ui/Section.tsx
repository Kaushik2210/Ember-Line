"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import { cn } from "@/lib/cn";

type Props = {
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

/** Collapsible group of controls: essentials stay open, detail is one click away. */
export function Section({ title, summary, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <section className="border-b border-line">
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((o) => !o)}
          className="flex min-h-11 w-full items-center justify-between gap-2 px-4 text-left"
        >
          <span className="text-sm font-semibold text-ink">{title}</span>
          <span className="flex min-w-0 items-center gap-2">
            {!open && summary && <span className="num truncate text-xs text-faint">{summary}</span>}
            <ChevronDown
              aria-hidden
              className={cn("size-4 shrink-0 text-faint transition-transform duration-150", open && "rotate-180")}
            />
          </span>
        </button>
      </h3>
      {open && (
        <div id={id} className="flex flex-col gap-4 px-4 pb-4">
          {children}
        </div>
      )}
    </section>
  );
}
