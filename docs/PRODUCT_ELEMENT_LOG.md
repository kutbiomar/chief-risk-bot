# ChiefRiskBot — Product element log

Status: Draft evidence log  
Last updated: 2026-05-12  
Companion plan: `docs/PRODUCT_REMEDIATION_PLAN.md`

This log is the evidence register for product remediation. Each row should stay narrow: one observed symptom, the surface where it was seen, the current status, and the remediation-plan row that owns follow-up.

## Current scope

- Runtime surface: `frontend-mvp/`
- Design reference: `frontend-design-ideal/DESIGN.md`
- Legacy/reference surface: `frontend/`

## Element log

| ID | Surface | Symptom / evidence | Status | Plan row |
|----|---------|--------------------|--------|----------|
| PEL-0.1 | Authenticated app | Browser console shows an undocumented 401 during happy-path demo; failing URL still needs trace evidence. | Started: usability sweep now records 4xx/5xx response URLs with viewport/page/request/auth context. | 0.1 |
| PEL-0.2 | Shell / auth | Logout was reported as unknown. Current repo evidence shows `frontend-mvp/_shell.js` exposes `#mvp-logout`; `_app.js` now calls server logout when a token exists, clears auth state, and redirects to login. Smoke coverage is still needed. | Started | 0.2 |
| PEL-0.3 | Login / auth | Register and forgot-password paths have partial manual verification only. Active MVP auth page has sign-in/create/reset panels wired to live API paths; stale demo copy and legacy links have been cleaned. Full scripted register/reset coverage still needs non-destructive test credentials. | Started | 0.3 |
| PEL-1.1 | Delivery / browser console | Analytics/CSP decision is documented in `docs/ANALYTICS_POLICY.md`: Cloudflare Insights is not intentionally enabled and CSP should not be widened for it by default. | OK | 1.1 |
| PEL-1.2 | Routing | URL style can mix clean paths and `.html` artifacts depending on route/deploy layer. Active MVP shell and app-generated links now prefer clean paths; server-side legacy redirects still need deployment verification. | Started | 1.2 |
| PEL-1.3 | Shell navigation | Nav `href`s in `frontend-mvp/_shell.js` currently point at clean canonical routes; drawer briefing history links use `/briefing?id=`. | Started | 1.3 |
| PEL-1.4 | Demo content | Demo family-office naming needs verification across static HTML, seed data, and production demo copy. Active MVP placeholder now uses `Whitmore Family Office`, matching the production smoke workspace contract. Legacy/reference surfaces still need separate archival or migration cleanup. | Started | 1.4 |
| PEL-2.1 | Shell chrome | Interactive shell chrome can appear inert. Initial target: workspace selector feedback. | Started: workspace selector now shows a support-managed v1 toast. | 2.1 |
| PEL-2.2 | Shell / landmarks | Shell nav is injected before page `<main>` and the mobile top bar now declares `role=\"banner\"`; axe sweep covers serious/critical landmark regressions. | OK | 2.2 |
| PEL-2.3 | Shell identity | Identity/workspace text should avoid misleading static labels before session data resolves. | Started: collapsed sidebar uses neutral `WS` before session data, then updates from `workspace_name`. | 2.3 |
| PEL-3.1 | Home | Greeting, KPIs, and briefing strip consume session, cockpit, liquidity, and briefing APIs in `initIndex`; focused browser coverage still needs seeded portfolio assertions. | Started | 3.1 |
| PEL-3.2 | Home / shell | Home eyebrow now includes `workspace_name` from the authenticated session, matching the shell workspace label source. | Started | 3.2 |
| PEL-4.1 | Cockpit / Assets | Cockpit refresh fetches cockpit/liquidity APIs, shows loading state, disables the button during refresh, and updates an as-of timestamp. Assets refresh already reloads live cockpit data. | Started | 4.1 |
| PEL-4.2 | Cockpit / Assets | Segment toggles re-render composition from live cockpit response dimensions; focused golden/contract tests still need to be added. | Started | 4.2 |
| PEL-4.3 | Risk register | Risk register rows now act as keyboard-accessible links into Positions; flag rows preserve ticker context and Positions honors `?ticker=` deep links. | OK | 4.3 |
| PEL-4.4 | Assets | Position creation now validates identifier/name, positive quantity, and positive market value before POST; happy-path e2e coverage still needs to be added. | Started | 4.4 |
| PEL-5.1 | Positions | Document upload/parse/apply API path is covered by `backend/tests/test_frontend_contract.py`; frontend upload UI shows file-required validation, busy state, parse progress, and opened review queue. | OK | 5.1 |
| PEL-5.2 | Positions | Empty save behavior is defined: new rows require identifier or name plus positive quantity and market value before API mutation. | Started | 5.2 |
| PEL-5.3 | Positions | Row selection now updates a stable `?positionId=` URL and reloads that row when linked directly. | Started | 5.3 |
| PEL-6.1 | Briefings | Generate flow has bounded terminal states: success opens/links to the reader, API errors surface in status/toast area, and a 45s timeout tells users to check history before retrying. | Started | 6.1 |
| PEL-6.2 | Briefings / reader | Briefing list and drawer history rows deep-link to `/briefing?id=` and the reader loads that id. | Started | 6.2 |
| PEL-7.1 | Documents | Upload pipeline shows queued/parse progress, opens the uploaded document in the review queue, and reports parse completion/errors. | Started | 7.1 |
| PEL-7.2 | Documents | Review UI has explicit states: no selection, source preview unavailable/non-PDF/PDF, no extraction, parse progress, review fields, and approval actions; selected documents now keep `?documentId=` in sync. | Started | 7.2 |
| PEL-8.1 | Liquidity | Liquidity is interactive in MVP: it has a configurable buffer target, stress-case toggle, refresh action, and explanatory chart caption. | OK | -1.2 / 8.1 |
| PEL-9.1 | Settings | Full settings persistence matrix is documented in `docs/SETTINGS_MATRIX.md`; Settings now exposes stable hash sections for workspace, AI, and support panels. | Started | 9.1 |
| PEL-10.1 | IA / routes | Scenarios and Access route visibility must match approved product IA. Both remain in MVP shell; production smoke now includes `/scenarios` and `/access`. | Started | -1.3 / 10.1 |
| PEL-10.2 | Briefing reader | Reader query contract needs smoke/e2e coverage. Drawer history now deep-links to `/briefing?id=`. | Started | 10.2 |
| PEL-11.1 | Design system | Material Symbols loading should match or document deviation from `DESIGN.md`. | Started: MVP font request now limits opsz to 20-24 and weight to 400; active nav icons use filled variant. | 11.1 |
| PEL-11.2 | Accessibility | Frontend usability sweep now runs axe WCAG 2/2.1 A/AA checks and blocks on serious/critical violations per route/viewport. | Started | 11.2 |
| PEL-11.3 | Cockpit / SVG | Cockpit/assets donut SVGs are decorative summaries in MVP and use `aria-hidden=\"true\"`; interactive data is represented by adjacent legends/tables. | OK | -1.4 / 11.3 |
| PEL-12.1 | Repo / auth | Token key mismatch between frontend trees creates confusion. | Started: `docs/ENVIRONMENTS.md` documents active frontend and token keys. | -1.1 / 12.1 |
| PEL-13.1 | QA | Coverage gaps are materially reduced: settings matrix is documented, Positions has URL/validation contracts, document upload has backend contract coverage, and usability sweep now includes route-level axe/console/network gates. | OK | 13.1 |
| PEL-13.2 | Ops / QA | Scheduled smoke and alerting signals are incomplete. | Started: usability sweep now records console route context, 4xx/5xx responses, and request failures for alert payloads. | 13.2 |

## Update rules

- When a row is fixed, change Status to `OK` and link the PR/issue.
- When a row is intentionally deferred, change Status to `Deferred` and link the issue.
- Do not delete rows during remediation; keep history visible until the plan is closed.
