"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

type Props = {
  open: boolean;
  title: string;
  onClose: () => void;
  side?: "left" | "right";
  children: React.ReactNode;
};

/** A non-blocking side panel. Escape closes it and focus returns to what opened it. */
export function Drawer({ open, title, onClose, side = "right", children }: Props) {
  const opener = useRef<Element | null>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    opener.current = document.activeElement;
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      (opener.current as HTMLElement | null)?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <>
      <div aria-hidden className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} />
      <aside
        role="dialog"
        aria-label={title}
        className={cn(
          "fixed inset-y-0 z-40 flex w-full max-w-md flex-col overflow-hidden border-line bg-panel shadow-2xl",
          side === "right" ? "right-0 border-l" : "left-0 border-r",
        )}
      >
        <div className="flex min-h-12 items-center justify-between border-b border-line px-4">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button
            ref={closeBtn}
            onClick={onClose}
            aria-label={`Close ${title}`}
            className="grid size-9 place-items-center rounded-md text-muted hover:text-ink pointer-coarse:size-11"
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </aside>
    </>
  );
}
