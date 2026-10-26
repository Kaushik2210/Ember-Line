"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Theme = "dark" | "light";

function readStored(): Theme | null {
  try {
    const v = localStorage.getItem("emberline-theme");
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null; // private mode or blocked storage: just follow the system
  }
}

/** Dark by default, as the product brief asks; the choice is remembered when storage allows it. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const t = readStored() ?? "dark";
    setTheme(t);
    document.documentElement.dataset.theme = t;
  }, []);

  const flip = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("emberline-theme", next);
    } catch {
      /* not persisted, still applied */
    }
  };

  return (
    <button
      type="button"
      onClick={flip}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className="grid size-9 place-items-center rounded-lg text-muted hover:bg-raised hover:text-ink pointer-coarse:size-11"
    >
      {theme === "dark" ? <Sun aria-hidden className="size-4" /> : <Moon aria-hidden className="size-4" />}
    </button>
  );
}
