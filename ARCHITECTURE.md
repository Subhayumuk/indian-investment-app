# NRI Investment & Tax Planner — Architecture Document

| | |
|---|---|
| **Document type** | Architecture Overview, High-Level Design (HLD) & Solution Design |
| **System** | NRI Investment & Tax Planner (`indian-investment-app`) |
| **Version** | 1.1 |
| **Last updated** | 2026-08-27 |
| **Status** | Living document — kept in sync with `CLAUDE.md`; update on material architecture changes |
| **Audience** | Enterprise/Solution Architects, technical reviewers, future maintainers |

---

## 1. Executive Summary

This system produces deterministic, rules-based tax and investment
recommendations for Non-Resident Indians (NRIs) across nine jurisdictions
(India plus eight residence countries: Denmark, UAE, UK, USA, Singapore,
Canada, Germany, Australia). It is a two-tier web application — a React
single-page application (SPA) frontend and a Python/FastAPI backend — with
no database and no AI/LLM inference in the request path. Domain logic
(tax rates, eligibility rules, DTAA provisions) is intended to live in
version-controlled YAML data files rather than code, making the system
auditable and updatable without a code change. **As of v1.1 this is true
for most, not all, of it** — see Section 6.4 for exactly which rules are
YAML-driven today versus still hardcoded pending a legal question or
because no external authority actually governs them (e.g. this app's own
allocation/confidence heuristics).

The system is currently a single-instance deployment (Render, Docker,
free tier) with no persistence layer, no authentication, and no
multi-tenancy — appropriate for its current stage (solo-developer learning
project transitioning toward a real personal-use tool) but with clearly
identified gaps before any production/multi-user posture (Section 11).

## 2. Business Context & Problem Statement

NRIs with financial ties to India face a two-jurisdiction tax and
investment-eligibility problem: what they can legally invest in, and how
it is taxed, depends on the interaction between India's FEMA/tax rules and
their country of residence's tax code and any India-DTAA (Double Taxation
Avoidance Agreement) in force. This is normally the domain of a paid
cross-border tax advisor. This system encodes that domain knowledge as
structured rules so an individual can self-serve a first-pass plan.

**Explicit non-goal:** this is not a substitute for professional advice.
The system generates disclaimers on every response (`disclaimer_generator.py`)
and is positioned as educational/planning output only.

## 3. Scope

**In scope:**
- Tax residency determination (India + 8 supported countries)
- Investment eligibility screening per residency
- India tax computation + foreign-country tax treatment + DTAA relief
- Risk/horizon-based asset allocation and instrument recommendations
- Best-effort ingestion of an existing portfolio via CAS (Consolidated
  Account Statement) PDF upload
- Indicative live gold price lookup

**Out of scope (current version):**
- User accounts, authentication, saved sessions
- Persistence of submitted financial data
- Any jurisdiction beyond the 9 currently modeled
- Automated *application* of tax-law changes — a monthly job (Section 6.5)
  now detects when a source likely changed and opens a tracking issue, but
  a human still reads the change and edits the YAML; nothing auto-applies
  a rule correction

## 4. Stakeholders

