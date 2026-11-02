"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";

/** "On this page" list that marks the section currently being read. */
export function Toc({ items }: { items: readonly (readonly [string, string])[] }) {
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const els = items.map(([id]) => document.getElementById(id)).filter((el): el is HTMLElement => !!el);
    if (els.length === 0) return;
    let raf = 0;
    // the current section is the last heading that has passed a reading line a quarter of the way down
    const update = () => {
      raf = 0;
      const line = window.innerHeight * 0.25;
      let current: string | null = null;
      for (const el of els) if (el.getBoundingClientRect().top <= line) current = el.id;
      setActive(current);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [items]);

  return (
    <nav aria-label="On this page" className="hidden lg:block">
      <ul className="sticky top-6 flex flex-col gap-1 text-sm">
        {items.map(([id, label]) => (
          <li key={id}>
            <a
              href={`#${id}`}
              aria-current={active === id ? "location" : undefined}
              className={cn(
                "block rounded-md px-2 py-1 hover:bg-raised hover:text-ink",
                active === id ? "bg-raised text-ink" : "text-muted",
              )}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
