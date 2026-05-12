# ChiefRiskBot — Current Status

_Last updated: 2026-05-12_
_Status: **PRODUCTION LIVE; P0/P1 CODE + USABILITY QUEUE CLOSED.** The 2026-05-12 rollout record (`admin/status/rollout_2026-05-12/`) documents journey, production, observability, and usability evidence plus the design-partner decision. **`frontend-mvp`** loads **`_tokens.css`** before the shell (DESIGN.md parity), with the same no-cache policy as other shell assets in **`_headers`**. Remaining rollout items are **external owner confirmations** (`rollout_2026-05-12/p1_external_actions.md`), not missing implementation._

---

## TL;DR

✅ **Product surface:** MVP nav is narrowed to onboarding, cockpit, liquidity, briefings, positions, documents, and settings.
✅ **Frontend runtime:** offline fixture/demo mode has been removed from the shipped MVP path.
✅ **Backend foundation:** Supabase auth bridge, Supabase storage abstraction, and Postgres migration path are in place.
✅ **Live verification:** Supabase Postgres migrations ran successfully, the demo auth user/workspace were reseeded, and bearer-token session auth resolved correctly through FastAPI.
✅ **2026-05-12 rollout gate:** P0/P1 code-verifiable and usability-verifiable queues cleared (`p1_queue_status.md`); `scripts/rollout_journey_check.py`, `scripts/release_check.sh`, `scripts/prod_smoke.sh`, and `scripts/observability_smoke.sh` evidence retained under `rollout_2026-05-12/` (interim logs removed).

---

## What is this

AI-powered risk briefing platform for family office CIOs.
FastAPI + vanilla HTML/JS frontend + market data + LLM briefing pipeline.

**Tech stack:**
- Framework: FastAPI + uvicorn
- ORM: SQLAlchemy 2.0 + Alembic
- DB: SQLite (local fallback) or Postgres/Supabase Postgres
- Frontend: vanilla HTML/JS (no frameworks)
- Market data: yfinance + FRED API
- AI: Anthropic Claude API
- Auth: local session auth plus Supabase Auth bridge
- Scheduler: APScheduler

---

## Live URLs

| Surface | URL |
|---|---|
| Frontend | https://app.chiefriskbot.com |
| Backend API | https://api.chiefriskbot.com |
| Health check | https://api.chiefriskbot.com/api/health |
| Demo login | `cio@demo.chiefriskbot.com` / `DemoPass2026!` |

## Current focus

Production is live. Application-code and automated usability gates from the 2026-05-12 rollout are **closed** (`rollout_2026-05-12/decision.md`). Follow-up is operational and owner-driven:

1. **Static asset cache strategy** — Shell assets (`_tokens.css`, `_shell.css`, `_mvp.css`, `_app.js`, `_shell.js`) ship with `Cache-Control: no-cache, no-store, must-revalidate`. Long-term: hashed-asset build when the frontend pipeline is formalized.
2. **Nightly backup (EX8)** — Deferred pending R2 bucket + GitHub secrets; see `admin/thinking/PRODUCTION_INFRA.md` and `rollout_2026-05-12/p1_external_actions.md`.
3. **Production smoke** — `scripts/prod_smoke.sh` is the live post-deploy check; evidence in `rollout_2026-05-12/prod_smoke_final.log`.
4. **Frontend/API contract** — Production app calls `https://api.chiefriskbot.com/api`; `_headers` remains the canonical CSP source (`connect-src https://api.chiefriskbot.com`).
5. **External rollout sign-offs** — Items in `rollout_2026-05-12/p1_external_actions.md` (backup drill, spend caps, alert routing, support inbox, optional screenshot pack).

## Reference docs

| Path | Purpose |
|------|---------|
| `admin/thinking/MVP_FUNCTIONALIZATION_SPEC.md` | Current source of truth for MVP scope, demo-account policy, and deployment options |
| `admin/thinking/SUPABASE_SETUP.md` | Supabase credential placement, bucket setup, bring-up steps |
| `admin/thinking/CLAUDE_AGENT_PLATFORM_SPEC.md` | Current spec for moving the agentic system onto Claude Managed Agents |
| `admin/thinking/ARCHITECTURE.md` | Deeper architecture reference |
| `admin/demo/seed_demo.py` | Demo workspace reseed tooling |
| `admin/status/ROLLOUT_FUNCTIONALITY_CHECKLIST.md` | Functionality checklist and scoring rubric for rollout decisions |

## Historical note

