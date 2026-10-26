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
- **Transactions are billed by rows returned, roughly 1 per 1,000 rows,** not per request (four test
  calls with 3k to 217k rows cost 210 transactions). Limit is 5,000 per 10 minutes. Request latency
  is 2-10 s, so the number of requests matters for wall time. We request one bbox per date chunk
  (instead of 10-degree grid tiles) to cut the request count several-fold at the same transaction cost.
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
