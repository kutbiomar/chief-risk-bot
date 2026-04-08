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
| A3 Redirect after login | Should land on cockpit if workspace is ready; onboarding if not | ❌ **Always redirects to `onboarding.html`** — code says `|| 'onboarding.html'`, ignores onboarding completion state |
| A4 Cockpit loads with live data | `GET /api/cockpit` → 200 with AUM, VaR, risk register | ✅ Works — but current demo DB has only $58K AUM/3 positions (needs seed) |
| A5 Cockpit risk register visible | Risk flags and agent scores rendered in table | ✅ Works |

**Blocker:** A3 — post-login redirect ignores onboarding completion; always dumps user on onboarding screen.

---

### Journey B — New user: CSV upload → cockpit

| Step | Requirement | Status |
|------|-------------|--------|
| B1 Navigate to `onboarding.html` | Page loads with step checklist | ✅ Works |
| B2 Upload CSV file | `POST /api/ingest/csv` → 200, snapshot created | ✅ Works |
| B3 VaR auto-computed | `POST /api/var/compute` called after upload | ✅ Called in `ensureVarReady()` |
| B4 Risk auto-run optional | "Run risk analysis" button calls `POST /api/risk/run` | ✅ Works |
| B5 Navigate to cockpit | Explicit link to `cockpit.html` | ⚠️ No CTA on onboarding page once steps complete — user has to know to click sidebar |
| B6 Cockpit reflects uploaded data | `GET /api/cockpit` shows new snapshot | ✅ Works |
| B7 Generate first briefing button | `POST /api/briefings/generate` | ✅ Works — BUT requires VaR committed first (cockpit auto-commits now; onboarding calls `/var/compute` explicitly) |

**Polish gap:** B5 — completion state on onboarding has no "Go to cockpit →" CTA.

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
| C7 Loading / error state while fetching | Spinner or skeleton before data arrives | ❌ **No loading state** — KPI area is blank white until response arrives |

**Polish gap:** C7 — no loading skeleton; blank white on slow network looks broken.

---

### Journey D — Briefing generation and export

| Step | Requirement | Status |
|------|-------------|--------|
| D1 Navigate to `briefings.html` | Lists existing briefings | ✅ Works |
| D2 Generate new briefing | `POST /api/briefings/generate` → redirects to detail | ✅ Works |
| D3 Briefing detail: headline, summary, risks, recs visible | `GET /api/briefings/{id}` → output fields rendered | ✅ Works |
| D4 Publish briefing | `POST /api/briefings/{id}/publish` | ✅ Works |
| D5 Export PDF | `GET /api/briefings/{id}/export/pdf` → file download | ⚠️ **WeasyPrint fails silently → downloads a `.txt` file with `.pdf` extension** — usable fallback but confusing in demo |
| D6 Nav active state | Sidebar "Briefings" item highlighted on briefing pages | ❌ `initBriefingDetail` calls `requireSession('briefings.html', ...)` instead of `'briefing.html'` — wrong active nav |

**Issue:** D5 — PDF download is actually a text file. WeasyPrint system deps missing.  
**Bug:** D6 — wrong active page string passed to shell; sidebar highlights wrong item.

---

### Journey E — Position editor (table.html)

| Step | Requirement | Status |
|------|-------------|--------|
| E1 Positions list renders | `GET /api/portfolio/positions` → items in table | ✅ Works |
| E2 Add new position | `POST /api/portfolio/positions` → new snapshot, position_id returned | ✅ Works |
| E3 Select and edit position | `PATCH /api/portfolio/positions/{id}` → successor snapshot | ✅ Works |
| E4 Delete position | `DELETE /api/portfolio/positions/{id}` in current snapshot | ✅ Works (frontend reloads with new `position_id` from PATCH before delete) |
| E5 Ticker disabled when editing | `form-ticker` is `disabled` on edit — correct | ✅ UX correct |
| E6 Loading guard on submit button | Button disabled while in-flight to prevent double-submit | ❌ **No disabled guard on submit button** |

**Bug:** E6 — double-clicking Save submits two concurrent PATCH/POST requests, creating duplicate snapshots.

---

### Journey F — Document upload and extraction

