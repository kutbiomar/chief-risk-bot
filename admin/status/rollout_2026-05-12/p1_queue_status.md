# P0/P1 Queue Status - 2026-05-12

Status after frontend usability sweep and final evidence run.

**Evidence bundle:** see `decision.md` (“Evidence (retained artifacts)”). Typical citations below use `release_check_with_rollout_journey.log`, `release_check_after_usability.log`, `prod_smoke_final.log`, `observability_smoke_final.log`, and `usability/frontend_usability_report.md`.

## P0 queue

| ID | Status | Evidence |
|---|---|---|
| P0-F01 Login, logout, session restore | Clear in code; production bearer flow clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F02 Broken-session handling | Clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` (invalid bearer rejection) |
| P0-F03 Main navigation shell | Clear for static contract and production routes | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F04 Home dashboard | Clear for production route/API availability | `prod_smoke_final.log`; rollout journey portfolio summary |
| P0-F05 Cockpit risk summary | Clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F06 Portfolio/Assets view | Clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F07 Liquidity view | Clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F08 Positions table | Clear | `release_check_with_rollout_journey.log` (positions create/update/delete) |
| P0-F09 Document upload | Clear | `release_check_with_rollout_journey.log` |
| P0-F10 Document parsing/review | Clear | `release_check_with_rollout_journey.log` (parse/review/approve/delete, HITL) |
| P0-F11 Document isolation/security | Clear | `release_check_with_rollout_journey.log`; backend tests in release check |
| P0-F12 Briefing generation | Clear locally; production generation intentionally not triggered by smoke | `release_check_with_rollout_journey.log` |
| P0-F13 Briefing list/detail/export | Clear | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P0-F14 API health/dependencies | Clear | `prod_smoke_final.log`; `observability_smoke_final.log` |
| P0-F15 Release smoke gate | Clear | `release_check_after_usability.log` |
| P0-F16 Backup/restore confidence | Deferred external action | `p1_external_actions.md`; `admin/thinking/PRODUCTION_INFRA.md` |

## P1 queue

| ID | Status | Evidence |
|---|---|---|
| P1-F01 New workspace onboarding | Clear | `release_check_with_rollout_journey.log` (register + onboarding CSV import) |
| P1-F02 Password reset | Clear locally; staging destructive reset remains credential-gated | `release_check_with_rollout_journey.log`; `p1_external_actions.md` |
| P1-F03 Settings page | Clear | `release_check_with_rollout_journey.log`; support card in `frontend-mvp/settings.html` |
| P1-F04 Access/team management | Clear for v1 scope | Access page copy; `/settings/members` in journey/smoke |
| P1-F05 Scenario/macro overlay | Clear for contract; live 5xx triage is API-side | `release_check_with_rollout_journey.log`; `prod_smoke_final.log` |
| P1-F06 Market-data degradation | Clear for no-key local fallback and API availability | `release_check_with_rollout_journey.log`; release backend tests |
| P1-F07 Cost/rate guardrails | Code clear; provider spend-cap proof deferred | Release backend tests; `p1_external_actions.md` |
| P1-F08 Production error visibility | Code clear; real external alert proof deferred | `observability_smoke_final.log`; `p1_external_actions.md` |
| P1-F09 Mobile/tablet usability | Clear | `usability/frontend_usability_report.md` |
| P1-F10 Legal/onboarding collateral | Clear | `admin/business/legal/*`; `admin/business/onboarding/*` |
| P1-F11 Support path | Code/docs clear; inbox confirmation deferred | Settings support mailto; `RUNBOOK.md`; `p1_external_actions.md` |
| P1-F12 Rollback path | Clear | `PRODUCTION_READINESS_CHECKLIST.md`; `RUNBOOK.md` |

## Summary

The P0/P1 application-code and frontend-usability queue is clear. Remaining rollout work is external evidence and owner confirmation, not missing repository implementation.
