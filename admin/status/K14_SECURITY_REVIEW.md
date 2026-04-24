# K14 Security Review Checklist

_Last updated: 2026-04-17_

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

## Production verification (required)

1. Confirm storage bucket remains private and object URLs are not public by default.
2. Confirm CORS allowlist only includes production frontend origin(s).
3. Confirm rate-limit behavior at edge + app layer under load.
4. Re-run Phase G regression checks on deployed stack.
5. Capture final sign-off and attach test evidence.
