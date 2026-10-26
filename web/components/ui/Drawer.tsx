"use client";
import { useEffect } from "react";

type Props = { open: boolean; title: string; onClose: () => void; children: React.ReactNode };

export function Drawer({ open, title, onClose, children }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <aside
      role="dialog"
      aria-label={title}
      className="fixed inset-y-0 right-0 z-40 w-full max-w-md overflow-y-auto border-l border-line bg-panel p-5 shadow-2xl"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold">{title}</h2>
        <button
          onClick={onClose}
          aria-label="Close"
          className="size-11 rounded-md text-muted hover:text-ink"
        >
          ✕
        </button>
      </div>
      {children}
    </aside>
  );
}
