# ChiefRiskBot Production Readiness Implementation Spec

_Created: 2026-05-03_
_Last expanded: 2026-05-03_
_Status: Draft for implementation_
_Purpose: Turn the May 2026 usability/production audit into executable release-hardening work._

This spec is the **authoritative gate list** for production release. It depends on, and does not duplicate, two adjacent docs:

- `admin/thinking/PRODUCTION_INFRA.md` — hosting, secrets, backup policy, alerting targets.
- `admin/thinking/RUNBOOK.md` — operational procedures, env handling.

If a section here conflicts with those, this spec wins for release-gate purposes; reconcile the other doc in the same PR.

## 1. Release Position

ChiefRiskBot is currently **demo-ready after review**, not production-ready.

The product now has a stronger demo path for Home, Assets, Scenarios, Access, Onboarding, and Documents, but production release must be gated by environment safety, clean change isolation, auth/session verification, document workflow proof, mobile usability, and full regression evidence.

## 2. Non-Negotiable Release Gates

Production release is blocked until all P0 gates are complete. P1 gates may be explicitly accepted by the product owner with a written deferral note attached to the release branch.

| Gate | Priority | Exit criterion |
|---|---:|---|
| Environment safety | P0 | Demo/admin scripts cannot mutate the wrong database without explicit target confirmation. |
| Clean release diff | P0 | Product fixes are isolated into reviewable commits/PRs; unrelated deletions/archive churn are separated. |
| Auth/session staging smoke | P0 | Supabase-mode auth passes login, logout, reset, session refresh, expired session, CORS, cookie-flag, and redirect tests on staging. |
| Full test baseline | P0 | Backend tests, JS syntax checks, destructive-migration check, alembic upgrade dry-run on a staging DB copy, and staging smoke pass from clean checkout. |
| Observability & error tracking | P0 | Backend errors land in a single triage surface; alerting per `PRODUCTION_INFRA.md` §5 is wired and tested with a synthetic incident. |
| Rate limiting & cost caps | P0 | Login is brute-force-resistant; document upload is size/MIME-bounded; AI briefing generation has a per-workspace daily quota and a hard global Anthropic spend cap. |
| Documents workflow proof | P1 | Upload, parse, review, approve, delete/rollback, malicious-input rejection, and cross-workspace isolation are verified. |
| Mobile table usability | P1 | Positions and data-heavy tables are usable at 375px, 390px, 430px, tablet, and desktop widths. |
| Backup restore drill | P1 | One successful restore drill is logged in `PRODUCTION_INFRA.md` §4 with sample-flow validation. |
| Font/CDN hardening | P2 | External icon/font loading no longer produces raw ligature flashes; CSP no longer requires Google Fonts hosts. |


## 3. Implementation Specs

### SPEC-P0-001: Environment Safety Guardrails

Problem:

- `admin/demo/seed_demo.py --documents-only` initially followed repo `.env` and seeded the configured Supabase database before being rerun against local SQLite.
- Any script that can seed, wipe, migrate, or mutate data must make the target impossible to confuse.

Required changes:

1. Add explicit target arguments to demo/admin scripts:
   - `--target local`
   - `--target staging`
   - `--target production`
2. Require `--confirm-target <expected-host-or-db-kind>` for any mutating operation.
3. Add `--dry-run` that prints:
   - resolved `DATABASE_URL` host or SQLite path
   - `AUTH_MODE`
   - demo workspace email
   - number of records that would be created, updated, or skipped
4. Refuse production-target seeding unless an extra destructive-production confirmation is present.
5. Document local/staging/prod env handling in `admin/thinking/RUNBOOK.md`.

Rollback path:

- Argument handling is additive; revert the script commit if needed. If a partial run mutated data, restore from the most recent backup per `PRODUCTION_INFRA.md` §4 and document the incident in `admin/status/codex_log`.

Acceptance criteria:

- Running `admin/demo/seed_demo.py --documents-only` without `--target` exits non-zero.
- Running with `--target local --confirm-target sqlite` succeeds against `backend/runtime/chiefriskbot.db`.
- Running with `--target production` without production confirmation exits non-zero.
- Dry run performs no DB writes.

Verification commands:

