# MVP2 Spec — ChiefRiskBot: Private Market Intelligence Platform

**Version:** 0.1 (Draft)
**Date:** 2026-04-08
**Branch:** mvp-demo

---

## What This Is

A workstream tool for family offices and small funds that eliminates the "Sunday Night Scramble." Users upload messy private market documents (PE/VC/HF reports, capital call notices, LP statements, DD files) and get back a clean, reconciled view of holdings, liquidity exposure, and risk — plus automated weekly briefings.

The central value proposition: **"You think you're diversified and liquid. We show you whether you actually are."**

---

## Users

**Primary:** Investment analyst or operations lead at a family office (2–15 person team, $100M–$2B AUM). Owns the Monday morning IC meeting prep. Currently spending 8–10 hours per week pulling data from PDFs, bank portals, and Excel.

**Secondary:** CIO / Principal. Reads the briefing, acts on alerts. Does not touch the data.

**Admin:** IT or COO. Manages user access, integrations, payment.

---

## Data Model (define this first — everything else depends on it)

### Fund

```
id, name, type (PE | VC | HF | RE | Other), manager_name,
vintage_year, fund_size, currency, jurisdiction,
created_at, updated_at
```

### Commitment

```
id, fund_id, committed_amount, called_capital, uncalled_capital,
nav, nav_date, nav_is_estimated (bool),
distributions_received, management_fee_rate, carry_rate,
created_at, updated_at
```

### Capital Event

```
id, fund_id, type (call | distribution | fee | recallable_distribution),
amount, currency, notice_date, due_date, effective_date,
source_document_id, notes
```

### Holding

```
id, fund_id (nullable), asset_name, asset_type (equity | bond | private_co | real_estate | crypto | cash | other),
geo_region, sector, currency, quantity, unit_cost, current_value,
current_value_date, current_value_source (market | manager_stated | estimated),
created_at, updated_at
```

### Document

```
id, filename, file_type (pdf | xlsx | email | csv | docx),
upload_date, uploaded_by_user_id, provider_name,
auto_category (capital_call | lp_statement | quarterly_report | dd_document | portfolio_summary | other),
processing_status (pending | processing | done | needs_review | failed),
extracted_data (jsonb), reconciliation_flags (jsonb)
```

### Deal (Pipeline)

```
id, name, stage (sourcing | dd | ic_review | closed | passed),
asset_type, target_commitment, target_close_date,
lead_analyst_id, documents (array of document_ids),
notes, created_at, updated_at
```

### ReconciliationFlag

```
id, document_id, field_name, document_value, system_value,
flagged_at, resolved_by, resolution_notes, status (open | resolved | overridden)
```

---

## P0 Features

### 1. Onboarding

- Org setup: name, base currency, reporting timezone
- Invite team members (email + role: admin | analyst | read-only)
- Initial fund/commitment entry (manual table, guided — no doc upload required to start)
- Short guided tour pointing at the three main views: Holdings, Cash Flow, Briefing

### 2. Document Upload + Ingestion Pipeline

**Upload UI:**
- Drag-and-drop or file picker, multi-file
- Supported: PDF, XLSX, CSV, .eml, DOCX
- Max file size: 50MB per file

**Ingestion Agent (backend):**

Step 1 — Classification
- Identify document type: capital call notice, LP statement, quarterly report, DD doc, portfolio summary
- Extract provider/fund name from header/footer/filename
- Auto-assign to fund if match found, else flag for user assignment

Step 2 — Extraction
- Capital call notices: due date, amount, fund, wire instructions
- LP statements: NAV, called capital, distributions, commitment balance
- Quarterly reports: underlying holdings table (if included), key metrics
- DD documents: tag to deal pipeline, no structured extraction

Step 3 — Normalization
- Map extracted fields to internal data model
- Handle currency conversion (base currency defined at org level)
- Mark all NAV fields with source = "manager_stated" and record the NAV date

Step 4 — Reconciliation Check
- Compare extracted values against existing system values
- Flag any discrepancy > 2% on NAV, called capital, or distributions
- Flag if a capital call due date is within 14 days (high-priority alert)

Step 5 — Human Review Queue
- Show user a diff view: "Document says X, system has Y — accept / override / investigate"
- All accepted changes logged with timestamp and user

