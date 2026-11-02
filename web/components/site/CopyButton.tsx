"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

/** Copies text to the clipboard and says so; falls back quietly when the clipboard is blocked. */
export function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      aria-label={done ? "Copied" : label}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 2000);
        } catch {
          /* clipboard blocked: the text is still selectable */
        }
      }}
      className="absolute right-2 top-2 inline-flex min-h-8 items-center gap-1.5 rounded-md border border-line bg-raised px-2 text-xs text-muted hover:text-ink pointer-coarse:min-h-11"
    >
      {done ? <Check aria-hidden className="size-3.5" /> : <Copy aria-hidden className="size-3.5" />}
      <span aria-live="polite">{done ? "Copied" : "Copy"}</span>
    </button>
  );
}
