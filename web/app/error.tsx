"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div className="grid min-h-dvh place-items-center bg-bg px-4 text-ink">
      <div role="alert" className="max-w-md text-center">
        <h1 className="text-xl font-semibold">Something broke on this page</h1>
        <p className="mt-2 text-sm text-muted">Your view is kept in the URL, so trying again usually picks up where you were.</p>
        <div className="mt-6 flex justify-center gap-3 text-sm">
          <button onClick={reset} className="min-h-10 rounded-lg bg-ink px-4 text-bg hover:opacity-90 pointer-coarse:min-h-11">
            Try again
          </button>
          <Link href="/" className="grid min-h-10 place-items-center rounded-lg border border-line bg-raised px-4 pointer-coarse:min-h-11">
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}
