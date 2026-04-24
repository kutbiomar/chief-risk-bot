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
| WeasyPrint PDF export in container | ✓ confirmed | `200` (26 KB) on `GET /api/briefings/{id}/export/pdf` (2026-04-24) |

## Production health verification — 2026-04-24

Live at `https://chief-risk-bot.fly.dev`. All 5 dependency components `ok` (see K13_QA_SWEEP.md for full response).

`GET /api/health` → `200`, `status: ok`, `environment: production`.

## Production verification — 2026-04-24

| Check | Status | Notes |
|---|---|---|
| Storage bucket private | ✓ confirmed | Supabase `documents` bucket has no public flag |
| HSTS on live app | ✓ confirmed | Fly enforces HTTPS + `force_https = true` in `fly.toml` |
| CORS origin enforcement | ✓ confirmed | `https://app.chiefriskbot.com` → `access-control-allow-origin` returned. `https://evil.example.com` → no ACAO header. |
| Rate-limit behavior on prod | ✓ confirmed | 12 rapid `POST /api/auth/login` → 401×10, then 429×2. |
| Phase G regression checks on deployed | ✓ confirmed | `/api/health` all 5 components ok. Full E2E pass recorded in K13. |

**K14 sign-off: complete (2026-04-24)**
