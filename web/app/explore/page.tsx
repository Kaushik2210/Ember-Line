import type { Metadata } from "next";
import { Suspense } from "react";
import { Workspace } from "@/components/explore/Workspace";

export const metadata: Metadata = { title: "Explore · EMBERLINE" };

export default function ExplorePage() {
  return (
    <Suspense fallback={<div className="grid h-dvh place-items-center bg-bg text-sm text-muted">Loading workspace…</div>}>
      <Workspace />
    </Suspense>
  );
}
