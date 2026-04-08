# ChiefRiskBot — Codebase Status Snapshot
_Last updated: 2026-04-08_

---

## What this repo is

AI-powered risk briefing platform for family office CIOs. Demo-first MVP.
FastAPI + Claude API + yfinance + FRED + SQLite (demo) / Postgres (prod).

**Current state: backend MVP scaffold is implemented locally and verified.**
The FastAPI backend, database models, migrations, routers, services, and tests now exist under `backend/`.
The static frontend still contains hardcoded demo pages in `app/static/`, so frontend integration remains incomplete,
but the repo is no longer "frontend-only."

### Backend implementation snapshot

- Implemented and tested:
  auth/session basics, CSRF, audit logger foundation, async jobs, CSV ingest,
  immutable portfolio snapshots, portfolio summary/positions, positions CRUD,
  market/macro enrichment, VaR, risk run orchestration, cockpit endpoint,
  briefing generation/list/detail/publish/export, settings/API key management,
  document upload/list/parse/review flow, onboarding state, and Alembic migrations.
- Verified locally:
  `.venv/bin/python -m pytest backend/tests` passes with 15 tests;
  migrations have been applied successfully to the local SQLite demo database.
- Still partial or deferred:
  weekly scheduler is not built, and live LLM/FRED behavior
  depends on `ANTHROPIC_API_KEY` / `FRED_API_KEY` with deterministic fallbacks when absent.

---

## Canonical source of truth

**ARCHITECTURE.md is canonical.** It was reviewed and patched by 8 Codex passes.
Where BACKEND_PLAN.md conflicts with ARCHITECTURE.md, ARCHITECTURE.md wins.

Known BACKEND_PLAN.md stale sections — do NOT follow these:
- "No auth in demo mode" (Phase 6) — **wrong**. Auth is in Phase B, first tranche.
- Project structure (`lib/cache.py`, `lib/schema.py`) — **outdated**. Use ARCHITECTURE.md's `schemas/` layout.
- Data layer table list — **incomplete**. Missing `auth_challenges`, `password_reset_tokens`,
  `async_jobs`, `fx_cache`, `audit_exports`, `onboarding_progress`, `access_requests`.
- Build sequence (old: 1A → 1C → 2A → 2B → 3 → 4...) — **outdated**. Use the Phase A/B/C/D sequence below.

BACKEND_PLAN.md is useful for: narrative rationale, demo script, VaR methodology explanation,
agent rubrics. Not useful for: schema, routes, or build order.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Framework | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 + Alembic |
| DB (demo) | SQLite — zero-config, portable |
| DB (prod) | Postgres — swap `DATABASE_URL`, no code changes |
| Market data | yfinance |
| Macro data | FRED API (`fredapi`) |
| PDF extraction | pdfplumber |
| DOCX extraction | python-docx |
| Data processing | pandas |
| AI | Anthropic SDK (Claude) |
| Config | pydantic-settings (12-factor, env-var driven) |
| Auth | bcrypt + SHA-256 + JWT-style session tokens |
| PDF export | WeasyPrint (server-side) |
| Scheduler | APScheduler |

---

## File map

### `app/static/` — prototype UI (unchanged, do not touch)

| File | Role |
|------|------|
| `_shell.css` | Shared tokens, layout, sidebar, topbar, buttons, cards, forms, tables |
| `_shell.js` | Shared sidebar/topbar injection + mobile drawer logic |
| `cockpit.css` | Page-specific styles for main risk dashboard |
| `cockpit.html` | Main dashboard: KPIs, portfolio, VaR, risk monitoring |
| `briefings.html` | Briefing archive list |
| `briefing.html` | Single briefing document view |
| `table.html` | Position table/editor |
| `sources.html` | Data source connection UI |
| `documents.html` | Document upload/extraction UI |
| `markets.html` | Market and macro context screen |
| `members.html` | Team/workspace management |
| `audit.html` | Compliance/audit log |
| `settings.html` | Workspace, AI, product settings |
| `onboarding.html` | Initial upload/setup flow |
| `login.html`, `invite.html`, `forgot.html`, `verify.html` | Auth flows |

### Root docs

