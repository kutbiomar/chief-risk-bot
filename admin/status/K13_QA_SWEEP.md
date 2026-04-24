# K13 QA Sweep Report

_Last updated: 2026-04-24_

## Scope

- Demo workspace path
- Fresh workspace path
- Signup, onboarding, cockpit, liquidity, briefings, positions, documents, settings, password reset

## Automated checks wired

- `scripts/qa_sweep.sh`
- Backend regression tests (`test_auth`, `test_phase_cd`, `test_security_regressions`, `test_health`, `test_liquidity`)
- Frontend JS syntax checks

## Local environment pass — 2026-04-24

All checks green on branch `MVP2` (latest commit `22e5cb3`):

```
$ bash scripts/qa_sweep.sh
Running backend regression suite...
31 passed, 1 warning in 14.57s
Running backend health/smoke tests...
3 passed, 1 warning in 3.13s
Checking shipped frontend scripts...
QA sweep complete.
```

Total: **34 passed, 0 failed**.

| Module | Tests | Result |
|---|---|---|
| `test_phase_cd` | 10 | ✓ pass |
| `test_auth` | 13 | ✓ pass |
| `test_security_regressions` | 8 | ✓ pass |
| `test_health` | 1 | ✓ pass |
| `test_liquidity` | 2 | ✓ pass |
| `node --check _app.js` | — | ✓ pass |
| `node --check _shell.js` | — | ✓ pass |

No P0 issues found in local pass.

## Deployed environment pass — 2026-04-24

Backend is live at `https://chief-risk-bot.fly.dev`. CI run 24893391298 deployed to staging + production (2 Fly machines, smoke checks passed).

**API health — all 5 components green:**

```json
{
  "status": "ok",
  "environment": "production",
  "components": {
    "database":        {"status": "ok", "latency_ms": 452.51},
    "supabase_auth":   {"status": "ok", "latency_ms": 394.58},
    "supabase_storage":{"status": "ok", "latency_ms": 117.43},
    "anthropic":       {"status": "ok", "latency_ms": 4251.83},
    "fred":            {"status": "ok", "latency_ms": 368.46}
  }
}
```

**Pending — demo user seed + E2E flow:**

Demo user (`cio@demo.chiefriskbot.com`) needs to be seeded via Fly console before full E2E matrix can run:

```bash
~/.fly/bin/flyctl ssh console --app [FLY_APP_NAME]
# inside the container:
python admin/demo/seed_demo.py
```

Once seeded, run:
1. Login → cockpit → liquidity → briefings → PDF export flow.
2. Log any findings as `K13.N` and close all P0 issues.
