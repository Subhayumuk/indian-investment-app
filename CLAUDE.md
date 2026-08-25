# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Where things stand (updated 2026-08-25)

The legacy Denmark-only pipeline (`agent/`, `app/schemas.py`, `app/services/`, `app/routes/planner.py`, `static/`, `/api/agent`, `/analyze`) has been **deleted**. The multi-country recommendation engine + React frontend (see Architecture below) is now the only pipeline. This repo also moved from a OneDrive-synced path to a plain local directory — active development inside a cloud-sync folder was causing the sync client to race against rapid file writes and occasionally revert uncommitted edits.

Current state:
- `.venv\Scripts\python.exe -m pytest -v` → **126/126 passing.**
- `frontend/` builds cleanly (`npm run build`) and `app/main.py` serves the build output at `/` (falls back to a JSON "not built yet" message if `frontend/dist` doesn't exist — see Architecture).
- Not yet done: a real deploy story for the frontend build (no Vercel/static config exists; `render.yaml`/`railway.toml`/`Procfile` only run the Python backend — see Deployment); the Pydantic v2 `class Config` deprecation in `app/models/user_profile.py` is unfixed but harmless.

## What this is

A FastAPI backend + React (Vite) frontend that produces a multi-country tax/investment planning recommendation for NRIs (Non-Resident Indians) with Indian savings/investments — covering India plus 8 residence countries (Denmark, UAE, UK, USA, Singapore, Canada, Germany, Australia). Deterministic and rules-driven off a YAML knowledge base; no LLM calls anywhere in the backend.

## Commands

Run everything through the venv interpreter directly rather than assuming an activated shell — this matches what the repo's own scripts and VS Code tasks do.

```powershell
# Backend — install deps (creates .venv if missing)
.\run_dev.bat          # runs the dev server, creating venv first if needed
.\run_tests.bat        # runs the test suite, creating venv first if needed

# Manual equivalents
.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
.venv\Scripts\python.exe -m pytest -v

# Single test file / test
.venv\Scripts\python.exe -m pytest tests/test_recommendation_engine.py -v
.venv\Scripts\python.exe -m pytest tests/test_recommend_api.py::test_recommend_returns_200_for_valid_payload -v

# Frontend (React/Vite wizard) — from frontend/
npm install
npm run dev       # Vite dev server on :5173; talks to backend via VITE_API_BASE_URL (defaults to http://127.0.0.1:8000)
npm run build      # outputs frontend/dist, which app/main.py serves at "/"
npm run lint       # oxlint
```

For local development, run the backend (`run_dev.bat`) and the frontend dev server (`npm run dev` in `frontend/`) side by side — the frontend talks to the backend over HTTP via `VITE_API_BASE_URL`, CORS is `*` by default. To see the production single-origin setup, run `npm run build` first and then just start the backend: `http://127.0.0.1:8000/` will serve the built app directly.

In Cursor/VS Code: `Ctrl+Shift+B` (or Run Task → "Run Tests"/"Run Dev Server") uses the tasks in `.vscode/tasks.json`, which call the same `.venv` python directly.

There is no Python linter configured (no ruff/flake8 config). The frontend has `oxlint`.

## Architecture

Request flow: `frontend/` React wizard (`Step1Residency` → `Step2Assets` → `Step3Goals` → `Step4Review` → `StepResults`, state managed by `hooks/useWizardForm.js`) → `frontend/src/api/planner.js` (`runPlanner`, posts to `${VITE_API_BASE_URL}/api/recommend`) → `app/api/recommendations.py` → `app/modules/recommendation_engine.py`.

- **`app/models/user_profile.py`** (`UserProfile`) — the Pydantic request model (personal/financial/residency/investment sections); **`app/models/recommendation.py`** (`RecommendationResponse`) — the response shape (allocation, instrument list, tax_summary, compliance, projections, key_insights, action_steps, disclaimers, confidence_overall).
- **`app/knowledge_base/`** — YAML rule tables per country/domain (`india/nri_taxation.yaml`, `india/account_types.yaml`, `india/product_rules.yaml`, `india/dtaa_provisions.yaml`, `india/fema_rules.yaml`, plus one `tax_rules.yaml` each for `denmark`, `uae`, `uk`, `usa`, `singapore`, `canada`, `germany`, `australia`, and `denmark/india_dtaa.yaml`). Loaded via `app/utils/kb_loader.py`.
- **`app/modules/`** — the engine, split by concern: `residency_engine.py` (tax residency determination), `eligibility_checker.py` (what an NRI from a given country can actually invest in), `tax_engine.py` (India + foreign-country tax treatment, DTAA), `allocation_engine.py` (risk/horizon → asset allocation), `instrument_catalog.py` (the instrument list itself), `confidence_scorer.py`, `explanation_builder.py`, orchestrated by `recommendation_engine.py`.
- **`app/utils/`** — `kb_loader.py` (YAML loading/caching), `currency_converter.py`, `disclaimer_generator.py`.
- **`app/api/cas_parser.py`** — parses uploaded CAS (Consolidated Account Statement) PDFs via `pdfplumber`; frontend client is `frontend/src/api/cas.js`.
- **`app/api/gold_price.py`** — live gold price lookup (uses `GOLD_API_KEY` from `app/config.py`, via `httpx`, falls back to a hardcoded price if unset or the upstream call fails); frontend client is `frontend/src/api/gold.js`.

**`recommendation_engine.py`'s `_flatten_profile`** adapts the nested `UserProfile` into a flat `SimpleNamespace` that the allocation/eligibility/confidence/explanation modules expect. Watch for the enum trap here: several `UserProfile` fields (`IndianResidentialStatus`, `AccountType`, `InvestmentGoal`) are `str, Enum` mixins, and on this Python version `str(some_member)` renders as `"ClassName.MEMBER"` rather than the member's value — always use `.value` when flattening an enum field into a plain string, never `str(...)`. Three bugs from exactly this mistake were fixed on 2026-08-25 (see `tests/test_recommendation_engine.py`'s regression tests for the specifics).

**`app/main.py`** mounts the API routers first (`health`, `recommendations`, `cas_parser`, `gold_price`, all under `/api` except health), then mounts `StaticFiles(directory=settings.STATIC_DIR, html=True)` at `/` last, so API routes always match before the frontend catch-all. `STATIC_DIR` defaults to `frontend/dist` (override via env var). If `frontend/dist/index.html` doesn't exist (frontend not built yet), `/` returns a JSON message instead of erroring.

Config (`app/config.py`) is env-var driven with a `functools.lru_cache`'d singleton (`get_settings()`).

## Testing conventions

Module-level tests (`test_allocation_engine.py`, `test_tax_engine.py`, `test_eligibility_checker.py`, `test_confidence_scorer.py`, `test_explanation_builder.py`, `test_instrument_catalog.py`, `test_currency_converter.py`, `test_disclaimer_generator.py`) call the `app/modules/*`/`app/utils/*` classes directly, constructing the flat `SimpleNamespace` profile shape those modules actually receive at runtime (not the nested `UserProfile`) — match that pattern for new module tests. `test_recommendation_engine.py` exercises `RecommendationEngine.generate()` end-to-end with a real nested `UserProfile`, asserting on the full `RecommendationResponse` shape and values. `test_recommend_api.py`, `test_cas_parser.py`, `test_gold_price_api.py` hit the FastAPI app via `TestClient` for the corresponding endpoints. `test_kb_loader.py` and `test_residency_engine.py` cover the knowledge-base loader and residency determination.

Known dead code worth knowing about if you touch routing: `app/api/recommendations.py` defines `GET /health` (mounted at `/api/health`), but `app/routes/health.py` registers the same literal path first in `app/main.py`, so Starlette's first-match routing always serves the `app/routes/health.py` version — the one in `recommendations.py` is unreachable. `tests/test_recommend_api.py` has a test documenting this.

## Deployment

Backend deploy configs exist for Render (`render.yaml`) and Railway (`railway.toml`), both running `uvicorn main:app --host 0.0.0.0 --port $PORT`; `Procfile` covers Heroku-style platforms — none of these currently build the frontend, so as configured they'd serve the "frontend build not found" JSON fallback rather than the app. Before deploying, either add a Node build step ahead of `uvicorn` (single-origin: FastAPI serves `frontend/dist`) or deploy `frontend/` separately (e.g. Vercel/Netlify) and scope `CORS_ORIGINS` (comma-separated, defaults to `*`) to that origin.