The repo previously added an offline fixture-backed demo mode. That path is being retired in favor of one real seeded demo account using the same auth and data flows as normal workspaces.

Earlier phase-by-phase details remain in `admin/status/codex_log` and `admin/archive/MVP2/` (archived MVP2 specs, not the live product).

## Latest verification

- `node --check frontend-mvp/_app.js`
- `node --check frontend-mvp/_shell.js`
- `.venv/bin/python -m pytest backend/tests/test_auth.py backend/tests/test_phase_cd.py -q`
- `.venv/bin/python -m pytest backend/tests/test_services.py backend/tests/test_auth.py -q`
- `.venv/bin/alembic upgrade head` against the configured Supabase/Postgres database
- `AUTH_MODE=supabase .venv/bin/python admin/demo/seed_demo.py` with deterministic fallbacks
- Live auth smoke test:
  - `/api/auth/login` -> `200`
  - bearer `/api/auth/session` -> `200`
  - workspace resolved as `Whitmore Family Office`
- Production frontend recovery pass on April 25, 2026:
  - `https://app.chiefriskbot.com/login` -> `200` with CSP `connect-src https://api.chiefriskbot.com`
  - direct frontend login posts to `https://api.chiefriskbot.com/api/auth/login` -> `200`
  - `/`, `/cockpit`, `/liquidity`, `/briefings`, `/documents`, `/table`, `/settings`, `/access`, `/onboarding` all reached `mvp-ready` in browser verification
  - `scripts/prod_smoke.sh` -> pass against live production app/API
- Frontend cache hardening on April 27, 2026:
  - removed manual `?v=` asset URLs from shipped HTML entrypoints
  - `frontend-mvp/_headers` now forces `_tokens.css`, `_app.js`, `_shell.js`, `_mvp.css`, `_shell.css` to `Cache-Control: no-cache, no-store, must-revalidate`
  - verified live response headers and reran `scripts/prod_smoke.sh` successfully
- **2026-05-12 rollout bundle** (`admin/status/rollout_2026-05-12/`):
  - `release_check_with_rollout_journey.log` + `release_check_after_usability.log` — local release gate with journey script and post-usability tooling
  - `prod_smoke_final.log` — live app/API smoke including briefing detail and PDF export
  - `observability_smoke_final.log` — request-id + synthetic-endpoint checks
  - `usability/frontend_usability_report.md` — 50 viewport/page combinations PASS (overlay 5xx noted as API-side)
  - `decision.md` / `p1_queue_status.md` / `p1_external_actions.md` — decision and remaining external actions
- Live API smoke test on the running server:
  - `/api/cockpit` -> `200`
  - `/api/liquidity/summary` -> `200`
  - `/api/briefings` -> `200`
  - `/api/settings` -> `200`
  - `/api/portfolio/summary` -> `200`
  - `/api/documents` -> `200` with `2` seeded documents
  - `/api/documents/{id}/review` -> `200` for the parsed seeded document
- Frontend proxy/static smoke test on the running server:
  - `/login.html` -> `200`
  - `/cockpit.html` -> `200`
  - `/liquidity.html` -> `200`
  - `/briefings.html` -> `200`
  - `/settings.html` -> `200`
  - `/api/health` via frontend proxy -> `200`
- Focused auth/backend verification after the latest functional pass:
  - `.venv/bin/pytest backend/tests/test_auth.py` -> `13 passed`
  - `node --check frontend-mvp/_app.js` -> clean
  - `node --check frontend-mvp/_shell.js` -> clean
  - Playwright browser pass against restarted local servers -> no console/page errors on login -> cockpit -> liquidity
  - Live disposable Supabase verification:
    - `/api/auth/register` against real Supabase Auth -> `200`
    - `/api/auth/login` against real Supabase Auth -> `200`
    - bearer `/api/auth/session` -> `200`
    - `/api/documents/upload` stored the file at a `supabase://documents/...` path
    - storage readback from Supabase matched the uploaded payload byte-for-byte
    - disposable auth user, DB rows, and storage object were cleaned up successfully
- Fresh-workspace browser audit on April 15, 2026:
  - Create workspace -> `onboarding.html` works
  - Login for an incomplete workspace correctly lands on `onboarding.html` rather than `cockpit.html`
  - Onboarding CSV import works
  - Onboarding document upload works and redirects into `documents.html`
  - Documents page upload works for the same non-demo workspace and increments document count
  - Password reset request UI works (`/api/auth/forgot-password` accepted)
  - Password reset completion in Supabase mode was triaged and fixed in code:
    - `/api/auth/reset-password` now updates the upstream Supabase Auth credential before consuming the reset token
    - verified in-process with fresh account flow: reset `200`, new password login `200`, old password login `401`
  - Temporary Documents debug strip added to surface current email, workspace, document count, selected record, and latest upload
