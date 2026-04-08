# ChiefRiskBot — Frontend Audit & Screen Inventory
*Cross-referenced against ARCHITECTURE.md. April 2026.*

---

## MVP Screen Inventory

13 screens exist. Categorized by demo relevance and backend readiness.

---

### Tier 1 — Core Demo Path (build backend first)

These screens are the demo. Every CIO sees them in sequence.

| Screen | File | Purpose | Backend Endpoints |
|---|---|---|---|
| Login | `login.html` | Auth entry | `POST /api/auth/login`, `POST /api/auth/totp/verify`, `GET /api/auth/google/authorize`, `POST /api/contact/request-access` |
| Onboarding | `onboarding.html` | CSV/doc upload wizard | `GET /api/onboarding/state`, `POST /api/onboarding/step/{n}/complete`, `POST /api/onboarding/skip`, `POST /api/ingest/csv`, `POST /api/ingest/document`, `GET /api/sources/providers` |
| Cockpit | `cockpit.html` | Risk dashboard | `GET /api/cockpit`, `GET /api/var/history`, `POST /api/risk/run`, `GET /api/risk/status/{job_id}` |
| Briefings list | `briefings.html` | Archive of generated briefings | `GET /api/briefings`, `POST /api/briefings/generate` |
| Single briefing | `briefing.html` | Full IC-ready document | `GET /api/briefings/{id}`, `PATCH /api/briefings/{id}`, `POST /api/briefings/{id}/publish`, `GET /api/briefings/{id}/export/pdf` |
| Position table | `table.html` | Holdings CRUD + reconciliation | `GET /api/portfolio/positions`, `GET /api/portfolio/positions/{id}`, `POST /api/portfolio/positions`, `PATCH /api/portfolio/positions/{id}`, `DELETE /api/portfolio/positions/{id}`, `POST /api/portfolio/positions/bulk` |
| Markets | `markets.html` | Macro context + movers | `GET /api/markets/prices`, `GET /api/markets/macro`, `GET /api/markets/sectors`, `GET /api/markets/volatility`, `GET /api/markets/movers`, `GET /api/markets/events` |

---

### Tier 2 — Supporting Screens (stub in demo, build post-MVP)

Exist in the UI, partially needed for demo context, but not on the critical path.

| Screen | File | Purpose | Demo Treatment |
|---|---|---|---|
| Documents | `documents.html` | PDF upload + extraction | Show upload UI; parse endpoint can be live but folder/tag features stub |
| Sources | `sources.html` | OAuth custodian connections | All providers show "Connect" button — all return 501 in demo |
| Audit | `audit.html` | Compliance log | Show real events from demo actions; export + verify chain = stub |
| Settings | `settings.html` | Workspace config + AI model | Briefing cadence + model selector = live; billing + API keys = stub |
| Members | `members.html` | Team management | Single-user demo workspace; show Omar as Owner; invite flow = stub |

---

### Tier 3 — Out of Demo Scope

| Screen | File | Reason |
|---|---|---|
| Public homepage | `index.html` | Marketing page — no backend needed for demo |
| Invite acceptance | `invite.html` | No multi-user in demo |
| Forgot password | `forgot.html` | Not needed for demo credentials |
| Email verification | `verify.html` | Not needed for demo |
| 404 | `404.html` | Error state — no backend |
| 500 | `500.html` | Error state — no backend |
| Maintenance | `maintenance.html` | Error state — no backend |
| Empty states | `empty-states.html` | UI component library — no backend |
| Components | `components.html` | UI component library — no backend |

---

## Screen-by-Screen Backend Gap Analysis

### cockpit.html

**What the frontend expects:**
- KPI strip: AUM, 1-day VaR (99%), Active Risk count (priority/elevated), HHI, Liquidity %
- Portfolio donut: % by asset class (5 slices) with position count
- VaR mini stats: 30D vol, Sharpe, Beta, Max DD
- Risk register table: 12 risks, each with title, severity, AUM affected, MC probability
- Mitigation tree: visual decision tree for selected risk
- VaR time series chart: 6-week history with event markers
- System status bar: source count, latency, sync status

