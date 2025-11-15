# Repository Guidelines

## Project Structure & Module Organization
- Core application lives in `app/` (FastAPI app in `app/main.py`).
- HTTP APIs are under `app/api/api_v1/endpoints/` (one module per domain, e.g. `properties.py`, `bookings.py`).
- Domain models are in `app/models/`, Pydantic schemas in `app/schemas/`, shared logic in `app/services/` and `app/utils/`.
- Database and config utilities live in `app/core/`; Supabase migrations live in `supabase/migrations/`; data scripts are in `populate_data/` and `tools/`.

## Build, Test, and Development Commands
- Create env and install deps: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
- Run API locally: `python run.py` (uses `ENVIRONMENT` from `.env`) or `fastapi dev app/main.py --host 0.0.0.0 --port 8000` for hot reload.
- Start infra services: `docker-compose up -d db redis`.
- Run tests (when present): `pytest` from repo root.

## Coding Style & Naming Conventions
- Python 3.10+, FastAPI, SQLAlchemy 2.x, Pydantic v2. Use type hints everywhere.
- Follow PEP 8 with 4‑space indentation and `snake_case` for modules, functions, and variables; `PascalCase` for classes and Pydantic models.
- Place new endpoints in the appropriate `app/api/api_v1/endpoints/*.py` file and wire them via the router in `app/api/api_v1/api.py`.
- Keep business logic in `services/` rather than inside route handlers where feasible.

## Testing Guidelines
- Use `pytest` (and `pytest-asyncio` for async code). Name test files like `tests/api/test_properties.py` and test functions `test_*`.
- Prefer fast, isolated tests around services and critical endpoints; add regression tests for every bug fix.
- Aim for meaningful coverage on new or changed code (roughly 80%+ where practical).

## Commit & Pull Request Guidelines
- Write clear, imperative commit messages similar to existing history, e.g. `Add booking pricing validation` or `Update agent contact fields`.
- Keep commits and PRs focused on a single logical change set; avoid drive‑by refactors.
- For PRs, include: short summary, motivation/context, notable implementation choices, tests run (`pytest`, manual checks), and any migration or config impact.

## Security & Configuration Tips
- Never commit secrets or real credentials. Use `.env` (based on `.env.example`) and `app.core.config.settings` for configuration.
- Avoid logging sensitive PII or auth tokens; prefer IDs and high‑level context in logs.
- When adding new settings, declare them in `app/core/config.py` and document expected env vars in `README.md` or `.env.example`.

## Agent-Specific Instructions
- When using automated tools or AI assistants, keep changes minimal, localized, and consistent with the existing module layout.
- Do not introduce new dependencies or cross‑cutting refactors without an accompanying rationale in the PR description.
