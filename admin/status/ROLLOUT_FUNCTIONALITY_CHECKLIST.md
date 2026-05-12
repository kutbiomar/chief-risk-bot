# Rollout Functionality Checklist

_Created: 2026-05-12_
_Purpose: determine how far ChiefRiskBot is from a credible external rollout._
_Inputs reviewed: `admin/status/STATUS.md`, `admin/status/PRODUCTION_READINESS_CHECKLIST.md`, `admin/status/USER_CHECKLIST.md`, `admin/business/ChiefRiskBot_Product_Spec.md`, `admin/thinking/ARCHITECTURE.md`, current frontend pages, backend routers, and test inventory._

## Verdict format

Use this checklist before each rollout decision. A feature is not "ready" because it exists in code; it is ready when it has fresh evidence from the intended environment.

| Rollout level | Minimum bar |
|---|---|
| Internal demo | All P0 items pass locally; no broken login, navigation, seeded data, or briefing flows. |
| Design-partner rollout | All P0 items pass on production or staging with production-like auth/data; P1 items either pass or have explicit owner-approved limits. |
| Paid customer rollout | All P0 and P1 items pass with evidence; P2 items have written deferrals, support process, and monitoring coverage. |

### Scoring method

Score only rows with evidence captured in the last 7 days for the target environment.

- **2 = Ready**: implemented, tested, and evidence path attached.
- **1 = Partial**: implemented but missing fresh evidence, has known UX limits, or covers only seeded/demo data.
- **0 = Gap**: not implemented, broken, untested, or blocked by external setup.
- **N/A = Deferred**: not part of the next rollout; must include an owner-approved note.

Readiness is:

```text
readiness = ready_points / applicable_points
```

Where `ready_points` is the sum of row scores and `applicable_points` is `2 * count(non-N/A rows)`.

Suggested interpretation:

- **90-100%**: rollout candidate after final smoke test.
- **75-89%**: design-partner candidate if all P0 rows are green and limitations are disclosed.
- **50-74%**: demo-only; close or defer the largest gaps before external users depend on it.
- **<50%**: not rollout-ready.

## Current baseline from repository docs

This is a document-based baseline, not a live QA result. Re-score after running the evidence checklist below.

| Area | Baseline | Why |
|---|---|---|
| Product shell and core navigation | Partial to ready | Production status says app pages and sidebar shell were verified, but evidence is older than 7 days. |
| Auth and session flows | Partial | Supabase bearer auth and smoke tests exist; password reset/session edge cases need fresh rollout evidence. |
| Demo/family-office data path | Partial to ready | Seeded demo workspace exists and main API endpoints have passed smoke checks; verify current production seed health. |
| Portfolio/risk/liquidity views | Partial | Pages and APIs exist; latest evidence needs refresh against rollout environment. |
| Documents and extraction workflow | Partial | Backend tests exist, but production upload/parse/review/approve/delete journey needs fresh evidence. |
| Briefings and PDF export | Partial to ready | Generation/export has previous production proof; rerun before rollout. |
| Operational readiness | Partial | Health checks and smoke scripts exist; R2 backup drill and some deferred hardening remain open. |
| Customer rollout process | Partial | Legal/onboarding docs exist; support inbox, alert routing, and user-side setup need confirmation. |

### Document-only score snapshot

The row scores below produce this starting point:

| Scope | Score | Interpretation |
|---|---:|---|
| P0 external-rollout gates | 15 / 32 = 47% | Too much evidence is stale or incomplete for an external rollout decision. |
| P1 design-partner confidence | 11 / 24 = 46% | Several features exist, but support/access/ops proof is not yet strong enough. |
| P2 scale hardening | 1 / 12 = 8% | Deferred hardening is expected for v1, but should be disclosed. |
| Overall tracked readiness | 27 / 68 = 40% | Treat as demo-only until fresh evidence upgrades the P0 rows to `2`. |

This does **not** mean only 40% of the product is built. It means only 40% of the rollout checklist is currently backed by fresh, decision-grade evidence in this document.

## P0 - must pass before any external rollout

