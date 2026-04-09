# Build Sequence

Status key:

- `[x]` complete
- `[~]` scaffolded or partial
- `[ ]` not started

## Current State

The MVP2 scaffold now has:

- core SQLAlchemy models
- Alembic migration scaffolding
- CRUD routers for funds, commitments, capital events, holdings, deals
- aggregation, liquidity, and alert service scaffolds
- document upload/parse/reconcile scaffolds
- weekly briefing generate/list/detail/publish/export scaffolds

It does not yet have:

- real Claude extraction
- production auth/session integration
- real PDF export
- frontend implementation
- onboarding
- payment
- full test coverage

## Phase 1 — Foundation

- `[x]` Define all core models.
- `[x]` Add FX support from day one.
- `[x]` Add audit coverage for cell-level edits.
- `[x]` Add migrations with `workspace_id` on every tenant table.
- `[~]` Embed RLS intent in migration.
  Current state: PostgreSQL-only policy hooks exist in the MVP2 migration scaffold.
  Remaining: validate and execute this against actual Supabase/Postgres, not just SQLite/local smoke runs.
- `[~]` Adapt deps and app wiring.
  Current state: local MVP2 dependency and app bootstrapping are present.
  Remaining: replace placeholder header-based user context with real auth/session dependencies.
- `[ ]` Reuse/copy auth models, jobs model, audit chain service, scheduler, settings router, and health router from the legacy codebase into MVP2.

## Phase 2 — Manual Data Entry

- `[x]` Build CRUD flows for funds, commitments, capital events, holdings, and deals.
- `[x]` Expose `/api/portfolio/summary` and `/api/portfolio/liquidity`.
- `[~]` Confirm the product is usable before document ingestion.
  Current state: backend-only verification exists via direct TestClient smoke runs.
  Remaining: frontend/manual-entry UI and role-aware audit logging.
- `[ ]` Adapt the frontend table editor in `frontend-mvp/_app.js` for MVP2 entities.
- `[ ]` Add CSV-paste/bulk import support for fund and commitment workflows.
- `[ ]` Record cell-level audit events from the CRUD endpoints.

## Phase 3 — Cash Flow Ladder And Holdings View

- `[x]` Implement `summarize_funds`, `summarize_capital_events`, and `summarize_holdings`.
- `[x]` Implement base and stress liquidity ladder scaffolding.
- `[x]` Implement deterministic alert scaffolding.
- `[x]` Include `Deal.target_commitment` pipeline outflows in liquidity logic.
- `[x]` Include recallable-distribution treatment in liquidity logic.
- `[~]` Validate the liquidity-gap workflow end to end.
  Current state: backend generation works.
  Remaining: realistic scenarios, configurable liquidity buffer, and UI validation.
- `[ ]` Build cockpit/dashboard frontend.
- `[ ]` Build liquidity ladder frontend.
- `[ ]` Add concentration and look-through exposure logic beyond current simple grouping.

## Phase 4 — Document Ingestion

- `[~]` Add document classification.
  Current state: deterministic keyword classifier exists.
  Remaining: Claude classification prompt and confidence handling.
- `[~]` Add document extraction per type.
  Current state: deterministic fallback extractors exist for capital calls, LP statements, quarterly reports, and DD docs.
  Remaining: real structured extraction with field-level confidence and better schema coverage.
- `[~]` Add reconciliation flow.
  Current state: flags are created and `/documents/{id}/reconcile` exists.
  Remaining: true entity matching, better variance logic, and accept/override application into system records.
- `[x]` Adapt the documents router with reconciliation endpoints.
- `[~]` Adapt the document service.
  Current state: local file storage and parse pipeline exist.
  Remaining: production storage backend, robust text extraction, async processing, and golden-dataset evaluation.
- `[ ]` Build reconciliation diff UI.
- `[ ]` Create the golden dataset and measure precision/recall targets.
- `[ ]` Log extraction results against human-corrected values for prompt iteration.

## Phase 5 — Weekly Briefing

- `[x]` Adapt the briefing service to funds/capital events/alerts/deals/liquidity.
- `[x]` Adapt the briefing router to `WeeklyBriefing`.
- `[~]` Add export support.
  Current state: `/export/pdf` returns a formatted HTML export stub.
  Remaining: actual PDF generation, likely via WeasyPrint.
- `[ ]` Build briefing frontend.
- `[ ]` Send briefing by email.
- `[ ]` Test the full flow: upload doc → extract → approve → briefing generated → sent by email.
- `[ ]` Reintroduce Claude-based narrative generation using the new briefing payload and prompt.

## Phase 6 — Onboarding And Polish

- `[ ]` Adapt onboarding wizard to fund setup flow.
- `[ ]` Write onboarding router adaptations.
- `[ ]` Payment integration.
- `[ ]` Final QA across all journeys.

## Additional Tasks From MVP2_STATUS.md

These are explicit remaining tasks or gaps still implied by the source status doc:

- `[ ]` Add config support for `supabase_url`, `supabase_key`, SMTP/email settings, document storage backend, reconciliation variance threshold, and capital-call alert window.
- `[ ]` Add dependency providers such as `get_claude_client()` and `get_document_processor()`.
- `[ ]` Reuse the legacy scheduler approach and move weekly briefing/document processing onto FastAPI background tasks and `pg_cron`, not Celery/Redis.
- `[ ]` Reuse the existing auth/session stack instead of the current placeholder header auth.
- `[ ]` Reuse or port the settings and health routes.
- `[ ]` Build the MVP2 cockpit route to aggregate funds, upcoming calls, alerts, and deals.
- `[ ]` Build the frontend pages called out in the status doc: `cockpit.html`, `documents.html`, `briefings.html`, `onboarding.html`, and the shared JS wiring in `_app.js`.
- `[ ]` Add real FX-rate sourcing from ECB or exchangerate-api and persist the conversion rate used at ingestion time.
- `[ ]` Ensure org-level base currency is defined in workspace settings and used consistently for display values.
- `[ ]` Add role-aware access control and eventual Supabase RLS validation in the real deployment target.

## Recommended Next Order

1. Replace placeholder auth/deps/config with the real reusable backend infrastructure from the legacy app.
2. Finish the briefing export path with real PDF generation and email delivery.
3. Upgrade document ingestion from deterministic fallback logic to real Claude extraction plus evaluation.
4. Start the frontend pages, beginning with cockpit, documents, and briefings.
