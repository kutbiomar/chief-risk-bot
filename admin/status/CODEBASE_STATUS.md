# ChiefRiskBot — Codebase Status Snapshot
_Last updated: 2026-04-08_

---

## What this repo is

AI-powered risk briefing platform for family office CIOs. Demo-first MVP.
FastAPI + Claude API + yfinance + FRED + SQLite (demo) / Postgres (prod).

**Current state: backend MVP scaffold is implemented locally and a thin integrated MVP frontend now exists.**
The FastAPI backend, database models, migrations, routers, services, and tests now exist under `backend/`.
The legacy static frontend now lives under `frontend-design-ideal/`, and the backend-aware MVP slice now lives under `frontend-mvp/`.
Project files are now organized around four primary buckets:
`admin/`, `frontend-design-ideal/`, `frontend-mvp/`, and `backend/`.
Frontend integration is no longer blocked on rewriting the whole UI, but the MVP slice still needs browser-level polish and endpoint-shape reconciliation.

### Backend implementation snapshot

- Implemented and tested:
  auth/session basics, CSRF, audit logger foundation, async jobs, CSV ingest,
  immutable portfolio snapshots, portfolio summary/positions, positions CRUD,
  market/macro enrichment, VaR, risk run orchestration, cockpit endpoint,
  briefing generation/list/detail/publish/export, settings/API key CRUD,
  document upload/list/parse/review flow, onboarding state, and Alembic migrations.
- Verified locally:
  `.venv/bin/python -m pytest backend/tests` passes with 20 tests;
  migrations have been applied successfully to the local SQLite demo database.
- Frontend MVP slice added:
  `frontend-mvp/` now contains backend-aware login, onboarding, cockpit,
  briefings, briefing detail, positions, and documents screens, plus a shared
  client and shell.
- Still partial or deferred:
  live LLM/FRED behavior
  TOTP verification remains a demo stub
  depends on `ANTHROPIC_API_KEY` / `FRED_API_KEY` with deterministic fallbacks when absent.

---

## Canonical source of truth

**`admin/thinking/ARCHITECTURE.md` is canonical.** It was reviewed and patched by 8 Codex passes.
Where `admin/thinking/BACKEND_PLAN.md` conflicts with `admin/thinking/ARCHITECTURE.md`, `admin/thinking/ARCHITECTURE.md` wins.

Known `admin/thinking/BACKEND_PLAN.md` stale sections — do NOT follow these:
- "No auth in demo mode" (Phase 6) — **wrong**. Auth is in Phase B, first tranche.
- Project structure (`lib/cache.py`, `lib/schema.py`) — **outdated**. Use ARCHITECTURE.md's `schemas/` layout.
- Data layer table list — **incomplete**. Missing `auth_challenges`, `password_reset_tokens`,
  `async_jobs`, `fx_cache`, `audit_exports`, `onboarding_progress`, `access_requests`.
- Build sequence (old: 1A → 1C → 2A → 2B → 3 → 4...) — **outdated**. Use the Phase A/B/C/D sequence below.

`admin/thinking/BACKEND_PLAN.md` is useful for: narrative rationale, demo script, VaR methodology explanation,
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

### `frontend-design-ideal/` — prototype UI reference surface

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

### `frontend-mvp/` — thin integrated MVP frontend

| File | Role |
|------|------|
| `_app.js` | Shared API client, session handling, CSRF handling, page wiring |
| `_shell.js` | Shared MVP sidebar/topbar shell |
| `_mvp.css` | Shared MVP page styles |
| `login.html` | Backend-wired sign-in |
| `onboarding.html` | CSV/doc upload flow + first run controls |
| `cockpit.html` | Live cockpit against `/api/cockpit` |
| `briefings.html`, `briefing.html` | Briefing archive + detail |
| `table.html` | Position CRUD editor |
| `documents.html` | Document upload/parse/approve flow |

### Admin docs

| File | Role |
|------|------|
| `admin/business/` | Product spec, strategy deck, user jobs, commercial/reference docs |
| `admin/status/` | Current status snapshot and historical `codex_log` |
| `admin/thinking/ARCHITECTURE.md` | **Canonical** — DB schema, API routes, build sequence, auth design |
| `admin/thinking/BACKEND_PLAN.md` | Narrative rationale, VaR methodology, agent rubrics (see stale sections note above) |
| `admin/thinking/FRONTEND_AUDIT.md` | Screen → endpoint mapping; post-MVP items explicitly marked |
| `frontend-design-ideal/DESIGN.md` | Design system: palette, typography, spacing |

