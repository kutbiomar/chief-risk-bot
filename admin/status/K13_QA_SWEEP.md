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

## Deployed environment pass

Status: **Pending** — blocked on `DEPLOY_ENABLED=true` (requires Fly + Cloudflare provisioning from USER_CHECKLIST items 2–3).

Required before launch:

1. Run full matrix against staging deployment.
2. Repeat against production candidate build.
3. Log any findings as `K13.N` and close all P0 issues.