| File | Role |
|------|------|
| `ARCHITECTURE.md` | **Canonical** — DB schema, API routes, build sequence, auth design |
| `BACKEND_PLAN.md` | Narrative rationale, VaR methodology, agent rubrics (see stale sections note above) |
| `FRONTEND_AUDIT.md` | Screen → endpoint mapping; post-MVP items explicitly marked |
| `DESIGN.md` | Design system: palette, typography, spacing |

---

## Implementation sequence

Build in this order. Each milestone is independently testable before the next.

### Phase A — Backend shell (milestone 1)
- `backend/` directory with `main.py`, `config.py`, `database.py`, `deps.py`
- Router registration skeleton and CORS config
- Health endpoint: `GET /api/health`
- SQLAlchemy models + Alembic migrations for foundational tables only:
  `workspaces`, `users`, `user_sessions`, `api_keys`, `password_reset_tokens`,
  `auth_challenges`, `workspace_settings`, `async_jobs`, `audit_events`,
  `portfolio_snapshots`, `positions`
- pytest smoke test: app boots, migrations run, health endpoint returns 200

**Milestone 1 done when:** app boots, migrations run, health passes.

### Phase B — Auth, audit, async job abstractions (milestone 1, continued)
Build these before any analytics. They are foundations that everything else writes through.