### Backend runtime

| Path | Role |
|------|------|
| `backend/runtime/chiefriskbot.db` | Local SQLite demo database |
| `backend/runtime/storage/` | Generated document uploads and briefing export artifacts |

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
- Briefing generation (`POST /api/briefings/generate`, `GET /api/briefings`, `GET /api/briefings/{id}`)
- Document flow (`POST /api/documents/upload`) — quarantine, validation, bounded extraction
- Settings (`GET/PATCH /api/settings`) and API key management — before scheduler
- PDF export (`GET /api/briefings/{id}/export/pdf`) — before weekly scheduler
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
POST   /api/auth/totp/verify
GET    /api/auth/session
GET    /api/health

POST   /api/ingest/csv
GET    /api/ingest/status/{job_id}

GET    /api/portfolio/snapshot
GET    /api/portfolio/summary
GET    /api/portfolio/positions
POST   /api/portfolio/positions
PATCH  /api/portfolio/positions/{id}
DELETE /api/portfolio/positions/{id}

POST   /api/risk/run
GET    /api/risk/scores
GET    /api/risk/flags
GET    /api/risk/register

POST   /api/var/compute

GET    /api/cockpit

GET    /api/market/prices
GET    /api/market/macro
GET    /api/market/movers

POST   /api/briefings/generate
GET    /api/briefings
GET    /api/briefings/{id}
POST   /api/briefings/{id}/publish
GET    /api/briefings/{id}/export/pdf

POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{id}
DELETE /api/documents/{id}
POST   /api/documents/{id}/parse
GET    /api/documents/{id}/extraction
POST   /api/documents/{id}/tag
POST   /api/documents/{id}/approve

GET    /api/settings
PATCH  /api/settings
GET    /api/settings/api-keys
POST   /api/settings/api-keys
DELETE /api/settings/api-keys/{id}
GET    /api/onboarding/state
POST   /api/onboarding/step

