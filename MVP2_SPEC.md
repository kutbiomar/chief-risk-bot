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

-- Macro overlay factor tags (populated at extraction time; editable via table editor)
factor_asset_class   TEXT,   -- e.g. "private_equity", "infrastructure"
factor_sector        TEXT,   -- e.g. "energy"
factor_subsector     TEXT,   -- e.g. "renewables:solar"
factor_market_segment TEXT,  -- e.g. "mid_cap", "emerging_markets"
factor_country       TEXT,   -- ISO-3166 alpha-2
factor_region        TEXT,   -- "western_europe", "us", "apac_developed"
factor_tag_source    TEXT,   -- "extracted" | "inferred" | "manual"
factor_tag_confidence FLOAT, -- 0.0–1.0

created_at, updated_at
```

### FactorScore

Daily macro risk scores for each factor node in the taxonomy.

```
id, factor_key TEXT,     -- e.g. "sector:energy:renewables:solar"
date DATE,
score FLOAT,             -- 0–100 (higher = more risk)
z_score FLOAT,           -- deviation from 90-day rolling mean
direction TEXT,          -- "improving" | "stable" | "deteriorating"
primary_driver TEXT,     -- which signal moved the score most
proxy_tickers JSONB,     -- ["TAN", "ICLN"] — the public proxies used
raw_signals JSONB,       -- snapshot of input values (price levels, spreads, etc.)
sentiment_modifier FLOAT,-- ±10% sentiment adjustment applied
confidence FLOAT,        -- 0.0–1.0 (lower when proxy coverage is thin)
created_at TIMESTAMP
```

### AssetFactorExposure

Many-to-many: each holding may be exposed to multiple factors with different weights.

```
id, holding_id FK → holdings,
factor_key TEXT,         -- matches FactorScore.factor_key
weight FLOAT,            -- 0.0–1.0, portion of holding's value exposed to this factor
source TEXT,             -- "extracted" | "inferred" | "manual"
confidence FLOAT,
created_at TIMESTAMP
```

### ProxyBasket

Defines which public instruments proxy each private asset class / sector combination.

```
id, basket_key TEXT UNIQUE,  -- e.g. "private_equity:energy:midstream"
display_name TEXT,
tickers JSONB,               -- [{"ticker": "AMJ", "weight": 0.60}, ...]
illiquidity_scalar FLOAT,    -- 1.1–1.5×, applied to proxy volatility
notes TEXT,
updated_at TIMESTAMP
```

### StressScenario

Named historical and hypothetical shock scenarios used for stress VaR.

```
id, name TEXT,               -- "GFC 2008", "COVID Crash", "2022 Rate Shock"
description TEXT,
factor_shocks JSONB,         -- {"sector:energy:upstream": -0.45, "macro:rates:10y": +0.03}
estimated_portfolio_impact FLOAT,  -- recomputed daily against current holdings
last_run_at TIMESTAMP,
created_at TIMESTAMP
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

Risk analysis now operates in two layers: the **Macro Overlay** (daily, forward-looking,
factor-driven) and the **VaR Engine** (daily, statistical, calibrated by the overlay).

---

#### 6a. Macro Risk Overlay (New)

The overlay runs every trading day at market close. It converts public market signals
into risk scores for every factor node in the taxonomy, then propagates those scores
across the portfolio using each holding's factor exposure weights.

**Factor Taxonomy (four dimensions, hierarchical):**
- Asset Class: PE, VC, Private Credit, Real Estate, Infrastructure, Public Equity, Fixed Income, Commodities, Cash
- Sector + Subsector: Energy (Upstream / Midstream / Downstream / Renewables:Solar / Renewables:Wind) · Technology · Healthcare · Industrials · Consumer · Financials · Real Assets
- Market Segment: Large Cap · Mid Cap · Small Cap / Early Stage · Emerging Markets · Frontier
- Country / Region: US · Western Europe · GCC · China · India · SEA · LatAm

**Signal sources (all already in stack):**
- Equity indices via yfinance: XLE (energy), TAN (solar), FAN (wind), AMJ (midstream), VNQ (real estate), MSCI EM, SOX (semis), S&P 500, Russell 2000
- Macro via FRED: 10Y Treasury yield, Fed Funds rate, IG/HY credit spreads, DXY
- Commodities via yfinance: WTI (CL=F), Brent (BZ=F), Natural Gas, Copper (HG=F), Gold (GC=F)
- Sentiment: LLM agent (claude-sonnet-4-6) processes daily financial headlines per sector, produces directional modifier ±10%

**Factor score:** 0–100 (higher = more risk). Derived from rolling 90-day z-score of
proxy index. Sentiment score is a modifier layered on top, not a primary signal.