- Auth: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`,
  `POST /api/auth/logout-all`, password reset flow skeleton (`/forgot`, `/reset`)
- CSRF: double-submit cookie pattern. Set both session cookie and CSRF cookie on login.
  Mutating requests (non-GET) via cookie auth require `X-CSRF-Token` header matching CSRF cookie.
- API key auth: `lookup_hash` (SHA-256, indexed) first, then `key_hash` (bcrypt slow verify).
  Never do bcrypt on every request without the lookup shortcut.
- Audit logger: `services/audit/logger.py` — append-only `AuditEvent` writer with SHA-256
  hash chain and `sequence_no`. Wire auth + position mutations through it from day one.
- Async job abstraction: parent job model/service used later by risk runs, doc parsing, exports.
  Create/update/poll by `job_id`.

### Phase C — Demo data path (milestones 2 and 3)
Build the vertical slice that makes the demo work.

- CSV ingest (`POST /api/ingest/csv`) with security gate, position persistence, snapshot creation
- Portfolio aggregation (`GET /api/portfolio/summary`, `GET /api/portfolio/positions`)
- Market/macro enrichment: `price_cache`, `fx_cache`, `macro_cache` population via yfinance + FRED
- VaR engine (`POST /api/var/compute`) — historical simulation in reporting currency
- Risk agents (`POST /api/risk/run`) — five analysts in parallel behind parent async job
- Cockpit composite endpoint (`GET /api/cockpit`) — single call returning all KPIs

**Milestone 2 done when:** CSV upload → snapshot → summary endpoint returns real aggregates.
**Milestone 3 done when:** VaR returns a real result with coverage metadata.

### Phase D — Content generation and secondary workflows (milestones 4 and 5)
Build only after Phase C is stable.

- Risk run orchestration (`POST /api/risk/run`) — async job, partial failure handling
- Briefing generation (`POST /api/briefing/generate`, `GET /api/briefings`, `GET /api/briefings/{id}`)
- Document ingest (`POST /api/ingest/document`) — quarantine, validation, bounded extraction
- Settings (`GET/PATCH /api/settings`) and API key management — before scheduler
- PDF export (`POST /api/briefing/{id}/export`) — before weekly scheduler
- Weekly briefing scheduler — last, depends on settings + PDF export

**Milestone 4 done when:** risk run async job executes all agents with partial-failure handling.
**Milestone 5 done when:** cockpit and briefing flows are end-to-end usable.

### Implementation status against plan

| Phase | Status | Notes |
|-------|--------|-------|
| Phase A | Done | App boot, config, database wiring, health endpoint, foundational migration |
| Phase B | Done | Auth/session, CSRF, API key lifecycle, audit logger, async job scaffold |
| Phase C | Done | CSV ingest, snapshot persistence, summary/positions, enrichment, VaR, cockpit |
| Phase D | Mostly done | Risk orchestration, briefings, documents flow, settings, PDF export, onboarding |

Phase D remaining work is limited to the deferred/non-finalized pieces called out in the implementation snapshot above.

---

## Explicitly post-MVP — do NOT implement

These are in ARCHITECTURE.md docs but must not be built during the MVP sprint:

| Feature | Reason deferred |
|---------|----------------|
| SSO (SAML, Google Workspace OAuth) | Enterprise sales feature. Email+password is sufficient for CIO demo. |
| `workspace_settings.sso_mode` + SAML fields | Dependent on SSO |
| `services/auth/google_oauth.py`, `services/auth/saml.py` | Dependent on SSO |
| Audit export (`audit_exports` table, `POST /api/audit/export`) | Useful post-demo |
| Access requests (`access_requests` table, `POST /api/contact/request-access`) | Marketing/waitlist flow, not needed for demo |
| Data source OAuth syncs (`sources.py` router, `sync_worker.py`) | Complex integration, post-MVP |
| `members.py` router beyond basic invite/role display | Post-MVP |
| Billing routes (all return 501 stub) | Intentional stubs — do not implement |
| Monte Carlo / multi-day VaR | Out of scope for MVP; historical simulation only |
| BYOK (bring your own key) for Claude | Post-MVP |

---

## Critical architectural decisions (settled — do not re-debate)

### Portfolio snapshots are immutable
Every ingest, every manual position edit creates a new snapshot. `POST/PATCH/DELETE` on
positions materializes a successor snapshot with `parent_snapshot_id` set, copies unaffected
rows forward, and flips `is_current` inside a single transaction. Never mutate historical rows.

### VaR uses historical simulation in reporting currency
- Use overlapping history window across all modeled positions and FX series
- Translate all returns to workspace `reporting_currency` before scenario aggregation
- Persist `effective_lookback_days` and `model_coverage_pct`
- Illiquid assets: model directly if possible, proxy if defensible, exclude and disclose if neither
- Do not use leave-one-out VaR contribution as the primary cockpit metric — use scenario-day contribution

### Agent orchestration uses parent async job, not bare asyncio.gather
- One `async_jobs` row with `job_type=risk_run` per orchestration
- Five child tasks with per-agent timeout, token cap, schema validation
- `asyncio.gather(..., return_exceptions=True)` so one failure does not cancel siblings
- Retry at most once for retryable failures; never retry prompt/schema validation failures
- Mark parent `succeeded` if >= 4 of 5 agents complete; `failed` if < 4 complete
- Cockpit renders completed agents first; shows degraded-state banner for missing agents

### Prompt injection defense for agent inputs
- Never pass raw CSV rows, raw document text, or user-supplied notes directly into agent prompts
- Serialize uploaded content into typed fields only (portfolio metrics, normalized positions, macro facts)
- System prompt declares uploaded data is evidence, not instruction
- Strip control-like strings from extracted text before it reaches agent prompts

### API key lookup: two-step
- First: indexed lookup by `lookup_hash` (SHA-256 of key, unique index) — O(1)
- Then: slow-hash verify against `key_hash` (bcrypt/Argon2id)
- Never run bcrypt on every request without the lookup shortcut

### Storage paths are server-generated
`storage_path` is always derived from trusted workspace/document UUIDs. Never use user-supplied
filenames as filesystem paths.

### Audit log is append-only with hash chain
Each `AuditEvent` row has a `sequence_no` (per-workspace monotonic counter) and a `prev_hash`
field. The hash chain makes log tampering detectable. Never delete or update audit rows.

---

## Security gates required at ingest (both CSV and document)

### CSV (`POST /api/ingest/csv`)
1. Allow-list content types and extensions (`.csv`, `.tsv` only)
2. Verify magic bytes where applicable
3. Reject payloads > 25MB (demo cap)
4. Normalize filename for display only; never use as filesystem path
5. Neutralize formula injection: any cell beginning with `=`, `+`, `-`, `@` must be
   escaped before re-export or spreadsheet rendering

### Document (`POST /api/ingest/document`)
1. Allow-list PDF/DOCX/XLSX only
2. Verify MIME + magic bytes agreement
3. Reject encrypted/password-protected files in demo mode
4. Quarantine upload until all validation passes — never route unvalidated files to extraction
5. Cap file size (50MB demo), page count
6. Cap raw extracted text bytes and extracted row/page count before sending to Claude
7. Files that fail validation never reach the Claude extraction call
8. Approval required before low-confidence or truncated extraction results can be bulk-imported

---

## API surface (MVP — from ARCHITECTURE.md)

```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/logout-all
GET    /api/auth/me
POST   /api/auth/forgot-password
POST   /api/auth/reset-password
POST   /api/auth/verify-totp
GET    /api/health

