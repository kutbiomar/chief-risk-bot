# P0/P1 External Actions and Deferrals - 2026-05-12

These items cannot be fully completed from repository code alone. They must be
confirmed by the rollout owner before design-partner onboarding.

## Required before design-partner rollout

| Checklist item | Status | Required owner action | Code/repo mitigation already in place |
|---|---|---|---|
| P0-F16 Backup and restore confidence | Deferred pending owner approval | Confirm R2 bucket/secrets, trigger `.github/workflows/backup.yml`, restore to scratch, and append drill result to `admin/thinking/PRODUCTION_INFRA.md`. | Backup workflow exists and validates required secrets before dumping/uploading. |
| P1-F07 Provider spend-cap proof | Deferred pending owner approval | Attach Anthropic monthly spend-cap screenshot or billing confirmation to the rollout folder. | App has quota/rate-limit code paths and release checks cover auth/upload guardrails. |
| P1-F08 External alert proof | Deferred pending owner approval | Confirm the real alert recipient/channel receives health-check or synthetic incident notifications. | `scripts/observability_smoke.sh` validates request-id echo and disabled synthetic endpoint state. |
| P1-F11 Support inbox confirmation | Deferred pending owner approval | Confirm `support@chiefriskbot.com` is live and monitored. | Settings now exposes `mailto:support@chiefriskbot.com`; support intake process is documented in `RUNBOOK.md`. |

## Automated evidence now covering former P0/P1 gaps

`scripts/rollout_journey_check.py` now runs a disposable local journey across:

- frontend page/data-page/static-shell contract
- fresh workspace registration
- onboarding CSV import
- portfolio summary/positions, cockpit, liquidity, overlay, settings, members APIs
- positions create/update/delete
- document upload -> parse -> review -> approve -> delete
- HITL capital-call review resolution
- briefing generate -> detail -> PDF export
- settings save and access/member profile
- password reset, old-password rejection, new-password login
- logout and invalid-token rejection

## Completed in this pass

- P1-F09 mobile/tablet visual proof is now covered by
  `usability/frontend_usability_report.md` with screenshots for desktop,
  tablet, and mobile viewports under `usability/screenshots/`.

This clears the code-verifiable P0/P1 queue. The table above remains external
evidence/owner-confirmation work rather than application code work.