```bash
python3 -m py_compile admin/demo/seed_demo.py
DATABASE_URL=sqlite:///./backend/runtime/chiefriskbot.db AUTH_MODE=local \
  .venv/bin/python admin/demo/seed_demo.py --target local --confirm-target sqlite --documents-only --dry-run
DATABASE_URL=sqlite:///./backend/runtime/chiefriskbot.db AUTH_MODE=local \
  .venv/bin/python admin/demo/seed_demo.py --target local --confirm-target sqlite --documents-only
```

### SPEC-P0-002: Clean Release Diff Isolation

Problem:

- The current worktree includes frontend fixes, demo seed changes, backend modifications, archive deletions, and local config changes.
- Production release cannot be reviewed or rolled back safely while unrelated changes are mixed.

Required changes:

1. Inventory all modified/deleted/untracked files.
2. Classify each file into one of:
   - `release-fix`
   - `demo-seed`
   - `production-hardening`
   - `unrelated-user-change`
   - `archive-cleanup`
   - `local-generated`
3. Produce separate commits/PRs for:
   - frontend usability fixes
   - demo document seed
   - environment safety
   - backend/document/auth changes if any are intentional
4. Remove local generated files from release scope:
   - `.wrangler/`
   - runtime DB/storage outputs unless explicitly intended
5. Do not revert unrelated user changes without explicit instruction.

Rollback path:

- Each commit is independently revertable. Document the SHA and rollback command per concern in the release PR description (e.g. `git revert <sha>` for FE-only fixes, `fly deploy --image <previous-sha>` for backend regressions).

Acceptance criteria:

- `git status --short` has no unexplained changes before production deployment.
- Each release PR can be reviewed by concern.
- Rollback path for each concern is obvious.

Verification commands:

```bash
git status --short
git diff --stat
git diff --check
```

### SPEC-P0-003: Auth And Session Production Smoke

Problem:

- Production auth uses Supabase-mode behavior and cross-origin app/API deployment.
- The recent `api_base` fix improves demo/local redirects, but production must be tested on real origins.

Required journeys:

1. Existing demo user login.
2. Logout.
3. Expired/invalid bearer token redirects to login.
4. Password reset request and completion in `AUTH_MODE=supabase`.
5. New password succeeds; old password fails.
6. Completed workspace lands on Cockpit.
7. Incomplete workspace lands on Onboarding with clear reason.
8. API base/session remains stable across redirects.

Required changes:

- Extend `scripts/prod_smoke.sh` to cover all eight journeys above. The current script covers journeys 1, 6, and 8 only.
- The script's contract is **environment-variable-driven**, not positional: it reads `CRB_APP_BASE`, `CRB_API_BASE`, `CRB_SMOKE_EMAIL`, `CRB_SMOKE_PASSWORD`. The current bash wrapper accepts no positional args; remove the positional examples elsewhere in this spec and in the checklist.
- Add `scripts/staging_smoke.sh` as a thin wrapper that pins staging defaults and runs the destructive journeys (reset password, login with rotated password) — these must never run against production. Destructive reset completion requires `CRB_SMOKE_RESET_TOKEN` and `CRB_SMOKE_ROTATED_PASSWORD`; without those, staging smoke must fail instead of reporting a partial auth pass.
- Add explicit assertions in the smoke script:
  - `Set-Cookie` on session response includes `Secure; HttpOnly; SameSite=Lax` (or `None` if cross-site auth is required — pick one and assert it).
  - `OPTIONS /api/cockpit` with `Origin: https://evil.example` returns no permissive `Access-Control-Allow-Origin`.
  - Bearer token from a logged-out session returns 401 on `/auth/session`.
  - Idle session (token older than configured TTL) returns 401 with the expected redirect hint.

Rollback path:

- Auth changes are backend-only and behind `AUTH_MODE`. To roll back: `fly deploy` the previous image, no DB rollback needed unless a migration was bundled. Document the previous image SHA in the release evidence packet.

Acceptance criteria:

- Smoke script passes against staging.
- The same script can run read-only (skipping reset/rotation journeys) against production.
- Failures identify the exact journey and endpoint with a non-zero exit code.

Verification commands:

```bash
CRB_APP_BASE=https://app-staging.chiefriskbot.com \
  CRB_API_BASE=https://api-staging.chiefriskbot.com/api \
  CRB_SMOKE_EMAIL="$STAGING_SMOKE_EMAIL" \
  CRB_SMOKE_PASSWORD="$STAGING_SMOKE_PASSWORD" \
  CRB_SMOKE_RESET_TOKEN="$STAGING_RESET_TOKEN" \
  CRB_SMOKE_ROTATED_PASSWORD="$STAGING_ROTATED_PASSWORD" \
  scripts/staging_smoke.sh
.venv/bin/pytest backend/tests/test_auth.py -q
```

