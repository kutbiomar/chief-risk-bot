# K13 QA Sweep Report

_Last updated: 2026-04-25_

## Scope

- Demo workspace path
- Fresh workspace path
- Signup, onboarding, cockpit, liquidity, briefings, positions, documents, settings, password reset

## Automated checks wired

- `scripts/qa_sweep.sh`
- `scripts/prod_smoke.sh`
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

**Deployed E2E pass — 2026-04-24:**

Demo user confirmed active (`cio@demo.chiefriskbot.com` / `DemoPass2026!`).

| Endpoint | Result |
|---|---|
| `POST /api/auth/login` | 200 ✓ |
| `GET /api/cockpit` | 200 ✓ |
| `GET /api/liquidity/summary` | 200 ✓ |
| `GET /api/briefings` | 200 ✓ |
| `GET /api/documents` | 200 ✓ |
| `GET /api/briefings/{id}/export/pdf` | **200 ✓ (26,226 bytes)** |
| `https://app.chiefriskbot.com/login` | 200 ✓ (Cloudflare Pages) |

**No P0 issues. K13 complete.**

## Production runtime follow-up — 2026-04-25

Post-deploy frontend recovery work added a dedicated production smoke path:

```
$ bash scripts/prod_smoke.sh
Smoke target app: https://app.chiefriskbot.com
Smoke target api: https://api.chiefriskbot.com/api
PASS: frontend login page and CSP
PASS: api health
PASS: api login
PASS: /auth/session
PASS: /onboarding/state
PASS: /cockpit
PASS: /liquidity/summary
PASS: /briefings
PASS: /settings
PASS: /documents
Production smoke complete.
```

Additional live browser verification on 2026-04-25 confirmed:

- production login succeeds through `https://api.chiefriskbot.com/api/auth/login`
- `/`, `/cockpit`, `/liquidity`, `/briefings`, `/documents`, `/table`, `/settings`, `/access`, and `/onboarding` all reach visible `mvp-ready` state
- cockpit KPI cards hydrate after shell render
