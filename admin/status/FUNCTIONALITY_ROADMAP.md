# Functionality Roadmap and Repo Index

_Created: 2026-05-12_

This is the compact "what exists / what remains" map for follow-on development.
It indexes the codebase by product capability and keeps gap notes close to file paths.

## Product intent

ChiefRiskBot helps a family-office CIO turn portfolio positions, documents, market data, and private-market flows into a weekly risk cockpit and briefing. The current repo is a real FastAPI monolith with vanilla-JS frontends, but several collaboration, governance, and production-readiness capabilities remain unfinished or stubbed.

## Source-of-truth notes

| Question | Current answer |
|---|---|
| Backend app entry | `backend/main.py` |
| API route modules | `backend/routers/*.py`, mounted under `/api` |
| Business logic | `backend/services/` |
| DB models | `backend/models/` |
| DB migrations | `backend/migrations/versions/` |
| Tests | `backend/tests/` |
| CI/Docker frontend target | `frontend/` (`Dockerfile`, `.github/workflows/ci-cd.yml`) |
| Richer MVP/docs frontend | `frontend-mvp/` |
| Design reference | `frontend-design-ideal/` |
| Visual decision source | `frontend-design-ideal/DESIGN.md` |
| Live status | `admin/status/STATUS.md` |
| Strict release gate | `admin/status/PRODUCTION_READINESS_CHECKLIST.md` |

Important drift: many admin docs still describe `frontend-mvp/` as the active surface, while CI/Docker deploy `frontend/`. Resolve this before feature UI work so contracts and screenshots do not split again.

## Implemented capability map

### Identity, workspace, and access

| Capability | Status | Main files |
|---|---|---|
| Local registration/login/session/logout | Implemented | `backend/routers/auth.py`, `backend/services/auth/*` |
| Supabase password auth bridge | Implemented | `backend/routers/auth.py`, `backend/services/auth/supabase.py` |
| Bearer token + cookie/CSRF clients | Implemented | `backend/routers/auth.py`, `frontend/_api.js` |
| API keys | Implemented | `backend/routers/settings.py`, `backend/models/auth.py` |
| Password reset tokens | Token lifecycle implemented; email delivery missing | `backend/routers/auth.py` |
| TOTP | Explicitly disabled | `backend/routers/auth.py` |
| RBAC | Roles stored; role enforcement incomplete | `backend/models/auth.py`, `backend/routers/*.py` |
| Members/invites | Members mutate; invites stubbed | `backend/routers/settings.py` |

### Portfolio and data ingestion

| Capability | Status | Main files |
|---|---|---|
| Portfolio snapshots and positions | Implemented | `backend/routers/portfolio.py`, `backend/models/portfolio.py` |
| CSV import | Implemented, synchronous job semantics | `backend/routers/ingest.py`, `backend/services/ingest/csv_parser.py` |
| Document upload/list/delete | Implemented with size/MIME checks | `backend/routers/documents.py`, `backend/services/documents.py` |
| Document parse/review/apply | Implemented | `backend/services/ingest/pipeline.py`, `backend/services/ingest/agents/*` |
| Supabase/local storage abstraction | Implemented | `backend/services/storage.py` |
| Custodian/API source connectors | Not implemented | planned only in docs/UI reference |
| Audit read/export | Not implemented | audit writer exists in `backend/services/audit/logger.py` |

### Analytics, risk, and briefing

| Capability | Status | Main files |
|---|---|---|
| Market/macro enrichment | Implemented with deterministic fallback | `backend/services/enrichment.py`, `backend/routers/market.py` |
| VaR compute/current result | Implemented | `backend/routers/var.py`, `backend/services/var.py`, `backend/services/analytics/*` |
| VaR history/contribution endpoints | Not implemented as standalone endpoints | `backend/routers/var.py` |
| Risk agent run/scores/flags/register | Implemented | `backend/routers/risk.py`, `backend/services/risk.py` |
| Risk job status endpoint | Not implemented | `backend/routers/risk.py` |
| Macro overlay/regime/scenarios | Implemented | `backend/routers/overlay.py`, `backend/services/overlay/*` |
| Liquidity ladder | Implemented | `backend/routers/liquidity.py`, `backend/services/liquidity.py` |
| Private-market fund CRUD | Not implemented | model exists in `backend/models/private_markets.py` |
| Briefing generation/list/detail/publish/PDF | Implemented | `backend/routers/briefings.py`, `backend/services/briefings.py` |
| Global AI spend evidence/alerting | Partially implemented | settings + readiness checklist |

### Operations and production

| Capability | Status | Main files |
|---|---|---|
| JSON logging, request IDs, metrics | Implemented | `backend/main.py`, `backend/services/observability.py` |
| Health endpoint | Implemented | `backend/routers/health.py` |
| Scheduler | Implemented in-process | `backend/services/scheduler.py` |
| CI tests and migration guard | Implemented | `.github/workflows/ci-cd.yml`, `scripts/check_destructive_migrations.py` |
| Staging/prod smoke scripts | Implemented | `scripts/staging_smoke.sh`, `scripts/prod_smoke.sh` |
| Nightly backup workflow | Wired; restore drill pending | `.github/workflows/backup.yml`, `admin/thinking/PRODUCTION_INFRA.md` |
| External alert proof | Pending | `admin/status/PRODUCTION_READINESS_CHECKLIST.md` |

## Frontend surface map

| Tree | Role | Notes |
|---|---|---|
| `frontend/` | Current deploy target in CI/Docker | API-wired pages for dashboard, cockpit, assets, positions, briefings, documents, liquidity, settings, login, onboarding |
| `frontend-mvp/` | Richer MVP surface | Adds scenarios/access/legal and a briefing drawer; many status docs and visual audits reference this tree |
| `frontend-design-ideal/` | Static design reference | Includes sources, markets, members, audit, components; not wired to API |

