# MVP2 Status
_Last updated: 2026-04-09_

---

## Current state

Phases A–D complete (auth, ingest, VaR, risk agents, briefings, document flow, cockpit).
Phase E (macro overlay, factor taxonomy, multi-agent extraction) complete.
Phase F (frontend: overlay page, factor tag editor, doc review UI, parse progress) complete.
Demo works end-to-end against local SQLite with 15 seeded positions.

**Pre-land review complete (2026-04-09).** 8 items auto-fixed. 9 critical issues still block ship.
See `admin/status/codex_log` Phase G refresh for the latest findings and fix specs.

### Blocking (P0 — fix before `/GSship`)
- G1: TOTP bypass (`auth.py:216` — hardcoded `"000000"`)
- G2: Default `SECRET_KEY="replace-me"` passes validation outside development
- G3: `asyncio.run()` crash in document parse pipeline under Uvicorn
- G4: CSRF missing on all state-mutating routes except logout
- G5: Snapshot `is_current` race condition (no SELECT FOR UPDATE)
- G6: API key resolves to oldest workspace user, not key owner
- G7: N+1 price-cache queries in enrichment and market endpoints
- G8: Zero workspace isolation tests (cross-tenant IDOR invisible)
- G9: No unauthenticated-access tests

MVP2 adds three new work streams on top of the working foundation:
1. **Factor taxonomy + data model** (schema-first)
2. **Macro risk overlay** (daily factor scoring, AUM triangulation, enhanced VaR)
3. **Multi-agent extraction pipeline** (layout-aware parsing, specialist agents, HITL)

Reference docs (read these before any E-phase task):
- `admin/thinking/MACRO_RISK_OVERLAY.md` — overlay architecture, factor taxonomy, VaR design
- `admin/thinking/EXTRACTION_STRATEGY.md` — extraction pipeline, agent specs, HITL design
- `admin/thinking/ARCHITECTURE.md` — canonical schema + routes (updated for MVP2)
- `MVP2_SPEC.md` — full feature spec (updated for MVP2)

---

## Task queue

MVP2 task queue is clear as of 2026-04-09. No pending items remain in this status file.
Phase G blocking review work is tracked above under `Blocking (P0 — fix before /GSship)`.

---

## Phase E — Completed tasks

| # | Task | Scope | Priority |
|---|------|-------|----------|
| ~~E1~~ | ~~Factor taxonomy schema + migration~~ | ✅ Done 2026-04-09. 8 proxy baskets, 6 stress scenarios seeded. Factor tag columns on positions (nullable). Migration `20260409_000004` applied. | ~~P0~~ |
| ~~E2~~ | ~~Signal collection + factor scoring~~ | ✅ Done 2026-04-09. Deterministic scoring live. `/api/overlay/factors` returning scored rows. | ~~P0~~ |
| ~~E3~~ | ~~Regime detector + proxy basket VaR~~ | ✅ Done 2026-04-09. Regime: `stress` (VIX trigger). Private VaR labelled `Estimated — proxy basket method`. | ~~P0~~ |
| ~~E4~~ | ~~Risk propagator + AUM triangulation endpoint~~ | ✅ Done 2026-04-09. `/api/overlay/aum-triangulation`, `/api/overlay/regime`, `/api/overlay/factors` all 200. Cockpit `overlay_summary` live with composite score + top risk factors. | ~~P0~~ |
| ~~E5~~ | ~~Stress scenario engine + alert engine~~ | ✅ Done 2026-04-09. `stress_scenarios.py` and `alert_engine.py` live. `/api/overlay/stress` returns 6 scenarios plus alerts. Cockpit merges overlay alerts into the active risk register. | ~~P1~~ |
| ~~E6~~ | ~~Overlay pipeline + scheduler~~ | ✅ Done 2026-04-09. `services/overlay/pipeline.py` live. Daily overlay refresh uses FastAPI lifespan scheduler + `async_jobs`, not Celery. `/api/overlay/run` returns tracked on-demand runs. | ~~P1~~ |
| ~~E7~~ | ~~Sentiment agent~~ | ✅ Done 2026-04-09. `services/overlay/sentiment_agent.py` applies a bounded `±10%` modifier to factor scores, exposed via `/api/overlay/factors`, with persisted sentiment metadata. | ~~P2~~ |
| ~~E8~~ | ~~Multi-agent extraction pipeline~~ | ✅ Done 2026-04-09. Layout-aware parse wired into `POST /api/documents/{id}/parse` with `librarian`, `accountant`, `risk_officer`, `treasury`, and `reconciliation`. Wire instructions remain HITL, provider-backed Azure/Opus hooks are optional, and review artifacts now persist separately from row confidence. | ~~P1~~ |
| ~~E9~~ | ~~AUM Triangulation frontend view~~ | ✅ Done 2026-04-09. Cockpit renders factor table, regime indicator, stress scenarios, overlay refresh, and triangulation summary from live overlay APIs. | ~~P1~~ |