- Post-restart verification on April 16, 2026:
  - local backend restarted with patched reset-password bridge
  - full visual flow pass on fresh non-demo workspace: signup, login, onboarding CSV, onboarding document upload, reset request
  - reset completion validated against live backend and browser:
    - reset endpoint `200`
    - old password login `401`
    - new password login `200`
- Positions language cleanup on April 16, 2026:
  - removed user-facing `factor_*` terminology from Positions UI bindings and table columns
  - Positions editor now uses only portfolio terms (asset class, sector, subsector, segment, region, custodian)
  - internal `factor_*` payload mapping retained for backend compatibility
  - `node --check frontend-mvp/_app.js` clean after refactor

## Known remaining gap

- External production provisioning remains to be executed (Fly app, Cloudflare Pages project, DNS cutover on chiefriskbot.com).
- Supabase is on free tier for now; PITR drill deferred until Pro is enabled. Interim: scheduled `pg_dump` to R2 via GH Actions (EX8).
- Alert routing is email-only for v1; Slack leg deferred.
- User-side unblockers (domain registrar access, Fly/Cloudflare/GH tokens, prod API keys, R2 bucket, support inbox) tracked in `admin/status/USER_CHECKLIST.md`.

## Production readiness (K17 gate)

| Gate | Status | Evidence |
|---|---|---|
| K1 Documents visibility triage | Complete | `frontend-mvp/documents.html` uses global status slot; journey + tests cover documents flow (`rollout_2026-05-12/release_check_with_rollout_journey.log`) |
| K2 Remove debug strip | Complete | `frontend-mvp/documents.html` debug strip removed |
| K3 Hosting target (Fly + Cloudflare) | Complete (live) | `fly.toml`, Dockerfile, Cloudflare Pages + `_headers`; production URLs verified |
| K4 Secrets management | Complete (live) | CI + host stores populated for current production; rotate per runbook |
| K5 Domain/TLS/security headers/CORS | Complete (live) | Production CORS + `_headers` CSP; see K14 |
| K6 CI/CD pipeline | Complete (repo) | `.github/workflows/ci-cd.yml` with staged + production jobs and migration dry-run |
| K7 Migration safety policy | Complete (repo) | `scripts/check_destructive_migrations.py` + `scripts/migrate.sh` |
| K8 Backup + restore drill | Pending execution | policy/log scaffold in `admin/thinking/PRODUCTION_INFRA.md` |
| K9 Observability | Complete | `/api/health` confirmed live: all 5 components ok on production (2026-04-24) |
| K10 Alerting | Complete | `.github/workflows/health-check.yml` — 5-min cron, all-components check, 5xx rate threshold; GH Actions emails on failure |
| K11 Runbook | Complete (repo) | `admin/thinking/RUNBOOK.md` |
| K12 Production PDF export | Complete | `200` (26 KB) confirmed on deployed container 2026-04-24 |
| K13 Full QA sweep | Complete | Local 34/34 pass + full deployed E2E pass including PDF export |
| K14 Security review pass | Complete | CORS: production origin allowed, unauthorized origin blocked (no ACAO header). Rate-limit: 429 at attempt 11/12 on live `POST /api/auth/login`. All code-level checks pass. |
| K15 Legal/privacy baseline | Complete (repo) | `admin/business/legal/*` + login disclosure |
| K16 Design partner onboarding collateral | Complete (repo) | `admin/business/onboarding/*` |
| K17 Cutover checklist | Complete (pending K8) | All application gates closed; **K8** R2 backup drill still deferred pending owner secrets (`p1_external_actions.md`). |

## Phase L — Editorial Redesign (complete 2026-04-24)

