# Decisions

- **Own git repo inside the project folder.** The folder sits under the user's home directory, which is
  itself a git repo. EMBERLINE has its own repo (`origin` = Ember-Line) so nothing is pushed to the wrong place.
- **Python tooling: uv + hatchling.** Fast, lockfile committed (`api/uv.lock`). Python 3.12+.
- **Windows dev:** `make` and Docker are not installed on the dev machine, so the `Makefile` and
  `docker-compose.yml` are provided but unverified there.
- **Next.js pinned to 15 (App Router), Tailwind v4,** per the brief.
- **Commits** are authored by the repo owner only, short plain messages, no tool attribution trailers.
