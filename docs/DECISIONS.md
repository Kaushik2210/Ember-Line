# Decisions

- **Own git repo inside the project folder.** The folder sits under the user's home directory, which
  is itself a git repo. EMBERLINE has its own repo (`origin` = Ember-Line) so nothing is pushed to the
  wrong place.
- **Python tooling: uv + hatchling.** Fast, lockfile committed (`api/uv.lock`). Python 3.12+.
- **Windows dev:** `make` and Docker are not installed on the dev machine, so the `Makefile` and
  `docker-compose.yml` are provided but unverified there.
- **Next.js pinned to 15 (App Router), Tailwind v4,** per the brief.
- **Commits** are authored by the repo owner only, short plain messages, no tool attribution trailers.

## FIRMS API facts (checked against the live API, not the docs)

- **Day range is 1-5, not 1-10.** A 10-day request returns HTTP 400 `Invalid day range. Expects [1..5].`
  Chunks are therefore 5 days, on a fixed grid anchored at 2000-01-01 so cache keys are stable.
- **A request costs 2 transactions per day of range, whatever the area or row count.** Measured by
  reading the key-status counter around single calls: a 5-day request costs 10 (Punjab in peak burning
  with 14,000 rows, a quiet week with 3 rows, a 30x12 degree Canada box, a 0.5 degree box: all 10) and a
  1-day request costs 2. Limit is 5,000 per 10 minutes as a sliding window, so about 500 five-day
  requests per window. An earlier note here said billing followed row counts; that was wrong.
  Consequences: large bboxes are free, so we request one bbox per 5-day chunk, and a full six-region
  prefetch (about 11,000 requests, 110,000 transactions) is roughly 3.7 hours of budget. The client
  polls the key-status endpoint and pauses before the window runs out instead of guessing.
- **When the budget is spent FIRMS answers in three different ways:** HTTP 200 `MAP_KEY is invalid or
  your have exceeded your transaction/time limit`, HTTP 400 `Exceeding allowed transaction limit.`, and
  HTTP 200 `Invalid MAP_KEY.` The last one looks like an auth failure, so the client checks the status
  endpoint before deciding the key is bad.
- **The MAP_KEY is in the URL path.** httpx logs URLs at INFO, so its logger is silenced and all
  errors are redacted before being raised.
- **Errors can arrive as HTTP 200 with a text body** (`Invalid MAP_KEY.`, `MAP_KEY is invalid or your
  have exceeded your transaction/time limit`). The client treats the first as fatal and the second
  as retryable.
- **SP data ends before NRT begins** (at the time of writing MODIS_SP to 2026-07-31, VIIRS SNPP SP to
  2026-06-30). Date ranges come from `/api/data_availability`, never hard-coded. A chunk cut short at
  the newest available date is cached as a partial file and re-fetched next time.
- **VIIRS platform** is taken from the source id (e.g. `VIIRS_SNPP_SP` -> SNPP), not from the raw
  `satellite` column, whose codes for the other satellites were not verified.
- **Sample data check:** over Punjab/Haryana for 2019-10-28 to 2019-11-06, VIIRS returned about 4x as
  many detections as MODIS, and median local overpass hours came out Terra ~10.8, Aqua ~13.2,
  SNPP ~13.4, consistent with the brief.

## Scope choices

- **Canada boreal** is bounded to BC/Alberta/Saskatchewan/NWT south of 61N rather than all of Canada,
  to keep request volume sane.
- **Prefetch default sources are MODIS_SP and VIIRS_SNPP_SP** (the sensors being harmonised). NOAA-20
  is opt-in via `--sources`. A full six-region prefetch is about 11,000 requests.

## Science choices backed by real data

- **Coincident overpass window is 30 minutes, not the 10 in the brief.** On Punjab/Haryana
  2019-10-28 to 2019-11-06, for each Aqua-MODIS pixel the nearest SNPP-VIIRS pixel (within 5 km) came
  a median of about 16 minutes later (IQR roughly -10 to +28). Only 19% of pairs fall within 10 min,
  54% within 30 and 64% within 60. The window is a parameter; 30 min is the default.
- **Co-observation proxy.** FIRMS gives no swath masks, so a detection is only judged by the other
  sensor if that sensor has a detection within 25 km and the time window. Detections without one are
  reported as not co-observed and excluded from agreement rates.
- **Persistent heat-source mask needs a long record.** On a 10-day window nearly every burning field
  looks persistent (it burned on 2 of 10 days) and the mask removed 86% of detections. The mask is only
  built from at least 365 distinct days.
- **Normalisation works on weekly totals, in log1p space,** and is applied to daily data by spreading
  the mapped weekly total over days in proportion to MODIS's own daily pattern.
