# Repository Guidelines

## Project Structure & Module Organization
- Source code lives in `src/pythreads/` (e.g., `api.py`, `threads.py`, `credentials.py`, `configuration.py`). Public imports resolve from the `pythreads` package.
- Tests are under `tests/` and named `test_*.py`. Networked smoke tests are marked with `@pytest.mark.smoke`.
- Documentation uses Sphinx in `docs/` and builds to `docs/build/html`.
- Example environment variables live in `.env.template`.

## Build, Test, and Development Commands
- Tooling: use `uv` (fast package manager). First time: `uv sync --dev`.
- Lint and types: `uv run ruff check --fix .` and `uv run pyright .`.
- Unit tests (no network): `CI=1 uv run pytest -m "not smoke"`.
- Smoke tests (real API): `uv run pytest -m "smoke"` (requires `THREADS_SMOKE_TEST_USER_ID` and `THREADS_SMOKE_TEST_TOKEN`).
- Coverage: `uv run pytest -m "not smoke" --cov=src/pythreads` then `uv run coverage html`.
- Docs: `uv run sphinx-build -b html docs/source docs/build/html`.

## Coding Style & Naming Conventions
- Python 3.8+ with type hints; use `dataclasses` for value objects and `Enum/StrEnum` for constants where appropriate.
- Indentation is 4 spaces. Follow PEP 8: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Run ruff and pyright locally before committing (see commands above).

## Testing Guidelines
- Framework: `pytest` with markers configured in `pyproject.toml`. Default test runs exclude `smoke`.
- Name tests `tests/test_*.py`. Prefer small, isolated tests; avoid network except in `@pytest.mark.smoke`.
- Aim to maintain high coverage (~90%+). Add tests alongside new features and bug fixes.
- For smoke tests, see `tests/server.py` and configure env from `.env.template`.

## Commit & Pull Request Guidelines
- Commits: short, imperative subject; optional scope prefix (e.g., `api:`, `pip:`). Add a body explaining the why when non-trivial.
- PRs: include a clear description, linked issues, and notes on tests/docs. Update docs when changing public APIs. CI must pass (lint + tests).

## Security & Configuration Tips
- Do not commit real tokens, certs, or keys. Use `.env.template` as a reference and local env vars for secrets.
- Local OAuth requires SSL: set `THREADS_SSL_CERT_FILEPATH` and `THREADS_SSL_KEY_FILEPATH` for flows used by `threads.py`.

## Agent-Specific Instructions
- Keep changes minimal and targeted; avoid unrelated refactors.
- If you change API signatures or behavior, update tests and docs in the same PR.
