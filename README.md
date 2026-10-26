# EMBERLINE

One consistent record of fire, from two sensors.

Harmonized MODIS + VIIRS fire calendar, built for NASA Space Apps 2026
(challenge: Harmonization of MODIS and VIIRS Hot Spots). Work in progress.

## Quickstart

```bash
cp .env.example .env        # then put your FIRMS key in FIRMS_MAP_KEY
cd api && uv sync
uv run pytest               # tests need no key and no network
uv run uvicorn emberline.main:app --reload --port 8000
```

```bash
cd web && npm install && npm run dev      # open http://localhost:3000/explore
```

## Keys

Only one key is needed: a free NASA FIRMS MAP_KEY from
https://firms.modaps.eosdis.nasa.gov/api/map_key/ . It is read by the API server only and is never
sent to the browser. NASA GIBS map imagery needs no key.

## Data

```bash
cd api
uv run python ../scripts/prefetch.py --dry-run                     # see how many requests a run needs
uv run python ../scripts/prefetch.py --regions punjab-haryana --start 2019-10-01 --end 2019-11-30
uv run python ../scripts/make_synthetic.py                         # SYNTHETIC data for dev/tests only
```

Downloaded data lives in `data/` (git-ignored). Synthetic data is always labelled and is never to be
shown as real. FIRMS API quirks found while building this are listed in `docs/DECISIONS.md`.

## Status

Phases 1 to 6 (scaffold, data layer, science core, API, Explore UI, landing/atlas/method/about) are done;
the polish pass and the submission kit are next. See
`CHANGELOG.md`. A real-data validation report for Punjab/Haryana is in `docs/validation/`.

API docs: run the API and open `/api/docs`.
