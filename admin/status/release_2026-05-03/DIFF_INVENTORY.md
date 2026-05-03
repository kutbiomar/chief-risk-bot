# Release Diff Inventory

_Created: 2026-05-03_
_Scope: Production readiness audit implementation pass._

## Verdict

Status: **Not clean enough for production release.**

The local readiness fixes are reviewable by concern, but the current worktree also contains staged archive deletions, local configuration edits, and generated deployment artifacts. P0-002 remains open until those are separated into their own commits/PRs or explicitly removed from release scope by the product owner. Do not treat the current mixed working tree as a production release branch.

## Release-Fix

Frontend usability and demo-readiness fixes:

- `frontend-mvp/_app.js`
- `frontend-mvp/_mvp.css`
- `frontend-mvp/_shell.css`
- `frontend-mvp/_shell.js`
- `frontend-mvp/access.html`
- `frontend-mvp/assets.html`
- `frontend-mvp/briefing.html`
- `frontend-mvp/briefings.html`
- `frontend-mvp/cockpit.html`
- `frontend-mvp/documents.html`
- `frontend-mvp/index.html`
- `frontend-mvp/legal.html`
- `frontend-mvp/liquidity.html`
- `frontend-mvp/login.html`
- `frontend-mvp/onboarding.html`
- `frontend-mvp/scenarios.html`
- `frontend-mvp/settings.html`
- `frontend-mvp/table.html`
- `frontend-mvp/favicon.svg`

Notes:

- These contain the user-facing audit fixes: API base persistence, Home/Assets render fixes, onboarding/access/scenario loading states, font-display hardening, briefing hero constraints, and mobile table wrappers.
- The latest pass also fixes briefing display currency, positions-table decision columns, and contradictory liquidity copy across Home, Briefings, Cockpit, and Assets.
- HTML entrypoints also reference the bundled SVG favicon to prevent cold-load `/favicon.ico` 404 noise.
- `frontend-mvp/overlay.html` is staged as deleted separately; confirm whether the Scenarios replacement is the intended release path before including that deletion.

## Demo-Seed

Demo data and operator runbook:

- `admin/demo/seed_demo.py`
- `admin/thinking/RUNBOOK.md`

Notes:

- The seed script now requires explicit target/confirmation flags and supports dry-run.
- Demo documents are idempotently seeded for local demo workspaces.

## Production-Hardening

Backend controls, smoke scripts, and release gates:

- `backend/config.py`
- `backend/main.py`
- `backend/routers/briefings.py`
- `backend/routers/documents.py`
- `backend/routers/health.py`
- `backend/routers/portfolio.py`
- `backend/schemas/portfolio.py`
- `backend/services/documents.py`
- `backend/services/briefings.py`
- `backend/services/observability.py`
- `backend/tests/test_health.py`
- `backend/tests/test_security_regressions.py`
- `.github/workflows/ci-cd.yml`
- `pyproject.toml`
- `scripts/observability_smoke.sh`
- `scripts/prod_smoke.sh`
- `scripts/staging_smoke.sh`
- `scripts/release_check.sh`
- `admin/thinking/PRODUCTION_READINESS_IMPLEMENTATION_SPEC.md`
- `admin/status/PRODUCTION_READINESS_CHECKLIST.md`
- `admin/status/release_check_2026-05-03.log`
- `admin/status/release_2026-05-03/journeys/local_sweep.md`
- `admin/status/release_2026-05-03/mobile/README.md`
- `admin/status/release_2026-05-03/mobile/*.png`

Notes:

- Local release gate passes when staging smoke is intentionally skipped with `CRB_SKIP_STAGING_SMOKE=1`; the 2026-05-03 log also runs observability smoke against the local API proxy.
- The CI/CD workflow now inserts `release_check_staging` after staging deployment and before production deployment, using GitHub secrets for the staging auth smoke.
- Staging smoke is now explicitly destructive for reset/rotation unless `CRB_SMOKE_REQUIRE_RESET=0`; production smoke remains non-destructive by default.
- Real GitHub staging auth output, alert-channel screenshot, journey screenshots, and backup-restore evidence are still required before production.

## Requires Review Before Release

Files changed outside the readiness implementation scope:

- `.github/workflows/backup.yml`
- `admin/thinking/PRODUCTION_INFRA.md`
- `admin/thinking/UI_AUDIT_2026-05-03.md`
- `backend/services/enrichment.py`

Notes:

- These may be intentional production work, but they were not fully audited in this pass.
- Do not include them in the release branch without a separate review of behavior and rollback.

## Unrelated User Change Or Local Config

Do not include in a production release without explicit owner approval:

- `.claude/settings.local.json`

Notes:

- Local assistant/tooling settings are not release artifacts.

## Archive-Cleanup

Large staged archive moves/deletions currently mixed into the worktree:

- `MVP2_codebase/**` staged deletions.
- `frontend-mvp-archive/**` staged deletions.
- `MVP2_SPEC.md -> admin/archive/MVP2/MVP2_SPEC.md`
- `MVP2_STATUS.md -> admin/archive/MVP2/MVP2_STATUS.md`
- `admin/archive/MVP2/README.md`

Notes:

- This should be a separate archive-cleanup commit/PR.
- It is risky to combine with runtime production hardening because rollback and review intent become unclear.

## Local-Generated

Generated or environment-specific files currently present:

- `.wrangler/`

Notes:

- Exclude from the production PR unless there is a specific Cloudflare deployment reason.

## Required Split Before Production

1. Commit/PR frontend usability fixes separately.
2. Commit/PR demo seeding and seed-script guardrails separately.
3. Commit/PR backend production-hardening and release scripts separately.
4. Move archive cleanup into its own PR or drop it from the release branch.
5. Remove local config/generated files from release scope.
6. Attach rollback SHA/image references in the release PR body.
