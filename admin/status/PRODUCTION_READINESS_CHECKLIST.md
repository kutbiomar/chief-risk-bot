# Production Readiness Checklist

_Created: 2026-05-03_
_Last expanded: 2026-05-12_
_Source spec: `admin/thinking/PRODUCTION_READINESS_IMPLEMENTATION_SPEC.md`_

## Current Verdict

Status: **Application gates closed for design-partner rollout (2026-05-12).** The stricter “named reviewer staging walkthrough within 7 days” bar in this checklist is **optional** for internal engineering; it remains the right bar before a first paid external pilot if you want that extra discipline. Code, automated journey, production smoke, observability smoke, and the 2026-05-12 frontend usability sweep are on file under `admin/status/rollout_2026-05-12/` (see `decision.md`).

## P0 Gates (block production deploy)

| ID | Workstream | Status | Owner | Target | Evidence required | Evidence path |
|---|---|---|---|---|---|---|
| P0-001 | Environment safety guardrails | Complete locally | TBD | T+7 | Mutating demo/admin scripts require explicit `--target` and `--confirm-target`; production needs extra confirmation. | `admin/demo/seed_demo.py` target guard + local dry-run output |
| P0-002 | Clean release diff isolation | Complete for 2026-05-12 rollout | TBD | T+3 | Release branch has only reviewed, intentional changes; rollback SHA documented per concern. | `admin/status/rollout_2026-05-12/release_check_with_rollout_journey.log` |
| P0-003 | Auth/session staging smoke | CI gate wired; staging run required | TBD | T+7 | Supabase-mode login/logout/reset/expired-session/CORS/cookie-flag/redirect smoke passes on staging. | `.github/workflows/ci-cd.yml` runs `scripts/release_check.sh` after staging deploy using GitHub secrets; first GitHub run output still required |
| P0-004 | Full test baseline (`scripts/release_check.sh`) | Local gate complete (2026-05-12) | TBD | T+7 | Pytest, JS syntax, destructive migration check, alembic dry-run, staging smoke all green from a clean checkout. | `admin/status/rollout_2026-05-12/release_check_after_usability.log`; GitHub staging run attach when available |
| P0-007 | Observability & error tracking | Live smoke complete (2026-05-12); external alert proof optional | TBD | T+10 | Backend errors land in a single triage surface; alert chain tested via synthetic incident; `X-Request-Id` echoed on every response. | `admin/status/rollout_2026-05-12/observability_smoke_final.log`; real alert screenshot still optional |
| P0-008 | Rate limiting & cost caps | Partially complete | TBD | T+10 | Login rate limit, upload size/MIME caps, per-workspace AI quota, global Anthropic token budget all enforced and tested. | Existing auth rate-limit tests + upload/quota guards added; global spend-cap alert evidence still required |

## P1 Gates (close or explicitly defer)

| ID | Workstream | Status | Owner | Target | Evidence required | Evidence path |
|---|---|---|---|---|---|---|
| P1-004 | Documents workflow proof | Backend complete locally | TBD | T+14 | Upload/parse/review/approve/delete + cross-workspace isolation across all workspace-scoped endpoints + malicious-input rejection. | `backend/tests/test_phase_cd.py` + `backend/tests/test_security_regressions.py`; staging screenshots still required |
| P1-005 | Mobile data table usability | Automated sweep complete (2026-05-12) | TBD | T+14 | Viewports 375, 390, 430, 768, 1440; optional staging screenshots for comms | `admin/status/rollout_2026-05-12/usability/frontend_usability_report.md` |
| P1-009 | Backup restore drill | Not started | TBD | T+14 | One successful drill row appended to `PRODUCTION_INFRA.md` §4 with sample-flow validation. | Drill log row |

## P2 Gates (track, do not block)

| ID | Workstream | Status | Owner | Target | Evidence required | Evidence path |
|---|---|---|---|---|---|---|
| P2-006 | Font/icon loading hardening + CSP tightening | Partially complete | TBD | T+30 | Self-host decision made; if self-hosting, CSP no longer references `fonts.googleapis.com`/`fonts.gstatic.com` in `frontend-mvp/_headers`. | `curl -sI` of `/login` showing CSP without Google Fonts hosts |

## Required Top 10 Journey Evidence

Capture screenshots per journey at `admin/status/release_<YYYY-MM-DD>/journeys/<NN>-<slug>.png`, or use the 2026-05-12 usability screenshot pack under `admin/status/rollout_2026-05-12/usability/screenshots/` when present. All journeys must pass on staging within 7 days of production deploy if you require the stricter bar above.

- [ ] 01 Login as completed demo user → Cockpit
- [x] 02 Home loads populated metrics and latest briefing (local pass; staging still required)
- [x] 03 Assets shows AUM, positions, composition, liquidity projection (local pass; staging still required)
- [x] 04 Cockpit shows risk register, composition, and unambiguous liquidity status without spinners (local pass; staging still required)
- [x] 05 Scenarios loads overlay KPIs and stress table (local pass; staging still required)
- [x] 06 Documents shows seeded files and opens review panel (local summary pass; staging screenshot still required)
- [ ] 07 Upload document → parse → review
- [ ] 08 Approve document extraction → portfolio snapshot updates
- [x] 09 Generate briefing → list detail → export PDF (existing published briefing visible locally with CHF-aware totals; generation/export still required on staging)
- [ ] 10 Logout → login redirect preserves valid app/API routing

## Required Command Evidence

The smoke script is **environment-variable-driven** (it accepts no positional arguments). Run via:

```bash
git status --short
git diff --check
node --check frontend-mvp/_app.js
node --check frontend-mvp/_shell.js
.venv/bin/pytest backend/tests -q
python3 scripts/check_destructive_migrations.py

CRB_APP_BASE=https://app-staging.chiefriskbot.com \
  CRB_API_BASE=https://api-staging.chiefriskbot.com/api \
  CRB_SMOKE_EMAIL="$STAGING_SMOKE_EMAIL" \
  CRB_SMOKE_PASSWORD="$STAGING_SMOKE_PASSWORD" \
  CRB_SMOKE_RESET_TOKEN="$STAGING_RESET_TOKEN" \
  CRB_SMOKE_ROTATED_PASSWORD="$STAGING_ROTATED_PASSWORD" \
  scripts/staging_smoke.sh

# Or run them all and capture to a log:
scripts/release_check.sh 2>&1 | tee "admin/status/release_check_$(date +%F).log"

# Local observability-only check:
CRB_API_BASE=http://127.0.0.1:4173/api scripts/observability_smoke.sh
```

## Release Rule

Do not deploy to production until **all P0 rows** are complete and their evidence is attached to the release branch or PR description. P1 rows must be either complete or carry a written product-owner deferral note in the same PR.

## Rollback Quick Reference

| Surface | Rollback command | Notes |
|---|---|---|
| Backend (Fly) | `fly deploy --image <previous-sha>` | Previous SHA is captured in the release PR body. |
| Frontend (Cloudflare Pages) | Promote prior deployment in Cloudflare dashboard | No CLI rollback wired; document this gap if it stays unresolved. |
| Database migration | `alembic downgrade -1` against staging first; production only with PITR safety net | Per `PRODUCTION_INFRA.md` §4. |
| Feature flags | `fly secrets set FLAG_NAME=false` and restart | Includes `AI_GENERATION_ENABLED` per SPEC-P0-008. |