| Step | Requirement | Status |
|------|-------------|--------|
| F1 Upload a PDF/DOCX/XLSX | `POST /api/documents/upload` → 200, `id` returned | ✅ Works |
| F2 Parse the document | `POST /api/documents/{id}/parse` → extraction runs | ⚠️ **Works only for valid files** — pdfplumber error (`No /Root object`) surfaces raw exception message to user for corrupted/non-PDF files |
| F3 View extraction results | `GET /api/documents/{id}/extraction` → positions, confidence | ✅ Works when parse succeeds |
| F4 Approve and import | `POST /api/documents/{id}/approve` → portfolio snapshot created | ✅ Works when parsed |
| F5 Error when parsing fails | User sees actionable error, not raw stack trace | ❌ **Raw pdfplumber exception text shown** — e.g. "No /Root object! - Is this really a PDF?" |
| F6 Parse button loading state | Button disabled while parse runs | ❌ **No loading guard** — parse can take seconds; double-click creates double parse |

---

### Journey G — Login edge cases

| Step | Requirement | Status |
|------|-------------|--------|
| G1 Wrong password | 401 shown as readable error | ✅ Works |
| G2 TOTP-enabled user | TOTP field revealed, hint shown | ✅ UI works — but stub only accepts `000000`; hint in UI is adequate for demo |
| G3 Session expired / invalid | Redirect to login with `?next=` param | ✅ Works |
| G4 Login page credentials hint | Placeholder shows current demo credentials | ❌ **Placeholder still shows `owner@example.com` / `secret123`** — stale after seed_demo.py creates `cio@demo.chiefriskbot.com` / `DemoPass2026!` |
| G5 Demo DB seeded before demo | 15 positions, $8.5M AUM visible on cockpit | ❌ **Not yet seeded** — current DB has 3 positions, $58K AUM from test runs |

---

## Post-seed QA

Seeded the real demo SQLite database on 2026-04-08 with `admin/demo/seed_demo.py`, then verified the seeded flow against that database via `TestClient`: login, session check, cockpit load, briefings list, briefing detail, PDF export attempt, and positions list.

Confirmed:
- Login for `cio@demo.chiefriskbot.com` succeeds.
- Cockpit returns `$8,500,000` total AUM.
- Positions endpoint returns `15` current positions.
- Briefings list and briefing detail both load for the seeded published briefing.

Remaining issues found after seed:
- PDF export returns `503` with detail `PDF export unavailable — WeasyPrint system libraries not installed` because the local machine is missing WeasyPrint system libraries (`libgobject-2.0-0` and related deps).
- `admin/demo/demo_portfolio.csv` still uses `asset_class=real_assets` for `VNQ`, `GLD`, and `PRIV_RE_FUND_B`; the current CSV parser does not recognize that label and defaults those rows to `alternative`, which changes the cockpit asset-class mix even though AUM and position counts are correct.

---

## /codex-bitch task queue

### Pending

**Tier 1 — Blockers (will embarrass in the room)**

| # | Task | Files | Priority |
|---|------|-------|----------|
| 23 | **Fix TOTP field always visible on login** — `frontend-mvp/login.html` wraps the TOTP input in `<div id="totp-wrap" hidden>` but `_mvp.css` sets `.mvp-field { display: flex }` which overrides the browser default `[hidden] { display: none }`. Add `[hidden] { display: none !important; }` to the top of `frontend-mvp/_mvp.css`. Confirm by loading `login.html` and asserting `#totp-wrap` is not visible before any form submit. | `frontend-mvp/_mvp.css` | **BLOCKER** |
| 24 | **Format raw enum values throughout the UI** — The strings `public_equity`, `fixed_income`, `real_assets`, `cash`, `private_equity`, `alternative` appear as-is in the cockpit asset-class breakdown, the positions table Asset Class column, and the position form dropdown. Add a shared `formatAssetClass(value)` helper in `frontend-mvp/_app.js` that maps each snake_case enum to its display label (`public_equity` → `Public Equity`, `fixed_income` → `Fixed Income`, `real_assets` → `Real Assets`, `cash` → `Cash & Equivalents`, `private_equity` → `Private Equity`, `alternative` → `Alternative`). Apply it: (1) cockpit allocation labels `bucket.label`, (2) position table `item.asset_class` cell, (3) position form `<select id="form-asset-class">` option labels. Also fix the asset_class column header in the table from `ASSET CLASS` to `Asset Class`. | `frontend-mvp/_app.js`, `frontend-mvp/table.html` | **BLOCKER** |
| 25 | **Remove UUIDs from all user-facing strings** — Three places expose raw UUIDs: (1) cockpit KPI meta: `snapshot ${body.snapshot_id.slice(0,8)}` — change to just `"Live"` or remove; (2) cockpit status notice after load: `"Cockpit refreshed for snapshot ${body.snapshot_id}."` — change to `"Updated just now."`; (3) positions page meta: `"${response.total} positions · snapshot ${response.snapshot_id.slice(0,8)}"` — change to `"${response.total} positions"`  All three are in `frontend-mvp/_app.js`. Search for `.slice(0,8)` and `snapshot_id` in that file to find every instance. | `frontend-mvp/_app.js` | **BLOCKER** |
| 26 | **Fix `real_assets` not recognised by CSV parser** — `admin/demo/demo_portfolio.csv` uses `asset_class=real_assets` for VNQ, GLD, PRIV_RE_FUND_B but `backend/services/ingest/csv_parser.py` normalisation does not include `real_assets` in its allow-list, defaulting those rows to `alternative`. Add `"real_assets"` to the normalised asset-class map in the parser so the cockpit mix reflects the intended allocation. Verify by re-running `seed_demo.py` and checking the cockpit asset-class breakdown. | `backend/services/ingest/csv_parser.py`, `admin/demo/demo_portfolio.csv` | **BLOCKER** |

