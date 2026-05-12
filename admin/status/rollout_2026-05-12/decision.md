# Rollout decision - 2026-05-12

Environment tested: local checkout plus live production app/API
Tested commit: pending final rerun
Tester: Cursor cloud agent
Rollout level requested: Design partner

P0 score: pending final rerun; code-verifiable queue covered by automated checks
P1 score: pending final rerun; code-verifiable queue covered by automated checks
P2 score: not rescored
Overall readiness: pending final rerun

Scoring note: this pass upgrades command/API evidence only. It does not replace
the required browser screenshots or recordings in
`ROLLOUT_FUNCTIONALITY_CHECKLIST.md`.

Decision: Proceed with disclosed limits only after external actions are approved

Blocking issues:
- External owner confirmations in `p1_external_actions.md` must be approved before design-partner onboarding.
- Browser screenshots/recordings are still recommended for final visual proof, but core route/static/API journey coverage is now automated.

Approved deferrals:
- P0-F16 backup/restore proof: deferred pending R2 bucket/secrets and owner-approved restore drill.
- P1-F07 provider spend-cap proof: deferred pending Anthropic billing/spend-cap confirmation.
- P1-F08 external alert proof: deferred pending real alert recipient/channel confirmation.
- P1-F09 mobile/tablet visual proof: deferred pending browser QA capture.
- P1-F11 support inbox confirmation: deferred pending owner confirmation that `support@chiefriskbot.com` is live.

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
- `p1_external_actions.md` - external owner actions and deferrals.
