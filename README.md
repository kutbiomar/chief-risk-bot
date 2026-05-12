# ChiefRiskBot

AI-powered risk briefing and monitoring platform for family-office CIOs.
FastAPI serves the API; vanilla HTML/CSS/JS serves the app.

## Start here

- Live project state: `admin/status/STATUS.md`
- Production gate checklist: `admin/status/PRODUCTION_READINESS_CHECKLIST.md`
- Functionality gap roadmap: `admin/status/FUNCTIONALITY_ROADMAP.md`
- Continuous improvement loop: `admin/status/IMPROVEMENT_LOOP.md`
- Design system: `frontend-design-ideal/DESIGN.md`
- Architecture reference: `admin/thinking/ARCHITECTURE.md`
- Operations runbook: `admin/thinking/RUNBOOK.md`

## Repo map

| Path | Purpose |
|---|---|
| `backend/` | FastAPI app, routers, SQLAlchemy models, services, Alembic migrations, tests |
| `frontend/` | Current CI/Docker/Cloudflare deploy target in this branch |
| `frontend-mvp/` | Richer MVP UI referenced by many status docs; reconcile before UI work |
| `frontend-design-ideal/` | Static design reference and visual north star, not API-wired |
| `admin/status/` | Current status, readiness checklists, release evidence |
| `admin/thinking/` | Architecture, infra, product, and implementation specs |
| `admin/business/` | Strategy, user jobs, legal, onboarding collateral |
| `scripts/` | Release, smoke, migration, QA, and observability checks |

## Local checks

```bash
pip install -e .[dev]
pytest backend/tests -q
node --check frontend/_api.js frontend/_app.js frontend/_shell.js
python scripts/check_destructive_migrations.py
```

Use `scripts/release_check.sh` before release branches. Visual/UI work must stay aligned with `frontend-design-ideal/DESIGN.md`.

## Optional improvement loop

The repeatable agent prompt lives in `admin/status/IMPROVEMENT_LOOP_PROMPT.md`.
To run it on a 10-minute locked loop, configure the agent command and start:

```bash
AGENT_LOOP_COMMAND='cursor-agent run --autonomous' admin/agent_improvement_loop.sh
```

After each successful task, the loop pushes the working branch, merges it into `main`, pushes `main`, and returns to the working branch. If integration fails for 15 minutes, it restores that loop's code changes and commits a failure log. The loop expires after 3 days and must then be invoked again. See `admin/status/IMPROVEMENT_LOOP.md` for context-cleanup hooks and guardrails.