### SPEC-P0-004: Full Test Baseline

Problem:

- Release decisions today rely on ad hoc local runs. There is no single command that proves the release branch is green from a clean checkout.

Required changes:

1. Wire `scripts/check_destructive_migrations.py` into the release-gate command set; the script already exists but is not enforced.
2. Add an alembic upgrade dry-run against a **copy** of the staging database (or a fresh SQLite from migrations) as part of the gate; never run against production.
3. Add a top-level `make release-check` (or `scripts/release_check.sh`) that runs, in order, and aborts on first failure:
   - `git diff --check`
   - `python3 -m py_compile` on all changed Python files
   - `node --check frontend-mvp/_app.js frontend-mvp/_shell.js`
   - `.venv/bin/pytest backend/tests -q`
   - `python3 scripts/check_destructive_migrations.py`
   - alembic dry-run against a disposable DB
   - `scripts/staging_smoke.sh` (env-var-driven, see SPEC-P0-003)
4. Capture stdout/stderr to `admin/status/release_check_<date>.log` and link from the release PR.

Rollback path:

- This spec adds tooling only. To roll back: revert the release-check script. No runtime impact.

Acceptance criteria:

- `scripts/release_check.sh` exits 0 from a clean checkout of the release branch.
- A failing migration check, smoke failure, or test failure produces a non-zero exit and an actionable message.

Verification commands:

```bash
scripts/release_check.sh
```

### SPEC-P0-007: Observability And Error Tracking

Problem:

- The backend has structured logging in places but no single triage surface for production errors. `PRODUCTION_INFRA.md` §5 lists alerting *targets* but no shipping spec.
- A production incident today would be diagnosed by tailing Fly logs, which is slow and fragile.

Required changes:

1. Add server-side error tracking (Sentry, Honeycomb, or equivalent) initialized in `backend/main.py` behind an env var (`SENTRY_DSN` or equivalent). Initialize only when set, so local/test paths stay quiet.
2. Tag every captured event with `workspace_id` (when available), `request_id`, `auth_mode`, and route. Strip `Authorization`, cookies, and document body content from breadcrumbs.
3. Wire alerts for the four targets in `PRODUCTION_INFRA.md` §5 (5xx > 1% / 5min, `/api/health` fail × 2, scheduler failures, audit logger failures) to a real channel — ops email at minimum, Slack/Teams if available.
4. Add a synthetic-incident test: a one-off endpoint behind a staging-only flag that raises a known exception, used to verify the alert chain end-to-end before each release that touches observability.
5. Add a `correlation-id`/`request-id` middleware that echoes back to clients in `X-Request-Id` so support requests can be traced.

Rollback path:

- Unset `SENTRY_DSN` in Fly secrets; the SDK will no-op. No code rollback needed.

Acceptance criteria:

- A deliberate 500 in staging produces an event in the triage surface within 60 seconds.
- The five-target alert chain has been tested at least once and the test is logged in `admin/status/codex_log`.
- `X-Request-Id` is present on every API response.

Verification commands:

```bash
curl -sI https://api-staging.chiefriskbot.com/api/health | grep -i x-request-id
.venv/bin/pytest backend/tests -k "logging or observability" -q
```

### SPEC-P0-008: Rate Limiting And Cost Caps

Problem:

- `/auth/login` has no rate limit; brute-forcing the demo account is currently possible.
- Document upload has no enforced size cap at the application layer; a multi-GB upload is a DoS vector.
- AI briefing generation calls Anthropic synchronously with no per-workspace quota and no global spend cap; one bug or one hostile workspace can run up unbounded cost.

Required changes:

1. **Login**: per-IP and per-email rate limit on `/auth/login` and `/auth/reset` (e.g. 10/min per IP, 5/min per email). Use the existing audit logger to record exceeded attempts.
2. **Uploads**: enforce a hard size cap (default 25 MB) and a MIME allowlist (`application/pdf`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `text/csv`) on the upload endpoint. Reject before reading the full body.
3. **AI generation**: per-workspace daily quota (default 5 briefings/day) and a global daily Anthropic-token budget read from env (`ANTHROPIC_DAILY_TOKEN_CAP`). Block with a 429 and a clear message when exceeded; never silently succeed with a degraded model.
4. Surface remaining quota on the briefings page so users understand limits.
5. Add a feature flag to disable AI generation entirely for incident response (`AI_GENERATION_ENABLED=false`).

