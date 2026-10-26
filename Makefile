.PHONY: dev api web prefetch test lint

api:
	cd api && uv run uvicorn emberline.main:app --reload --port 8000

web:
	cd web && npm run dev

dev:
	$(MAKE) -j2 api web

prefetch:
	cd api && uv run python ../scripts/prefetch.py

test:
	cd api && uv run pytest
	cd web && npm test

lint:
	cd api && uv run ruff check . && uv run mypy emberline
	cd web && npm run lint && npm run typecheck