**Backend gaps vs ARCHITECTURE.md:**
- `GET /api/cockpit` — covers KPIs, donut, risk register ✓
- `GET /api/var/history` — covers VaR chart ✓
- `POST /api/risk/run` + `GET /api/risk/status/{job_id}` — required to render async/degraded agent runs ✓
- Mitigation tree — **NOT in architecture plan and should stay out of backend for demo.**
  Generate statically in the frontend from the top priority risk / deterministic flags.
- Monte Carlo `P(loss>5%)` per risk — **NOT computed by VaR engine and should not be added
  as a backend field for demo.** If the UI keeps it, label it as indicative frontend-only copy
  or remove it from the MVP screen.
- Real-time sync status bar — demo can show static "all synced 3m ago"

**Action:** Remove backend dependency on mitigation-tree and per-risk MC probability from the MVP audit.

---

### briefings.html

**What the frontend expects:**
- Featured briefing card: title, week label, version, status, reviewer name, risk pills
- "Top risks called out" with severity + MC probability
- Recommended actions (3 items with ticker, description, size estimate, timing)
- Archive grid: past briefings as cards with metadata
- Filters: period (Week/Month/Quarter), status (All/Published/Draft/Archived), search

**Backend gaps vs ARCHITECTURE.md:**
- `GET /api/briefings` — ✓ with filters
- `recommended_actions` field — already aligned with the Phase 5 briefing output direction in
  `BACKEND_PLAN.md`; keep this as an `output_json` contract item, not a separate table field.
- Reviewer name on briefing — **NOT tracked in architecture and not required for MVP.**
  Render publisher / generated-by metadata instead of adding a new review workflow.
- `POST /api/briefings/generate` — ✓

---

### briefing.html

**What the frontend expects:**
- Full editorial document: headline, byline, body sections, pull quotes
- Section 3: recommended actions numbered 01/02/03 with size + timing
- Section 4: 11 talking points
- Right sidebar: "At a glance" stats (AUM, 1W VaR, P(loss>5%), etc.), risk pills
- Footer: model name, prompt paths, review count
- Buttons: Edit (CIO role), Send (publish), Download PDF

**Backend gaps vs ARCHITECTURE.md:**
- "At a glance" sidebar stats require `/api/briefings/{id}` to return the portfolio
  snapshot summary alongside the briefing document. This is reasonable as a response-shape
  requirement on `GET /api/briefings/{id}`.
- "Prompt paths" in footer — do not expose filesystem/prompt paths. If needed, return a simple
  `agents_used` array or model metadata in the briefing detail response.
- "Review count" — needs `version` field on briefing. Already in schema ✓
- PDF download — `GET /api/briefings/{id}/export/pdf` ✓ (stub for demo)

---

### table.html

**What the frontend expects:**
- Position table with columns: Ticker, Name, Quantity, Price, Market Value, Asset Class,
  Sector, Custodian, Source (API/Manual/PDF), Last Updated
- Inline cell editing with source provenance indicator
- Row drawer: linked risks + attached documents
- Bulk import button
- History button (per row)
- Filter: asset class, custodian, search

**Backend gaps vs ARCHITECTURE.md:**
- Row drawer "linked risks" — can be derived client-side from `GET /api/risk/flags` +
  current position ticker for demo; no dedicated endpoint required yet.
- Row drawer "attached documents" — requires a real link model and remains post-MVP.
- Row edit history — `GET /api/audit?subject_type=position&subject_id={id}` already covers
  this need; no position-specific alias endpoint is required for MVP.
- Source provenance indicator (API vs Manual vs PDF) — already in `positions.price_source` ✓
- Manual override with revert — `PATCH /api/portfolio/positions/{id}` with
  `override_value` + `override_by` + `override_at` already in schema ✓

---

### documents.html

**What the frontend expects:**
- Left panel: folder tree with counts
- Document list: filename, folder, tag, size, modified date
- Preview panel (right): extracted fields, holdings sample, source/period metadata
- Actions: upload, tag, reconcile, delete, re-parse

