"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";

/** "On this page" list that marks the section currently being read. */
export function Toc({ items }: { items: readonly (readonly [string, string])[] }) {
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const els = items.map(([id]) => document.getElementById(id)).filter((el): el is HTMLElement => !!el);
    if (els.length === 0 || typeof IntersectionObserver === "undefined") return;
    const seen = new Map<string, boolean>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) seen.set(e.target.id, e.isIntersecting);
        // the first heading (in page order) inside the reading band wins
        const first = els.find((el) => seen.get(el.id));
        if (first) setActive(first.id);
      },
      { rootMargin: "-10% 0px -75% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
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