Rollback path:

- All limits are env-var-driven. To loosen or disable, change the env var and restart Fly machines; no deploy required.

Acceptance criteria:

- 11th login attempt from one IP within a minute returns 429.
- Uploading a 100MB file returns 413 without buffering the full body.
- 6th briefing generation in 24h for a workspace returns 429 with a helpful message.
- Anthropic token budget exhaustion returns 503 globally with an alert.

Verification commands:

```bash
.venv/bin/pytest backend/tests -k "rate_limit or quota or upload_size" -q
# manual: hammer /auth/login from a single IP and confirm 429
```

### SPEC-P1-004: Documents Workflow Proof

Problem:

- Seeded documents fix the demo empty state, but production readiness requires the real workflow to be proven.

Required journeys:

1. Upload PDF into `private_equity`.
2. Upload XLSX into `custodian_statements`.
3. Parse pending document.
4. Open extraction review.
5. Save edited review.
6. Approve into portfolio.
7. Verify new current snapshot and position count.
8. Delete or archive a document.
9. Confirm cross-workspace access is denied (extends to: positions, briefings, snapshots, audit events, FX, liquidity — not documents alone; one shared test fixture that asserts isolation across all workspace-scoped endpoints).
10. Confirm failed parse gives a useful error state.
11. Reject malicious uploads: filename traversal (`../etc/passwd`), MIME spoofing (`.exe` renamed to `.pdf`), oversize body, zero-byte file, embedded JavaScript in PDF (must not be executed by the parser).

Required changes:

- Add backend tests for parse/review/approve/delete workflow.
- Add browser smoke for seeded Documents page:
  - non-empty summary
  - folder filter
  - open parsed document
  - review panel visible
- Improve UI labels if `pending`, `needs_review`, and `done` are unclear.

Acceptance criteria:

- Fresh local seed shows at least 5 demo documents.
- `/api/documents` returns seeded records for the demo workspace.
- `/api/documents/{id}/review` returns review data for parsed records.
- Approval creates a new current portfolio snapshot only when the user explicitly approves.

Verification commands:

```bash
DATABASE_URL=sqlite:///./backend/runtime/chiefriskbot.db AUTH_MODE=local \
  .venv/bin/python admin/demo/seed_demo.py --target local --confirm-target sqlite --documents-only
.venv/bin/pytest backend/tests/test_phase_cd.py backend/tests/test_security_regressions.py -q
```

### SPEC-P1-005: Mobile Data Table Usability

Problem:

- Positions/table usability on small screens was flagged but not fully reproduced.
- Data tables are central to trust; unreachable rows or columns are release blockers for mobile demos.

Required pages:

- Positions (`table.html`)
- Assets composition table
- Cockpit risk register
- Documents list/review
- Liquidity schedule/table surfaces

Required viewport matrix:

| Viewport | Purpose |
|---|---|
| 375 x 812 | iPhone small baseline |
| 390 x 844 | common iPhone baseline |
| 430 x 932 | large phone |
| 768 x 1024 | tablet |
| 1440 x 900 | desktop |

Required changes:

- Ensure every wide table has a scroll wrapper.
- Preserve reachable click targets.
- Avoid text overlap in buttons, table cells, and cards.
- Add sticky first column only when it improves usability and does not create clipping.

Acceptance criteria:

- No horizontal page-level overflow except intentional table scroll containers.
- All primary actions are visible/reachable.
- No text overlap or clipped row controls.
- Browser screenshots are captured for each page/viewport.

Verification commands:

```bash
node --check frontend-mvp/_app.js
node --check frontend-mvp/_shell.js
```

Browser verification should use the in-app browser or Playwright screenshot pass.

### SPEC-P2-006: Font And Icon Loading Hardening

Problem:

- `display=swap` reduces Material Symbols flash, but the app still relies on Google-hosted font delivery.

Required decision:

- Either self-host fonts/icons, or replace Material Symbols with a bundled icon set.

