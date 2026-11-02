import Link from "next/link";
import { PageShell } from "@/components/site/SiteShell";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <PageShell current="">
      <div className="mx-auto max-w-xl px-4 py-24 text-center sm:px-6">
        <p className="num text-sm text-faint">404</p>
        <h1 className="mt-2 text-2xl font-semibold">This page isn&apos;t in the record</h1>
        <p className="mt-3 text-sm text-muted">The link may be old or mistyped. These places exist:</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm">
          <Link className="rounded-lg border border-line bg-raised px-4 py-2 hover:border-[var(--border-strong)]" href="/explore">
            Explore
          </Link>
          <Link className="rounded-lg border border-line bg-raised px-4 py-2 hover:border-[var(--border-strong)]" href="/atlas">
            Atlas
          </Link>
          <Link className="rounded-lg border border-line bg-raised px-4 py-2 hover:border-[var(--border-strong)]" href="/">
            Home
          </Link>
        </div>
      </div>
    </PageShell>
  );
}
