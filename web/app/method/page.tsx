import type { Metadata } from "next";
import { MethodLive } from "@/components/site/MethodLive";
import { Equation, Prose } from "@/components/site/Prose";
import { PageShell } from "@/components/site/SiteShell";

export const metadata: Metadata = {
  title: "Method · EMBERLINE",
  description: "How EMBERLINE harmonizes MODIS and VIIRS active-fire records: data, equations, validation, assumptions and limits.",
};

const TOC = [
  ["summary", "Summary"],
  ["data", "Data"],
  ["why", "Why the sensors differ"],
  ["pipeline", "Pipeline"],
  ["time", "Local solar time"],
  ["quality", "Quality policy"],
  ["grid", "Common grid and measures"],
  ["overpass", "Coincident overpasses"],
  ["normalisation", "Normalisation"],
  ["daily", "The harmonized daily series"],
  ["terra", "Terra-only years"],
  ["seasonality", "Seasonality"],
  ["unusual", "Unusual periods"],
  ["validation", "Validation results"],
  ["limits", "Assumptions and limitations"],
  ["references", "References"],
] as const;

const SRC = {
  modisFirms: "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html",
  viirsFirms: "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html",
  viirs375: "https://www.earthdata.nasa.gov/data/instruments/viirs/viirs-i-band-375-m-active-fire-data",
  faqModis: "https://forum.earthdata.nasa.gov/viewtopic.php?t=5191",
  faqViirs: "https://forum.earthdata.nasa.gov/viewtopic.php?t=5189",
  terraDrift: "https://terra.nasa.gov/about/terras-orbit-changes/terra-orbital-drift-information",
  terraManeuver: "https://modis-land.gsfc.nasa.gov/news.html",
  c61: "https://www.earthdata.nasa.gov/data/catalog/lancemodis-mcd14dl-6.1nrt",
  firms: "https://www.earthdata.nasa.gov/data/tools/firms",
  gibs: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&request=GetCapabilities",
  csiszar: "https://directreadout.sci.gsfc.nasa.gov/publications_documents/Csiszar_et_al_2014_JGR.pdf",
};