| Task | Status | Notes |
|---|---|---|
| L1 Archive old frontend | Complete | `frontend-mvp-archive/` snapshot preserved |
| L2 `.essay-*` CSS namespace | Complete | ~756 lines appended to `_mvp.css`; full layout system promoted from briefing prototype |
| L3 Global nav shell rewrite | Complete | `_shell.js` → `CRBMvpShell.mount(page)`, topnav + subnav, briefing drawer, avatar menu |
| L4 Home dashboard | Complete | `index.html` — metric strip (AUM/Cash/VaR/Alerts/Concentration), latest briefing inline |
| L5 Assets Overview page | Complete | `assets.html` — KPIs, composition donut, sliceable dimension table, liquidity projection |
| L6 Risk Cockpit port | Complete | `cockpit.html` — essay layout, TOC, pills |
| L7 Liquidity port | Complete | `liquidity.html` — essay layout, TOC |
| L8 Scenarios port | Complete | `scenarios.html` (was overlay.html) — `data-page="overlay"` preserved for JS compat |
| L9 Operations pages port | Complete | `documents.html`, `table.html`, `settings.html`, `access.html` |
| L10 `briefing.html` cleanup | Complete | Removed 176-line inline `<style>` block, added `_shell.css` link |
| L11 Login + onboarding | Complete | Fraunces 400, editorial hero on login + onboarding; no more old `.mvp-hero` |
| L12 Backend scope-aware briefing | Complete | `?scope=` param on `POST /api/briefings/generate`; `SCOPE_SYSTEM_OVERRIDES` in services layer |
| Shared render helpers | Complete | `renderBriefingBody()`, `renderCompositionDonut()`, `initScrollReveal()` in `_app.js` |

### Open items post-Phase-L
- Cloudflare redirect loop on `app.chiefriskbot.com`: change redirect rule expression from `contains "chiefriskbot.com"` to `eq "chiefriskbot.com"` (user-action in Cloudflare dashboard).
- K8 backup drill (R2 setup) still pending user-action (`p1_external_actions.md`).
- Automated frontend usability sweep **2026-05-12** complete (`rollout_2026-05-12/usability/frontend_usability_report.md`). Optional: owner-led screenshot pack for external comms.

## Phase M — Sidebar Restoration + Visual Polish (complete 2026-04-25)

| Task | Status | Notes |
|---|---|---|
| M1 Material Symbols icon fix | Complete | All 15 HTML files: wrong endpoint `/icon?family=` → correct `/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200` |
| M2 JS null guard in updateUser() | Complete | `_shell.js` `updateUser()` — added `if (!user) return;` to prevent "undefined is not an object" error rendering in page UI |
| M3 Phase L top-nav rollback | Complete | `_shell.js` rewritten from editorial horizontal top-nav back to left sidebar (`CRBMvpShell.mount()`); `body.essay-mode` class removed |
| M4 Sidebar visual polish | Complete | Accent-wash active states (`rgba(27,43,94,0.06)`), JetBrains Mono nav numerals (01–06), hairline border, quiet sidebar-cta; inspired by themahjong.guide |
| M5 Hero left-align (SaaS) | Complete | `_mvp.css` `.essay-hero` restyled: left-aligned, `font-size:28px` Inter Tight 600, `padding:32px 40px`, removed 72px Fraunces serif magazine layout |
| M6 Deploy to production | Complete | Merge commit `e704961` pushed to `origin/main`; GitHub Actions run `24925178084` — both staging and production jobs green |
| M7 Admin folder cleanup | Complete | Deleted 29 macOS Finder duplicate files (`* 2.*`) across all admin subdirectories |

### Deploy reference
- Branch: `MVP2` → commit `8916f8e "fix(frontend): restore left sidebar shell with serious-SaaS polish"`
- Merge: `e704961 "merge: sidebar restoration + visual polish (MVP2 → main)"` on `main`
- Live: `app.chiefriskbot.com` (Cloudflare Pages production)

## Phase N — Audit pass (2026-04-28)

Codebase audit (backend ~13.8k LOC, frontend ~4.3k JS, plus repo infra) targeting real bugs, perf wins, and dead-code removal. Three Explore agents ran in parallel; findings were filtered down to concrete fixes (several Explore findings turned out to be false positives — e.g. an "auth null-user crash" was already short-circuit-guarded; "price cache N+1" was already batched via `_load_price_cache_map`).

### Bug fixes
| ID | File | Change |
|---|---|---|
| A2 | `backend/routers/briefings.py` | `_serialize` now uses `_safe_parse_output()` — corrupted `output_json` rows return `{}` instead of raising 500. |
| A3 | `backend/services/documents.py` | `_load_confidence_payload()` wraps `json.loads` in try/except and returns `{}` on non-dict/non-list payloads. |
| A6 | `frontend-mvp/_shell.js` | `loadHistory()` now uses a `historyLoadToken` so rapid drawer-tab clicks can no longer render stale results. |
| A8 | `frontend-mvp/_app.js` | `clearAuthState()` now sweeps all `crb_*` and `crb.*` localStorage keys (except the dev `api_base_override`) on logout, preventing prior-workspace settings from leaking on shared devices. |