**AUM Triangulation View:**
A pivot table updated daily. Shows for each factor: AUM exposed ($), % of portfolio,
current risk score, direction (improving / stable / deteriorating). This is the primary
risk dashboard for the CIO — one view that answers "where is my capital and how risky
is it *right now*?"

| Factor | AUM Exposed | % Portfolio | Risk Score | Direction |
|---|---|---|---|---|
| Energy — Renewables | $82M | 16.4% | 71 | ↓ deteriorating |
| US Large Cap Equity | $145M | 29% | 42 | → stable |
| Real Estate — Commercial | $61M | 12.2% | 68 | ↓ deteriorating |
| Private Credit — US | $47M | 9.4% | 61 | → stable |
| ... | | | | |

**Overlay alerts:**
- Factor score > 75 with > 10% AUM exposure → Amber alert on dashboard
- Factor score > 85 with > 5% AUM exposure → Red alert + push notification
- Portfolio composite score moves > 10 points intraday → "Market conditions changed materially"
- Risk regime switches (see §6b) → Immediate notification + VaR recompute

---

#### 6b. VaR Engine (Enhanced)

**Risk Regime Detection:**
VIX and credit spreads determine the VaR methodology in use:

| VIX | Credit Spread | Regime | VaR Window |
|---|---|---|---|
| < 18 | IG < 150bps | Normal | Historical 90-day |
| 18–28 | IG 150–250bps | Stress | Historical 30-day, recent data 2× weighted |
| > 28 | IG > 250bps | Crisis | GFC scenario floor — statistical VaR overridden |

Regime is displayed on the dashboard at all times. Regime changes are logged and
surfaced in the brief ("Risk model operating in Stress regime since Tuesday").

**Public Holdings VaR:**
- Historical simulation VaR: 1-day at 95% and 99% confidence
- Data: daily price returns from yfinance
- Portfolio VaR accounts for cross-asset correlations (covariance matrix, 90-day rolling)
- Factor attribution: each holding's VaR contribution decomposed by factor exposure

**Private Holdings VaR — Proxy Basket Method:**
Each private fund/holding is mapped to a proxy basket of public instruments. The basket's
realized volatility, adjusted for illiquidity, becomes the VaR estimate for that position.

```
Private VaR = VaR(proxy basket) × illiquidity_scalar

Illiquidity scalars:
  PE Buyout:       1.3×  (leverage amplifies; smoothed NAVs understate)
  VC:              1.5×  (binary outcomes, extreme skew)
  Private Credit:  1.2×  (lower vol but credit default tail)
  Infrastructure:  1.1×  (regulated cash flows, lower correlation)
  Real Estate:     1.3×  (illiquid; cap rate moves lag market)
```

Example proxy baskets:
- US Midstream PE → 60% AMJ + 25% XLE + 15% 10Y yield sensitivity
- US Solar Infrastructure → 70% TAN + 20% ICLN + 10% 10Y yield sensitivity
- US Buyout (generalist) → 60% S&P 500 + 25% Russell 2000 + 15% HY credit spread

When a factor score spikes, proxy basket volatility for all holdings tagged to that
factor is widened dynamically before VaR computation.

All private VaR numbers are labelled: *"Estimated — proxy basket method. Actual losses
may differ."* Label is non-removable.

**Stress Scenarios (run alongside VaR daily):**

| Scenario | Key Shocks | Typical Portfolio Impact |
|---|---|---|
| GFC 2008 | Credit +500bps, Equity −50%, RE −40% | PE −35%, RE −30% |
| COVID Crash 2020 | Equity −35%, VIX → 80 | VC −40%, Healthcare +10% |
| 2022 Rate Shock | 10Y +300bps, Tech −50% | VC −50%, RE cap rate expansion |
| Renewables Policy Reversal | Solar ETF −40% | Renewables Infra −25% |
| Energy Price Collapse | WTI −60%, Gas −70% | Energy PE −45% |
| EM Contagion | MSCI EM −40%, EM FX −25% | EM funds −35% |

Each scenario's estimated dollar impact is recomputed daily against current holdings.
Output: "Under 2022 Rate Shock, estimated portfolio decline: −$47M (−9.4%)."

**Risk Decomposition (carried over, enhanced):**
- Top 5 contributors to total portfolio VaR (by factor)
- Concentration score: Herfindahl index on sector, geo, and manager
- Manager concentration: % of NAV with any single GP
- Vintage year clustering alert: if > 30% of PE/VC commitments share a 2-year vintage window
- Fund lifecycle flags: PE fund > 7 years old with < 1× DPI flagged for review

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

### Macro Overlay Agent

