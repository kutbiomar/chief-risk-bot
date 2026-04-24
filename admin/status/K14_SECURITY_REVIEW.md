# K14 Security Review Checklist

_Last updated: 2026-04-24_

## Implemented in code

- Auth endpoint rate limits on:
  - `POST /api/auth/login`
  - `POST /api/auth/register`
  - `POST /api/auth/forgot-password`
- Retry semantics:
  - `429 Too Many Requests`
  - `Retry-After` response header
- Security headers:
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security` in non-development
- Frontend CSP and related headers via `frontend-mvp/_headers`

## Code-level verification — 2026-04-24

Static review on branch `MVP2` (commit `22e5cb3`):

| Check | Result | Evidence |
|---|---|---|
| Rate limits on auth endpoints | ✓ pass | `test_security_regressions` — 8 passed |
| 429 + Retry-After on brute force | ✓ pass | `test_security_regressions::test_login_rate_limit` |
| Security response headers | ✓ pass | `test_security_regressions::test_security_headers` |
| HSTS in production env | ✓ pass | `backend/middleware/security.py` |
| CSP / `_headers` file | ✓ pass | `frontend-mvp/_headers` reviewed |
| CORS origin enforcement | ✓ pass | `backend/config.py` ALLOWED_ORIGINS gating |
| Auth token scoping (workspace isolation) | ✓ pass | `test_auth` — 13 passed |
| Supabase storage bucket is private | ✓ confirmed | no public flag on `documents` bucket |

## Production verification (pending deployed env)

Status: **Pending** — blocked on `DEPLOY_ENABLED=true`.

Required before launch:

1. Confirm storage bucket remains private and object URLs are not public by default.
2. Confirm CORS allowlist only includes production frontend origin(s) (not `*`).
3. Confirm rate-limit behavior at edge + app layer under load.
4. Re-run Phase G regression checks on deployed stack.
5. Capture final sign-off and attach test evidence.