POST   /api/ingest/csv
POST   /api/ingest/document
GET    /api/ingest/status/{job_id}

GET    /api/portfolio/summary
GET    /api/portfolio/positions
POST   /api/portfolio/positions
GET    /api/portfolio/positions/{id}
PATCH  /api/portfolio/positions/{id}
DELETE /api/portfolio/positions/{id}

POST   /api/risk/run
GET    /api/risk/scores
GET    /api/risk/flags
GET    /api/risk/status/{job_id}

POST   /api/var/compute
GET    /api/var/history

GET    /api/cockpit

GET    /api/market/prices
GET    /api/market/macro
GET    /api/market/movers

POST   /api/briefing/generate
GET    /api/briefings
GET    /api/briefings/{id}
PATCH  /api/briefings/{id}
POST   /api/briefings/{id}/publish
POST   /api/briefings/{id}/export

POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{id}
DELETE /api/documents/{id}
POST   /api/documents/{id}/parse
POST   /api/documents/{id}/approve

GET    /api/audit/events
GET    /api/settings
PATCH  /api/settings
GET    /api/members
POST   /api/members/invite
DELETE /api/members/{id}
GET    /api/onboarding/state
POST   /api/onboarding/step

# Billing routes — 501 stubs only, no implementation
GET    /api/billing/plan
POST   /api/billing/upgrade
```

---

## /codex-bitch task queue

### Pending

| # | Task | Command | Priority |
|---|------|---------|----------|

### Completed

| # | Task | Outcome | Date |
|---|------|---------|------|
| 0 | Initial architecture plan review (ARCHITECTURE.md v1) | 6 CRITICAL + 12 WARN found. REVISE FIRST verdict. | 2026-04-07 |
| 1 | Fix ARCHITECTURE.md schema gaps | Immutable snapshots, `parent_snapshot_id`, `security_id`, `async_jobs`, SSO fields, VaR route → POST, `sequence_no` on audit. | 2026-04-08 |
| 2 | Schema cross-validation: all FKs, routes, nullable semantics | All FK declarations resolve. Added `password_reset_tokens`, `onboarding_progress`, `access_requests`, `audit_exports`. Async job types aligned. | 2026-04-08 |
| 3 | VaR engine design review | Reporting-currency historical simulation, overlapping history windows, illiquid asset policy (direct/proxy/exclude), scenario-day contribution math, FX handling. | 2026-04-08 |
| 4 | Agent orchestration review | Parent `risk_run` job, per-agent status/error tracking, bounded token budgets, partial-result failure semantics, schema-first prompt injection defense. | 2026-04-08 |
| 5 | Auth system review | Double-submit CSRF, indexed SHA-256 API key lookup + bcrypt verify, `auth_challenges` table, session-family/logout-all, password reset invalidation. | 2026-04-08 |
| 6 | File ingest security audit | Quarantine gates, CSV formula neutralization, server-generated storage paths, malware scan status, extraction text/row caps. | 2026-04-08 |
| 7 | FRONTEND_AUDIT.md gap review | Screen endpoint lists expanded, stale backend additions pruned, briefing/document response shapes aligned in both docs. | 2026-04-08 |
| 8 | Build sequence validation | Audit moved earlier, enrichment before analytics, settings before scheduler, PDF export before weekly scheduler. | 2026-04-08 |

---

## Design system (short version)

- Background: warm cream `#fff8f6`
- Accent: navy `#1B2B5E` only
- Headlines: Fraunces (serif)
- UI text: Inter Tight
- Numerics: JetBrains Mono
- Aesthetic: "private bank reading room" — no dark mode in v1
- Full spec: `DESIGN.md`