**Trigger:** Daily at market close (5pm ET) via Celery beat; also on-demand
**Runtime:** ~90 seconds
**Model:** claude-sonnet-4-6 (factor scoring + sentiment); claude-opus-4-6 (regime narrative)
**Sub-agents (parallel):**
- Signal Collector: fetches yfinance + FRED data for all tracked tickers
- Sentiment Agent: processes past 24h financial headlines per portfolio sector
- Factor Scorer: computes z-scores + weighted factor scores
- Regime Detector: evaluates VIX + credit spreads → sets risk regime
- Propagation Engine: maps factor scores → portfolio positions → AUM triangulation table
- Alert Generator: checks thresholds, queues notifications

**Output:** Daily `FactorScore` rows, updated `AUM Triangulation` view, regime flag,
alert notifications if thresholds breached
**Failure mode:** If market data fetch fails, carry forward previous day's scores with
a staleness flag. Never silently drop — surface "Risk data as of [date]" on dashboard.

### Risk Analyst Agent

**Trigger:** After Macro Overlay Agent completes; also on new holdings data or manual refresh
**Tools:** Factor scores (from overlay), proxy basket definitions, yfinance price history,
Herfindahl calculator, VaR engine, stress scenario definitions
**Output:** VaR result object (public + private + total), stress scenario impacts,
concentration flags, risk decomposition by factor
**Runs:** Daily (post-overlay) + on demand

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

1. **Data model + migrations** — schema first: include FactorScore, AssetFactorExposure,
   ProxyBasket, StressScenario tables, and factor tag columns on holdings from day one
2. **Table editor** — manual entry, proves the outputs are useful without ingestion;
   factor tags editable inline (fallback when extraction isn't running yet)
3. **Cash flow ladder** — the "aha" feature, buildable on manually-entered data
4. **Holdings aggregation view** — asset class / geo / sector pivots;
   factor tag columns are already in schema so this view is overlay-ready from the start
5. **Proxy basket definitions** — seed the DB with 8–10 baskets covering common fund types;
   no code needed yet, just the config
6. **Signal collection + factor scoring** — yfinance + FRED daily fetch, z-score computation,
   factor score storage; no UI yet — verify scores in DB directly
7. **Public VaR** — historical simulation using existing price data; prove the VaR engine
   works on public positions before touching private
8. **Private proxy VaR** — wire factor scores → proxy basket volatility → illiquidity scalar;
   label everything "Estimated"
9. **AUM Triangulation view** — the daily factor risk dashboard; this is the overlay's UI;
   show AUM, %, score, direction per factor row
10. **Regime detection** — VIX + credit spread classifier; switch VaR window automatically;
    surface regime label on dashboard
11. **Stress scenarios** — 5 core scenarios as config; daily recomputation against holdings;
    show estimated portfolio impact in $
12. **Document upload + ingestion pipeline** — classification + extraction; Risk Officer Agent
    populates factor tags automatically at ingestion time
13. **Reconciliation layer** — diff view, accept/override flow
14. **Sentiment agent** — LLM news processing per sector; ±10% modifier on factor scores;
    lowest priority because it's additive not foundational
15. **Briefing generator** — last; by now the data layer is clean and the overlay is live
16. **Onboarding flow** — polish once core is working

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
2. **Proxied VaR disclosure** — how prominently to surface the "this is estimated" caveat? Needs user testing. Current plan: non-removable label on every private VaR number.
3. **Multi-currency** — handle at data model level from day one or simplify to single base currency for MVP?
4. **Supabase vs. custom auth** — Supabase row-level security handles org isolation well, but adds vendor dependency. Decision needed before auth implementation.
5. **Briefing tone/format** — needs a real family office user to validate before building the generator.
6. **Factor tag coverage** — for private funds with no disclosed look-through holdings, factor tags are inferred from manager mandate + fund type. Confidence will be lower. How prominently to surface "inferred" vs. "extracted" tags in the UI?
7. **Proxy basket maintenance** — who owns updating proxy baskets when new instruments become better proxies (e.g., new clean energy ETFs)? Suggest: admin-editable in settings, reviewed quarterly.
8. **Sentiment agent news sources** — financial news APIs (NewsAPI, Refinitiv) have cost and rate-limit implications. For MVP, RSS scraping of FT/Reuters/WSJ is sufficient. Upgrade path needed.
9. **Illiquidity scalar calibration** — the 1.1–1.5× scalars are judgement-based defaults. A real family office may want to override these per fund. Should they be editable per holding or per asset class globally?
10. **Stress scenario customisation** — the 5 built-in scenarios cover common risks. CIOs will want custom scenarios ("What if GCC real estate drops 30%?"). Custom scenario builder is P1.
