# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Where things stand (updated 2026-08-25)

**Nothing described below the legacy pipeline is committed yet.** Last commit is `76bfb00` (2026-08-01). Everything since then — a new React frontend, a whole second recommendation engine, a 9-country YAML knowledge base — is sitting uncommitted in the working tree (`git status` shows it as modified/untracked files). Test evidence (`api_response.txt`) shows the new `/api/recommend` endpoint was working end-to-end as of 2026-08-09, so the gap between "last commit" and "last working state" is ~3 weeks of work not yet checked in.

Current state when picking this back up:
- `.venv\Scripts\python.exe -m pytest -v` → **36/36 passing.**
- The **old pipeline still works and is untouched in behavior** (`agent/agent_logic.py`, `/api/agent`, `static/index.html`) — it grew by ~520 lines to support new multi-country fields but wasn't replaced.
- The **new pipeline** (`/api/recommend`, `frontend/`) is a parallel, much larger system — see Architecture below — and has no dedicated tests yet for its core modules (`recommendation_engine`, `tax_engine`, `allocation_engine`, `eligibility_checker`, `confidence_scorer`) or for the `cas_parser`/`gold_price` endpoints. Only `test_kb_loader.py` and `test_residency_engine.py` exist for the new code.
- Repo root has leftover manual-test scratch files not meant to be committed: `api_error.txt`, `api_response.txt`, `body.json` (curl output from testing `/api/recommend`). Clean these up or gitignore them before committing.
- `frontend/` has its own `.gitignore` (covers `node_modules`, `dist`), so it's safe to `git add frontend/` without pulling in installed packages.

**Likely next steps:** decide whether the two pipelines (legacy Denmark-only `/api/agent` + new multi-country `/api/recommend`) are meant to converge or whether the new one is a full replacement; write tests for the new `app/modules/*` engines; commit the accumulated work (probably as more than one commit, given the scope); decide the new frontend's deploy story (no Vercel/static config exists for it yet).

## What this is

A FastAPI backend that produces tax/investment planning output for NRIs (Non-Resident Indians) with Indian savings/investments. There are **two parallel systems** in this repo right now:

1. **Legacy pipeline** — Denmark-specific, deterministic, no LLM calls, no external I/O. Frontend is a static HTML page (`static/index.html`, vanilla JS) served directly by FastAPI.
2. **New pipeline** — multi-country (India, Denmark, UAE, UK, USA, Singapore, Canada, Germany, Australia), rules-driven off a YAML knowledge base, served to a proper React/Vite wizard frontend (`frontend/`). Also includes CAS (Consolidated Account Statement) PDF parsing and a live gold-price lookup.

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
.venv\Scripts\python.exe -m pytest tests/test_agent_logic.py -v
.venv\Scripts\python.exe -m pytest tests/test_api.py::test_planner_api_returns_200_for_valid_sample -v

