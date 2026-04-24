# Codebase Status — ARCHIVED

_Last updated: 2026-04-15_  
_Archived: 2026-04-13_

**See `STATUS.md` for current project status.**

This file is kept for historical reference only. It contains the Phase A–D planning that has been completed and superseded by subsequent phases.

---

## Quick reference

**Tech stack:**
- Framework: FastAPI + uvicorn
- ORM: SQLAlchemy 2.0 + Alembic
- DB: SQLite (demo), Postgres (prod)
- Market: yfinance + FRED API
- AI: Anthropic Claude SDK
- Scheduler: APScheduler

**Key paths:**
- `admin/thinking/ARCHITECTURE.md` — **Canonical** (schema, routes, auth)
- `admin/thinking/BACKEND_PLAN.md` — Rationale only (methodology, rubrics)
- `frontend-design-ideal/DESIGN.md` — Design system (palette, typography)
- `backend/models/` — SQLAlchemy ORM
- `backend/services/` — Business logic
- `backend/routers/` — FastAPI routes
- `backend/tests/` — pytest suite
- `frontend-mvp/` — Working UI (8 pages)
- `admin/demo/seed_demo.py` — Demo data loader

**File organization:**
```
frontend-design-ideal/     # Design reference (not active UI)
frontend-mvp/              # Working MVP frontend
backend/                   # FastAPI backend
admin/
  thinking/                # Architecture docs
  business/                # Product spec
  demo/                    # Demo tooling
  status/                  # Project status (this directory)
```

---

## What changed

Phases A–D built the backend foundation (auth, VaR, briefings, documents).  
Phases E–J added overlay/extraction/liquidity and frontend UI.  
This archive is now superseded twice:

- first by the offline-demo-oriented MVP closeout from 2026-04-10
- then by the 2026-04-15 functionalization effort that removed the fixture runtime path and moved the app toward Supabase-backed auth, DB, and storage

See `STATUS.md` for the live project state and `codex_log` for the 2026-04-15 Supabase cutover record.
