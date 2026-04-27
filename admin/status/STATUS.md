# ChiefRiskBot — Current Status

_Last updated: 2026-04-25_  
_Status: **PRODUCTION FRONTEND RESTORED AND VERIFIED.** Direct API auth, loading-state fixes, and asset cache-busting are live on `app.chiefriskbot.com`. Sidebar shell remains the shipped Phase M direction._

---

## TL;DR

✅ **Product surface:** MVP nav is narrowed to onboarding, cockpit, liquidity, briefings, positions, documents, and settings.  
✅ **Frontend runtime:** offline fixture/demo mode has been removed from the shipped MVP path.  
✅ **Backend foundation:** Supabase auth bridge, Supabase storage abstraction, and Postgres migration path are in place.  
✅ **Live verification:** Supabase Postgres migrations ran successfully, the demo auth user/workspace were reseeded, and bearer-token session auth resolved correctly through FastAPI.

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

Production is live. Immediate product blockers are closed. Current follow-up work is operational hardening:

1. **Static asset cache strategy** — current query-versioned `_app.js` / CSS URLs are working in production; replace with hashed assets or explicit immutable-cache rules when the frontend build pipeline is formalized.
2. **Nightly backup (EX8)** — Deferred. `backup.yml` is wired and ready. Activate when R2 is set up: create `chiefriskbot-backups` bucket in Cloudflare R2, generate an R2 API token (Object Read & Write, scoped to that bucket), then add `R2_ACCOUNT_ID` (= your CF Account ID), `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` as secrets in GitHub → `24April26` environment.
3. **Production smoke automation** — `scripts/prod_smoke.sh` now exists, passes against the live app/API, and is wired into `.github/workflows/ci-cd.yml` as the post-production `smoke_production` job.
4. **Frontend/API contract** — production frontend calls `https://api.chiefriskbot.com/api` directly. Bearer token is the intended production auth path; `_headers` is the canonical Pages CSP source and must continue to allow `connect-src https://api.chiefriskbot.com`.

## Reference docs

| Path | Purpose |
|------|---------|
| `admin/thinking/MVP_FUNCTIONALIZATION_SPEC.md` | Current source of truth for MVP scope, demo-account policy, and deployment options |
| `admin/thinking/SUPABASE_SETUP.md` | Supabase credential placement, bucket setup, bring-up steps |
| `admin/thinking/CLAUDE_AGENT_PLATFORM_SPEC.md` | Current spec for moving the agentic system onto Claude Managed Agents |
| `admin/thinking/ARCHITECTURE.md` | Deeper architecture reference |
| `admin/demo/seed_demo.py` | Demo workspace reseed tooling |

## Historical note

The repo previously added an offline fixture-backed demo mode. That path is being retired in favor of one real seeded demo account using the same auth and data flows as normal workspaces.

Earlier phase-by-phase details remain in `codex_log` and `MVP2_STATUS.md`.

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
| K1 Documents visibility triage | In progress | frontend `documents` focus/visibility fix + backend visibility regression test added |
| K2 Remove debug strip | Complete | `frontend-mvp/documents.html` debug strip removed |
| K3 Hosting target (Fly + Cloudflare) | In progress | `fly.toml`, `Dockerfile`, Cloudflare headers/wrangler config added |
| K4 Secrets management | In progress | docs + CI wiring added; secret population in host stores pending |
| K5 Domain/TLS/security headers/CORS | In progress | backend security headers + production CORS validation + frontend `_headers` added |
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
| K17 Cutover checklist | Complete (pending K8) | All gates closed except K8 (R2 backup — deferred, user-action required). Phase L unblocked. |

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
- K8 backup drill (R2 setup) still pending user-action.
- Full visual QA sweep requires live auth to verify nav + page renders end-to-end.

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