Required changes if self-hosting:

- Add local font assets under a versioned frontend asset path.
- Update `_shell.css` font-face rules.
- Remove Google Material Symbols link from HTML entrypoints.
- Keep `font-display: swap`.

Acceptance criteria:

- No raw ligature text appears on cold load.
- Production CSP does not need Google Fonts for icons.
- Pages still render acceptable typography if primary font fails.

Required CSP update (dependency):

- When self-hosting lands, edit `frontend-mvp/_headers` to remove `https://fonts.googleapis.com` from `style-src` and `https://fonts.gstatic.com` from `font-src`. The current header still allows them; tightening the CSP is part of this gate, not a follow-up.

Verification:

- Browser cold-load screenshots with cache disabled.
- `curl -sI https://app.chiefriskbot.com/login | grep -i content-security-policy` shows no Google Fonts hosts.

### SPEC-P1-009: Backup Restore Drill

Problem:

- Daily backups run via `.github/workflows/backup.yml` to R2, but no restore has been proven. An untested backup is not a backup.

Required changes:

1. Execute the drill template in `PRODUCTION_INFRA.md` §4 against a Supabase scratch project at least once before first external partner onboarding.
2. After a successful drill, append a row to the **Drill log** table in `PRODUCTION_INFRA.md` §4 with date, executor, restore target, result, and notes.
3. Add a quarterly cadence reminder (calendar event or scheduled GitHub issue).

Rollback path:

- Drill is read-only against the production backup. The scratch project is disposable.

Acceptance criteria:

- One drill row exists in `PRODUCTION_INFRA.md` §4 with a non-`Pending` result before production release.
- Drill validated: login + document upload + briefing PDF export against the restored DB.

Verification commands:

```bash
# Trigger backup workflow manually (already supports workflow_dispatch).
gh workflow run backup.yml
# Then follow the manual restore template; this is a humans-in-the-loop drill.
```

## 4. Top 10 Production Journeys

These must be demonstrated on staging before production release:

1. Login as completed demo user -> Cockpit.
2. Home loads populated metrics and latest briefing.
3. Assets shows AUM, positions, composition, projection.
4. Cockpit shows risk register and composition without spinners.
5. Scenarios loads overlay KPIs and stress table.
6. Documents shows seeded files and opens review panel.
7. Upload document -> parse -> review.
8. Approve document extraction -> portfolio snapshot updates.
9. Generate briefing -> list detail -> export PDF.
10. Logout -> login redirect preserves valid app/API routing.

## 5. Release Evidence Packet

Before production release, attach or link the artifacts below to the release PR description. Each artifact lives at the path shown so future audits can reproduce the packet.

| Artifact | Path / source | Required by |
|---|---|---|
| Clean diff inventory | `git status --short` pasted in PR body | P0-002 |
| Whitespace check | `git diff --check` output | P0-002 |
| Release-check log | `admin/status/release_check_<YYYY-MM-DD>.log` | P0-004 |
| Backend pytest | included in release-check log | P0-004 |
| JS syntax check | included in release-check log | P0-004 |
| Destructive migration check | included in release-check log | P0-004 |
| Staging smoke | included in release-check log | P0-003 |
| Synthetic-incident alert proof | screenshot or alert-channel link | P0-007 |
| Rate-limit & quota proof | pytest output for `rate_limit`/`quota` tests | P0-008 |
| Top-10 journey screenshots | `admin/status/release_<YYYY-MM-DD>/journeys/` | §4 |
| Mobile viewport matrix | `admin/status/release_<YYYY-MM-DD>/mobile/` | P1-005 |
| Backup restore drill row | `PRODUCTION_INFRA.md` §4 drill log | P1-009 |
| Previous Fly image SHA (rollback target) | release PR body | P0-002, P0-003 |

## 6. Definition Of Done

Production-ready means:

- A clean, reviewed release branch exists.
- All P0 gates (P0-001 through P0-008) are closed with evidence.
- P1 gates are either closed or explicitly accepted as non-blocking by product owner with a written deferral note in the release PR.
- Release evidence packet is complete and linked from the release PR.
- Rollback command and previous image SHA are documented.
- No demo/admin script can mutate production-like data without explicit confirmation.
- Observability is live: the synthetic-incident test fired an alert at least once on the current release.
- Anthropic spend and per-workspace AI quota are bounded and tested.