**Document Management System:**
- Auto-organise into folder hierarchy: Provider > Fund > Document Type > Year
- Manual drag-to-reorganise supported
- Full-text search across all uploaded documents
- Version history per document (re-upload replaces, old version retained)

### 3. Table Editor (Manual Data Entry)

Supabase-style inline table editor for every core entity:
- Funds
- Commitments
- Capital Events
- Holdings
- Deals

Features:
- Add / edit / delete rows inline
- Bulk import via CSV paste
- Column filters and sort
- Cell-level audit trail (who changed what, when)
- Export to CSV / Excel

This is the fallback when document ingestion fails or user prefers manual entry. It must work standalone — the product is useful before any documents are uploaded.

### 4. Aggregated Holdings View

Three pivot axes (toggle between):

**By Asset Class:** PE, VC, HF, Real Estate, Public Equity, Fixed Income, Cash, Other
**By Geography:** Region and country breakdown
**By Sector:** GICS sectors, with "Unknown" bucket for unclassified privates

Each view shows:
- Current value (with data freshness indicator — days since last NAV update)
- % of total portfolio
- Cost basis and unrealised gain/loss (where available)
- Stale data callout: any holding with NAV > 90 days old is flagged visually

**Look-through concentration alerts:**
- If any single asset, manager, or sector exceeds configurable thresholds (default: 20% single name, 40% single sector), surface a banner alert on this view
- Show cross-fund exposure: "NVIDIA appears in Fund A directly and Fund B indirectly — combined exposure: 12%"

### 5. Cash Flow and Liquidity Projection

The core "aha" feature.

**Cash Flow Ladder:**
- X-axis: monthly buckets, 24 months forward
- Bar chart: expected inflows (distributions) vs. outflows (unfunded commitments, fees)
- Net liquidity position per month, cumulative
- Configurable "liquidity buffer" target (e.g. keep $2M cash at all times)

**Data sources for the ladder:**
- Unfunded commitments: from commitment table, assume linear drawdown over remaining fund life unless capital call notices override
- Expected distributions: from manager-stated schedules or user-entered estimates
- Fees: management fee schedule from fund terms

**Probability weighting:**
- Distributions marked as "confirmed" (notice received) vs. "estimated" (modelled)
- User can toggle between base case (expected) and stress case (distributions delayed 6 months)

**Alert logic:**
- "Liquidity gap detected: outflows exceed liquid assets in Month 7 by $3.2M"
- "Capital call due in 14 days — $1.5M to Fund XYZ. Current cash balance: $4.1M. OK."

### 6. Risk Analysis

**VaR — Public Holdings:**
- Standard historical VaR (1-day, 95% and 99%) for public equity/bond positions
- Data source: yfinance (existing), expandable to paid data later

**VaR Proxy — Private Holdings:**
- Assign each private fund a benchmark proxy (e.g. Cambridge Associates PE index, MSCI World for GE-style funds)
- Use proxy volatility to estimate private market VaR
- Clearly label: "Estimated — based on [benchmark] proxy"
- This is a known limitation; surface it in the UI

**Risk Decomposition:**
- Top 5 contributors to portfolio VaR
- Concentration score (Herfindahl index on sector and geo)
- Manager concentration (% of NAV with single manager)

**Private Market Risk Flags (qualitative):**
- Fund age vs. typical lifecycle (is a 2019 fund overdue for distributions?)
- GP concentration (more than 3 funds with same manager)
- Vintage year clustering (all funds from 2021–2022 = J-curve risk at same time)

### 7. Automated Weekly Briefing

Generated every Monday at configurable time (default 7am local).

**Contents:**
1. Executive summary: portfolio value, week-over-week change, top 3 alerts
2. Liquidity snapshot: next 90 days cash flow, any gaps
3. Capital events this week: calls due, distributions received
4. Holdings changes: any NAV updates received, reconciliation flags resolved/outstanding
5. Deal pipeline: any deals moved stage, upcoming IC decisions
6. Risk summary: VaR, top concentration flags
7. Documents received this week: list with processing status

**Format:** PDF + in-app view. Sent via email to configured recipients.

**User control:** Can regenerate on demand, edit before sending, configure recipients per briefing section.