**Tier 2 — Copy surgery (makes it look built, not scaffolded)**

| # | Task | Files | Priority |
|---|------|-------|----------|
| 27 | **Replace all developer-facing page subtitles** — Every page description currently references "MVP", "backend", "wired to", "layer", "snapshot", "materializes", etc. Replace all six with product-facing copy: (1) `cockpit.html` hero `<p>`: `"Your portfolio's current risk picture — VaR, concentration, and the active risk register."` (2) `briefings.html` hero `<p>`: `"Weekly AI-generated risk memos for your investment committee. Generate a new briefing or review a prior one."` (3) `onboarding.html` hero `<p>`: `"Set up your workspace: upload your portfolio, connect data sources, and generate your first briefing."` (4) `table.html` hero `<p>`: `"Your current portfolio positions. Add, edit, or remove holdings — each change creates a versioned snapshot."` (5) `documents.html` hero `<p>`: `"Upload custodian statements and fund reports. ChiefRiskBot extracts positions and maps them to your portfolio."` (6) `briefing.html` hero subtitle (the `<p>` under the title): remove the loading subtitle entirely — the breadcrumb and meta row are sufficient. | `frontend-mvp/cockpit.html`, `briefings.html`, `onboarding.html`, `table.html`, `documents.html`, `briefing.html` | HIGH |
| 28 | **Fix login page headline, subtitle, and footer** — (1) Replace headline `<h1>Integrated demo frontend.</h1>` with `<h1>Know your risk before the committee does.</h1>` (2) Replace subtitle `<p>This is the thin MVP surface wired to the FastAPI backend…</p>` with `<p>Sign in to your ChiefRiskBot workspace.</p>` (3) Remove the entire `<div class="mvp-metadata">` footer block at the bottom of the left panel that reads "Served from \`frontend-mvp/\`" and "API proxied through \`/api\`". (4) Update email placeholder to `cio@demo.chiefriskbot.com` and password placeholder to `DemoPass2026!`. | `frontend-mvp/login.html` | HIGH |
| 29 | **Format week codes as human dates everywhere** — `week-15-2026` and similar ISO-week strings appear in: briefing list card metadata, briefing detail title, briefing detail meta row, and the status notice after generating. Add a `formatWeekLabel(str)` helper in `frontend-mvp/_app.js` that converts `"week-15-2026"` → `"Week of 7 Apr 2026"` (using `Date` + `Intl.DateTimeFormat`). The week number can be converted to a Monday date via the ISO week date algorithm. Apply the helper wherever `item.week_label` or `briefing.week_label` is rendered. | `frontend-mvp/_app.js` | HIGH |
| 30 | **Show workspace name from session in sidebar** — The sidebar `_shell.js` currently hardcodes `"ChiefRiskBot MVP"` as the workspace name in `document.getElementById('mvp-workspace-name').textContent`. The session response (`GET /api/auth/session`) returns `user.workspace_id` but not workspace name. Two options: (a) add `workspace_name` to `UserResponse` / `SessionResponse` schemas in `backend/schemas/auth.py` and populate from the `Workspace` table in the session endpoint; then render it in `updateShellUser()` in `_app.js`; OR (b) as a quick fix, derive the display name from `sessionStorage` or remove "MVP" so it just shows `"ChiefRiskBot"`. Option (a) is preferred. | `backend/schemas/auth.py`, `backend/routers/auth.py`, `frontend-mvp/_app.js` | HIGH |
| 31 | **Fix briefing detail breadcrumb** — `initBriefingDetail()` passes `['Workspace', 'Briefings', 'Detail']` as the crumbs array to `requireSession()`. Replace the static string `'Detail'` with the loaded briefing's human-formatted week label once the briefing has loaded: after `loadBriefing()` resolves, call `window.CRBMvpShell?.updateCrumb(2, formatWeekLabel(briefing.week_label))` or re-mount the shell with updated crumbs. As a minimum viable fix, change `'Detail'` to `'Briefing'`. | `frontend-mvp/_app.js` | MEDIUM |