Key frontend gaps:

- Pick and document the canonical app tree before new UI work.
- Align onboarding contracts (`/onboarding/status` vs `/onboarding/state`).
- Wire or remove placeholder shell controls such as notifications/help.
- Productize design-reference screens that matter: sources, markets, members, audit.
- Replace MVP hardcoded FX rates with server-provided reporting currency/rates.

## Priority roadmap

### P0: Trust, safety, and release integrity

1. **Resolve canonical frontend**
   - Decide whether `frontend/` or `frontend-mvp/` is the active product surface.
   - Update Dockerfile, CI, Cloudflare deploy commands, status docs, and smoke checks to match.
   - Keep one client auth/storage convention.

2. **Enforce RBAC**
   - Add shared dependencies such as `require_role("owner", "admin")`.
   - Gate settings, API keys, members, portfolio mutations, briefing publish, overlay/risk runs, and destructive document actions.
   - Add tests for owner/admin/viewer behavior and cross-workspace denial.

3. **Finish production-readiness evidence**
   - Attach staging CI smoke output.
   - Complete Top 10 journey screenshots/sign-off.
   - Run backup/restore drill and log the row in `PRODUCTION_INFRA.md`.
   - Fire and capture a synthetic observability alert.

4. **Replace reset-token-only password recovery**
   - Add transactional email provider/config.
   - Send reset links without exposing tokens in logs or UI.
   - Test local and Supabase auth modes.

### P1: Product completeness for design partners

1. **Real invites and member lifecycle**
   - Add invite model, token, expiry, accept/revoke flow, and email.
   - Replace `pending-{email}` responses in `settings.py`.

2. **Audit log API**
   - Add `GET /api/audit` filters by actor/action/entity/date.
   - Add export or CSV endpoint if needed for committees.
   - Extend audit writes beyond portfolio mutations to settings, documents, briefings, API keys, and member changes.

3. **Sources/connectivity screen**
   - Model custodians/data sources, refresh state, last successful ingest, and error messages.
   - Start with manual/CSV/document sources before OAuth/custodian APIs.

4. **Risk and VaR completion**
   - Add risk job status or convert runs to honest synchronous actions.
   - Add VaR history endpoint and a stable contributions payload for UI charts.

5. **Private markets CRUD**
   - Expose funds, commitments, and capital events.
   - Connect private-market edits directly to the liquidity ladder and document extraction approvals.

### P2: Platform hardening

1. **Billing**
   - Replace hardcoded Stripe test URL with config/integration or hide the portal until enabled.

2. **Scheduler durability**
   - Decide whether in-process APScheduler is enough for single-instance Fly.
   - If multi-instance, add persistence/locking or move to external jobs.

3. **Notifications**
   - Implement notification/help shell actions or remove them.
   - Consider briefing-ready, ingest-failed, backup-failed, and alert-threshold events.

4. **Cost controls**
   - Surface global Anthropic budget usage and alert thresholds.
   - Add operational evidence for cap enforcement.

5. **CSP/font hardening**
   - Decide whether to self-host fonts/icons.
   - Tighten `frontend*/_headers` if self-hosting lands.

### P3: Maintainability and polish

1. **OpenAPI/client contract**
   - Prefer response models over untyped dicts for high-traffic routes.
   - Keep `backend/tests/test_frontend_contract.py` updated with the canonical frontend.

2. **Service extraction**
   - Move shared cockpit/risk-register composition out of router-to-router calls.
   - Consolidate duplicate document parsing header maps.

3. **Frontend modularity**
   - Keep large vanilla JS files indexed by section comments or split by page once the canonical tree is chosen.
   - Keep design tokens aligned with `DESIGN.md`.

4. **Spec hygiene**
   - Mark aspirational sections in `admin/thinking/ARCHITECTURE.md`.
   - Keep this roadmap and readiness checklist linked from PR descriptions for product work.

## Known stubs and mismatch index

| Area | File | Why it matters |
|---|---|---|
| Invites | `backend/routers/settings.py` | Returns fake pending invite IDs; no persistence or accept flow |
| Billing | `backend/routers/settings.py` | Hardcoded Stripe test portal |
| TOTP | `backend/routers/auth.py` | Schema exists but verify endpoint returns disabled |
| Password reset email | `backend/routers/auth.py` | Token lifecycle exists; no delivery subsystem |
| Role authorization | `backend/routers/*.py` | Authenticated users can reach most mutating endpoints unless route-specific checks exist |
| Risk job status | `backend/routers/risk.py` | Docs imply async status; route only returns immediate run output |
| VaR history | `backend/routers/var.py` | Current/compute only; no trend/history route |
| Audit read API | `backend/services/audit/logger.py` | Writer exists; no UI/API to review evidence |
| Frontend authority | `frontend/`, `frontend-mvp/` | CI/Docker and status docs point at different trees |
| Onboarding states | `backend/routers/onboarding.py`, `frontend/_app.js` | Main frontend expects states the status endpoint does not return |

## Suggested next development slices

1. Canonical frontend decision + docs/CI/deploy alignment.
2. RBAC dependency + tests around settings/API keys/members/portfolio mutations.
3. Real invite model and accept flow.
4. Audit read API and settings/document/briefing audit coverage.
5. Sources screen API foundation.
6. VaR history + risk job status cleanup.
7. Backup/restore and staging journey evidence.

Each slice should include targeted tests and one small status-doc update. Avoid broad refactors until the frontend source of truth is resolved.
