# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Where things stand (updated 2026-08-27)

The legacy Denmark-only pipeline (`agent/`, `app/schemas.py`, `app/services/`, `app/routes/planner.py`, `static/`, `/api/agent`, `/analyze`) has been **deleted**. The multi-country recommendation engine + React frontend (see Architecture below) is now the only pipeline. This repo also moved from a OneDrive-synced path to a plain local directory — active development inside a cloud-sync folder was causing the sync client to race against rapid file writes and occasionally revert uncommitted edits.

Current state:
- `.venv\Scripts\python.exe -m pytest -v` → **172/172 passing.**
- `frontend/` builds cleanly (`npm run build`) and `app/main.py` serves the build output at `/` (falls back to a JSON "not built yet" message if `frontend/dist` doesn't exist — see Architecture).
- Render deploy is now Docker-based single-origin (see Deployment) — `render.yaml` builds `Dockerfile`, which compiles the frontend in a Node stage and copies `frontend/dist` into the Python runtime stage, so `render.yaml` no longer needs its own buildCommand/PYTHON_VERSION.
- Not yet done: `railway.toml`/`Procfile` still only run the Python backend (untouched — Render is the deploy target in use); the Pydantic v2 `class Config` deprecation in `app/models/user_profile.py` is unfixed but harmless.
- In progress: a "Holdings Review" feature (grounded, LLM-narrated analysis of existing mutual fund holdings vs. a computed benchmark) — plan at `~/.claude/plans/deep-rolling-lamport.md`. Phase A landed and is verified end-to-end against live data: CAS parser now captures mutual fund ISIN (was silently discarded before), and `app/modules/amfi_nav_client.py`/`mfapi_client.py`/`market_data_client.py` resolve an ISIN to real AMFI scheme data + mfapi.in trailing returns — confirmed working from Render's actual network via a (since-removed) temporary diagnostic endpoint, including two real bugs it caught before Phase B could build on top of them: AMFI's `NAVAll.txt` redirects `www.` → `portal.` (httpx doesn't follow redirects by default) and its live column layout (`Scheme Code;ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;NAV;Date`) differs from what initial research assumed. Not yet wired into any endpoint — that's Phase B.
- **2026-08-27 session: knowledge-base maintenance + closed a real architecture gap.** Started from "how do we keep the YAML tax data updated" and ended up finding that most of `app/knowledge_base/` was never actually read by the app at all — only `residency_rules` was loaded; `tax_engine.py` and `eligibility_checker.py` each hardcoded their own separate copy of tax rates/eligibility rules in Python, contradicting this doc's own "edit YAML, not code" framing. Two real, live bugs were found and fixed as a direct result: NRI FD interest TDS was hardcoded at 10% (the *resident* rate) instead of 30% (the actual NRI rate), and Sovereign Gold Bonds were hardcoded `eligible: True` for NRIs when the YAML (correctly) says NRIs can't subscribe to new SGB issuances. Both modules are now genuinely YAML-driven for the parts that were safe to wire (equity/FD/dividend/SGB tax rates; instrument eligibility, country restrictions, repatriation limits) — see Architecture below for what's still deliberately hardcoded and why. Also added: `source_url`/`monitor_url` metadata on every knowledge_base file, `scripts/check_kb_freshness.py` (24-month calendar backstop), `scripts/check_kb_source_changes.py` (monthly fingerprint-based change detection — only alerts when a source page actually changed, not on a fixed schedule), and a monthly GitHub Action wiring both into a single tracking issue. India's own tax site (`incometaxindia.gov.in`) blocks scripted requests with a 403; worked around via a `monitor_url` pointing at `incometax.gov.in`'s news feed instead. Australia/Canada/Germany's tax sites are still unmonitored (same kind of block, no workaround found yet).

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
- **`app/knowledge_base/`** — YAML rule tables per country/domain (`india/nri_taxation.yaml`, `india/account_types.yaml`, `india/product_rules.yaml`, `india/dtaa_provisions.yaml`, `india/fema_rules.yaml`, plus one `tax_rules.yaml` each for `denmark`, `uae`, `uk`, `usa`, `singapore`, `canada`, `germany`, `australia`, and `denmark/india_dtaa.yaml`). Every file carries `version`/`last_updated`/`source`/`source_url` metadata (and `monitor_url` on the 3 India files whose `source_url` blocks scripted fetches). Loaded via `app/utils/kb_loader.py`. **Not everything here is actually consumed yet** — `residency_engine.py` reads `residency_rules`; `tax_engine.py` reads `tds_rates`/`capital_gains` for equity/FD/dividend/SGB only (debt fund/real estate/gold LTCG are deliberately still hardcoded pending unresolved legal questions — see the 2026-08-27 session note above); `eligibility_checker.py` reads `product_rules.yaml`/`fema_rules.yaml` for instrument eligibility and repatriation limits (FATCA/FBAR/T1135 compliance and FX exchange rates are deliberately still hardcoded — no matching YAML model, and FX rates are volatile market data a YAML file wouldn't fix anyway). `allocation_engine.py` and `confidence_scorer.py` were never meant to be YAML-driven — they encode this app's own product judgment (age/goal/horizon adjustments, confidence weights), not an external authority's facts, so there's no corresponding YAML for them.
- **`scripts/`** — knowledge-base maintenance tooling, not part of the request path: `check_kb_freshness.py` (flags any file whose `last_updated` is stale or missing — a 24-month calendar backstop) and `check_kb_source_changes.py` (fetches each file's `monitor_url`/`source_url` monthly and fingerprints the visible text, only flagging a file when its source plausibly changed; state persists in `scripts/kb_source_state.json`, committed back by the workflow each run). Wired into `.github/workflows/kb-freshness-check.yml`, which runs both monthly and opens a single GitHub issue if either flags something. Neither script edits YAML data itself — a human still reads the source and decides what, if anything, changes, per the same principle as `explanation_builder.py` never deciding a fund verdict (see `HOW_IT_WORKS.md` §8).
- **`app/modules/`** — the engine, split by concern: `residency_engine.py` (tax residency determination), `eligibility_checker.py` (what an NRI from a given country can actually invest in), `tax_engine.py` (India + foreign-country tax treatment, DTAA), `allocation_engine.py` (risk/horizon → asset allocation), `instrument_catalog.py` (the instrument list itself), `confidence_scorer.py`, `explanation_builder.py`, orchestrated by `recommendation_engine.py`.
- **`app/utils/`** — `kb_loader.py` (YAML loading/caching), `currency_converter.py`, `disclaimer_generator.py`.
- **`app/api/cas_parser.py`** — parses uploaded CAS (Consolidated Account Statement) PDFs via `pdfplumber`: mutual funds, stocks, and (added 2026-08-26) a life insurance summary from the NSDL e-Insurance Account (eIA) section, feeding `UserProfile.financial.insurance_sum_assured_inr` — previously an unused field, now wired into `explanation_builder.py`'s key insights (flags cover below ~10x annual income) and action steps (flags no cover at all). Frontend client is `frontend/src/api/cas.js`.
- **`app/api/gold_price.py`** — live gold price lookup (uses `GOLD_API_KEY` from `app/config.py`, via `httpx`, falls back to a hardcoded price if unset or the upstream call fails); frontend client is `frontend/src/api/gold.js`.

**`recommendation_engine.py`'s `_flatten_profile`** adapts the nested `UserProfile` into a flat `SimpleNamespace` that the allocation/eligibility/confidence/explanation modules expect. Watch for the enum trap here: several `UserProfile` fields (`IndianResidentialStatus`, `AccountType`, `InvestmentGoal`) are `str, Enum` mixins, and on this Python version `str(some_member)` renders as `"ClassName.MEMBER"` rather than the member's value — always use `.value` when flattening an enum field into a plain string, never `str(...)`. Three bugs from exactly this mistake were fixed on 2026-08-25 (see `tests/test_recommendation_engine.py`'s regression tests for the specifics).

**`app/main.py`** mounts the API routers first (`health`, `recommendations`, `cas_parser`, `gold_price`, all under `/api` except health), then mounts `StaticFiles(directory=settings.STATIC_DIR, html=True)` at `/` last, so API routes always match before the frontend catch-all. `STATIC_DIR` defaults to `frontend/dist` (override via env var). If `frontend/dist/index.html` doesn't exist (frontend not built yet), `/` returns a JSON message instead of erroring.

Config (`app/config.py`) is env-var driven with a `functools.lru_cache`'d singleton (`get_settings()`).

## Testing conventions

Module-level tests (`test_allocation_engine.py`, `test_tax_engine.py`, `test_eligibility_checker.py`, `test_confidence_scorer.py`, `test_explanation_builder.py`, `test_instrument_catalog.py`, `test_currency_converter.py`, `test_disclaimer_generator.py`) call the `app/modules/*`/`app/utils/*` classes directly, constructing the flat `SimpleNamespace` profile shape those modules actually receive at runtime (not the nested `UserProfile`) — match that pattern for new module tests. `test_recommendation_engine.py` exercises `RecommendationEngine.generate()` end-to-end with a real nested `UserProfile`, asserting on the full `RecommendationResponse` shape and values. `test_recommend_api.py`, `test_cas_parser.py`, `test_gold_price_api.py` hit the FastAPI app via `TestClient` for the corresponding endpoints. `test_kb_loader.py` and `test_residency_engine.py` cover the knowledge-base loader and residency determination.

Known dead code worth knowing about if you touch routing: `app/api/recommendations.py` defines `GET /health` (mounted at `/api/health`), but `app/routes/health.py` registers the same literal path first in `app/main.py`, so Starlette's first-match routing always serves the `app/routes/health.py` version — the one in `recommendations.py` is unreachable. `tests/test_recommend_api.py` has a test documenting this.

## Deployment

**Render** (`render.yaml`) is the active deploy target: `runtime: docker`, building the root `Dockerfile`. That Dockerfile is a two-stage build — a `node:20-alpine` stage runs `npm ci && npm run build` in `frontend/`, then a `python:3.12.8-slim` stage installs `requirements.txt` and copies the Node stage's `frontend/dist` in alongside `app/`/`main.py`. Single origin: FastAPI serves the built frontend at `/` and the API under `/api`, exactly as in local dev after `npm run build`. The container's `CMD` reads Render's injected `$PORT` (`sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}'`); `.dockerignore` keeps `.venv`/`node_modules`/`.git`/tests out of the build context.

**Railway** (`railway.toml`) and **`Procfile`** (Heroku-style) are unchanged — still native Python-only configs (`uvicorn main:app --host 0.0.0.0 --port $PORT`), so as configured they'd serve the "frontend build not found" JSON fallback rather than the app. If either of these becomes the actual deploy target, point them at the same `Dockerfile` (Railway supports a Docker builder; Heroku-style platforms would need a container-based deploy instead of `Procfile`) rather than re-deriving a native buildCommand — Render's Python runtime doesn't ship Node either, which is why this repo moved to Docker instead of patching buildCommand.

`CORS_ORIGINS` (comma-separated, defaults to `*`) only matters if the frontend is ever deployed separately (e.g. Vercel/Netlify) instead of single-origin — not needed for the current Render setup.
