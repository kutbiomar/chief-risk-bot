# Rollout decision - 2026-05-12

Environment tested: local checkout plus live production app/API
Tested commit: 9383027
Tester: Cursor cloud agent
Rollout level requested: Design partner

P0 score: 30 / 30 applicable code-verifiable points; P0-F16 deferred pending owner approval
P1 score: 18 / 18 applicable code/usability-verifiable points; external proof items deferred pending owner approval
P2 score: not rescored
Overall readiness: P0/P1 code queue clear; rollout still depends on approved external actions

Scoring note: `scripts/rollout_journey_check.py` now covers the code-verifiable
P0/P1 journey queue in a disposable local environment, while `prod_smoke.sh`
covers live production route/API/briefing-PDF availability. The remaining
items are external confirmations or visual artifacts listed in
`p1_external_actions.md`.

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

## Evidence (retained artifacts)

Interim diagnostic logs from the rollout sweep were removed from the repository to reduce duplication. The following paths remain authoritative:

- `baseline_environment.txt`
- `release_check_with_rollout_journey.log` — local `scripts/release_check.sh` including `scripts/rollout_journey_check.py`
- `release_check_after_usability.log` — release gate after frontend usability / Playwright tooling updates
- `prod_smoke_final.log` — live production smoke (routes, API, briefing detail, PDF export)
- `observability_smoke_final.log` — live request-id and synthetic-endpoint checks
- `usability/frontend_usability_report.md` and `usability/frontend_usability_results.json` — 50 viewport/page combinations PASS (overlay 5xx noted as API-side)
- `p1_queue_status.md`, `p1_external_actions.md`, and this `decision.md`