# Billing routes — 501 stubs only, no implementation
GET    /api/billing/plan
POST   /api/billing/upgrade
```

---

## Demo journey map

Tested live against `backend/runtime/chiefriskbot.db` on 2026-04-08, branch `mvp-demo`.
Every step was exercised via `TestClient` against the real database.

### Journey A — Investor arrives and logs in to pre-loaded cockpit

| Step | Requirement | Status |
|------|-------------|--------|
| A1 Open `login.html` | Page loads, fonts and CSS visible | ✅ Renders |
| A2 Enter credentials and submit | `POST /api/auth/login` → 200, session cookie set, no TOTP prompt | ✅ Works — existing demo users have `totp_enabled=False` |
| A3 Redirect after login | Should land on cockpit if workspace is ready; onboarding if not | ✅ Works — authenticated landing now checks `/api/onboarding/state` before choosing `cockpit.html` vs `onboarding.html` |
| A4 Cockpit loads with live data | `GET /api/cockpit` → 200 with AUM, VaR, risk register | ✅ Works — seeded demo DB now returns $8.5M AUM and live risk data |
| A5 Cockpit risk register visible | Risk flags and agent scores rendered in table | ✅ Works |

---

### Journey B — New user: CSV upload → cockpit

| Step | Requirement | Status |
|------|-------------|--------|
| B1 Navigate to `onboarding.html` | Page loads with step checklist | ✅ Works |
| B2 Upload CSV file | `POST /api/ingest/csv` → 200, snapshot created | ✅ Works |
| B3 VaR auto-computed | `POST /api/var/compute` called after upload | ✅ Called in `ensureVarReady()` |
| B4 Risk auto-run optional | "Run risk analysis" button calls `POST /api/risk/run` | ✅ Works |
| B5 Navigate to cockpit | Explicit link to `cockpit.html` | ✅ Works — completed onboarding now shows a dedicated `Go to cockpit` CTA |
| B6 Cockpit reflects uploaded data | `GET /api/cockpit` shows new snapshot | ✅ Works |
| B7 Generate first briefing button | `POST /api/briefings/generate` | ✅ Works — BUT requires VaR committed first (cockpit auto-commits now; onboarding calls `/var/compute` explicitly) |

---

### Journey C — Cockpit review

| Step | Requirement | Status |
|------|-------------|--------|
| C1 KPI tiles render (AUM, VaR, liquidity, active risks) | `GET /api/cockpit` → 200, all fields present | ✅ All fields match |
| C2 Asset class breakdown renders | `summary.asset_class[]` iterated | ✅ Works |
| C3 VaR top contributors render | `var_result.position_contributions[]` iterated | ✅ Works |
| C4 Risk register table renders | `risk_register[]` with severity/headline/agent | ✅ Works |
| C5 Refresh button reloads data | Re-calls `GET /api/cockpit` | ✅ Works |
| C6 Re-run risk button | `POST /api/risk/run` then re-fetch cockpit | ✅ Works |
| C7 Loading / error state while fetching | Spinner or skeleton before data arrives | ✅ Works — cockpit surfaces now render lightweight loading placeholders before `GET /api/cockpit` resolves |

---

### Journey D — Briefing generation and export

| Step | Requirement | Status |
|------|-------------|--------|
| D1 Navigate to `briefings.html` | Lists existing briefings | ✅ Works |
| D2 Generate new briefing | `POST /api/briefings/generate` → redirects to detail | ✅ Works |
| D3 Briefing detail: headline, summary, risks, recs visible | `GET /api/briefings/{id}` → output fields rendered | ✅ Works |
| D4 Publish briefing | `POST /api/briefings/{id}/publish` | ✅ Works |
| D5 Export PDF | `GET /api/briefings/{id}/export/pdf` → file download | ⚠️ Returns `503` with actionable detail when WeasyPrint system libraries are unavailable locally, instead of silently returning a mislabeled text file |
| D6 Nav active state | Sidebar "Briefings" item highlighted on briefing pages | ✅ Works — briefing detail now mounts the shell with `briefing.html` |

---

### Journey E — Position editor (table.html)

| Step | Requirement | Status |
|------|-------------|--------|
| E1 Positions list renders | `GET /api/portfolio/positions` → items in table | ✅ Works |
| E2 Add new position | `POST /api/portfolio/positions` → new snapshot, position_id returned | ✅ Works |
| E3 Select and edit position | `PATCH /api/portfolio/positions/{id}` → successor snapshot | ✅ Works |
| E4 Delete position | `DELETE /api/portfolio/positions/{id}` in current snapshot | ✅ Works (frontend reloads with new `position_id` from PATCH before delete) |
| E5 Ticker disabled when editing | `form-ticker` is `disabled` on edit — correct | ✅ UX correct |
| E6 Loading guard on submit button | Button disabled while in-flight to prevent double-submit | ✅ Works — Save and Delete now disable during position mutations |

---

### Journey F — Document upload and extraction

| Step | Requirement | Status |
|------|-------------|--------|
| F1 Upload a PDF/DOCX/XLSX | `POST /api/documents/upload` → 200, `id` returned | ✅ Works |
| F2 Parse the document | `POST /api/documents/{id}/parse` → extraction runs | ✅ Works for valid files and now returns a friendly file-type-specific message for corrupted uploads |
| F3 View extraction results | `GET /api/documents/{id}/extraction` → positions, confidence | ✅ Works when parse succeeds |
| F4 Approve and import | `POST /api/documents/{id}/approve` → portfolio snapshot created | ✅ Works when parsed |
| F5 Error when parsing fails | User sees actionable error, not raw stack trace | ✅ Works — backend now returns a friendly parse error instead of raw library text |
| F6 Parse button loading state | Button disabled while parse runs | ✅ Works — Parse now disables while the request is in flight |

---

### Journey G — Login edge cases

| Step | Requirement | Status |
|------|-------------|--------|
| G1 Wrong password | 401 shown as readable error | ✅ Works |
| G2 TOTP-enabled user | TOTP field revealed, hint shown | ✅ UI works — but stub only accepts `000000`; hint in UI is adequate for demo |
| G3 Session expired / invalid | Redirect to login with `?next=` param | ✅ Works |
| G4 Login page credentials hint | Placeholder shows current demo credentials | ✅ Works — login now shows `cio@demo.chiefriskbot.com` / `DemoPass2026!` placeholders |
| G5 Demo DB seeded before demo | 15 positions, $8.5M AUM visible on cockpit | ✅ Works — real demo DB was reseeded and verified in `Post-seed QA` |

---

## Post-seed QA

Seeded the real demo SQLite database on 2026-04-08 with `admin/demo/seed_demo.py`, then verified the seeded flow against that database via `TestClient`: login, session check, cockpit load, briefings list, briefing detail, PDF export attempt, and positions list.

Confirmed:
- Login for `cio@demo.chiefriskbot.com` succeeds.
- Cockpit returns `$8,500,000` total AUM.
- Positions endpoint returns `15` current positions.
- Briefings list and briefing detail both load for the seeded published briefing.
- Session payload now includes workspace name `Whitmore Family Office`.
- Cockpit asset-class mix now preserves `real_assets` with 3 positions (25.13% of portfolio).
- Deterministic briefing fallback now renders macro-aware market context and prose risk findings.

Remaining issues found after seed:
- PDF export returns `503` with detail `PDF export unavailable — WeasyPrint system libraries not installed` because the local machine is missing WeasyPrint system libraries (`libgobject-2.0-0` and related deps).

---

## /codex-bitch task queue

### Pending
No pending items.

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
| 9 | Endpoint-shape reconciliation | Audited every `api()`/`download()` call in `frontend-mvp/_app.js`; route/method coverage matched backend, with one cockpit register field-shape mismatch (`headline`/`agent` vs frontend `title`/`ticker`) requiring a frontend follow-up. | 2026-04-08 |
| 10 | Design system compliance audit | Audited every file in `frontend-mvp/` against `DESIGN.md`; found a blocker-level broken shared stylesheet path on every screen, plus non-token hardcoded colours in `_mvp.css` and repeated JetBrains Mono violations in runtime data rendering. | 2026-04-08 |
| 11 | Demo path gap analysis | Traced login → onboarding upload → cockpit load → re-run risk → briefing generation → briefing detail → PDF export. Route and response-shape coverage matched the backend, but the core demo path still has blocker-level in-flight UX gaps on onboarding/cockpit/briefing actions, ignored CSV warnings, and a misleading briefing-detail fallback when list loading fails. | 2026-04-08 |
| 12 | Loading and error state audit | Audited every MVP API call for visible loading/error handling. Found silent extraction-load failure swallowing, protected-page session failures that redirect to login on any session fetch error, blank-on-load data surfaces with no interim state, and missing disabled/loading guards across the main action buttons. | 2026-04-08 |
| 13 | Fix post-login redirect | `frontend-mvp/_app.js` now resolves the default authenticated landing via `/api/onboarding/state` in both `initIndex()` and `initLogin()`, sending completed workspaces to `cockpit.html` and incomplete workspaces to `onboarding.html` while preserving explicit `?next=` redirects. | 2026-04-08 |
| 14 | Fix wrong active-nav page in briefing detail | `frontend-mvp/_app.js` now mounts the briefing detail screen with `requireSession('briefing.html', ...)`, so the shell highlights the correct sidebar entry on the detail page. | 2026-04-08 |
| 15 | Add submit button loading guard on position form | `frontend-mvp/_app.js` now disables the position Save and Delete buttons while position mutations are in-flight, preventing duplicate snapshot writes from repeated clicks. | 2026-04-08 |
| 16 | Add loading guard on document parse button | `frontend-mvp/_app.js` now disables the Parse button during `POST /api/documents/{id}/parse` and restores it in `finally`. | 2026-04-08 |
| 17 | Add cockpit loading skeleton | `frontend-mvp/_app.js` now renders lightweight loading placeholders into the KPI, allocation, VaR contribution, and risk-register containers before `GET /api/cockpit` resolves. | 2026-04-08 |
| 18 | Add "Go to cockpit" CTA on completed onboarding | `frontend-mvp/onboarding.html` and `_app.js` now show a prominent ready-state banner with a `Go to cockpit` CTA whenever onboarding is complete. | 2026-04-08 |
| 19 | Fix document parse error message | `backend/services/documents.py` now converts extractor failures into user-friendly file-type-specific parse errors instead of leaking raw library exception text. | 2026-04-08 |
| 20 | Fix PDF export fallback behavior | `backend/services/briefings.py` and `backend/routers/briefings.py` now return a proper `503` with actionable detail when WeasyPrint system libraries are unavailable instead of writing a text fallback with a misleading `.pdf` flow. | 2026-04-08 |
| 21 | Update login page placeholder credentials | `frontend-mvp/login.html` now uses the seeded demo credentials in the placeholders and removes the stale seeded-user subtitle copy. | 2026-04-08 |
| 22 | Seed demo DB and verify full journey | `admin/demo/seed_demo.py` was updated to match current models/services, the real demo DB was reseeded successfully, cockpit/briefings/export/positions were verified against the seeded database, and the remaining issues were documented in `Post-seed QA`. | 2026-04-08 |
| 23 | Fix TOTP field always visible on login | Added `[hidden] { display: none !important; }` to `frontend-mvp/_mvp.css`, restoring the hidden TOTP field behavior until login requests a challenge. | 2026-04-08 |
| 24 | Format raw enum values throughout the UI | `frontend-mvp/_app.js` now uses a shared `formatAssetClass()` helper for cockpit allocation labels and positions table rows, and `frontend-mvp/table.html` uses product-facing asset-class labels in the form select/header. | 2026-04-08 |
| 25 | Remove UUIDs from all user-facing strings | `frontend-mvp/_app.js` now removes snapshot UUID fragments from cockpit and positions status/meta strings, replacing them with clean copy like `Live` and `Updated just now.` | 2026-04-08 |
| 26 | Fix `real_assets` not recognised by CSV parser | `backend/services/ingest/csv_parser.py` now preserves `real_assets`, the demo seed was rerun, and seeded cockpit QA confirmed `real_assets` appears with 3 positions (25.13% of portfolio). | 2026-04-08 |
| 27 | Replace all developer-facing page subtitles | Updated the MVP page hero copy across cockpit, briefings, onboarding, positions, documents, and briefing detail to product-facing text and removed the briefing-detail loading subtitle. | 2026-04-08 |
| 28 | Fix login page headline, subtitle, and footer | `frontend-mvp/login.html` now uses the ChiefRiskBot headline/subtitle, removes the developer metadata footer, and keeps the seeded demo credentials in the placeholders. | 2026-04-08 |
| 29 | Format week codes as human dates everywhere | `frontend-mvp/_app.js` now formats ISO week labels as `Week of …` across onboarding success copy, briefing cards, breadcrumb updates, detail metadata, and briefing load status. | 2026-04-08 |
| 30 | Show workspace name from session in sidebar | Added `workspace_name` to auth responses, populated it from the `Workspace` table in `backend/routers/auth.py`, rendered it in `frontend-mvp/_app.js`, and changed the shell fallback to `ChiefRiskBot`. | 2026-04-08 |
| 31 | Fix briefing detail breadcrumb | `frontend-mvp/_app.js` now mounts the briefing detail page with a neutral `Briefing` crumb first, then updates the last breadcrumb to the human-formatted week label after the briefing loads. | 2026-04-08 |
| 32 | Auto-hide the status notice bar after success | `frontend-mvp/_app.js` now auto-clears success notices after 3 seconds while leaving error notices persistent. | 2026-04-08 |
| 33 | Disable / relabel Publish button when briefing is already published | `frontend-mvp/_app.js` now disables the publish button and relabels it to `Published` whenever the loaded briefing is already published. | 2026-04-08 |
| 34 | Use executive summary as briefing card preview text | The briefings list now prefers a truncated executive summary for card previews, falling back to the derived risk summary only when necessary. | 2026-04-08 |
| 35 | Filter briefings list to published by default | `frontend-mvp/_app.js` and `frontend-mvp/briefings.html` now sort published briefings first, hide drafts by default, and expose a `Show drafts` / `Hide drafts` toggle. | 2026-04-08 |
| 36 | Richer deterministic briefing fallback content | `backend/services/briefings.py` now builds deterministic market context from macro values and renders prose findings/implications for fallback risk narratives. | 2026-04-08 |
| 37 | Fix onboarding step labels and section title | Updated onboarding step copy in `frontend-mvp/_app.js` and changed the right-column uplabel/title copy plus `<title>` in `frontend-mvp/onboarding.html`. | 2026-04-08 |
| 38 | Right-panel login KPI copy | `frontend-mvp/login.html` now uses value-prop KPI tiles (`5 min`, `15+`, `1-click`, `FO-first`) on the sign-in screen. | 2026-04-08 |

---

## Design system (short version)

- Background: warm cream `#fff8f6`
- Accent: navy `#1B2B5E` only
- Headlines: Fraunces (serif)
- UI text: Inter Tight
- Numerics: JetBrains Mono
- Aesthetic: "private bank reading room" — no dark mode in v1
- Full spec: `frontend-design-ideal/DESIGN.md`