# Frontend (new React/Vite wizard) — from frontend/
npm install
npm run dev       # Vite dev server; talks to backend via VITE_API_BASE_URL (defaults to http://127.0.0.1:8000)
npm run build
npm run lint       # oxlint
```

Open http://127.0.0.1:8000 for the legacy static UI once the backend dev server is running. The new React frontend runs separately via Vite's own dev server and calls the backend over HTTP (CORS is currently `*` by default — see `app/config.py`).

In Cursor/VS Code: `Ctrl+Shift+B` (or Run Task → "Run Tests"/"Run Dev Server") uses the tasks in `.vscode/tasks.json`, which call the same `.venv` python directly.

There is no Python linter configured (no ruff/flake8 config). The frontend has `oxlint`.

## Architecture

### Legacy pipeline (Denmark-only)

Request flow: `static/index.html` (vanilla JS `fetch`) → `POST /api/agent` (or `/analyze`, a compatibility alias with identical behavior) → `app/routes/planner.py` → three sequential transforms → JSON response rendered back into a `<pre>` block as plain text.

1. **`app/schemas.py`** (`PlannerInput`) — validates the raw frontend payload. All fields are optional with defaults; `model_to_actual_dict` (only fields the client actually sent) and `model_to_normalized_dict` (full payload with defaults filled in) are both produced and both flow downstream — don't collapse these into one, tests and the response formatter depend on seeing both. Now also carries multi-country fields (`tax_residency_country`, `tax_residency_currency`, `exchange_rate_to_inr`) and additional holding types (mutual funds, stocks, property, repatriation) added alongside the new pipeline's needs.
2. **`app/services/input_adapter.py`** (`adapt_planner_inputs`) — translates frontend-shaped field names (e.g. `india_principal_inr`, `has_nro_account`, `tax_resident_denmark`) into the internal vocabulary `agent_logic.py` expects (e.g. `india_amount_in_inr`, `india_account_type`, `dk_residency`). This is the seam to edit if you add a new frontend field that needs to reach the agent — add the mapping here rather than changing `agent_logic.py`'s expected keys.
3. **`agent/agent_logic.py`** (`analyze_tax`) — the actual planning engine, pure functions, no I/O. Key sub-steps: `calculate_liquid_reserve` (emergency fund sizing, falls back to percentage-of-savings rules if no monthly-expenses figure given) → `build_investment_allocation` (risk profile × horizon → percentage allocation table) → `build_denmark_tax_actions` / `build_india_tax_notes` (account-type-aware and allocation-aware compliance notes, driven by string-matching on `investment_type`/account-type text — see below) → `build_follow_up_questions` → `build_display_text` (assembles the final markdown report). Everything is returned as one structured dict with `display_text` embedded.

Then `app/services/response.py` (`normalize_response`) wraps the agent's structured result together with the actual/normalized inputs into the final `{output, result, structured_result}` shape the frontend and tests expect — `output` is a human-readable text rendering built by `app/services/formatting.py` (`build_readable_summary`), `result`/`structured_result` carry the same dict for structured consumers.

**Important coupling to preserve:** `build_denmark_tax_actions` and `build_india_tax_notes` both branch on `investment_type` strings from the allocation list (e.g. `"Fixed Deposits" in inv_type`, `"Equity Mutual Funds" in inv_type`). If you rename or add investment types in `build_investment_allocation`, update the matching conditionals in both functions or those branches will silently stop firing.

### New pipeline (multi-country)

Request flow: `frontend/` React wizard (`Step1Residency` → `Step2Assets` → `Step3Goals` → `Step4Review` → `StepResults`, state managed by `hooks/useWizardForm.js`) → `frontend/src/api/planner.js` (`runPlanner`, posts to `${VITE_API_BASE_URL}/api/recommend`) → `app/api/recommendations.py` → `app/modules/recommendation_engine.py`.

- **`app/models/user_profile.py`** (`UserProfile`) — the Pydantic request model (personal/financial/residency/investment sections); **`app/models/recommendation.py`** (`RecommendationResponse`) — the response shape (allocation, instrument list, tax_summary, compliance, projections, key_insights, action_steps, disclaimers, confidence_overall).
- **`app/knowledge_base/`** — YAML rule tables per country/domain (`india/nri_taxation.yaml`, `india/account_types.yaml`, `india/product_rules.yaml`, `india/dtaa_provisions.yaml`, `india/fema_rules.yaml`, plus one `tax_rules.yaml` each for `denmark`, `uae`, `uk`, `usa`, `singapore`, `canada`, `germany`, `australia`, and `denmark/india_dtaa.yaml`). Loaded via `app/utils/kb_loader.py`.
- **`app/modules/`** — the engine, split by concern: `residency_engine.py` (tax residency determination), `eligibility_checker.py` (what an NRI from a given country can actually invest in), `tax_engine.py` (India + foreign-country tax treatment, DTAA), `allocation_engine.py` (risk/horizon → asset allocation), `instrument_catalog.py` (the instrument list itself), `confidence_scorer.py`, `explanation_builder.py`, orchestrated by `recommendation_engine.py`.
- **`app/utils/`** — `kb_loader.py` (YAML loading/caching), `currency_converter.py`, `disclaimer_generator.py`.
- **`app/api/cas_parser.py`** — parses uploaded CAS (Consolidated Account Statement) PDFs via `pdfplumber`; frontend client is `frontend/src/api/cas.js`.
- **`app/api/gold_price.py`** — live gold price lookup (uses `GOLD_API_KEY` from `app/config.py`, via `httpx`); frontend client is `frontend/src/api/gold.js`.

Both pipelines are mounted simultaneously in `app/main.py`: `planner_router` (legacy, no prefix) alongside `recommendations_router`, `cas_router`, `gold_router` (all under `/api`).

Config (`app/config.py`) is env-var driven with a `functools.lru_cache`'d singleton (`get_settings()`); errors from the planner routes are caught and returned as 500 JSON with `traceback` only when `DEBUG=true`. New env var: `GOLD_API_KEY`.

## Testing conventions

`tests/test_api.py` hits the FastAPI app via `TestClient` and asserts response *shape* (`output` present and non-empty, `structured_result` or `result` present) rather than exact content — it's deliberately parametrized with edge-case payloads (empty body, nulls, zero amounts, unknown risk profile) to prove the pipeline never 500s on missing/invalid optional input. `tests/test_agent_logic.py` tests the pure functions directly with exact expected numbers (e.g. allocation percentages sum to 100, `investable_amount` arithmetic). When adding a field, prefer extending the parametrized "does not crash" cases in `test_api.py` over adding a new near-duplicate test.

`tests/test_kb_loader.py` and `tests/test_residency_engine.py` cover the start of the new pipeline's test surface — the bulk of `app/modules/` (recommendation/tax/allocation/eligibility/confidence engines) and the `cas_parser`/`gold_price` endpoints have no dedicated tests yet.

## Deployment

Backend-only deploy configs exist for Render (`render.yaml`) and Railway (`railway.toml`), both running `uvicorn main:app --host 0.0.0.0 --port $PORT`; `Procfile` covers Heroku-style platforms. `STATIC_DIR` env var controls where `app/main.py` looks for `index.html` to serve at `/`. There is no Vercel/frontend deploy config for the new `frontend/` React app yet — if it's deployed separately, `CORS_ORIGINS` (comma-separated, defaults to `*`) will need to be scoped to the real frontend origin.
