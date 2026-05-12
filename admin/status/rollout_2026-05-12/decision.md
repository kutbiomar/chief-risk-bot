# Rollout decision - 2026-05-12

Environment tested: local checkout plus live production app/API
Tested commit: 9ac27ee
Tester: Cursor cloud agent
Rollout level requested: Design partner

P0 score: 19 / 32 automated-evidence points
P1 score: 14 / 24 automated/docs-evidence points
P2 score: not rescored
Overall readiness: 33 / 56 for P0+P1 tracked evidence

Scoring note: this pass upgrades command/API evidence only. It does not replace
the required browser screenshots or recordings in
`ROLLOUT_FUNCTIONALITY_CHECKLIST.md`.

Decision: Do not proceed yet

Blocking issues:
- Fresh browser evidence is still missing for the required P0/P1 journeys.
- Backup/restore proof or an owner-approved design-partner deferral is still missing.
- Full production document upload -> parse -> review -> approve evidence is still missing.
- Browser logout/session-clear behavior is not captured; production smoke uses bearer auth and skips cookie logout.
- Staging password-reset rotation smoke is skipped because reset credentials are not configured.
- Support inbox confirmation is still a user-side blocker, though the runbook process is now documented.
- Anthropic spend-cap/provider alert proof is not attached.
- Mobile/tablet screenshot evidence has not been refreshed for this rollout folder.

Approved deferrals:
- None recorded yet.

Evidence:
- `baseline_environment.txt`
- `local_checks.log` - initial local check; pytest path missing before environment setup.
- `local_checks_after_fixes.log` - JS syntax, backend tests, and migration safety passed after setup.
- `release_check.log` - canonical release check passed before smoke-script hardening.
- `release_check_after_fixes.log` - release check passed after active `frontend-mvp` JS coverage was added.
- `release_check_final.log` - final release check passed after briefing PDF smoke coverage was added.
- `prod_smoke_timeout.log` - first production smoke timed out after `/liquidity/summary`; direct endpoint diagnostic was fast.
- `prod_smoke.log` - production smoke rerun passed with the original coverage.
- `prod_smoke_after_fixes.log` - expanded production smoke passed for core pages, portfolio, members, documents, overlay.
- `prod_smoke_pdf_after_fixes.log` - expanded production smoke passed including briefing detail and PDF export.
- `observability_smoke.log` - production request-id and disabled synthetic endpoint smoke passed.
- `observability_smoke_after_fixes.log` - post-fix observability smoke passed.
