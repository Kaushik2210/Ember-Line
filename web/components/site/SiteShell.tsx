import Link from "next/link";
import { ThemeToggle } from "@/components/explore/ThemeToggle";

const NAV = [
  { href: "/explore", label: "Explore" },
  { href: "/atlas", label: "Atlas" },
  { href: "/method", label: "Method" },
  { href: "/about", label: "About" },
] as const;

// Wording supplied by NASA for users of FIRMS data (earthdata.nasa.gov/data/tools/firms).
export const ACKNOWLEDGMENT =
  "We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System (ESDIS).";

export function SiteHeader({ current, overlay = false }: { current?: string; overlay?: boolean }) {
  return (
    <header className={overlay ? "absolute inset-x-0 top-0 z-20" : "border-b border-line bg-panel"}>
      <div className="mx-auto flex min-h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="text-sm font-semibold tracking-wide text-ink">
          EMBERLINE
        </Link>
        <nav aria-label="Main" className="ml-auto flex items-center gap-0.5 sm:gap-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              aria-current={current === n.href ? "page" : undefined}
              className={`grid min-h-9 place-items-center rounded-lg px-2.5 text-sm pointer-coarse:min-h-11 ${
                current === n.href ? "bg-raised text-ink" : "text-muted hover:text-ink"
              }`}
            >
              {n.label}
            </Link>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-panel">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <p className="max-w-3xl text-xs leading-relaxed text-faint">{ACKNOWLEDGMENT}</p>
        <p className="mt-3 text-xs text-faint">
          Built for NASA Space Apps 2026, challenge &ldquo;Harmonization of MODIS and VIIRS Hot Spots&rdquo;. Satellite data are
          NASA&apos;s; this project is not affiliated with or endorsed by NASA.
        </p>
      </div>
    </footer>
  );
}

export function PageShell({ current, children }: { current: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg text-ink">
      <SiteHeader current={current} />
      <main id="content" className="flex-1">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
