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
| PEL-0.3 | Login / auth | Register and forgot-password paths have partial manual verification only. | Open | 0.3 |
| PEL-1.1 | Delivery / browser console | CSP policy and Cloudflare Insights behavior need an explicit analytics decision. | Open | 1.1 |
| PEL-1.2 | Routing | URL style can mix clean paths and `.html` artifacts depending on route/deploy layer. | Open | 1.2 |
| PEL-1.3 | Shell navigation | Nav `href`s in `frontend-mvp/_shell.js` currently point at clean canonical routes; drawer briefing history links use `/briefing?id=`. | Started | 1.3 |
| PEL-1.4 | Demo content | Demo family-office naming needs verification across static HTML, seed data, and production demo copy. Active MVP placeholder now uses `Whitmore Family Office`, matching the production smoke workspace contract. Legacy/reference surfaces still need separate archival or migration cleanup. | Started | 1.4 |
| PEL-2.1 | Shell chrome | Interactive shell chrome can appear inert. Initial target: workspace selector feedback. | Started: workspace selector now shows a support-managed v1 toast. | 2.1 |
| PEL-2.2 | Shell / landmarks | Top/header landmark order needs accessibility validation after shell refactor. | Open | 2.2 |
| PEL-2.3 | Shell identity | Identity/workspace text should avoid misleading static labels before session data resolves. | Started: collapsed sidebar uses neutral `WS` before session data, then updates from `workspace_name`. | 2.3 |
| PEL-3.1 | Home | Greeting, KPIs, and briefing strip must prove they consume session/API data. | Open | 3.1 |
| PEL-3.2 | Home / shell | Workspace copy in Home should match sidebar/session values. | Open | 3.2 |
| PEL-4.1 | Cockpit / Assets | Refresh action must prove it reloads data and updates as-of state. | Open | 4.1 |
| PEL-4.2 | Cockpit / Assets | Segment toggles must prove they swap data, legend, and chart values. | Open | 4.2 |
| PEL-4.3 | Risk register | Register rows need a stable drill-down contract. | Open | 4.3 |
| PEL-4.4 | Assets | "Add position" needs happy-path and validation coverage. | Open | 4.4 |
| PEL-5.1 | Positions | Upload document flow is unverified in CI/staging. | Open | 5.1 |
| PEL-5.2 | Positions | Add-row modal empty-save behavior is undefined. | Open | 5.2 |
| PEL-5.3 | Positions | Row-level links lack route/target coverage. | Open | 5.3 |
| PEL-6.1 | Briefings | Generate flow needs terminal success, error, and timeout states. | Open | 6.1 |
| PEL-6.2 | Briefings / reader | History rows must deep-link to the same briefing in the reader. | Open | 6.2 |
| PEL-7.1 | Documents | Upload pipeline needs visible status transitions. | Open | 7.1 |
| PEL-7.2 | Documents | Review action needs a documented UI state machine. | Open | 7.2 |
| PEL-8.1 | Liquidity | Page has no in-content controls; product intent is undecided. | Product decision needed | -1.2 / 8.1 |
| PEL-9.1 | Settings | Full settings persistence matrix is unknown. | Open | 9.1 |
| PEL-10.1 | IA / routes | Scenarios and Access route visibility must match approved product IA. Both remain in MVP shell; production smoke now includes `/scenarios` and `/access`. | Started | -1.3 / 10.1 |
| PEL-10.2 | Briefing reader | Reader query contract needs smoke/e2e coverage. Drawer history now deep-links to `/briefing?id=`. | Started | 10.2 |
| PEL-11.1 | Design system | Material Symbols loading should match or document deviation from `DESIGN.md`. | Started: MVP font request now limits opsz to 20-24 and weight to 400; active nav icons use filled variant. | 11.1 |
| PEL-11.2 | Accessibility | Route-level accessibility baseline is unknown. | Open | 11.2 |
| PEL-11.3 | Cockpit / SVG | Donut/SVG segments need a decorative-vs-interactive accessibility decision. | Product decision needed | -1.4 / 11.3 |
| PEL-12.1 | Repo / auth | Token key mismatch between frontend trees creates confusion. | Started: `docs/ENVIRONMENTS.md` documents active frontend and token keys. | -1.1 / 12.1 |
| PEL-13.1 | QA | Coverage gaps remain across positions rows and settings matrix. | Open | 13.1 |
| PEL-13.2 | Ops / QA | Scheduled smoke and alerting signals are incomplete. | Started: usability sweep now records console route context, 4xx/5xx responses, and request failures for alert payloads. | 13.2 |

## Update rules

- When a row is fixed, change Status to `OK` and link the PR/issue.
- When a row is intentionally deferred, change Status to `Deferred` and link the issue.
- Do not delete rows during remediation; keep history visible until the plan is closed.