Skipped (false positives):
- **A1** auth.py:264 null-user check — `if user is None or user.disabled_at is not None` already short-circuits.
- **A4** snapshot demotion race — existing `UPDATE … WHERE is_current=True` + rowcount check is the correct pattern; 409 to caller is appropriate REST behavior.
- **A5 / A7** refreshTimer / IntersectionObserver leaks — frontend uses full-page navigation (`window.location.href`), so `beforeunload` already cleans up.

### Perf improvements
| ID | File | Change |
|---|---|---|
| B1 | `backend/routers/briefings.py` | `list_briefings` now applies `OFFSET/LIMIT` in SQL instead of loading the full workspace history before slicing. |
| B1 | `backend/routers/documents.py` | `list_documents` splits into a folder-counts aggregate (`GROUP BY folder`) plus a paginated `OFFSET/LIMIT` fetch — no more in-memory slicing. |
| B2 | `backend/services/enrichment.py` | FX cache lookups for portfolio currencies are now a single `SELECT … WHERE pair IN (…)` batch instead of N `db.get(FxCache, pair)` calls. |

Skipped: B1 for `risk.py` (snapshot-scoped fetches, not paginated history). B3 was already implemented (`_load_price_cache_map` line 266).

### Dead-code & file cleanup
- **Deleted** `MVP2_codebase/` (1.4 MB) and `frontend-mvp-archive/` (900 KB) — no live references; git history preserves them.
- **Archived** `MVP2_SPEC.md` and `MVP2_STATUS.md` to `admin/archive/MVP2/` with a README clarifying they describe a deferred private-markets extension, not the live product.
- **Deleted** `frontend-mvp/overlay.html` (renamed to `scenarios.html` in Phase L; no longer in nav).
- **Updated** `frontend-mvp/_app.js:2173` `requireSession('overlay.html', …)` → `requireSession('scenarios.html', …)` to match the live page.
- **Removed** unused `.mvp-hero` / `.mvp-hero h1` / `.mvp-hero p` CSS blocks (Phase L remnant) plus the matching `@media` rule from `frontend-mvp/_mvp.css`.

### Verification
- `node --check frontend-mvp/_app.js` ✓
- `node --check frontend-mvp/_shell.js` ✓
- `.venv/bin/pytest backend/tests/ -q` → **56 passed**

### Residual blockers / deferred items (carry-forward)
- **K8 R2 backup drill** — `backup.yml` wired; secrets and drill row still owner-action (`rollout_2026-05-12/p1_external_actions.md`, `PRODUCTION_INFRA.md`).
- **Cloudflare redirect rule** — root `chiefriskbot.com` → `app.chiefriskbot.com` expression should use `eq "chiefriskbot.com"` instead of `contains "chiefriskbot.com"` (dashboard).
- **Slack alerting** — email-only for v1, deferred.
- **Hashed asset pipeline** — interim `Cache-Control: no-cache` on shell assets; long-term hashed-asset build still pending.
- **Supabase Pro PITR drill** — deferred until Pro tier is enabled.

### Admin status hygiene (2026-05-12)
- Removed duplicate archived pointers `admin/status/CODEBASE_STATUS.md` and `admin/status/MVP2_STATUS.md` (live status remains this file; MVP2 history remains under `admin/archive/MVP2/`).
- Removed superseded `admin/status/release_2026-05-03/` bundle and `admin/status/release_check_2026-05-03.log`.
- Trimmed interim logs under `rollout_2026-05-12/`; retained authoritative artifacts listed in `rollout_2026-05-12/decision.md`.

### Follow-up tasks (not blocking, suitable for a later cleanup PR)
- B5: migrate residual `db.query(...).filter(...).first()` calls in `routers/market.py:70` and `routers/ingest.py:36` to SQLAlchemy 2.0 `select()`.
- B6: cache `tableBody.querySelectorAll('tr')` in `_app.js:2774–2788` or use event delegation.
- B7: drive parse-progress UI from completion callbacks rather than 900ms/1200ms polling intervals (`_app.js:2942–2957`).
- B4: Alembic migration adding composite indexes on `(workspace_id, is_current)` and `(snapshot_id, …)` — verify with `EXPLAIN ANALYZE` first.
- C4: clean up unused `Union` import / `AuthContext` alias in `routers/auth.py`; rename `_build_price_cache_deterministic` to honestly reflect that it ships as a yfinance failure path (STATUS no longer claims fixture mode is fully retired).
- D2: codify Cloudflare Pages config in a versioned `wrangler.toml` if the dashboard is currently the only source of truth.