export default function MethodPage() {
  return (
    <PageShell current="/method">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[200px_minmax(0,1fr)]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-6 flex flex-col gap-1 text-sm">
            {TOC.map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`} className="block rounded-md px-2 py-1 text-muted hover:bg-raised hover:text-ink">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <article className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Method</h1>
          <p className="mt-3 max-w-[70ch] text-muted">
            What EMBERLINE computes, with the equations, the choices behind them and what they cannot tell you. Numbers on this page are
            either parameters of the method or are computed from the NASA record when you load it.
          </p>

          <Prose>
            <h2 id="summary">Summary</h2>
            <p>
              MODIS (1 km) and VIIRS (375 m) both report active fires, but a count of detections from one cannot be compared with a count
              from the other. EMBERLINE puts both on a common grid, measures how they disagree where they observe the same fires, learns a
              mapping from MODIS to VIIRS-equivalent units on the years both exist, validates that mapping on years it never saw, and uses
              it to reconstruct a VIIRS-equivalent record back to 2000 with prediction bands. Seasonality and unusual periods are then
              computed on that single record.
            </p>
            <p>
              The challenge&apos;s four goals map to the workspace: select an area and period (controls), explore historical hotspots (map
              and calendar), identify seasonal patterns and unusual periods (seasonality and unusual-periods tabs), and normalise the
              records so comparisons are meaningful (this page and the sensor-agreement tab).
            </p>

            <h2 id="data">Data</h2>
            <p>
              Detections come from the NASA FIRMS Area API. The standard-processing products are used: <code>MODIS_SP</code> (Terra and
              Aqua together, from 2000-11-01) and <code>VIIRS_SNPP_SP</code> (Suomi NPP, from 2012-01-20). Valid date ranges are read from
              FIRMS&apos;s data-availability endpoint, never fixed in code. Terra and Aqua each have a documented start of high-quality fire
              data (November 2000 and 4 July 2002) <a href={SRC.faqModis} target="_blank" rel="noopener noreferrer">[1]</a>, and FIRMS
              lists the Suomi NPP VIIRS 375 m coverage as starting 20 January 2012 <a href={SRC.viirsFirms} target="_blank" rel="noopener noreferrer">[2]</a>.
            </p>
            <p>
              Both sensors are mapped to one table. MODIS reports brightness temperatures in channels 21 and 31 and a confidence of 0 to
              100; VIIRS reports I4 and I5 brightness temperatures and a confidence of low, nominal or high. Fire radiative power (FRP, in
              megawatts) exists in both and is the most directly comparable quantity.
            </p>
            <p>
              Practical facts learned from the live API, because they affect any reproduction: a request may span 1 to 5 days (not the 10
              the public text suggests), and the transaction cost was measured at 2 per requested day regardless of area. NOAA-20 and
              NOAA-21 are available in FIRMS but are not used here: the harmonisation is fitted between Aqua/Terra MODIS and Suomi NPP
              VIIRS only.
            </p>

            <h2 id="why">Why the sensors differ</h2>
            <ul>
              <li>
                <strong>Pixel size.</strong> VIIRS 375 m pixels respond to smaller, lower-intensity fires than MODIS 1 km pixels
                <a href={SRC.viirs375} target="_blank" rel="noopener noreferrer"> [3]</a>. In regions of many small fires VIIRS has far more detections.
              </li>
              <li>
                <strong>Overpass time.</strong> Terra crosses the equator in the morning and Aqua in the afternoon
                <a href={SRC.modisFirms} target="_blank" rel="noopener noreferrer"> [4]</a>; Suomi NPP&apos;s VIIRS crosses at about 13:30
                <a href={SRC.viirs375} target="_blank" rel="noopener noreferrer"> [3]</a>. Fires have a daily cycle, so each samples a different part of it.
              </li>
              <li>
                <strong>Pixel growth with scan angle.</strong> MODIS pixels get bigger toward the edge of the scan; FIRMS reports the actual
                pixel size as scan and track <a href={SRC.modisFirms} target="_blank" rel="noopener noreferrer">[4]</a>. VIIRS footprints grow off-nadir too <a href={SRC.viirs375} target="_blank" rel="noopener noreferrer">[3]</a>.
              </li>
              <li>
                <strong>Confidence schemes</strong> differ (numeric against classes), so one policy maps both onto a common rule.
              </li>
              <li>
                <strong>Non-fire heat.</strong> FIRMS flags hot spots as presumed vegetation fire (0), active volcano (1), other static
                land source (2) or offshore (3) <a href={SRC.modisFirms} target="_blank" rel="noopener noreferrer">[4]</a>. Only presumed vegetation fire is kept, and a persistence mask removes places that burn on a large share of days.
              </li>
              <li>
                <strong>FRP processing.</strong> FIRMS notes that VIIRS 375 m FRP comes from a hybrid of 375 m and 750 m data, with the
                M13 channel added from 2015 <a href={SRC.viirsFirms} target="_blank" rel="noopener noreferrer">[2]</a>. FRP may therefore not be perfectly homogeneous across that change.
              </li>
            </ul>

            <h2 id="pipeline">Pipeline</h2>
            <ol>
              <li>Download in 5-day chunks, cache as Parquet, read back through DuckDB.</li>
              <li>Convert times to local solar time; apply the quality policy.</li>
              <li>Aggregate to a common grid: detections, burning 1 km footprints and summed FRP per cell and local day.</li>
              <li>Match Aqua-MODIS to Suomi NPP-VIIRS detections that are close in space and time.</li>
              <li>Fit normalisation models on weekly totals over the overlap; validate leave-one-year-out; choose.</li>
              <li>Produce the harmonized daily series with prediction bands; flag reconstructed days.</li>
              <li>Compute climatology, season markers, STL, and unusual periods against leave-one-year-out baselines.</li>
            </ol>

            <h2 id="time">Local solar time</h2>
            <p>The two sensors are compared by local solar time so day-of-year patterns line up across longitudes.</p>
            <Equation label="local solar time">
              t<sub>local</sub> = (t<sub>UTC</sub> + λ / 15) mod 24 &nbsp; hours, &nbsp; with λ the longitude in degrees east.
            </Equation>
            <p>If the shift crosses midnight the local date moves by one day, forward or back.</p>

            <h2 id="quality">Quality policy</h2>
            <p>Defaults, all adjustable in the workspace:</p>
            <ul>
              <li>MODIS confidence of at least 30; VIIRS confidence nominal or high.</li>
              <li>Fire type 0 (presumed vegetation fire); rows with no type are kept.</li>
              <li>
                Persistent heat sources are removed: 0.02° cells with detections on more than 10% of the days of the record. A fraction of
                days is meaningless on a short record, where a field burning on two of ten days looks persistent, so the mask is only built
                from at least 365 distinct days.
              </li>
            </ul>

            <h2 id="grid">Common grid and measures</h2>
            <p>Both sensors are aggregated onto a regular grid (0.1, 0.25 or 0.5 degrees) or an H3 grid (resolution 4 to 6). Per cell and local day:</p>
            <ul>
              <li><strong>Detections</strong> (raw count), shown only to demonstrate the mismatch.</li>
              <li>
                <strong>Burning 1 km footprints</strong>: unique 0.01° footprints with at least one detection. VIIRS pixels in the same
                footprint count once, so this presence measure does not scale with pixel size.
              </li>
              <li><strong>Fire radiative power</strong>: the sum in megawatts, the default measure.</li>
            </ul>

            <h2 id="overpass">Coincident overpasses</h2>
            <p>
              Aqua-MODIS and Suomi NPP-VIIRS both pass in the afternoon, so detections close in space and time describe the same fires. A
              VIIRS detection is matched to the nearest MODIS detection satisfying
            </p>
            <Equation label="matching rule">
              d(<var>p</var><sub>V</sub>, <var>p</var><sub>M</sub>) ≤ 750 m &nbsp; and &nbsp; |<var>t</var><sub>V</sub> − <var>t</var><sub>M</sub>| ≤ 30 min,
            </Equation>
            <p>
              with distance on the sphere. Several VIIRS pixels can fall in one MODIS pixel, so a MODIS detection is corroborated when at
              least one matches, and its FRP ratio is the sum of the matched VIIRS FRP over the MODIS FRP.
            </p>
            <p>
              The 30-minute window is a measured choice, not a convention: on a 10-day Punjab and Haryana sample, the nearest VIIRS pixel
              within 5 km trailed the Aqua pixel by a median of about 16 minutes, and only 19% of pairs fell within 10 minutes. The window is
              a parameter.
            </p>
            <p>
              FIRMS publishes no swath masks, so a detection is judged by the other sensor only if that sensor has a detection within 25 km
              and the time window, as a proxy that it was looking. Detections without one are excluded from the rates and counted
              separately. This proxy is conservative in quiet scenes.
            </p>

            <h2 id="normalisation">Normalisation</h2>
            <p>
              Models are fitted on weekly totals over the weeks both sensors observed completely, in log space, because weekly totals are
              heavy-tailed and often near zero:
            </p>
            <Equation label="log mapping">
              <var>u</var> = ln(1 + <var>x</var><sub>MODIS</sub>), &nbsp; <var>v</var> = ln(1 + <var>x</var><sub>VIIRS</sub>), &nbsp; <var>v̂</var> = <var>f</var>(<var>u</var>; season).
            </Equation>
            <p>Candidates for <em>f</em>:</p>
            <ul>
              <li>a straight line fitted with Huber loss, robust to outlier weeks;</li>
              <li>a straight line fitted by Theil–Sen, the median of pairwise slopes;</li>
              <li>seasonal quantile mapping: match the MODIS distribution to the VIIRS distribution within each meteorological season, with unit-slope tails beyond the fitted range;</li>
              <li>isotonic regression, a monotone non-decreasing step fit.</li>
            </ul>
            <p>
              Two baselines are always scored for context and never selected: <code>raw</code> (use MODIS as it is) and <code>scale</code> (a
              single multiplicative factor). If a fitted model does not clearly beat <code>scale</code>, the workspace says so.
            </p>
            <h3>Validation</h3>
            <p>
              Each calendar year is predicted by a model fitted on all the other years (leave-one-year-out). Reported per model: R² and mean
              absolute error in log units, mean absolute error and relative bias in original units, rank correlation, and interval coverage.
              The model with the lowest log error among the four candidates is chosen unless you force one.
            </p>
            <h3>Prediction intervals</h3>
            <p>
              Intervals are cross-conformal. With out-of-fold absolute residuals <var>r</var><sub>i</sub> = |<var>v</var><sub>i</sub> − <var>v̂</var><sub>i</sub>| and nominal level 1 − α:
            </p>
            <Equation label="conformal interval">
              <var>q</var> = Quantile<sub>⌈(<var>n</var>+1)(1−α)⌉ / <var>n</var></sub>(<var>r</var><sub>i</sub>), &nbsp; interval = [ e<sup><var>v̂</var> − <var>q</var></sup> − 1, e<sup><var>v̂</var> + <var>q</var></sup> − 1 ].
            </Equation>
            <p>
              Coverage is checked on each held-out year using the threshold from the other years&apos; residuals, so it is tested on data the
              model did not see. Where a MODIS total lies beyond the range seen when fitting, the band is widened by a factor of 1.5.
            </p>

            <h2 id="daily">The harmonized daily series</h2>
            <p>
              Where VIIRS observed a day, its own value is used and no band is shown. Elsewhere the weekly MODIS total <var>W</var> is mapped
              to <var>f</var>(<var>W</var>) and spread over the seven days in proportion to MODIS&apos;s own daily pattern:
            </p>
            <Equation label="daily disaggregation">
              ŷ<sub>d</sub> = <var>x</var><sub>d</sub> · <var>f</var>(<var>W</var>) / <var>W</var>, &nbsp; (and <var>f</var>(0) / 7 on each day of a week with no MODIS detections).
            </Equation>
            <p>
              Only complete weeks are reconstructed; a day with no data is a gap, never a zero. The model works at weekly scale, so within a
              week the day-to-day shape is MODIS&apos;s, not VIIRS&apos;s.
            </p>

            <h2 id="terra">Terra-only years</h2>
            <p>
              Before Aqua&apos;s fire record began (4 July 2002) <a href={SRC.faqModis} target="_blank" rel="noopener noreferrer">[1]</a>, MODIS
              fire data come from Terra alone, with far fewer overpasses. Reading those years through the two-satellite model makes them look
              like unusually quiet years. A separate model is therefore fitted on Terra&apos;s own overlap with VIIRS and used for the weeks
              before the Aqua date, and unusual periods found there carry a reliability caveat.
            </p>

            <h2 id="seasonality">Seasonality</h2>
            <ul>
              <li>
                <strong>Climatology.</strong> For each of 365 calendar days, the median, interquartile range and 10th to 90th percentile of
                the harmonized series, pooling the same day and the 7 days either side across years (29 February is skipped).
              </li>
              <li>
                <strong>Season markers.</strong> The year is cut at its quietest day; start, peak and end are the days when cumulative
                activity reaches 10%, 50% and 90%. The peak is the activity-weighted median day, not the single busiest day.
              </li>
              <li>
                <strong>Several seasons.</strong> Regions that burn twice a year (crop residue, for example) are split into runs where the
                smoothed climatology stays above 20% of its maximum, and each run gets its own markers.
              </li>
              <li>
                <strong>STL.</strong> A robust seasonal-trend decomposition (period 52) of the weekly log series gives a long-term trend and a
                seasonal component.
              </li>
            </ul>

            <h2 id="unusual">Unusual periods</h2>
            <p>For each day, a robust score against a baseline built from every other year (so an extreme year never contaminates its own baseline):</p>
            <Equation label="robust score">
              <var>z</var> = ( ln(1 + <var>y</var>) − median<sub>−year</sub> ) / max( 1.4826 · MAD<sub>−year</sub>, floor ).
            </Equation>
            <p>
              The floor is 5% of a high percentile of the positive values, which stops a handful of detections in an otherwise empty season
              from scoring enormously. A sustained event is |<var>z</var>| &gt; 2.5 for at least 3 consecutive days of the same sign (one day
              of gap is bridged) whose total departure from baseline is at least 1% of a typical year. Whole fire years are ranked by the
              same robust score of their totals against the other years.
            </p>

            <h2 id="validation">Validation results</h2>
          </Prose>
          <Prose className="mt-4">
            <MethodLive />
          </Prose>

          <Prose>
            <h2 id="limits">Assumptions and limitations</h2>
            <ul>
              <li>
                <strong>A reconstruction is an estimate.</strong> The mapping is learned where both sensors exist and extended to years
                where only MODIS does. It assumes the relationship between the sensors did not change before 2012, which cannot be tested
                with this data.
              </li>
              <li>
                <strong>Bands are wide on purpose.</strong> Weekly totals from the two sensors disagree by more than a constant factor, partly
                because of different overpass times and different pixel sizes. The bands report that.
              </li>
              <li>
                <strong>Weekly model, daily series.</strong> Day-to-day shape inside a reconstructed week is MODIS&apos;s.
              </li>
              <li>
                <strong>No swath masks.</strong> Co-observation is inferred from nearby detections, which biases rates toward busy scenes.
              </li>
              <li>
                <strong>FRP homogeneity.</strong> VIIRS FRP processing changed in 2015 <a href={SRC.viirsFirms} target="_blank" rel="noopener noreferrer">[2]</a>; effects on a long FRP record are not corrected.
              </li>
              <li>
                <strong>Terra&apos;s orbit.</strong> After its last inclination maneuver on 27 February 2020 Terra drifts to an earlier
                crossing time <a href={SRC.terraDrift} target="_blank" rel="noopener noreferrer">[5]</a>. NASA expects minimal impact on science; EMBERLINE does not model it.
              </li>
              <li>
                <strong>Suomi NPP is ageing.</strong> NASA notes its end of life is anticipated on or before October 2026
                <a href={SRC.viirs375} target="_blank" rel="noopener noreferrer"> [3]</a>, so the VIIRS reference side of the mapping will need another satellite.
              </li>
              <li>
                <strong>Detection is not burned area.</strong> Active fire detections show where fire was burning when a satellite passed. No
                independent ground truth is used for validation; agreement is measured between the two sensors only.
              </li>
              <li>
                <strong>Standard against near-real-time data.</strong> Only standard-processing data are used for the record. Newer near-real-time data are not stitched in.
              </li>
              <li>
                <strong>Local choices.</strong> The coincidence window, quality thresholds and persistence mask are tuned on and for the regions shown.
              </li>
            </ul>

            <h2 id="references">References</h2>
            <h3>NASA sources</h3>
            <ol>
              <li>
                <a href={SRC.faqModis} target="_blank" rel="noopener noreferrer">FIRMS FAQ: Questions about MODIS active fire data</a>, NASA Earthdata Forum (launch dates and start of high-quality fire data).
              </li>
              <li>
                <a href={SRC.viirsFirms} target="_blank" rel="noopener noreferrer">FIRMS: VIIRS active fire hot spots</a> (attributes, temporal coverage, FRP processing).
              </li>
              <li>
                <a href={SRC.viirs375} target="_blank" rel="noopener noreferrer">VIIRS I-Band 375 m Active Fire Data</a>, NASA Earthdata.
              </li>
              <li>
                <a href={SRC.modisFirms} target="_blank" rel="noopener noreferrer">FIRMS: MODIS fire and thermal anomalies</a> (attributes, fire type codes, overpass).
              </li>
              <li>
                <a href={SRC.terraDrift} target="_blank" rel="noopener noreferrer">Terra Orbital Drift Information</a>, and{" "}
                <a href={SRC.terraManeuver} target="_blank" rel="noopener noreferrer">MODIS Land Team news</a> (final maneuver date).
              </li>
              <li>
                <a href={SRC.c61} target="_blank" rel="noopener noreferrer">MODIS Collection 6.1 near-real-time fire product</a>; <a href={SRC.faqViirs} target="_blank" rel="noopener noreferrer">FIRMS FAQ for VIIRS</a>.
              </li>
              <li>
                <a href={SRC.csiszar} target="_blank" rel="noopener noreferrer">Csiszar et al. (2014), Journal of Geophysical Research</a>, on active fires from Suomi NPP VIIRS.
              </li>
              <li>
                <a href={SRC.gibs} target="_blank" rel="noopener noreferrer">NASA GIBS WMTS capabilities</a>, the source of the imagery layers and their date ranges.
              </li>
              <li>
                <a href={SRC.firms} target="_blank" rel="noopener noreferrer">FIRMS at NASA Earthdata</a> (acknowledgment wording).
              </li>
            </ol>
            <h3>Statistical methods</h3>
            <ul>
              <li>Huber, P. J. (1964). Robust estimation of a location parameter. <em>Annals of Mathematical Statistics</em> 35(1), 73–101.</li>
              <li>Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall&apos;s tau. <em>Journal of the American Statistical Association</em> 63, 1379–1389.</li>
              <li>Cleveland, R. B., Cleveland, W. S., McRae, J. E., &amp; Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on loess. <em>Journal of Official Statistics</em> 6(1), 3–73.</li>
              <li>Lei, J., G&apos;Sell, M., Rinaldo, A., Tibshirani, R. J., &amp; Wasserman, L. (2018). Distribution-free predictive inference for regression. <em>Journal of the American Statistical Association</em> 113(523), 1094–1111.</li>
            </ul>
          </Prose>
        </article>
      </div>
    </PageShell>
  );
}
