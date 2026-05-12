# ChiefRiskBot — Analytics and CSP policy

Status: Active for v1 remediation  
Last updated: 2026-05-12

## Decision

Cloudflare Web Analytics / Insights is **not enabled intentionally** in the v1 app shell.

The active MVP frontend (`frontend-mvp/`) does not include a Cloudflare beacon snippet. Its `_headers` Content Security Policy intentionally keeps `script-src 'self'` and does not allow `static.cloudflareinsights.com`. If Cloudflare injects a beacon outside the repo, the expected remediation is to disable that injection in Cloudflare rather than broadening app CSP by default.

## Current CSP source

`frontend-mvp/_headers` is the frontend CSP source for the active remediation surface:

```text
script-src 'self'
connect-src 'self' https://api.chiefriskbot.com
```

## Revisit conditions

If product analytics becomes required, create a separate issue that names:

1. the analytics provider,
2. the exact script/connect origins,
3. the privacy/legal basis,
4. the user-facing disclosure update, and
5. a smoke check proving no unrelated script origins were opened.
