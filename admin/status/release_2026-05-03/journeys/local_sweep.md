# Local Journey Sweep

_Date: 2026-05-03_
_Target: `http://127.0.0.1:4173` with local SQLite API proxy to `http://127.0.0.1:8001`_
_Status: Pass locally. Staging evidence still required before production._

## Result

All checked pages reached `body:not(.mvp-app-loading)` and produced zero browser console errors in the in-app browser.

| Journey surface | Assertion target | Result |
|---|---|---|
| Home | `#home-metrics` | Populated AUM, cash, concentration, VaR, alerts |
| Assets | `#assets-kpis` | Populated AUM, positions, composition KPIs |
| Cockpit | `#cockpit-kpis` | Populated value, VaR, active risks, liquidity outlook |
| Scenarios | `#overlay-kpis` | Populated composite score, factors, alerts |
| Documents | `#documents-summary` | 5 documents, 4 parsed, 1 pending |
| Briefings | `#briefings-list` | Published weekly briefing visible |
| Liquidity | `#liquidity-kpis` | Populated calls, unfunded, distributions, net position |
| Positions | `#positions-body` | Position rows visible |
| Access | `#access-summary` | Current signed-in user/session visible |

## Follow-Up Production-Fix Verification

_Date: 2026-05-03_
_Target: same local browser/API proxy setup._

| Finding | Verification | Result |
|---|---|---|
| Briefing currency mismatch | Home and Briefings now render AUM, VaR base, and liquidity shortfall in CHF using the workspace reporting currency. | Pass locally |
| Positions table missing core values | Positions table headers now expose quantity, price, market value, source, added, and modified; the first seeded row rendered `CHF 2,184,000.00` price and `CHF 2,184,000` market value. | Pass locally |
| Liquidity contradictions | Assets projection now shows cash, net 90-day flow, projected cash, and buffer shortfall; Cockpit leads with `Buffer breach` and no longer says `None` while a buffer shortfall exists. | Pass locally |
| Observability smoke | `scripts/observability_smoke.sh` verified `/health` echoes `X-Request-Id` and `/health/synthetic-error` is disabled by default. | Pass locally |
| Browser console | In-app browser logs were empty after visiting Table, Assets, Cockpit, and Briefings. | Pass locally |

## Remaining Release Evidence

- Staging run of the same journeys.
- Screenshot capture to the per-journey paths required by `PRODUCTION_READINESS_CHECKLIST.md`.
- Destructive staging-only journeys: password reset completion, document upload/parse/review/approve, briefing generation/export, logout/login loop.
