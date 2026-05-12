# Frontend Visual/Auth Audit — 2026-04-25

_Scope: live production frontend at `https://app.chiefriskbot.com`, cross-checked against current admin status and `frontend-design-ideal/DESIGN.md`._

## Admin Context Checked First

- `admin/status/STATUS.md` is the canonical live status (Phase M complete; 2026-05-12 rollout bundle under `admin/status/rollout_2026-05-12/`).
- Duplicate archived snapshots that lived at `admin/status/CODEBASE_STATUS.md` and `admin/status/MVP2_STATUS.md` were removed on 2026-05-12; historical MVP2 material remains under `admin/archive/MVP2/`.
- `admin/thinking/FRONTEND_AUDIT.md` is historical screen/backend inventory, not the current production defect list.

## Executive Summary

Production frontend is not currently wired to the live API. The backend is healthy and the demo login succeeds directly against `https://api.chiefriskbot.com`, but the browser app posts and fetches relative `/api/...` URLs on `https://app.chiefriskbot.com`. Cloudflare Pages is serving HTML or `405` from those paths instead of proxying to the backend.

Result: sign-in fails in the browser, protected pages render without a valid user, and data widgets remain in loading/placeholder states. This is the main reason "content doesn't load" and "auth is not properly working."

## Findings

### P0 — Production auth posts to the wrong host

**Evidence**

- Browser login posts to `https://app.chiefriskbot.com/api/auth/login`.
- That request returns `405`.
- Direct backend login works:
  - `POST https://api.chiefriskbot.com/api/auth/login` -> `200`
  - user: `Victoria Whitmore`
  - workspace: `Whitmore Family Office`

**Likely cause**

`frontend-mvp/_app.js` builds API URLs with:

```js
fetch(path.startsWith('/api') ? path : `/api${path}`, ...)
```

On Cloudflare Pages this resolves to the frontend host. There is no active Pages proxy/rewrite from `/api/*` to `https://api.chiefriskbot.com/api/*`.

**Impact**

Users cannot sign in through the production UI even though the backend auth service is working.

### P0 — Protected pages do not reliably fail closed

**Evidence**

Unauthenticated visits to app pages render the application shell instead of redirecting to login:

- `https://app.chiefriskbot.com/cockpit`
- `https://app.chiefriskbot.com/assets`
- `https://app.chiefriskbot.com/liquidity`
- `https://app.chiefriskbot.com/briefings`
- `https://app.chiefriskbot.com/documents`
- `https://app.chiefriskbot.com/table`
- `https://app.chiefriskbot.com/settings`
- `https://app.chiefriskbot.com/access`
- `https://app.chiefriskbot.com/onboarding`

The shell shows `WORKSPACE —`, user `CR`, and `Loading...` in the sidebar.

**Likely cause**

GET requests to `https://app.chiefriskbot.com/api/...` return `200 text/html` from the frontend SPA fallback. The frontend `api()` helper accepts any `2xx` response and returns the HTML string, so session and data loaders can proceed with invalid response shapes rather than treating them as auth/data failures.

**Impact**

This is both a UX defect and a security posture defect. The app shell is visible without a valid session, and the user sees blank/partial screens instead of a clear login redirect.

### P0 — Data loading is broken across the app host

**Evidence**

Direct backend API with bearer token:

- `/api/auth/session` -> `200`
- `/api/onboarding/state` -> `200`
- `/api/cockpit` -> `200`
- `/api/liquidity/summary` -> `200`
- `/api/briefings` -> `200`
- `/api/settings` -> `200`
- `/api/portfolio/summary` -> `200`
- `/api/documents` -> `200`

Same GET paths on the frontend host:

- `https://app.chiefriskbot.com/api/cockpit` -> `200 text/html`
- `https://app.chiefriskbot.com/api/briefings` -> `200 text/html`
- `https://app.chiefriskbot.com/api/documents` -> `200 text/html`
- `https://app.chiefriskbot.com/api/settings` -> `200 text/html`

**Impact**

Pages render placeholders instead of live data:

- Home: AUM/Cash/Concentration/VaR/Alerts show dashes.
- Cockpit/assets/liquidity/briefings/documents/table/settings: multiple loading placeholders remain.
- Sidebar workspace/user identity never resolves.

### P1 — Design system font direction is inconsistent after Phase M

**Evidence**

`frontend-design-ideal/DESIGN.md` says dashboard/page heroes should use Fraunces and explicitly lists "sans-serif headlines on the dashboard" as an anti-pattern. Current active CSS overrides `.essay-hero h1` to Inter Tight:

```css
.essay-hero h1 {
  font-family: 'Inter Tight', sans-serif;
  font-weight: 600;
  font-size: 28px;
}
```

This explains the visible mismatch between the login/brand serif treatment and app page headers like "Risk Cockpit", "Liquidity Ladder", and "Assets Overview".

**Impact**

The product now mixes the original "private bank reading room" editorial type system with a more generic SaaS header style. This undermines the design system and makes the typography feel inconsistent across screens.

### P2 — Font loading is not normalized across all pages

Most active pages load Fraunces weights `400`, `700`, and `900`, but some pages still use older font links that omit `400`:

- `frontend-mvp/briefings.html`
- `frontend-mvp/overlay.html`
- `frontend-mvp/legal.html`

Because shared CSS still contains 400-weight Fraunces rules, those pages can rely on browser synthesis or cached font state, which contributes to uneven text rendering.

### P2 — CSP blocks Cloudflare analytics script

Every audited page logs:

```text
Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/...' violates Content-Security-Policy: "script-src 'self'".
```

This is not blocking product functionality, but it creates console noise and means analytics is either unintentionally enabled by Cloudflare or the CSP needs to allow the beacon source intentionally.

## Recommended Fix Order

1. Fix API routing first. Either add a Cloudflare Pages Function/proxy for `/api/*` or update `frontend-mvp/_app.js` and `_shell.js` to use `https://api.chiefriskbot.com/api` in production.
2. Harden the frontend API helper:
   - reject non-JSON responses for API calls
   - throw when expected auth/data payloads are missing
   - fail closed to `login.html` on invalid session payloads
3. Re-run auth and page-load QA:
   - login -> authenticated landing
   - cockpit/assets/liquidity/briefings/documents/table/settings/access
   - unauthenticated protected-page visit -> login redirect
4. Restore the typography contract:
   - set `.essay-hero h1` back to Fraunces for dashboard/page heroes, or explicitly update `DESIGN.md` if Phase M intentionally changed the design direction
   - normalize Google Font links across all active HTML files
5. Decide whether to allow or disable Cloudflare Insights under CSP.

## Verification Commands Used

```bash
curl https://api.chiefriskbot.com/api/health
curl -X POST https://api.chiefriskbot.com/api/auth/login
curl -X POST https://app.chiefriskbot.com/api/auth/login
curl https://app.chiefriskbot.com/api/cockpit
```

Headless browser sweep covered:

`index`, `login`, `cockpit`, `assets`, `liquidity`, `briefings`, `documents`, `table`, `settings`, `access`, `onboarding`.