**Tier 3 — Polish (designer's eye)**

| # | Task | Files | Priority |
|---|------|-------|----------|
| 32 | **Auto-hide the status notice bar after success** — The green `.mvp-notice.success` banner fires on every page load (cockpit refresh, positions load, briefings load, documents load) and stays permanently visible. For success-tone notices only, add a `setTimeout(() => setStatus(node, '', ''), 3000)` after each `setStatus(…, 'success')` call in `_app.js`. Leave error notices persistent (they require user action). This affects `loadCockpit()`, `loadPositions()`, `loadBriefings()`, and `loadDocuments()`. | `frontend-mvp/_app.js` | HIGH |
| 33 | **Disable / relabel Publish button when briefing is already published** — In `initBriefingDetail()` inside `loadBriefing()`, after rendering the briefing, check `if (briefing.status === 'published')` and set the publish button to `disabled` with label `"Published"`. On re-load after `publishBriefing()` succeeds, the same check will update it. | `frontend-mvp/_app.js` | HIGH |
| 34 | **Use executive summary as briefing card preview text** — The briefings list cards currently show the raw first portfolio-risk entry: `"Concentration: Concentration Risk Analyst: priority risk (score 9/10)"`. In `initBriefings()` replace `briefingSummary(item.output)` with: use `item.output.executive_summary` truncated to 120 characters as the card preview. Keep `briefingSummary()` as a fallback if `executive_summary` is empty. | `frontend-mvp/_app.js` | HIGH |
| 35 | **Filter briefings list to published by default** — The list currently shows all drafts alongside published briefings, making it look messy. In `loadBriefings()`, sort `items` so published briefings appear first, then drafts. Add a small toggle button `"Show drafts"` / `"Hide drafts"` above the list that filters the rendered cards. Default to showing published only. | `frontend-mvp/_app.js`, `frontend-mvp/briefings.html` | MEDIUM |
| 36 | **Richer deterministic briefing fallback content** — When `ANTHROPIC_API_KEY` is absent, `backend/services/briefings.py` `_generate_briefing_deterministic()` produces placeholder copy: market context is one sentence ("Macro environment reflects current market conditions"), and risk narratives are raw agent strings. Improve the deterministic output: (1) build market context from actual `macro_cache` values (VIX, 10Y yield, DXY) — e.g. `"VIX at {vix:.1f}, 10Y at {ust10y:.2f}%, DXY at {dxy:.1f}. {risk_tone} macro backdrop for the portfolio."` (2) for each risk score, construct a prose sentence from `score.agent`, `score.severity`, and `score.score` — e.g. `"Concentration risk is elevated (score {score}/10). The portfolio's largest single holding represents an outsized share of AUM."` This makes the fallback usable in a no-API-key demo. | `backend/services/briefings.py` | MEDIUM |
| 37 | **Fix onboarding step labels and section title** — Three copy issues in `frontend-mvp/onboarding.html` and `_app.js`: (1) the `STEP_LABELS` map in `_app.js` has `enrichment_run: 'Market enrichment and VaR ready'` — change to `'Portfolio valued & market data refreshed'`; (2) the right-column section title "DO THIS TASK" (rendered as `<div class="uplabel">DO THIS TASK</div>` in `onboarding.html`) — change to `"Actions"`; (3) the onboarding page title in `<title>` still reads "ChiefRiskBot MVP" — change to "Workspace Setup — ChiefRiskBot". | `frontend-mvp/onboarding.html`, `frontend-mvp/_app.js` | MEDIUM |
| 38 | **Right-panel login KPI copy** — The four KPI tiles on the login right panel currently read: "7 thin MVP screens", "Live backend status", "Docs primary wedge", "FO family office-first". Replace with value-prop stats: (1) `"5 min"` / `"to first briefing"`, (2) `"15+"` / `"risk factors monitored"`, (3) `"1-click"` / `"PDF for the committee"`, (4) `"FO-first"` / `"built for family offices"`. These tiles are hardcoded in `frontend-mvp/login.html` inside `.mvp-grid.cards-4`. | `frontend-mvp/login.html` | MEDIUM |

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

---

## Design system (short version)

- Background: warm cream `#fff8f6`
- Accent: navy `#1B2B5E` only
- Headlines: Fraunces (serif)
- UI text: Inter Tight
- Numerics: JetBrains Mono
- Aesthetic: "private bank reading room" — no dark mode in v1
- Full spec: `frontend-design-ideal/DESIGN.md`
