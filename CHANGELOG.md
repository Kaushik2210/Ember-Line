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
