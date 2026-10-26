# Pitch

All numbers below are computed by the pipeline from NASA FIRMS data and appear in the app. Re-check them
in the running app before presenting; they change only if the data or method changes.

## The 2-minute script

**0:00 The problem.** "MODIS and VIIRS both watch fire from space, but they disagree. Over Punjab and
Haryana, VIIRS reports 1.7 times the fire radiative power MODIS does on days both were watching. Over
eastern Australia it reports less. So a calendar built from either one, or from both naively, shifts when
the satellite changes, not when the fire does."

**0:20 The record.** Open the landing page. "EMBERLINE turns the two records into one calendar. Twenty-six
years, 45% of the days reconstructed from MODIS into VIIRS-equivalent units, with uncertainty bands."

**0:35 See the disagreement.** Open the workspace on Punjab and Haryana. Drag the compare slider on the
default day (7 Nov 2016). "Same day, same place. MODIS on the left, VIIRS on the right, over NASA imagery.
VIIRS sees many small fires because its pixels are smaller. One third of MODIS detections are also seen
by VIIRS."

**1:00 The fix, and the proof.** Sensor agreement tab. "Raw MODIS is 41% low against VIIRS. After
normalising it is 1% off, measured on years the model never saw (leave-one-year-out), so the improvement
is not self-flattering." Open "Why they differ" for the overpass-time and pixel-size explanation.

**1:20 What it shows.** Calendar, then Unusual periods. "Each season is compared only with the others.
2024-25 stands out as 3.5 robust standard deviations below the rest. We report it; we do not claim to
know why." Atlas: "Australia's 2019-20 season comes out 7.2 standard deviations above the others
without being told to look for it."

**1:45 Honest by design.** Data quality tab and Method page. "What each sensor contributes by year,
documented events, and a plain list of limits. Nothing here is invented: where data is not downloaded the
app says so."

**1:55 Close.** "One consistent record of fire, from two sensors. Every number traceable, every
uncertainty shown."

## 5-slide outline

1. **The disagreement.** Two sensors, different pixel size, different overpass time, different totals
   (1.7x in Punjab, 0.74x in eastern Australia). Visual: the compare slider screenshot.
2. **Approach.** Quality policy, common grid, coincident-overpass matching, weekly normalisation fitted
   on VIIRS-era years, cross-conformal intervals. Visual: the architecture diagram from the README.
3. **Proof.** Bias -41% to +1%, R-squared (log) 0.77 to 0.89 on held-out years in Punjab; show the
   before/after scatter. State the Australia result too (model chosen per region).
4. **What it reveals.** Seasonal markers, unusual periods, Australia 2019-20. Visual: calendar and the
   anomaly view.
5. **Honest limits and next steps.** Reconstructed pre-2012 values, FRP processing change in 2015, Terra
   drift, no burned area. Next: more regions, VIIRS NOAA-20/21 as the reference after SNPP.

## Challenge objectives to features

| Objective | Where it is answered |
|---|---|
| Select an area and period | Region presets, draw box, GeoJSON upload, date range with presets, shareable URL |
| Explore historical hotspots | MODIS/VIIRS compare slider and overlay over GIBS imagery, time scrubber, hotspot inspector |
| Find seasonal patterns and unusual periods | Seasonality tab (typical season, markers), Unusual periods tab (robust-z anomalies with a materiality floor) |
| Normalize so comparisons are meaningful | Harmonized calendar, Sensor agreement tab, Why they differ drawer, Method page, methods-card export |
| Trust the result | Data quality tab, leave-one-year-out validation, uncertainty bands, labelled limits |

## Likely questions

- **"Why not just scale one by a constant?"** A scale baseline is evaluated alongside the models. In Punjab it
  does well (log R-squared 0.85 against 0.89 for the chosen model), so say the gain is real but modest
  there; the validation report has the table.
- **"Is 2024-25 in Punjab real?"** The pipeline flags it; causes are not established here.
- **"Is the data real?"** Yes, NASA FIRMS standard-processing archive. Synthetic data exists for tests
  and is always labelled.