| Stakeholder | Interest |
|---|---|
| End user (NRI individual) | Accurate, understandable, actionable plan |
| Solo developer/owner | Maintainability, learning value, low operating cost |
| Future reviewer (this document's audience) | Architectural soundness, identified risk, upgrade path |

## 5. High-Level Design (HLD)

### 5.1 System Context (C4 Level 1)

```mermaid
flowchart TB
    User((NRI User))
    System["NRI Investment & Tax Planner"]
    GoldAPI["goldapi.io\n(external gold price service)"]

    User -- "Fills wizard,\nuploads CAS PDF,\nreceives recommendation" --> System
    System -- "Live gold price request\n(optional, API-key gated)" --> GoldAPI
    GoldAPI -. "price data, or\nnothing if unavailable" .-> System
```

The system has exactly one external dependency (`goldapi.io`), and it is
non-critical: absence of an API key or a failed call falls back to a
hardcoded price (`app/api/gold_price.py`), so the core recommendation flow
has **zero hard external dependencies**.

### 5.2 Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph Client["Client (Browser)"]
        SPA["React SPA (Vite build)\nfrontend/"]
    end

    subgraph Backend["Backend Container (single Docker image)"]
        API["FastAPI application\napp/main.py"]
        Rec["Recommendation Engine\napp/modules/"]
        CAS["CAS PDF Parser\napp/api/cas_parser.py"]
        Gold["Gold Price Router\napp/api/gold_price.py"]
        KB[("Knowledge Base\napp/knowledge_base/*.yaml\n(loaded/cached at runtime)")]
    end

    SPA -- "HTTPS, same origin\n/api/*" --> API
    API --> Rec
    API --> CAS
    API --> Gold
    Rec --> KB
```

**Key point for review:** there is no database container, no cache layer,
no message queue. The "Knowledge Base" is not a database — it is static
YAML shipped inside the same Docker image, loaded into memory
(`app/utils/kb_loader.py`, `lru_cache`d). This is a deliberate simplicity
choice appropriate to the current scale (see Section 9, Scalability).

### 5.3 Key Architectural Principles

1. **Deterministic over generative.** No LLM/AI call sits in the
   recommendation path. Every output is traceable to an explicit rule in a
   YAML file or a branch in Python code — auditable and reproducible by
   design, which matters for anything tax-adjacent.
2. **Rules as data, not code — the goal, mostly reached.** Country-specific
   tax/eligibility rules are meant to live in YAML
   (`app/knowledge_base/<country>/*.yaml`), not hardcoded in Python, so a
   rule correction is a data change reviewable by a non-engineer domain
   expert. `tax_engine.py` and `eligibility_checker.py` were found on
   2026-08-27 to each hold their own separate hardcoded copy of exactly
   this kind of data instead — a real, live discrepancy this way (NRI FD
   TDS wrong at 10% instead of 30%; Sovereign Gold Bonds wrongly marked
   eligible for NRIs). Both are now wired to the YAML for the parts that
   were safe to (Section 6.4); a few pieces remain deliberately hardcoded,
   documented in the same section.
3. **Stateless request/response.** The backend holds no session state and
   persists nothing between requests (confirmed: no database, no file
   writes of user data anywhere in `app/`). Every `/api/recommend` call is
   fully self-contained.
4. **Single-origin deployment.** Frontend and backend ship as one Docker
   image, served from one origin — see Section 8.
5. **Fail-soft on non-critical paths.** Gold price lookup and CAS PDF
   parsing both degrade gracefully (hardcoded fallback; partial/failed
   parse status) rather than erroring the whole flow.

## 6. Solution Design

### 6.1 Component Design

| Component | Responsibility |
|---|---|
| `app/models/user_profile.py` (`UserProfile`) | Request contract: personal, financial, residency, investment-goal data |
| `app/models/recommendation.py` (`RecommendationResponse`) | Response contract: allocation, instruments, tax summary, compliance notes, projections, insights, action steps, disclaimers, confidence score |
| `app/modules/recommendation_engine.py` | Orchestrator; flattens the nested request into the flat shape the sub-engines expect, calls each in sequence, assembles the response |
| `app/modules/residency_engine.py` | Determines tax residency status (India + destination country) from the profile |
| `app/modules/eligibility_checker.py` | Filters which Indian investment products are legally available to this specific NRI |
| `app/modules/tax_engine.py` | Computes India-side tax, destination-country tax, and DTAA relief |
| `app/modules/allocation_engine.py` | Derives an asset allocation from stated risk tolerance and investment horizon |
| `app/modules/instrument_catalog.py` | Maps allocation categories to concrete instruments |
| `app/modules/confidence_scorer.py` | Scores how complete/reliable the input data was, surfaced to the user |
| `app/modules/explanation_builder.py` | Converts structured results into plain-language insights and action steps |
| `app/utils/kb_loader.py` | Loads and caches the YAML knowledge base |
| `app/utils/currency_converter.py` | INR/foreign-currency conversion helper |
| `app/utils/disclaimer_generator.py` | Generates the legal/educational disclaimers attached to every response |
| `app/api/cas_parser.py` | Best-effort extraction of holdings from an uploaded NSDL CAS PDF |
| `app/api/gold_price.py` | Live gold price with hardcoded fallback |

### 6.2 Core Sequence: Generate Recommendation

```mermaid
sequenceDiagram
    participant SPA as React SPA
    participant API as POST /api/recommend
    participant Engine as RecommendationEngine
    participant Res as ResidencyEngine
    participant Elig as EligibilityChecker
    participant Tax as TaxEngine
    participant Alloc as AllocationEngine
    participant Cat as InstrumentCatalog
    participant Conf as ConfidenceScorer
    participant Exp as ExplanationBuilder

    SPA->>API: UserProfile (JSON)
    API->>Engine: generate(profile)
    Engine->>Engine: _flatten_profile() -> SimpleNamespace
    Engine->>Res: determine residency
    Engine->>Elig: check eligible instruments
    Engine->>Tax: compute India + foreign tax, DTAA
    Engine->>Alloc: derive allocation %
    Engine->>Cat: map allocation -> instruments
    Engine->>Conf: score confidence
    Engine->>Exp: build insights + action steps
    Engine-->>API: RecommendationResponse
    API-->>SPA: 200 OK, JSON response
```

**Documented gotcha (relevant to code-review/maintenance risk):** the
`_flatten_profile` step converts several typed enums (`IndianResidentialStatus`,
`AccountType`, `InvestmentGoal`) into plain strings for the downstream
modules. On this Python version, `str(enum_member)` yields `"ClassName.MEMBER"`
rather than the member's value — three real bugs stemmed from exactly this
in the past (see `CLAUDE.md`, `tests/test_recommendation_engine.py`
regression tests). This is now covered by regression tests, but it is the
single most fragile point in the data-flow and worth flagging to any
reviewer extending `UserProfile` with new enum fields.

### 6.3 Data Model

- **Request** (`UserProfile`): nested Pydantic model — personal info,
  financial details, residency details, investment goals/risk profile.
- **Response** (`RecommendationResponse`): allocation percentages,
  concrete instrument list, tax summary (India + foreign + DTAA relief),
  compliance notes (FEMA), multi-year projections, key insights, action
  steps, disclaimers, and an overall confidence score.
- No data model is persisted; both are pure request/response DTOs.

### 6.4 Knowledge Base Design

`app/knowledge_base/` is organized one directory per country
(`india/`, `denmark/`, `uae/`, `uk/`, `usa/`, `singapore/`, `canada/`,
`germany/`, `australia/`), each holding one or more YAML rule files
(e.g. `india/nri_taxation.yaml`, `india/dtaa_provisions.yaml`,
`<country>/tax_rules.yaml`). Every file carries `version`, `last_updated`,
`source`, and `source_url` metadata (see Section 6.5). `app/utils/kb_loader.py`
loads and `lru_cache`s these at process start. This design means:
- Rule corrections/updates ship as a data-only pull request.
- The rule engine's Python code doesn't need to understand every country's
  specifics — it consumes a common schema per rule type.
- There is currently **no schema validation layer** on the YAML beyond what
  `kb_loader.py`/consuming code implicitly expects — a malformed YAML edit
  would surface as a runtime error, not a caught data-validation error
  (flagged as a gap in Section 11).

**What's actually wired to the YAML today (as of v1.1) versus what
consumes it only partially or not at all:**

| Module | Reads from `knowledge_base/`? | Detail |
|---|---|---|
| `residency_engine.py` | Yes, fully | `nri_taxation.yaml::residency_rules` |
| `tax_engine.py` | Partially | Equity STCG/LTCG, NRO FD interest TDS, dividend TDS, and SGB redemption read from `nri_taxation.yaml`. Debt fund, real estate, and gold LTCG stay hardcoded — the 2026-08-27 rate audit found these have genuinely unresolved legal questions (overlapping 2023/2024 rule changes for debt funds; a disputed NRI-eligibility question for the real-estate grandfather clause), and wiring them would mean guessing at law rather than a human verifying it. DTAA benefit rates (`get_dtaa_benefit`) and foreign-country tax summaries (`get_foreign_tax_summary`) are still fully hardcoded, not yet migrated. |
| `eligibility_checker.py` | Partially | Instrument eligibility, US/Canada restrictions, and NRE/NRO repatriation limits read from `product_rules.yaml`/`fema_rules.yaml`. Per-country currency codes read from each country's `tax_rules.yaml` (currently the only code that reads those 8 files at all). FATCA/FBAR/T1135 compliance requirements stay hardcoded — no matching YAML model exists for multi-jurisdictional compliance obligations. FX exchange rates also stay hardcoded on purpose: unlike tax rates, these are volatile daily market data, and a YAML file wouldn't fix staleness any better than Python does — a live rate API would be the actual fix, not attempted here. |
| `allocation_engine.py`, `confidence_scorer.py` | No, by design | These encode this app's own product judgment (age/goal/horizon allocation shifts, confidence scoring weights) — not an external authority's facts, so there was never a YAML file for them to read. Not a gap. |

### 6.5 Knowledge Base Maintenance Pipeline

Added 2026-08-27, in `scripts/` (not part of the request path):

- **`scripts/check_kb_freshness.py`** — flags any knowledge_base file whose
  `last_updated` is older than a threshold (24 months when run by the
  scheduled workflow), or missing the field entirely. A calendar-based
  backstop only.
- **`scripts/check_kb_source_changes.py`** — fetches each file's
  `monitor_url` (falling back to `source_url`) monthly, strips it to
  visible text, and hashes it. Only flags a file when that hash differs
  from the last run — not on a fixed schedule. State (last-seen hash per
  file) persists in `scripts/kb_source_state.json`, committed back to the
  repo by the workflow. A hash change can be a false positive (an
  unrelated part of the page moved) — it means "go look," not "this
  number is now wrong."
- **`.github/workflows/kb-freshness-check.yml`** — runs both scripts on
  the 1st of every month (`workflow_dispatch` also available for a manual
  run) and opens a single GitHub issue, labeled `kb-freshness`, if either
  flags something — reusing an existing open issue instead of creating
  duplicates. Neither script edits YAML data; a human still decides what,
  if anything, changes, consistent with this project's broader "AI/scripts
  detect, a human decides" posture (see `HOW_IT_WORKS.md` §8).
- **Known coverage gap:** `incometaxindia.gov.in` (the source for 3 of the
  4 India-specific files) and `ato.gov.au` return `403 Forbidden` to
  scripted requests — confirmed by hand, not assumed. The 3 India files
  were given a `monitor_url` pointing at `incometax.gov.in`'s news feed
  (a different domain, not blocked) as a workaround. Australia, Canada, and
  Germany's sources are still blocked with no workaround found yet — those
  3 files fall back to the freshness calendar check only, which can't tell
  you *if* something changed, only that it's been a long time.

### 6.6 API Surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness check (served by `app/routes/health.py`; a duplicate route in `recommendations.py` is dead code — Starlette's first-match routing always serves the `routes/health.py` version) |
| `POST` | `/api/recommend` | Core recommendation generation |
| `GET` | `/api/instruments` | Static reference list of investment instruments |
| `POST` | `/api/parse-cas` | Best-effort CAS PDF holdings extraction |
| `GET` | `/api/gold-price` | Current gold price (live or fallback) |
| `GET` | `/` (and all unmatched paths) | Serves the built React SPA (`StaticFiles`, mounted last as catch-all) |

## 7. Deployment Architecture

### 7.1 Deployment Diagram

```mermaid
flowchart TB
    Dev["Developer: git push"] --> GH["GitHub\nSubhayumuk/indian-investment-app"]
    GH -- "Blueprint sync\n(render.yaml)" --> Render["Render Platform"]

    subgraph Build["Render Docker Build"]
        S1["Stage 1: node:20-alpine\nnpm ci && npm run build"]
        S2["Stage 2: python:3.12.8-slim\npip install -r requirements.txt\ncopy app/ + frontend/dist"]
        S1 -- "frontend/dist" --> S2
    end

    Render --> Build
    Build --> Container["Running container\nuvicorn main:app --port $PORT"]
    Container --> URL["https://indian-investment-app.onrender.com"]
```

### 7.2 CI/CD Flow

There is no separate CI pipeline (no GitHub Actions configured). Render's
Blueprint sync acts as a minimal CD mechanism: any push to `main` triggers
an automatic rebuild and redeploy. **There is no automated test gate before
deploy** — `pytest` is run manually/locally, not as a required check before
Render deploys a new push. This is a gap relative to a production posture
(Section 11).

### 7.3 Environments

Single environment: Render production, free tier. **No staging/preview
environment exists.** Every push to `main` deploys directly to the only
running instance.

## 8. Non-Functional Requirements

| Category | Current posture |
|---|---|
| **Security** | No authentication/authorization (system is single-user, no accounts). `GOLD_API_KEY` is the only secret, sourced from env var, never committed. CORS defaults to `*` (acceptable only because frontend and backend are single-origin in the deployed configuration; would need scoping if the frontend were ever split out). No PII is persisted — every request is processed and discarded in memory. |
| **Availability/Reliability** | Render free tier: single instance, no redundancy, no SLA. The instance sleeps after ~15 minutes idle and cold-starts (roughly a minute) on the next request. No documented recovery/rollback procedure beyond re-pushing a prior commit. |
| **Scalability** | Stateless request handling means horizontal scaling is architecturally straightforward if needed, but the current Render plan runs exactly one instance with no autoscaling configured. Knowledge-base YAML is loaded once per process and cached — negligible per-request overhead. |
| **Performance** | No LLM inference in the path — response time is dominated by Python rule evaluation (sub-second) plus network/cold-start latency, not model latency. |
| **Maintainability** | Rules are externalized to YAML where wired (Section 6.4); 172 automated tests cover engine modules, API endpoints, YAML-vs-code drift for the wired rules (Section 6.4), and regression cases for the known enum-flattening bug class plus the two rate/eligibility bugs found 2026-08-27. A monthly job (Section 6.5) flags when a rule's source may have changed. No linter is configured for the Python side (frontend has `oxlint`). |
| **Cost** | $0/month on Render's free tier as currently configured (Docker build minutes are well within the free monthly allowance). |
| **Compliance/Disclaimer** | Every response includes generated disclaimers (`disclaimer_generator.py`) framing output as educational, not professional tax/legal/investment advice. |

## 9. Technology Stack & Rationale

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React 19 + Vite | Fast dev/build tooling; SPA fits a linear multi-step wizard well |
| Backend framework | FastAPI | Async-capable, automatic OpenAPI docs, first-class Pydantic integration for request/response validation |
| Data validation | Pydantic v2 | Strong typed request/response contracts, enum support |
| Rule storage | YAML + PyYAML | Human/domain-expert-editable, diffable in version control, no schema-migration overhead of a database |
| PDF parsing | pdfplumber | Handles NSDL CAS PDF text extraction without a paid OCR service |
| HTTP client (outbound) | httpx | Async-compatible, used for the gold-price call and in tests |
| Containerization | Docker (multi-stage) | Portable, reproducible builds; solves the "Render's Python runtime has no Node.js" constraint cleanly |
| Hosting | Render (Docker runtime) | Free tier suffices at current scale; Blueprint (`render.yaml`) gives declarative, version-controlled deploy config |

## 10. RAID Log (Risks, Assumptions, Issues, Dependencies)

| Type | Item | Impact / Mitigation |
|---|---|---|
| **Risk** | Single free-tier instance, no redundancy | Acceptable for personal use; would need a paid tier + multi-instance for any real availability guarantee |
| **Risk** | YAML tax rules can still silently go stale for 3 of 9 residence countries | India's monitoring works via a `monitor_url` workaround (Section 6.5); Australia, Canada, Germany's sources block scripted fetches with no workaround found — those fall back to a 24-month calendar check that can't detect an actual change |
| **Risk** | `tax_engine.py`'s debt fund/real estate/gold LTCG rules, and `get_dtaa_benefit`/`get_foreign_tax_summary`, remain hardcoded, not YAML-driven | Same "can go stale unnoticed" risk the 2026-08-27 migration fixed for equity/FD/dividend/SGB and instrument eligibility — deliberately deferred pending the unresolved legal questions noted in Section 6.4, not forgotten |
| **Risk** | Other 8 countries' `tax_rules.yaml` have never been audited against real current law | Only India's `nri_taxation.yaml` got a full field-by-field audit (2026-08-27); the same staleness the audit found in India's file (Budget 2024 rates never applied) may exist elsewhere and hasn't been checked |
| **Risk** | No automated test gate in the deploy pipeline | A broken commit could deploy directly to production; mitigate by running `pytest` before every push (currently a manual discipline, not enforced) |
| **Risk** | No YAML schema validation | A malformed rule file fails at runtime, not at data-authoring time |
| **Assumption** | Users self-report accurate financial/residency data | No independent verification of any input; output quality is bounded by input honesty/accuracy |
| **Constraint** | No LLM/AI calls by design | Limits recommendations strictly to what is explicitly encoded in the knowledge base — cannot handle a jurisdiction or scenario not modeled |
| **Dependency** | `goldapi.io` (external, optional) | Non-critical — hardcoded fallback if unavailable or unconfigured |
| **Issue (known, non-blocking)** | `GET /health` defined twice (`app/routes/health.py` and `app/api/recommendations.py`); the second is unreachable dead code | Documented, covered by a test asserting the routing behavior; low priority to remove |
| **Issue (found and fixed 2026-08-27)** | `tax_engine.py` hardcoded NRI NRO FD interest TDS at 10% (the resident rate) instead of 30% (the actual NRI rate) | Fixed, then made impossible to silently regress by wiring the value to `nri_taxation.yaml` with a regression test |
| **Issue (found and fixed 2026-08-27)** | `eligibility_checker.py` hardcoded Sovereign Gold Bonds as `eligible: True` for NRIs; the YAML correctly says NRIs can't subscribe to new SGB issuances | Fixed the same way — wired to `product_rules.yaml`, regression test added |
| **Issue (flagged, not fixed)** | `eligibility_checker.py`'s "$250,000/year LRS" outward remittance figure, shown to every user, is a scheme for India-resident individuals — it doesn't govern NRIs at all (their repatriation is the NRO/NRE limits shown alongside it) | Left as-is pending a product decision on what this field should actually say; not a YAML-wiring problem, since `fema_rules.yaml` has no such figure either |

## 11. Known Technical Debt / Open Items

- Pydantic v2 `class Config` deprecation in `app/models/user_profile.py`
  (unfixed, harmless — will require a `ConfigDict` migration before
  Pydantic v3).
- `railway.toml` and `Procfile` are stale relative to the current Docker
  deploy approach — they still describe a native Python-only start command
  and would need to be pointed at the same `Dockerfile` (or removed) if
  Railway/Heroku-style hosting is ever actually used.
- `README.md` describes the deleted legacy single-country pipeline and is
  out of date relative to the current architecture described in this
  document and in `CLAUDE.md`.
- No staging environment, no CI test gate before deploy — both would be
  the first additions before any move toward multi-user or production use.
- No YAML schema validation for the knowledge base.

## 12. Appendix: Glossary

| Term | Meaning in this document |
|---|---|
| NRI | Non-Resident Indian — an Indian citizen/origin individual tax-resident elsewhere |
| DTAA | Double Taxation Avoidance Agreement — a treaty preventing the same income being taxed twice by two countries |
| FEMA | Foreign Exchange Management Act — Indian law governing cross-border financial transactions |
| CAS | Consolidated Account Statement — a single statement of all an investor's Indian mutual fund/demat holdings |
| C4 model | A standard notation for architecture diagrams at increasing zoom levels (Context, Container, Component, Code) — Sections 5.1/5.2 use Levels 1 and 2 |
| DTO | Data Transfer Object — a plain data structure used to move data between layers, with no persistence or behavior of its own |