| ID | Functionality | Ready when | Score | Evidence path / command |
|---|---|---|---:|---|
| P0-F01 | Login, logout, and session restore | A seeded user can log in, refresh a protected page, call authenticated APIs, log out, and be redirected away from protected pages. | 1 | `scripts/prod_smoke.sh`; screenshots for login -> cockpit -> logout |
| P0-F02 | Broken-session handling | Expired/invalid token clears local auth state and sends the user to login without rendering stale workspace data. | 1 | Browser capture plus backend auth test output |
| P0-F03 | Main navigation shell | Sidebar links load Home, Cockpit, Assets, Liquidity, Briefings, Documents, Positions, Settings, and Access without JS console errors. | 1 | Browser QA log for `frontend-mvp/*.html` routes |
| P0-F04 | Home dashboard | Home shows AUM, cash, VaR/risk indicators, latest briefing, and no indefinite loading states for the seeded workspace. | 1 | Screenshot plus `/api/portfolio/summary` and `/api/briefings` responses |
| P0-F05 | Cockpit risk summary | Cockpit renders risk register, concentration/liquidity status, and risk narrative with data consistent with APIs. | 1 | Screenshot plus `/api/cockpit` response |
| P0-F06 | Portfolio/Assets view | Assets page shows AUM, allocation/composition, liquidity projection, and values in the workspace reporting currency. | 1 | Screenshot plus `/api/portfolio/summary` response |
| P0-F07 | Liquidity view | Liquidity page shows summary, runway/projection, and no misleading "safe" state when data is missing. | 1 | Screenshot plus `/api/liquidity/summary` response |
| P0-F08 | Positions table | User can view positions and complete the intended add/edit/delete or import path without corrupting totals. | 1 | Browser recording plus focused portfolio/import tests |
| P0-F09 | Document upload | User can upload an allowed document type/size and receives a clear success or validation error. | 1 | Browser recording plus `backend/tests/test_phase_cd.py` |
| P0-F10 | Document parsing/review | Uploaded document can be parsed, reviewed, approved, and reflected in portfolio or document state as designed. | 1 | Journey evidence for upload -> parse -> review -> approve |
| P0-F11 | Document isolation/security | A user cannot see, fetch, review, approve, or delete another workspace's documents. | 1 | `backend/tests/test_security_regressions.py` |
| P0-F12 | Briefing generation | User can generate a briefing from current workspace data and see a non-empty narrative tied to visible metrics. | 1 | Browser recording plus `/api/briefings/generate` output |
| P0-F13 | Briefing list/detail/export | Generated and prior briefings list correctly, detail pages open, and PDF export returns a valid PDF. | 1 | `scripts/prod_smoke.sh`; PDF artifact |
| P0-F14 | API health and dependency status | `/api/health` reports database and required services clearly enough for support triage. | 1 | `/api/health` response in rollout environment |
| P0-F15 | Release smoke gate | Syntax checks, backend tests, migration safety check, and rollout smoke script pass from a clean checkout. | 1 | `scripts/release_check.sh` log |
| P0-F16 | Backup and restore confidence | At least one backup artifact exists and a restore drill has been documented or explicitly deferred for the rollout level. | 0 | `admin/thinking/PRODUCTION_INFRA.md` drill row |

## P1 - required for design-partner confidence

| ID | Functionality | Ready when | Score | Evidence path / command |
|---|---|---|---:|---|
| P1-F01 | New workspace onboarding | A fresh user can register or be invited, complete onboarding, import positions/upload documents, and land in the app. | 1 | Fresh-workspace browser recording |
| P1-F02 | Password reset | Request and completion work against the active auth provider; old password fails and new password succeeds. | 1 | Browser/API evidence for reset flow |
| P1-F03 | Settings page | Workspace settings load, save intended fields, and do not expose secrets or unsupported controls. | 1 | Screenshot plus `/api/settings` response |
| P1-F04 | Access/team management | Access page behavior is explicit: invites/roles work, or the UI clearly marks the feature unavailable for v1. | 0 | Access page QA notes |
| P1-F05 | Scenario/macro overlay | Scenarios page renders factor scores, stress table, and explanation using current or seeded market data. | 1 | Screenshot plus overlay tests |
| P1-F06 | Market-data degradation | yfinance/FRED/API failures show stale-data or unavailable states rather than fabricated freshness. | 1 | Forced-failure smoke or unit test |
| P1-F07 | Cost/rate guardrails | Login limits, upload limits, AI quotas, and Anthropic spend-cap/alert process are proven. | 1 | Auth tests; quota config; provider spend-cap screenshot |
| P1-F08 | Production error visibility | A synthetic error creates a triageable alert with request ID and enough context to debug. | 1 | `scripts/observability_smoke.sh`; alert screenshot |
| P1-F09 | Mobile/tablet usability | Core pages are usable at 375, 390, 430, 768, and 1440 widths. | 1 | `admin/status/release_<date>/mobile/` screenshots |
| P1-F10 | Legal and onboarding collateral | Login disclosures, privacy/terms/data handling docs, getting-started guide, and walkthrough script are current. | 2 | `admin/business/legal/*`; `admin/business/onboarding/*` |
| P1-F11 | Support path | Users know where to ask for help; support inbox exists; first-response process is written. | 0 | Support inbox confirmation; runbook update |
| P1-F12 | Rollback path | Backend, frontend, database, and feature-flag rollback steps are documented and have a named owner. | 1 | `admin/status/PRODUCTION_READINESS_CHECKLIST.md`; release PR body |