---

## Build order (Phase E)

```
E1 (schema) → E2 (signals + scoring) → E3 (regime + proxy VaR)
            → E4 (propagator + API)  → E5 (stress + alerts)
            → E6 (worker)            → E9 (frontend)
            → E8 (extraction)        → E7 (sentiment — last)
```

Phase E build order was executed successfully on 2026-04-09.

---

## New API routes (Phase E)

```
POST   /api/overlay/run                   # On-demand overlay run (async job)
GET    /api/overlay/factors               # All FactorScore rows for today
GET    /api/overlay/aum-triangulation     # AUM × factor exposure × risk score
GET    /api/overlay/regime                # Current regime + trigger conditions
GET    /api/overlay/stress                # Latest stress scenario results
GET    /api/documents/{id}/review         # Review extraction artifacts + unresolved field reviews
PATCH  /api/documents/{id}/review         # Save manual corrections and resolve review flags
```

Extend: `GET /api/cockpit` → add `overlay_summary: { regime, composite_score, top_risk_factors[], as_of_date }`

---

## New files (Phase E)

```
backend/services/overlay/
    pipeline.py           # Full overlay orchestrator
    signal_collector.py   # yfinance + FRED + commodity daily fetch
    factor_scorer.py      # z-score → 0–100 factor scores
    sentiment_agent.py    # LLM news → sector sentiment modifier (E7)
    regime_detector.py    # VIX + credit spread → risk regime
    propagator.py         # Factor scores × AUM → portfolio risk signal
    proxy_baskets.py      # ProxyBasket registry + volatility computation
    stress_scenarios.py   # Named shocks → estimated $ portfolio impact
    alert_engine.py       # Threshold checks → risk_flags + notifications

backend/services/analytics/
    factor_var.py         # Factor attribution + regime-aware VaR windowing

backend/services/ingest/
    layout_parser.py      # Azure Document Intelligence wrapper
    agents/
        librarian.py      # Document classification (claude-sonnet-4-6)
        accountant.py     # NAV / commitments extraction
        risk_officer.py   # Sector exposure + factor tag population
        treasury.py       # Dates + wire instructions
        reconciliation.py # Cross-document validation (claude-opus-4-6)

backend/migrations/versions/
    20260409_000004_mvp2_overlay_slice1.py
    20260409_000005_extraction_artifacts.py

backend/routers/
    overlay.py            # New router for /api/overlay/* routes
```

---

## Key constraints (don't revisit)

- Private VaR label is non-removable: `"Estimated — proxy basket method"`
- Wire instructions: always HITL regardless of extraction confidence
- Reconciliation agent: `claude-opus-4-6` only — do not downgrade
- Sentiment agent is a ±10% modifier — it cannot override a primary factor score
- Regime switch always triggers immediate notification + VaR recompute
- Factor tag columns on `positions` are nullable — backwards-compatible with existing positions
- MVP2 execution model is FastAPI + APScheduler + `async_jobs`; no Celery worker was added
