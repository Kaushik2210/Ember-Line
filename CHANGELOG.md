# Changelog

## Phase 1: scaffold
- FastAPI skeleton with `/api/health`, settings from env, pytest + ruff set up.
- Next.js 15 app (Tailwind v4, TypeScript strict) with design tokens and a small UI kit.
- Makefile, docker-compose, Dockerfiles, design and decision docs.

## Phase 2: data layer
- FIRMS async client (retries, backoff, rate limiter, key redaction), availability and key status.
- Common MODIS/VIIRS schema with local solar time; 5-day date chunking on a fixed grid.
- Parquet cache with atomic writes and partial-chunk handling; DuckDB store with tile de-dupe.
- Resumable ingest, `scripts/prefetch.py` (dry run), SYNTHETIC generator and `scripts/make_synthetic.py`.
- Found and handled live API limits: day range 1-5, 2 transactions per requested day.

## Phase 3: science core
- Quality policy (MODIS confidence, VIIRS classes, fire type, persistent heat-source mask).
- Common grid (regular or H3) with det_count, active_1km and frp_sum_mw per cell and local day.
- Aqua-MODIS vs SNPP-VIIRS coincident overpass matching with a co-observation proxy; 30 min window
  chosen from measured offsets.
- Normalisation: Huber, Theil-Sen, seasonal quantile mapping and isotonic, with leave-one-year-out
  validation and cross-conformal intervals; daily harmonisation back to 2000; Terra-only model for
  the years before Aqua.
- Seasonality (climatology, per-season markers, STL) and anomalies (leave-one-year-out robust z,
  sustained events, season ranking), plus NASA-sourced data-quality annotations.
- Real-data validation report for Punjab/Haryana in `docs/validation/`.

## Phase 4: API
- FastAPI endpoints: analyze (jobs with SSE progress, idempotent, results cached on disk), result,
  hotspots (capped at 50k, aggregated above), availability, regions, export (CSV, GeoJSON, methods card).
- Guardrails (area, period, GeoJSON size), live fetch for uncached areas with a request cap, CORS
  locked to the web origin.

## Phase 5: Explore UI
- `/explore` workspace: left rail (region presets, search, draw a box, upload GeoJSON; period; sensors;
  quality policy; grid; model), run panel with live stage names, header with share, export and theme.
- Map: GIBS true-colour imagery, deck.gl hotspots from typed arrays, MODIS | VIIRS compare slider,
  overlay mode, time scrubber with play, click-for-details, box drawing, PNG export.
- Analytics dock: harmonized calendar (canvas, raw MODIS / raw VIIRS / harmonized), seasonality
  (ribbons, selected year, per-season markers, STL), unusual periods, sensor agreement (held-out
  before/after scatter, overpass table) and data quality (platform timeline, sourced events).
- "Why they differ" drawer with explanations tied to the run's own numbers; provenance line with the
  NASA acknowledgment; CSV, GeoJSON and methods-card export; PNG on every chart.
- All state that defines a view (region, period, options, tab, day, job) lives in the URL.
- API additions found while using it: weekly out-of-fold predictions in the payload, live fetch that
  extends a cached tile and tolerates small gaps, a "waiting for NASA's limit" stage.
