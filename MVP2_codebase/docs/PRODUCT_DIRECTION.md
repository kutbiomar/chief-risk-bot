# Product Direction

## Positioning

ChiefRiskBot MVP2 is a private market intelligence platform for family offices and small funds. Its main job is to remove the weekly manual scramble required to consolidate PE, VC, hedge fund, and real-estate reporting into a decision-ready view.

## Core User Promise

"You think you're diversified and liquid. We show you whether you actually are."

## Primary Jobs To Be Done

- Upload messy private market documents and extract structured data.
- Maintain accurate fund, commitment, holding, and capital-event records.
- Reconcile incoming statements against the current system state.
- Project liquidity over the next 24 months under base and stress scenarios.
- Surface alerts before Monday investment meetings.

## Product Boundaries

Included in MVP2:

- Fund and commitment tracking
- Capital call and distribution tracking
- Holdings aggregation by asset class, geography, and sector
- Reconciliation workflow
- Liquidity ladder and gap detection
- Deal pipeline tracking
- Weekly briefings

Explicitly out of P0:

- Live market-data-heavy workflows
- VaR for private assets
- Celery and Redis job infrastructure
- Email ingestion unless demanded by a launch customer

## Non-Negotiable Design Constraints

- Multi-currency support is P0.
- Every tenant table needs `workspace_id`.
- Original amounts and converted amounts must both be retained.
- Recallable distributions must not be treated as immediately liquid.
- Alerts should be deterministic and explainable.