**Backend gaps vs ARCHITECTURE.md:**
- Folder counts — keep as a useful response-shape addition on `GET /api/documents`.
- Preview thumbnail — `GET /api/documents/{id}/preview` returns PNG ✓
- "Reconciled to table: Yes" status — needs a `reconciled_to_snapshot` bool on
  `extraction_results`. Prefer a derived/reported field in the document response rather than
  adding a dedicated reconciliation FK for MVP.
- "Linked rows" (SPY, NVDA, AAPL...) — true document-position linking remains post-MVP.

---

### sources.html

**What the frontend expects:**
- Source cards: provider logo, name, type, last synced, status, position count
- Actions: Reconnect, Test, Delete
- "Connect new source" flow with OAuth

**Backend gaps vs ARCHITECTURE.md:**
- All endpoints ✓ in architecture
- For demo: all providers return `{status: "coming_soon"}` from
  `GET /api/sources/providers`. No OAuth flows needed in demo.
- `GET /api/sources/providers` already exists in architecture ✓

---

### markets.html

**What the frontend expects:**
- Price strip: 6 tiles, refreshes every 60 seconds
- S&P 500 vs UST 10Y indexed chart (6-month)
- VIX + MOVE volatility chart (12-month)
- GICS sector heatmap (12 sectors, daily %)
- Macro events calendar (this week, with severity tags)
- Movers in your book (from current portfolio, daily P&L)
- Alert creation (threshold-based)

**Backend gaps vs ARCHITECTURE.md:**
- `GET /api/markets/prices` ✓
- `GET /api/markets/sectors` ✓
- `GET /api/markets/events` ✓
- `GET /api/markets/movers` ✓
- `GET /api/markets/volatility` ✓
- Indexed price chart (S&P vs UST 10Y, 6-month) — not currently in architecture.
  For MVP, derive it from existing macro/price payloads or simplify the chart.
- Alert creation — **NOT in architecture.** Out of scope for demo. Show button,
  return 501 with tooltip "Alerts coming soon."
- 60-second auto-refresh — frontend JS interval calling `GET /api/markets/prices`.
  No WebSocket required for demo.

---

### audit.html

**What the frontend expects:**
- Grouped log (by date) with icons per event type
- Event types: auth, AI generation, data edit, source sync, error
- Filter bar: type, member, date range, search
- Export button (CSV)
- Verify chain button

**Backend gaps vs ARCHITECTURE.md:**
- `GET /api/audit` with filters ✓
- `POST /api/audit/export` ✓ (stub for demo — return CSV of displayed events)
- `POST /api/audit/verify` ✓ (stub for demo — return `{valid: true}`)
- `icon_type` should remain a derived frontend mapping from `event_type` + `action`;
  no backend field is required.

---

### settings.html

**What the frontend expects:**
- Workspace details form (name, slug, currency, timezone, address)
- Briefing cadence (day, time, recipients, toggles)
- AI model selector + tone + custom instructions + token usage
- API keys (list with prefix, create, revoke)
- Danger zone (export, delete)
- Billing section (plan, seats, next invoice)

**Backend gaps vs ARCHITECTURE.md:**
- Token usage this month — useful, but not yet in architecture. Keep out of MVP required scope
  unless settings page explicitly needs a live usage card.
- Billing section — stub for demo. Return mock plan data.
- All other settings endpoints ✓ in architecture.

---

### login.html

**What the frontend expects:**
- Email + password form
- "Keep me signed in" checkbox (sets session TTL)
- Forgot password link
- Google Workspace SSO button
- SAML SSO button
- "Request access" link (leads to public contact form)
- Right panel: social proof stats

**Backend gaps:**
- All auth endpoints ✓ in architecture
- SAML — stub for demo (return 501 "SSO requires enterprise plan")
- Social proof stats from `GET /api/stats` ✓

---

### onboarding.html (Step 2: Connect data)