---

## P1 Features (post-MVP)

- API connections to fund administrators (iLEVEL, Allvue, Cobalt)
- Brokerage account connections (Interactive Brokers, Schwab, Fidelity via Plaid or direct)
- Bank portal integrations for cash balance
- LP portal scraping (where no API exists)
- Mobile view (read-only, briefing + alerts)
- Co-investor data sharing (share a deal room with external parties)

---

## Agent Architecture

### Ingestion Agent

**Trigger:** Document uploaded
**Tools:** PDF parser, Excel reader, email parser, classification model, extraction prompts, reconciliation checker
**Output:** Structured JSON matched to data model, reconciliation flags, human review queue items
**Failure mode:** Mark document as "needs_review", notify uploader, never silently drop data

### Risk Analyst Agent

**Trigger:** New holdings data, weekly schedule, manual refresh
**Tools:** yfinance (public), benchmark proxy lookup, Herfindahl calculator, VaR engine
**Output:** Risk decomposition object, concentration alerts, liquidity gap alerts
**Runs:** On demand + nightly recalculation

### Briefing Generator Agent

**Trigger:** Weekly schedule (Monday 7am) or manual
**Tools:** Reads from all core tables, pulls outstanding flags, generates narrative via Claude
**Output:** Structured briefing object → rendered PDF + in-app view
**Tone guidance:** Concise, direct, no filler. Lead with decisions and alerts, not charts.

---

## Tech Stack

**Backend:** FastAPI (existing), PostgreSQL via Supabase (for table editor + auth)
**Document processing:** LlamaParse or pymupdf for extraction, Claude for classification + normalization
**Risk engine:** Python (pandas, numpy), yfinance for public data
**Frontend:** Vanilla JS (existing MVP approach), upgrade to React if table editor complexity demands it
**Auth:** Supabase Auth (team management, row-level security per org)
**Storage:** Supabase Storage for document files
**Scheduling:** Celery + Redis (briefing generation, nightly risk recalc)
**Email:** Resend or SendGrid for briefing delivery

---

## Audit Trail Requirements

Every data change must log:
- Entity type + ID
- Field changed
- Old value → new value
- Changed by: user_id OR agent name
- Source: manual | document_id | api_sync
- Timestamp

This is non-negotiable for compliance and for "why did this number change?"

---

## Reconciliation Rules

| Field | Flag threshold | Priority |
|---|---|---|
| NAV | > 2% variance | High |
| Called capital | Any variance | High |
| Distributions | Any variance | High |
| Commitment balance | > 1% variance | Medium |
| Capital call due date | Within 14 days | Critical |
| NAV staleness | > 90 days | Medium |
| Missing fund assignment | On upload | Low |

---

## Build Order

1. **Data model + migrations** — get the schema right before writing a single UI component
2. **Table editor** — manual entry, proves the outputs are useful without ingestion
3. **Cash flow ladder** — the "aha" feature, buildable on manually-entered data
4. **Holdings aggregation view** — asset class / geo / sector pivots
5. **Document upload + basic ingestion** — classification + extraction, human review queue
6. **Reconciliation layer** — diff view, accept/override flow
7. **Risk analysis** — VaR (public), proxied VaR (private), concentration flags
8. **Briefing generator** — last, because it depends on everything above being reliable
9. **Onboarding flow** — polish once core is working

---

## What This Is Not (v1)

- Not a trading platform
- Not a fund accounting system (Advent, Investran) — we're a layer on top, not a replacement
- Not a CRM for investor relations
- No LP portal (showing your investors their performance — that's a different product)
- No automated bank scraping in P0

---

## Open Questions

1. **PDF ingestion accuracy bar** — what % extraction accuracy is acceptable before a document goes to human review? (Suggested: flag if confidence < 85% on any key field)
2. **Proxied VaR disclosure** — how prominently to surface the "this is estimated" caveat? Needs user testing.
3. **Multi-currency** — handle at data model level from day one or simplify to single base currency for MVP?
4. **Supabase vs. custom auth** — Supabase row-level security handles org isolation well, but adds vendor dependency. Decision needed before auth implementation.
5. **Briefing tone/format** — needs a real family office user to validate before building the generator.
