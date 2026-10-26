# Contributing

Thanks for looking. Setup is in the [README](README.md).

- **Checks before a pull request:** in `api/` run `uv run ruff check .`, `uv run mypy emberline` and
  `uv run pytest`; in `web/` run `npx tsc --noEmit`, `npx eslint .` and `npx vitest run`. CI runs the same.
- **Never fabricate.** No invented statistics, citations or data. Synthetic data must stay labelled and is
  for development and tests only. Numbers shown in the app come from the API.
- **Science changes** need a test and a note in `docs/DECISIONS.md` saying what was measured and why.
- **Commits:** small, one change each, plain messages in the imperative ("fix calendar year axis").
- **Secrets:** the FIRMS key lives in `.env` only. Never commit it, data files or logs that contain URLs.