**What the frontend expects:**
- Progress stepper (5 steps)
- Provider tiles with OAuth or SFTP label
- "Don't see your custodian? Upload files" fallback
- Skip button

**Backend gaps:**
- `GET /api/onboarding/state` ✓
- `POST /api/onboarding/step/{n}/complete` ✓
- `GET /api/sources/providers` — needed here too ✓
- OAuth flows — all stub for demo
- **Missing screen: onboarding Step 3 (Upload docs)** — the "Upload docs" step shown
  in the stepper does not have a dedicated HTML file. The `documents.html` file handles
  the full document library, not the onboarding upload step. **For demo: reuse
  `POST /api/ingest/document` from within onboarding flow. No new screen needed.**

---

## Missing Backend Items (Summary)

Gaps found by auditing frontend that should actually be reflected in backend response shapes or lightweight additions:

| Item | Priority | Complexity | Where to Add |
|---|---|---|---|
| `portfolio_snapshot` in briefing detail | Demo | Trivial | Add to `GET /api/briefings/{id}` response |
| `agents_used` in briefing detail | Demo | Trivial | Add to `GET /api/briefings/{id}` response |
| `folder_counts` in document list | Demo | Trivial | Add to `GET /api/documents` response |
| `recommended_actions` in briefing output | Demo | Low | `briefing_runs.output_json` schema |
| Optional derived `reconciled_to_snapshot` field in document detail | Demo | Low | `GET /api/documents/{id}` response |

Items the frontend audit previously proposed but should stay out of MVP backend scope:

| Item | Reason |
|---|---|
| Mitigation tree endpoint | Better handled as static/demo UI logic from existing risk data |
| Per-risk MC probability estimate | Conflicts with the historical-simulation VaR design |
| `reviewed_by` on briefing | Adds workflow state not required for MVP |
| Position-linked risks endpoint | Can be derived from existing risk payloads |
| Position edit history endpoint | Existing audit endpoint already covers this |
| Document-position link table | Post-MVP link-model concern rather than MVP API gap |
| Indexed price chart endpoint | Can be deferred or derived from existing price payloads in demo |
| Monthly token usage endpoint | Nice-to-have, not required for MVP screen correctness |
| `reconciled_snapshot_id` on extractions | Post-MVP link-model concern |
| `icon_type` on audit events | Better as frontend-derived presentation mapping |

---

## Screens to Consolidate or Remove

| Screen | Recommendation |
|---|---|
| `empty-states.html` | Component reference only — delete before ship |
| `components.html` | Component reference only — delete before ship |
| `maintenance.html` | Keep as static HTML — no backend needed |
| `index.html` | Marketing page — serve statically, no API calls needed in demo |
| `invite.html` | Keep for post-MVP multi-user; stub the acceptance endpoint |
| `forgot.html` + `verify.html` | Keep as static forms; backend email stub |

---

## Navigation Consistency Issues

Across all screens, the left nav links point to these destinations:

```
cockpit.html     → /cockpit
briefings.html   → /briefings
table.html       → /table
documents.html   → /documents
sources.html     → /sources
markets.html     → /markets
members.html     → /members
settings.html    → /settings
audit.html       → /audit
```

FastAPI should serve all static HTML files from `/app/static/` at these routes.
Add a catch-all route that serves `404.html` for any unknown path.

The nav does not include a Login/Logout button. **Add logout to the nav shell.**
The shell component (`_shell.css` implies a shared nav) needs a `POST /api/auth/logout`
call wired to the user avatar/menu in the top-right corner.

---

## Demo Flow — Minimum Screens Required

If demo is time-boxed to 20 minutes, these are the 6 screens that tell the story:

```
1. Login → onboarding (CSV upload)
2. Table → positions loaded, enriched with live prices
3. Cockpit → KPI strip, risk register, VaR tile
4. Click a risk → agent reasoning visible
5. Briefings → "Generate briefing" button
6. Single briefing → full IC document, talking points, actions
```

Markets and Documents are second-act screens for extended demos.
Members, Settings, and Audit are compliance story screens for enterprise conversations.
