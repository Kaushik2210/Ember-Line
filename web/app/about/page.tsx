import type { Metadata } from "next";
import { Prose } from "@/components/site/Prose";
import { ACKNOWLEDGMENT, PageShell } from "@/components/site/SiteShell";

export const metadata: Metadata = {
  title: "About · EMBERLINE",
  description: "Data sources, NASA attribution, how to cite and where the code lives.",
};

const REPO = "https://github.com/Kaushik2210/Ember-Line";

const SOURCES = [
  {
    name: "MODIS active fire (MODIS_SP)",
    what: "Terra and Aqua MODIS, 1 km, standard processing. Hot spots with confidence 0 to 100, FRP, pixel size, day or night and fire type.",
    href: "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html",
    via: "NASA FIRMS Area API",
  },
  {
    name: "VIIRS 375 m active fire (VIIRS_SNPP_SP)",
    what: "Suomi NPP VIIRS I-band, 375 m, standard processing. Hot spots with confidence classes, FRP, day or night and fire type.",
    href: "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html",
    via: "NASA FIRMS Area API",
  },
  {
    name: "Corrected reflectance true-colour imagery",
    what: "Terra MODIS and Suomi NPP VIIRS daily imagery, and the Blue Marble base layer, shown behind the detections.",
    href: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&request=GetCapabilities",
    via: "NASA GIBS (no key needed)",
  },
] as const;

export default function AboutPage() {
  return (
    <PageShell current="/about">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">About</h1>
        <Prose className="mt-4">
          <p>
            EMBERLINE was built for NASA Space Apps 2026, for the challenge &ldquo;Harmonization of MODIS and VIIRS Hot Spots&rdquo;. It
            turns two satellite fire records that cannot be compared directly into one consistent, uncertainty-aware record of burning
            activity for any region and period.
          </p>

          <h2 id="sources">Data sources</h2>
          <p>All satellite data are NASA&apos;s. The only credential needed to run the project is a free FIRMS map key.</p>
        </Prose>
        <ul className="mt-4 flex flex-col gap-3">
          {SOURCES.map((s) => (
            <li key={s.name} className="rounded-xl border border-line bg-panel p-4">
              <h3 className="text-sm font-semibold text-ink">{s.name}</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">{s.what}</p>
              <p className="mt-2 text-xs text-faint">
                {s.via} ·{" "}
                <a href={s.href} target="_blank" rel="noopener noreferrer" className="text-viirs hover:underline">
                  Product description
                </a>
              </p>
            </li>
          ))}
        </ul>

        <Prose>
          <h2 id="attribution">Acknowledgment</h2>
          <p>{ACKNOWLEDGMENT}</p>
          <p>
            This is an independent project. It is not affiliated with or endorsed by NASA, and NASA is not responsible for its results.
          </p>

          <h2 id="honesty">What this is not</h2>
          <p>
            A harmonized record is a statistical estimate, shown with its uncertainty. Active-fire detections are not burned area, and the
            validation compares the two sensors with each other, not with ground truth. The <a href="/method#limits">method page</a> lists the
            limits in full. Figures in the app are computed from the data; sample data used while developing is always labelled
            &ldquo;SYNTHETIC DATA&rdquo; and is never presented as real.
          </p>

          <h2 id="cite">How to cite</h2>
          <p>If you use EMBERLINE in your work, please cite the project and, separately, NASA FIRMS using the wording above.</p>
        </Prose>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-panel p-4 text-xs leading-relaxed text-ink">
          <code>{`@misc{emberline2026,
  title        = {{EMBERLINE}: a harmonized MODIS and VIIRS fire calendar},
  author       = {{EMBERLINE contributors}},
  year         = {2026},
  howpublished = {NASA Space Apps Challenge 2026},
  url          = {${REPO}}
}`}</code>
        </pre>

        <Prose>
          <h2 id="code">Code</h2>
          <p>
            The source, the validation report for Punjab and Haryana, and the notes on every design decision are in the{" "}
            <a href={REPO} target="_blank" rel="noopener noreferrer">
              project repository
            </a>
            . The API is a Python 3.12 FastAPI service with a tested scientific core; the web app is Next.js.
          </p>
        </Prose>
      </div>
    </PageShell>
  );
}