## P2 - does not block a controlled rollout, but limits scale

| ID | Functionality | Ready when | Score | Evidence path / command |
|---|---|---|---:|---|
| P2-F01 | Hashed static asset pipeline | Shared frontend assets can be cached long-term without stale-bundle risk. | 0 | Build/deploy proof; cache headers |
| P2-F02 | Supabase PITR restore | Supabase Pro PITR is enabled and a restore drill is completed. | 0 | PITR drill log |
| P2-F03 | Slack or incident-channel alerting | Critical alerts route to a monitored channel, not only email. | 0 | Alert test screenshot |
| P2-F04 | Self-hosted fonts/icons or final CSP | CSP/font strategy is finalized and documented. | 1 | `_headers` response and CSP decision |
| P2-F05 | Automated visual regression | Key pages have repeatable browser snapshots in CI or release check. | 0 | CI artifact path |
| P2-F06 | Usage/billing readiness | Plan limits, billing state, and customer/account lifecycle are defined for paid rollout. | 0 | Product/ops decision doc |

## Rollout evidence checklist

Create a dated folder before each rollout decision:

```bash
mkdir -p "admin/status/rollout_$(date +%F)"
```

Attach or link:

- [ ] `git status --short` from the tested checkout.
- [ ] `git diff --check`.
- [ ] `node --check frontend-mvp/_app.js`.
- [ ] `node --check frontend-mvp/_shell.js`.
- [ ] `.venv/bin/pytest backend/tests -q`.
- [ ] `python3 scripts/check_destructive_migrations.py`.
- [ ] `scripts/release_check.sh 2>&1 | tee admin/status/rollout_<YYYY-MM-DD>/release_check.log`.
- [ ] `scripts/prod_smoke.sh 2>&1 | tee admin/status/rollout_<YYYY-MM-DD>/prod_smoke.log`.
- [ ] Screenshots or video for each P0 browser journey.
- [ ] One note listing known limitations that will be disclosed to users.
- [ ] One owner-approved deferral note for each P0/P1 row scored `0` or `N/A`.

## Browser journeys to record

1. Login -> Home -> Cockpit -> logout.
2. Login -> Assets -> Positions -> verify totals and currency.
3. Login -> Liquidity -> verify summary and projection.
4. Login -> Documents -> upload -> parse/review -> approve/delete.
5. Login -> Briefings -> generate -> open detail -> export PDF.
6. Fresh user/workspace -> onboarding -> import positions -> first dashboard.
7. Password reset request -> reset completion -> new password login.
8. Mobile viewport pass for Home, Cockpit, Documents, Briefings, and Positions.

## Current gap summary to update after scoring

- **Likely rollout blockers:** backup/restore proof, support inbox confirmation, access/team-management behavior, fresh P0 browser evidence.
- **Likely design-partner disclosures:** limited alerting channel, interim static-asset cache strategy, Supabase PITR deferred until paid tier, seeded/demo-data assumptions where applicable.
- **Likely non-blocking hardening:** hashed assets, visual regression automation, final billing/plan limits.

## Decision record template

Copy this block into `admin/status/rollout_<YYYY-MM-DD>/decision.md`.

```markdown
# Rollout decision - <YYYY-MM-DD>

Environment tested:
Commit:
Tester:
Rollout level requested: Internal demo / Design partner / Paid customer

P0 score:
P1 score:
P2 score:
Overall readiness:

Decision: Proceed / Proceed with disclosed limits / Do not proceed

Blocking issues:
-

Approved deferrals:
-

Evidence:
-
```
