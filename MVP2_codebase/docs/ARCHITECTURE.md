# Architecture Outline

## Backend Domains

- `models/funds.py`: `Fund`, `Commitment`
- `models/capital.py`: `CapitalEvent`
- `models/holdings.py`: `Holding`
- `models/deals.py`: `Deal`, `DealDocument`
- `models/reconciliation.py`: `ReconciliationFlag`
- `models/liquidity.py`: `LiquidityProjection`
- `models/fx.py`: `FxRate`

## Service Areas

- `services/extraction/`: classify and extract structured fields from uploaded documents
- `services/portfolio/`: aggregation and look-through exposure logic
- `services/liquidity.py`: 24-month cash flow ladder and scenario modelling
- `services/alerts.py`: deterministic rule engine
- `services/briefings.py`: weekly briefing assembly and rendering

## Router Plan

- `routers/funds.py`: CRUD for funds, commitments, capital events, holdings, and summary endpoints
- `routers/deals.py`: deal pipeline CRUD
- `routers/alerts.py`: active alerts and acknowledgements
- `routers/documents.py`: upload, processing status, reconciliation actions
- `routers/briefings.py`: weekly briefing runs and output retrieval

## Frontend Views

- `pages/onboarding/`: org setup and first fund/commitment workflow
- `pages/cockpit/`: fund summary, upcoming calls, liquidity alerts, open reconciliations
- `pages/documents/`: upload queue, document detail, reconciliation diff
- `pages/holdings/`: aggregations by asset class, geography, and sector
- `pages/liquidity/`: ladder visualization with base and stress modes
- `pages/briefings/`: weekly briefings list and detail view

## Architectural Decisions

- Use Supabase/Postgres as the core data platform.
- Keep auth, audit, scheduler, and health patterns from the legacy codebase where practical.
- Use AI only for document classification and field extraction.
- Keep core portfolio logic deterministic and auditable.
