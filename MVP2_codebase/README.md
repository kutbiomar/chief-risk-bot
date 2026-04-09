# MVP2 Codebase

This directory is a clean starting point for the revised MVP2 product: a private market intelligence platform for family offices and small funds.

## Revised Product Idea

The product focus is no longer general market risk monitoring. MVP2 is centered on four connected workflows:

1. Document ingestion for LP statements, capital calls, quarterly reports, and diligence files.
2. Reconciliation between extracted document data and system records.
3. Liquidity forecasting across commitments, capital events, and deal pipeline outflows.
4. Deterministic alerts and weekly briefings for analysts, CIOs, and COOs.

## What Changed From The Legacy MVP

- Private markets operations replaced generic portfolio risk as the core use case.
- Manual data entry is a first-class fallback, not a secondary admin tool.
- Multi-currency handling is P0 and must be designed into every model.
- Deal pipeline data must feed liquidity projections.
- AI is used for document classification and extraction, not for core alert logic.

## Recommended Structure

- `docs/`: product direction, architecture, and build sequence
- `backend/`: new domain models, routers, services, and migrations
- `frontend/`: pages and shared app shell for the revised UI

## Immediate Build Priorities

- Model funds, commitments, capital events, holdings, deals, reconciliation, liquidity, and FX.
- Enforce `workspace_id` across all tenant data for RLS-ready multi-tenancy.
- Make manual fund and capital-event entry work before any document automation.
- Build the liquidity ladder before briefing generation.

## Local Demo Path

- Run Alembic from `MVP2_codebase`: `../.venv/bin/alembic -c alembic.ini upgrade head`
- Start the backend app and open `/app/login.html`
- Demo login:
  - email: `auth@example.com`
  - password: `secret123`
- The development bootstrap seeds:
  - workspace: `demo-workspace`
  - user: `demo-user`
  - base currency: `USD`
  - reporting timezone: `UTC`

## Source Inputs

- `MVP2_SPEC.md`
- `MVP2_STATUS.md`
