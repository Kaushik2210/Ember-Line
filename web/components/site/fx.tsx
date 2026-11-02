"use client";

import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";
import { type ElementType, type ReactNode, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

// Motion for the marketing pages. Everything here is decoration: it is switched off for visitors who ask
// for reduced motion, and none of it hides content from assistive technology.

const EASE = [0.22, 1, 0.36, 1] as const;

/** Rising embers on a canvas. Pauses when off screen, and draws nothing under reduced motion. */
export function Embers({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || reduce) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const COLORS = ["230,159,0", "255,90,77", "184,166,255", "86,180,233"];
    type P = { x: number; y: number; r: number; vy: number; vx: number; c: string; a: number; ph: number };
    let w = 0;
    let h = 0;
    let parts: P[] = [];
    let raf = 0;
    let visible = true;
    const spawn = (anywhere: boolean): P => ({
      x: Math.random() * w,
      y: anywhere ? Math.random() * h : h + 10,
      r: 0.8 + Math.random() * 2.2,
      vy: 0.25 + Math.random() * 0.8,
      vx: (Math.random() - 0.5) * 0.25,
      c: COLORS[Math.floor(Math.random() * COLORS.length)],
      a: 0.25 + Math.random() * 0.5,
      ph: Math.random() * Math.PI * 2,
    });
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.min(90, Math.max(24, Math.round(w / 18)));
      parts = Array.from({ length: n }, () => spawn(true));
    };
    const tick = (t: number) => {
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      ctx.clearRect(0, 0, w, h);
      for (const p of parts) {
        p.y -= p.vy;
        p.x += p.vx + Math.sin(t / 1400 + p.ph) * 0.18;
        if (p.y < -10) Object.assign(p, spawn(false));
        const fade = Math.min(1, p.y / (h * 0.5));
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
        g.addColorStop(0, `rgba(${p.c},${p.a * fade})`);
        g.addColorStop(1, `rgba(${p.c},0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 5, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting));
    io.observe(canvas);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
    };
  }, [reduce]);

  return <canvas ref={ref} aria-hidden className={cn("pointer-events-none absolute inset-0 h-full w-full", className)} />;
}

/** Headline whose words rise into place one after another. */
export function SplitWords({ text, className, accent }: { text: string; className?: string; accent?: string }) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <span className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {words.map((w, i) => {
          const hot = accent ? accent.split(" ").includes(w.replace(/[.,]/g, "")) : false;
          return (
            <span key={`${w}-${i}`} className="inline-block overflow-hidden align-bottom pb-[0.08em]">
              <motion.span
                className={cn("inline-block", hot && "shimmer")}
                initial={reduce ? false : { y: "110%", rotate: 4, opacity: 0 }}
                animate={{ y: 0, rotate: 0, opacity: 1 }}
                transition={{ duration: 0.9, ease: EASE, delay: 0.15 + i * 0.07 }}
              >
                {w}
                {i < words.length - 1 ? " " : ""}
              </motion.span>
            </span>
          );
        })}
      </span>
    </span>
  );
}

/**
 * Fades and lifts its children into view as they scroll on screen. The server and no-JS render shows
 * everything; only elements that start below the fold are hidden, once the page has hydrated.
 */
export function Reveal({
  children,
  delay = 0,
  as = "div",
  className,
}: {
  children: ReactNode;
  delay?: number;
  as?: "div" | "li" | "section" | "p" | "h2";
  className?: string;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLElement>(null);
  const [state, setState] = useState<"visible" | "hidden" | "shown">("visible");

  useEffect(() => {
    const el = ref.current;
    if (!el || reduce || typeof IntersectionObserver === "undefined") return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.92) return;
    setState("hidden");
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        setState("shown");
        io.disconnect();
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduce]);

  const Tag = as as ElementType;
  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        opacity: state === "hidden" ? 0 : 1,
        transform: state === "hidden" ? "translateY(28px)" : "none",
        transition: state === "shown" ? `opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1) ${delay}s, transform 0.7s cubic-bezier(0.22, 1, 0.36, 1) ${delay}s` : undefined,
      }}
    >
      {children}
    </Tag>
  );
}

/** A card with a light that follows the pointer and a slight 3D tilt. Fine pointers only. */
export function Glow({ children, className }: { children: ReactNode; className?: string }) {
  const onMove = (e: React.PointerEvent<HTMLElement>) => {
    if (e.pointerType !== "mouse") return;
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    el.style.setProperty("--mx", `${x}px`);
    el.style.setProperty("--my", `${y}px`);
    el.style.setProperty("--ry", `${((x / r.width) * 2 - 1) * 4}deg`);
    el.style.setProperty("--rx", `${-((y / r.height) * 2 - 1) * 4}deg`);
  };
  const onLeave = (e: React.PointerEvent<HTMLElement>) => {
    e.currentTarget.style.setProperty("--rx", "0deg");
    e.currentTarget.style.setProperty("--ry", "0deg");
  };
  return (
    <div onPointerMove={onMove} onPointerLeave={onLeave} className={cn("glow", className)}>
      {children}
    </div>
  );
}

/** Digits count up (scramble, then settle) when the text first scrolls into view. Other characters stay put. */
export function Scramble({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();
  const [inView, setInView] = useState(false);
  const [shown, setShown] = useState(text);

  useEffect(() => {
    const el = ref.current;
    if (!el || reduce || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        setInView(true);
        io.disconnect();
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduce]);

  useEffect(() => {
    if (!inView || reduce) return;
    const start = performance.now();
    const DUR = 900;
    let raf = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / DUR);
      const settled = Math.floor(t * text.length);
      setShown(text.split("").map((ch, i) => (/\d/.test(ch) && i >= settled ? String(Math.floor(Math.random() * 10)) : ch)).join(""));
      if (t < 1) raf = requestAnimationFrame(step);
      else setShown(text);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduce, text]);

  // the real value is always in the accessibility tree, only the visible glyphs animate
  return (
    <span ref={ref} className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>{shown}</span>
    </span>
  );
}

/** Thin bar across the top of the page that fills as you scroll. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const x = useSpring(scrollYProgress, { stiffness: 120, damping: 28, mass: 0.4 });
  return <motion.div aria-hidden style={{ scaleX: x }} className="pointer-events-none fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-gradient-to-r from-modis via-harmonized to-viirs" />;
}

/** Endless strip of region names. Decorative: the same regions are listed as cards below. */
export function Marquee({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  const row = [...items, ...items];
  return (
    <div aria-hidden className="marquee overflow-hidden border-y border-line bg-panel/60 py-3 backdrop-blur">
      <div className="marquee-track flex w-max gap-10 whitespace-nowrap text-xs uppercase tracking-[0.18em] text-muted">
        {row.map((n, i) => (
          <span key={`${n}-${i}`} className="flex items-center gap-10">
            {n}
            <span className="size-1 rounded-full bg-harmonized" />
          </span>
        ))}
      </div>
    </div>
  );
}
