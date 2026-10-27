import type { Metadata } from "next";
import { AtlasGrid } from "@/components/site/AtlasGrid";
import { PageShell } from "@/components/site/SiteShell";

export const metadata: Metadata = {
  title: "Atlas · EMBERLINE",
  description: "Eight places where MODIS and VIIRS tell different stories about fire, with findings computed from the record.",
};

export default function AtlasPage() {
  return (
    <PageShell current="/atlas">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Atlas</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Regions chosen because the two sensors tell them differently. Under each story are the findings EMBERLINE computed from
          the NASA record, not written by hand, and a link that opens the same analysis in the workspace.
        </p>
        <div className="mt-8">
          <AtlasGrid />
        </div>
      </div>
    </PageShell>
  );
}
