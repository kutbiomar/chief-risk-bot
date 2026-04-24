# MVP2 Status & Codex Build Instructions

**Branch:** MVP2
**Date:** 2026-04-08
**Status:** PRE-BUILD — spec complete, no code written yet

---

## What MVP2 Is

A private market intelligence platform for family offices and small funds. Eliminates the "Sunday Night Scramble" — the 8–10 hour manual grind of extracting data from PE/VC/HF PDFs, bank portals, and Excel before Monday IC meetings.

**Core value:** "You think you're diversified and liquid. We show you whether you actually are."

Full product spec: `MVP2_SPEC.md`

---

## Reuse Summary from Existing Codebase

The existing ChiefRiskBot codebase (on `mvp-demo` branch) provides significant reusable infrastructure. Overall: ~60% backend infrastructure reuse, ~70% frontend reuse, ~40% business logic reuse.

### REUSE AS-IS (copy without changes)

| Component | Files | Notes |
|-----------|-------|-------|
| FastAPI app structure | `backend/main.py` | Swap router list only (lines 34-45) |
| Database layer | `backend/database.py` | SQLAlchemy engine + session factory |
| Auth models | `backend/models/auth.py` | User, Session, ApiKey, TOTP — exact match |
| Auth router | `backend/routers/auth.py` | All 10 endpoints unchanged |
| Auth services | `backend/services/auth/` | Password hashing, session tokens |
| Audit service | `backend/services/audit/` | AuditEvent with hash chain — keep as-is |
| Jobs model | `backend/models/jobs.py` | AsyncJob for background processing |
| Audit model | `backend/models/audit.py` | AuditEvent for tamper-evident logging |
| Scheduler | `backend/services/scheduler.py` | APScheduler — add MVP2 job types |
| Settings router | `backend/routers/settings.py` | Workspace config — unchanged |
| Health router | `backend/routers/health.py` | GET /health — unchanged |
| CSS design system | `frontend-mvp/_mvp.css` | Color palette, typography, layout — product-agnostic |
| Auth shell JS | `frontend-mvp/_shell.js` | Auth check + page init |
| Login page | `frontend-mvp/login.html` | Unchanged |

### ADAPT (keep structure, change domain logic)

| Component | Files | What Changes |
|-----------|-------|-------------|
| Config | `backend/config.py` | Add: supabase_url, supabase_key, smtp_*, document_storage_backend, reconciliation_variance_threshold_pct (default 2.0), capital_call_alert_days (default 14) |
| Deps | `backend/deps.py` | Add: get_claude_client(), get_document_processor() |
| Content models | `backend/models/content.py` | Add fields to Document: auto_category, provider_name, fund_id (FK), reconciliation_flags (jsonb). Rename BriefingRun → WeeklyBriefing, change output_json schema |
| Onboarding model | `backend/models/onboarding.py` | Change step names: "Fund data populated", "First capital call uploaded", "Liquidity projection run" |
| Documents router | `backend/routers/documents.py` | Keep all endpoints. Add POST /documents/{id}/reconcile (show diff, accept/override) |
| Ingest router | `backend/routers/ingest.py` | Remove CSV parser. Keep file upload flow. Change extraction target to capital events / LP statements |
| Briefing router | `backend/routers/briefings.py` | Same endpoints. Change BriefingRun → WeeklyBriefing, change payload schema |
| Briefing service | `backend/services/briefings.py` | Rewrite: _build_briefing_payload() to use funds/capital_events/alerts/deals. Rewrite BRIEFING_SYSTEM_PROMPT (CRO → CIO/COO). Keep Claude call pattern + PDF export (WeasyPrint) |
| Cockpit router | `backend/routers/cockpit.py` | Aggregate: funds + upcoming capital calls + alerts + deals (not portfolio + risks + market) |
| Document service | `backend/services/documents.py` | Keep file I/O, storage, text extraction (pdfplumber, openpyxl). Rewrite extraction schema targets |
| App JS | `frontend-mvp/_app.js` | Keep: formatting utils, table editor pattern, API call wrapper, form validation. Rewrite: page handlers, state management, entity schemas (Position → Fund/Commitment/CapitalEvent) |
| HTML pages | `frontend-mvp/*.html` | Keep structure. Rewrite cockpit.html. Adapt documents.html (add reconciliation diff view), onboarding.html (fund setup wizard), briefings.html |

### DISCARD (delete, build from scratch)

| Component | Files | Replacement |
|-----------|-------|-------------|
| Portfolio models | `backend/models/portfolio.py` | Create: funds.py, capital.py, holdings.py, deals.py |
| Analytics models | `backend/models/analytics.py` | Create: reconciliation.py, liquidity.py, compliance.py |
| Portfolio router | `backend/routers/portfolio.py` | Create new fund/commitment/holding/deal CRUD router |
| Risk router | `backend/routers/risk.py` | Create: alerts.py (deterministic rules, no AI) |
| Market router | `backend/routers/market.py` | No live market data in MVP2 |
| VAR router | `backend/routers/var.py` | No VaR for private assets in MVP2 |
| Risk service | `backend/services/risk.py` | Create: services/alerts.py (threshold rules) |
| Portfolio service | `backend/services/portfolio.py` | Create: services/portfolio/aggregations.py (fund-level aggregation) |
| CSV parser | `backend/services/ingest/csv_parser.py` | No CSV positions; CSV templates for fund/commitment import |

---

## New Files to Create

### Data Models

**`backend/models/funds.py`**
```python
# Fund: id, workspace_id, name, type (PE|VC|HF|RE|Other), manager_name,
#        vintage_year, fund_size, currency, jurisdiction, created_at, updated_at
# Commitment: id, fund_id, committed_amount, called_capital, uncalled_capital,
#              nav, nav_date, nav_is_estimated (bool), distributions_received,
#              management_fee_rate, carry_rate, created_at, updated_at
#              NOTE: nav_is_estimated bool is NOT enough — add nav_confidence_pct (0-100)
#              NOTE: missing currency field — add commitment_currency
```

**`backend/models/capital.py`**
```python
# CapitalEvent: id, fund_id, workspace_id,
#   type (call|distribution|fee|recallable_distribution),
#   amount, currency, notice_date, due_date, effective_date,
#   source_document_id (FK → Document), notes,
#   is_confirmed (bool — confirmed=notice received, else modelled),
#   created_at, updated_at
```

**`backend/models/holdings.py`**
```python
# Holding: id, fund_id (nullable), workspace_id,
#   asset_name, asset_type (equity|bond|private_co|real_estate|crypto|cash|other),
#   geo_region, sector, currency,
#   quantity, unit_cost, current_value, current_value_date,
#   current_value_source (market|manager_stated|estimated),
#   commitment_id (nullable FK — link holding to its parent commitment for look-through),
#   created_at, updated_at
```

**`backend/models/deals.py`**
```python
# Deal: id, workspace_id, name,
#   stage (sourcing|dd|ic_review|closed|passed),
#   asset_type, target_commitment, target_close_date,
#   lead_analyst_id (FK → User), notes,
#   created_at, updated_at
# DealDocument: deal_id, document_id (join table)
```

**`backend/models/reconciliation.py`**
```python
# ReconciliationFlag: id, document_id, workspace_id,
#   entity_type (commitment|capital_event|holding),
#   entity_id, field_name,
#   document_value (str), system_value (str), variance_pct (float),
#   flagged_at, resolved_by (FK → User), resolution_notes,
#   status (open|resolved|overridden)
```

**`backend/models/liquidity.py`**
```python
# LiquidityProjection: id, workspace_id, generated_at,
#   projection_months (int, default 24),
#   base_currency, scenario (base|stress),
#   monthly_buckets (jsonb — array of {month, inflows, outflows, net, cumulative}),
#   liquidity_gaps (jsonb — array of {month, gap_amount, description})
```

### New Services

**`backend/services/extraction/classifier.py`**
- Input: raw text from document
- Output: document_type (capital_call | lp_statement | quarterly_report | dd_document | portfolio_summary | other)
- Method: Claude with classification prompt. Include confidence score.
- Fallback: keyword matching (contains "capital call notice" → capital_call)

**`backend/services/extraction/extractors.py`**
- One extractor per document type:
  - `extract_capital_call(text)` → {fund_name, amount, currency, due_date, notice_date, wire_instructions}
  - `extract_lp_statement(text)` → {fund_name, nav, nav_date, called_capital, uncalled, distributions, commitment_balance}
  - `extract_quarterly_report(text)` → {fund_name, nav, nav_date, underlying_holdings (list), key_metrics}
- All extractors use Claude with structured output (JSON mode or tool use)
- Each field includes a confidence score (0-100)
- Flag any field with confidence < 85 for human review

**`backend/services/extraction/reconciler.py`**
- Input: extracted data dict + existing system values for that fund/commitment
- Output: list of ReconciliationFlag objects
- Rules:
  - NAV variance > reconciliation_variance_threshold_pct → flag HIGH
  - Called capital: any variance → flag HIGH
  - Distributions: any variance → flag HIGH
  - Commitment balance variance > 1% → flag MEDIUM
  - Capital call due in < capital_call_alert_days → flag CRITICAL
  - NAV date > 90 days old → flag MEDIUM (stale)
- Threshold is configurable via config.reconciliation_variance_threshold_pct

**`backend/services/portfolio/aggregations.py`**
- `summarize_funds(workspace_id, db)` → total_committed, total_called, total_uncalled, distributions_received; by fund type
- `summarize_capital_events(workspace_id, db)` → upcoming calls (next 30/60/90 days), recent distributions
- `summarize_holdings(workspace_id, db)` → by asset class, geo, sector; concentration flags
- `get_look_through_exposure(workspace_id, db)` → cross-fund asset exposure (only when holdings data available from GP reports)

**`backend/services/liquidity.py`**
- `generate_cash_flow_ladder(workspace_id, db, scenario='base')` → LiquidityProjection
- Outflows: unfunded commitments (linear drawdown over remaining fund life), confirmed capital calls
- Inflows: confirmed distributions, estimated distributions from manager schedules
- Include deal pipeline outflows (Deal.target_commitment where stage = ic_review)
- Stress scenario: delay all estimated distributions by 6 months
- Alert: flag any month where net cumulative < configured liquidity_buffer

**`backend/services/alerts.py`**
- Deterministic rules engine — no AI
- Rules:
  - Capital call due < 14 days → CRITICAL
  - Capital call due < 30 days → HIGH
  - Single fund > 30% of total committed → ELEVATED
  - Single manager > 40% of total committed → ELEVATED
  - Uncalled commitments > 50% of total NAV → WATCH
  - Liquidity gap in next 90 days → HIGH
  - NAV stale > 90 days on any fund → WATCH
  - Open reconciliation flags > 0 → INFO
- Output: list of {rule, severity, entity_id, entity_type, message, created_at}

### New Routers

**`backend/routers/funds.py`**
```
POST   /api/portfolio/funds                  → create fund
GET    /api/portfolio/funds                  → list funds (with commitment summary)
GET    /api/portfolio/funds/{id}             → fund detail
PUT    /api/portfolio/funds/{id}             → update
DELETE /api/portfolio/funds/{id}             → soft delete

POST   /api/portfolio/commitments            → add commitment to fund
GET    /api/portfolio/commitments            → list (filter by fund_id)
PUT    /api/portfolio/commitments/{id}       → update NAV/called
DELETE /api/portfolio/commitments/{id}       → soft delete

POST   /api/portfolio/capital-events         → record call or distribution
GET    /api/portfolio/capital-events         → list (filter by fund, type, date range)
PUT    /api/portfolio/capital-events/{id}    → update
DELETE /api/portfolio/capital-events/{id}    → delete

POST   /api/portfolio/holdings               → add holding (manual)
GET    /api/portfolio/holdings               → list (filter by fund, asset_type)
PUT    /api/portfolio/holdings/{id}          → update valuation
DELETE /api/portfolio/holdings/{id}          → soft delete

GET    /api/portfolio/summary                → aggregated view: total commitment, called, uncalled, distributions
GET    /api/portfolio/liquidity              → cash flow ladder (query param: scenario=base|stress)

POST   /api/deals                            → create deal
GET    /api/deals                            → list deals (filter by stage)
PUT    /api/deals/{id}                       → update stage/notes
DELETE /api/deals/{id}                       → soft delete

GET    /api/alerts                           → list active alerts (all rules)
POST   /api/alerts/{id}/acknowledge          → mark seen
```

---

## Critical Issues to Fix During Build

These were identified in the second opinion review. Address them before writing any service logic:

1. **Add `commitment_currency` to Commitment model** — Commitment has no currency field. All arithmetic across Fund/Commitment/CapitalEvent requires currency conversion. Without this field you cannot reconcile multi-currency portfolios.

2. **Add FX Rate table** — Create `backend/models/fx.py`: FxRate (base_currency, quote_currency, rate, rate_date, source). Store the conversion rate used at ingestion time alongside every converted value. Do not rely on yfinance for FX — it has gaps. Use exchangerate-api or ECB data.

3. **Multi-currency is P0, not an open question** — Every monetary calculation must specify a currency and a conversion rate. Define org-level base_currency in WorkspaceSetting. All display values convert to base_currency. Store original currency + amount alongside converted values — never discard originals.

4. **Add `commitment_id` FK to Holding** — The Holding model needs an explicit link to its parent Commitment for look-through aggregation. `fund_id (nullable)` alone does not establish the chain Document → Holding → Commitment → Fund.

5. **Add audit event table** for cell-level edits — The table editor needs a separate AuditEvent per cell change: entity_type, entity_id, field_name, old_value, new_value, changed_by, changed_at. Do not rely on SQLAlchemy updated_at timestamps — they do not record what changed or who changed it.

6. **Define ingestion accuracy measurement** before writing extraction logic:
   - Create a golden dataset of 10 real LP statement formats (anonymised)
   - Define precision/recall per field type (NAV, called capital, distributions, due date)
   - Target: flag for human review if confidence < 85% on any key numeric field
   - Log extraction results vs. human-corrected values to improve prompts over time

7. **Supabase RLS policies must be designed before any data model code** — Every table needs a workspace_id column and a RLS policy: `USING (workspace_id = current_setting('app.current_workspace_id')::uuid)`. One org must never see another org's data. This is a security requirement, not a polish item.

8. **Deal pipeline must feed liquidity projection** — Deal.target_commitment + Deal.target_close_date must appear as outflows in the cash flow ladder when stage = 'ic_review'. The spec originally omitted this.

9. **Recallable distributions need explicit treatment in cash flow ladder** — CapitalEvent.type includes `recallable_distribution`. Define the treatment: recallable capital is NOT liquid until the GP's recall period expires. Add `recall_period_days` and `recall_expires_at` fields to CapitalEvent for this type.

10. **Drop Celery + Redis for MVP** — Use Supabase pg_cron + async FastAPI background tasks (BackgroundTasks) for the weekly briefing job and document processing queue. Celery requires worker management, dead letter queues, and Redis uptime — too much ops overhead for a small team building v1. Revisit at scale.

---

## Build Order

Follow this sequence strictly. Each phase must be complete before starting the next.

**Phase 1 — Foundation (data model first)**
1. Write all new SQLAlchemy models (funds.py, capital.py, holdings.py, deals.py, reconciliation.py, liquidity.py, fx.py)
2. Write Alembic migrations for all new tables
3. Verify RLS policy design is embedded in migration (workspace_id on every table)
4. Copy auth models, jobs, audit models unchanged
5. Adapt config.py, deps.py
6. Wire up new models to main.py

**Phase 2 — Manual data entry (table editor)**
7. Write funds router (CRUD: Fund, Commitment, CapitalEvent, Holding, Deal)
8. Adapt frontend table editor (_app.js) for new entity schemas
9. Verify: user can manually enter fund + commitment + capital events without uploading any documents
10. Verify: cash flow ladder works on manually-entered data

**Phase 3 — Cash flow ladder & holdings view**
11. Write aggregations service (summarize_funds, summarize_capital_events, summarize_holdings)
12. Write liquidity service (cash flow ladder, base + stress scenarios)
13. Write alerts service (deterministic rules)
14. Build cockpit/dashboard frontend (funds summary, upcoming capital calls, alerts)
15. Build cash flow ladder frontend (24-month bar chart)
16. Verify: the "aha" feature — liquidity gap alert works end-to-end

**Phase 4 — Document ingestion**
17. Write extraction classifier (Claude prompt for document type classification)
18. Write extractors per document type (capital_call, lp_statement, quarterly_report)
19. Write reconciler (compare extracted vs. system values, emit ReconciliationFlags)
20. Adapt documents router (add /reconcile endpoint)
21. Adapt document service (keep file I/O, swap extraction schema)
22. Build reconciliation diff UI (document says X, system has Y — accept/override)
23. Evaluate against golden dataset — iterate until confidence thresholds are met

**Phase 5 — Weekly briefing**
24. Adapt briefing service (new payload builder, new system prompt)
25. Adapt briefing router (WeeklyBriefing, same endpoints)
26. Build briefing frontend (in-app view first, PDF second)
27. Test end-to-end: upload doc → extract → approve → briefing generated → sent by email

**Phase 6 — Onboarding & polish**
28. Adapt onboarding wizard (fund setup flow)
29. Write onboarding router adaptations
30. Payment integration (Stripe — standard, not custom)
31. Final QA across all journeys

---

## Tech Stack Decisions

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Database | PostgreSQL via Supabase | RLS for multi-tenancy, storage for documents, auth for user management |
| Auth | Supabase Auth + existing session model | Existing model is solid; Supabase handles MFA and SSO |
| Document storage | Supabase Storage | Collocated with DB; no S3 ops overhead for MVP |
| PDF extraction | pymupdf (fitz) + Claude | pymupdf for text extraction; Claude for classification + field extraction |
| Excel extraction | openpyxl (existing) | Keep as-is |
| Email ingestion | Gmail/Outlook OAuth → parse .eml | Needs inbox OAuth — scope to P1 unless a key customer requires it |
| Background jobs | FastAPI BackgroundTasks + Supabase pg_cron | NOT Celery + Redis; too much ops overhead for MVP |
| PDF generation | WeasyPrint (existing) | Keep for briefing PDF export |
| FX rates | ECB Data API or exchangerate-api.com | Not yfinance — gaps in FX coverage |
| Email delivery | Resend | Simple, developer-friendly, good deliverability |
| Frontend | Vanilla JS (existing pattern) | Keep for P0; evaluate React if table editor complexity grows |

---

## Open Questions (must resolve before coding)

1. **Ingestion accuracy bar**: Define precision/recall targets per field type before writing extractors. Suggested: flag for human review if confidence < 85% on NAV, called capital, distributions, due date.

2. **Briefing tone/format**: Get 2-3 real family office users to review a draft briefing before building the generator. The weekly briefing is a key retention driver — get the format right early.

3. **Email ingestion scope**: Is email parsing (capital call notices forwarded to a monitored inbox) in P0 or P1? It requires Gmail/Outlook OAuth which adds auth complexity. Recommend P1 unless a launch customer requires it.

4. **Benchmark proxies for private VaR**: Cambridge Associates indices are paywalled. If proxied VaR is ever added (currently excluded from P0), identify a free/affordable benchmark proxy source.

---

## Frontend Components to Build

Design system reference: `frontend-design-ideal/DESIGN.md`.
Typography: Fraunces (headings), Inter Tight (UI), JetBrains Mono (all numerics).
Palette: paper `#fff8f6`, navy accent `#1B2B5E`, severity colors for alerts.
All monetary values, percentages, dates, and ratios use JetBrains Mono with `font-feature-settings: "tnum"`.

Components are grouped by page/feature. Reuse status: ✅ exists (adapt), 🆕 new build.

---

### SHARED / PRIMITIVE COMPONENTS

| Component | Status | Description |
|-----------|--------|-------------|
| `KpiStrip` | 🆕 | Top-of-page row of 4–6 headline numbers. Font: JetBrains Mono 20px/700. Fields: label (Inter Tight uplabel), value (mono-lg), delta (±%, coloured by severity). Used on Dashboard, Holdings, Liquidity pages. |
| `AlertBanner` | 🆕 | Full-width dismissible bar in 4 severities: CRITICAL (red), HIGH (amber), ELEVATED (orange), WATCH (grey). Shows icon + one-line message + "View" CTA. Stacks vertically if multiple active. |
| `AlertBadge` | 🆕 | Inline pill: severity colour + label text. Used in table rows and card subheads to surface alert state without a full banner. |
| `DataFreshnessTag` | 🆕 | Small tag showing days since last update. `< 30d` → neutral. `30–90d` → amber. `> 90d` → red. Appears next to any NAV or valuation figure. |
| `StatusChip` | ✅ | Existing severity chips (priority/elevated/watch/good). Reuse as-is; extend with `STALE` and `CRITICAL` states. |
| `EmptyState` | 🆕 | Consistent empty state for tables and charts: illustration-free, Fraunces headline ("No funds added yet"), Inter Tight body, primary CTA button. |
| `ConfirmDialog` | ✅ | Existing modal pattern. Adapt for destructive actions (delete fund, override reconciliation flag). |
| `ToastNotification` | 🆕 | Transient bottom-right toast for async feedback: "Document extracted", "Reconciliation flag resolved", "Briefing sent". Auto-dismiss after 4s. |
| `PageHeader` | ✅ | Fraunces display title + subtitle. Reuse existing pattern. |
| `SectionDivider` | ✅ | Hairline rule with optional label. Reuse. |
| `LoadingSpinner` | ✅ | Existing spinner. Reuse. |

---

### NAVIGATION & SHELL

| Component | Status | Description |
|-----------|--------|-------------|
| `Sidebar` | ✅ | Adapt existing sidebar. New nav items: Dashboard, Holdings, Capital Events, Liquidity, Documents, Deals, Briefings, Alerts, Settings. Remove: Risk Scores, Market Data. |
| `TopBar` | ✅ | Keep workspace name + user avatar + sign out. Add: global alert count badge (red dot if any CRITICAL/HIGH alerts active). |
| `BreadcrumbNav` | 🆕 | Fund → Commitment → detail drill-down needs breadcrumbs. Inter Tight 12px, paper-3 background, chevron separator. |

---

### DASHBOARD (replaces `cockpit.html`)

| Component | Status | Description |
|-----------|--------|-------------|
| `DashboardKpiStrip` | 🆕 | 5 KPIs: Total Committed, Total Called, Uncalled Commitments, Distributions Received, Portfolio NAV. All JetBrains Mono. Each shows currency-converted base value + data freshness. |
| `UpcomingCapitalCallsCard` | 🆕 | Card listing capital calls due in the next 30/60/90 days. Columns: Fund, Amount, Due Date, Days Remaining. Due date < 14 days highlighted CRITICAL. Sortable by due date. |
| `LiquiditySnapshotCard` | 🆕 | Mini version of the cash flow ladder — next 6 months only, bar chart. Inflows (distributions) green, outflows (calls + fees) amber. Net line. "View full projection" CTA. |
| `AlertsRailCard` | 🆕 | Right-rail card listing all active alerts in severity order. Each row: badge + one-line message + acknowledge button. Collapses if zero alerts. |
| `DealPipelineSummaryCard` | 🆕 | Compact deal pipeline: count of deals by stage (sourcing / DD / IC review / closed / passed), total target commitment in IC review. CTA: "View all deals". |
| `RecentDocumentsCard` | 🆕 | Last 5 uploaded documents. Columns: filename, fund, classification, processing status chip, uploaded at. "Review" CTA for documents in `needs_review` state. |
| `WeeklyBriefingPreviewCard` | ✅ | Adapt existing briefing preview. Show executive summary text + "Read full briefing" CTA. |

---

### HOLDINGS VIEW

| Component | Status | Description |
|-----------|--------|-------------|
| `HoldingsPivotToggle` | 🆕 | Segmented control: Asset Class / Geography / Sector. Switches the breakdown view. Inter Tight 12px. Active state: navy background, white text. |
| `HoldingsBreakdownTable` | 🆕 | Main holdings table. Columns vary by pivot: Name, Type/Region/Sector, Current Value, % of Portfolio, Cost Basis, Unrealised G/L, Data Freshness. Numeric columns: JetBrains Mono, right-aligned. Stale rows dimmed + DataFreshnessTag. Sortable columns. |
| `ConcentrationAlert` | 🆕 | Inline banner within Holdings view. Triggered when any single name > 20% or sector > 40% of portfolio. Cites the specific name + threshold breached. |
| `LookThroughRow` | 🆕 | Expandable row within Holdings table showing cross-fund exposure. E.g. "US Tech Semiconductors: 12% total (Fund A direct 7% + Fund B indirect 5%)". Expand icon + indented child rows. Only visible when underlying holdings data exists from GP reports. |
| `HoldingsExportButton` | 🆕 | Export filtered table to CSV/Excel. Single button, dropdown with format choice. |

---

### FUND & COMMITMENT TABLES (table editor, replaces `table.html` for portfolio entities)

| Component | Status | Description |
|-----------|--------|-------------|
| `FundTable` | ✅ 🔄 | Adapt existing table editor. Columns: Fund Name, Type, Manager, Vintage, Fund Size, Currency, Jurisdiction. Inline add/edit/delete. Clicking a fund name drills into FundDetailPage. |
| `CommitmentTable` | 🆕 | Per-fund inline table. Columns: Committed, Called, Uncalled, NAV, NAV Date, Distributions Received, Mgmt Fee %, Carry %. All monetary values: JetBrains Mono. NAV Date shows DataFreshnessTag. |
| `CapitalEventTable` | 🆕 | Global or per-fund table. Columns: Type chip (call/distribution/fee/recallable), Fund, Amount, Currency, Notice Date, Due Date, Status chip (confirmed/estimated), Source Document link. Upcoming calls with due date < 14d show CRITICAL AlertBadge. Sortable by due date. |
| `HoldingTable` | 🆕 | Per-fund or global table. Columns: Asset Name, Asset Type, Region, Sector, Currency, Qty, Unit Cost, Current Value, Value Date, Value Source chip. Inline add/edit/delete. |
| `InlineEditCell` | ✅ | Existing inline cell edit (click to edit, blur/enter to save). Reuse as-is. |
| `CsvImportButton` | ✅ | Adapt existing CSV import. New templates: fund template, commitment template (different columns from current position template). |
| `AuditTrailDrawer` | 🆕 | Slide-in right drawer showing cell-level change log for the selected row: field, old value → new value, changed by, timestamp. Triggered by "History" icon on row hover. JetBrains Mono for values, mono-sm for timestamps. |

---

### CAPITAL EVENTS PAGE

| Component | Status | Description |
|-----------|--------|-------------|
| `CapitalEventFilterBar` | 🆕 | Filter row above the CapitalEventTable: Type (all/calls/distributions/fees), Fund (dropdown), Date Range picker, Status (confirmed/estimated). Resets to defaults via "Clear" link. |
| `CapitalEventCalendarStrip` | 🆕 | Horizontal 12-week strip with dots on dates where capital events fall. Click a dot to jump to that event in the table below. CRITICAL dates (< 14 days) shown in red. |
| `MarkConfirmedButton` | 🆕 | Inline button on estimated capital events: "Mark as confirmed (notice received)". Updates is_confirmed flag. Shows ReconciliationFlag if the confirmed amount differs from the modelled amount. |

---

### LIQUIDITY PROJECTION PAGE

| Component | Status | Description |
|-----------|--------|-------------|
| `LiquidityCashFlowChart` | 🆕 | 24-month grouped bar chart. Per month: inflows bar (green) + outflows bar (amber). Net cumulative line overlay (navy). Months with liquidity gap highlighted with red background band. X-axis: MMM YY labels. Y-axis: base currency. JetBrains Mono tick labels. Tooltip on hover: fund breakdown of that month's flows. |
| `ScenarioToggle` | 🆕 | Two-state toggle: Base Case / Stress (distributions delayed 6 months). Switching re-fetches projection data and animates chart. |
| `LiquidityGapCallout` | 🆕 | If any month has a gap: prominent callout card above the chart. "Liquidity gap detected: Month 7 (Oct 2026) — outflows exceed inflows by $3.2M. Suggested action: [trim S&P position / arrange credit facility]." CRITICAL severity styling. |
| `MonthlyBreakdownTable` | 🆕 | Below the chart: table with one row per month. Columns: Month, Inflows (by source), Outflows (by fund), Net, Cumulative Balance. Expandable rows to show per-fund breakdown. JetBrains Mono throughout. |
| `LiquidityBufferSetting` | 🆕 | Small inline control: "Minimum cash buffer: $____". Edits WorkspaceSetting.liquidity_buffer. Updates gap detection immediately. |

---

### DOCUMENT MANAGEMENT PAGE (adapts `documents.html`)

| Component | Status | Description |
|-----------|--------|-------------|
| `DocumentUploadZone` | ✅ | Existing drag-and-drop zone. Reuse. Add: accepted file type tooltip (PDF, XLSX, CSV, .eml, DOCX, max 50MB). |
| `DocumentListTable` | ✅ | Adapt existing document list. New columns: Provider, Fund (auto-assigned or "Assign →"), Classification chip, Processing Status chip, Reconciliation Flags count badge. |
| `ClassificationChip` | 🆕 | Colour-coded chip for document type: capital_call (amber), lp_statement (blue), quarterly_report (teal), dd_document (purple), portfolio_summary (grey), other (grey). |
| `DocumentProcessingStatusChip` | ✅ | Adapt existing extraction status chip. States: pending (grey), processing (animated), done (green), needs_review (amber + count of flags), failed (red). |
| `FundAssignmentDropdown` | 🆕 | Inline dropdown on unassigned documents. Autocomplete from existing fund list. "Create new fund" option at bottom. Saves on select. |
| `ReconciliationDiffView` | 🆕 | The most important new component. Shown when user clicks "Review" on a document with needs_review status. Side-by-side: Document says / System has. Per-field rows: field name, document value (JetBrains Mono), system value (JetBrains Mono), variance %. Row background: red if HIGH, amber if MEDIUM. Per-row actions: Accept Document Value / Keep System Value / Investigate. Submit button to resolve all flags. |
| `ExtractionConfidenceBar` | 🆕 | Per-document confidence indicator: horizontal bar 0–100% with numeric label. Green > 85%, amber 70–85%, red < 70%. Appears in document detail and as a column in DocumentListTable. |
| `DocumentFolderTree` | 🆕 | Left sidebar on Documents page showing auto-folder hierarchy: Provider > Fund > Doc Type > Year. Clicking a folder filters the table. Collapse/expand. Count badge per folder. |
| `DocumentSearchBar` | ✅ | Adapt existing search. Full-text search across document content. Debounced, 300ms. |

---

### DEAL PIPELINE PAGE

| Component | Status | Description |
|-----------|--------|-------------|
| `DealKanbanView` | 🆕 | Kanban board with columns: Sourcing / DD / IC Review / Closed / Passed. Each deal is a card: deal name, asset type chip, target commitment (JetBrains Mono), lead analyst avatar, target close date. Drag-to-move between stages (updates Deal.stage via API). |
| `DealListView` | 🆕 | Toggle from Kanban to table view. Columns: Name, Stage chip, Asset Type, Target Commitment, Target Close Date, Lead Analyst, Documents count, Last Updated. |
| `DealCard` | 🆕 | Used in Kanban and as detail header. Shows deal name (Fraunces h2), stage chip, target commitment (JetBrains Mono mono-lg), target close date, lead analyst, document count badge. |
| `DealDetailDrawer` | 🆕 | Slide-in right drawer for deal detail: KPIs at top, notes editor (plain text, auto-save), linked documents list (with upload button), stage history timeline. |
| `DealDocumentLinkPanel` | 🆕 | Within DealDetailDrawer: shows documents tagged to this deal. Drag existing documents from library or upload new. Thumbnail + filename + classification chip. |
| `LiquidityImpactNote` | 🆕 | Within DealDetailDrawer: "Adding this commitment will add $Xm outflow in [month]. Liquidity impact: [green OK / amber watch / red gap]." Auto-computed from target_commitment + target_close_date vs. current cash flow ladder. |

---

### WEEKLY BRIEFING PAGE (adapts `briefings.html` + `briefing.html`)

| Component | Status | Description |
|-----------|--------|-------------|
| `BriefingListTable` | ✅ | Adapt existing. Columns: Date, Status chip (draft/published), Capital Events Covered, Alerts Included, Sent To count. Add "Download PDF" button per row. |
| `BriefingDetailView` | ✅ | Adapt existing rich text view. Sections: Executive Summary, Capital Events This Week, Liquidity Watch, Deal Pipeline Updates, Risk Summary, Documents Received, Data Caveats. Each section collapsible. |
| `BriefingGenerateButton` | ✅ | Adapt existing. "Generate briefing for this week". Shows loading state with estimated time. |
| `BriefingRecipientConfig` | 🆕 | Settings sub-panel: add/remove email recipients per briefing section. E.g. "CIO receives all sections; Analyst receives Capital Events + Documents only." |
| `DataCaveatsSection` | 🆕 | Auto-generated section at bottom of every briefing. Lists: any stale NAVs used (fund name + days stale), any open reconciliation flags not yet resolved, any holdings with estimated valuation source. Styled distinctly (paper-3 background, smaller type). |

---

### ALERTS PAGE

| Component | Status | Description |
|-----------|--------|-------------|
| `AlertsTable` | 🆕 | Full table of all active and recent alerts. Columns: Severity chip, Rule description, Entity (fund name / document name), Value, Threshold, Triggered At, Status (active/acknowledged). |
| `AcknowledgeButton` | 🆕 | Per-row button on active alerts. Marks alert acknowledged by current user + timestamp. Does not suppress re-triggering if condition persists. |
| `AlertRulesConfig` | 🆕 | Settings sub-panel: list of all active alert rules with their thresholds. User can adjust: capital call alert days (default 14), concentration threshold (default 20%), NAV staleness threshold (default 90 days), liquidity buffer amount. Saves to WorkspaceSetting. |

---

### ONBOARDING WIZARD (adapts `onboarding.html`)

| Component | Status | Description |
|-----------|--------|-------------|
| `OnboardingWizard` | ✅ 🔄 | Adapt existing wizard shell. New steps: (1) Workspace setup, (2) Add first fund, (3) Add first commitment, (4) Upload first document, (5) Review extraction, (6) Run liquidity projection. Progress bar at top. |
| `FundSetupStep` | 🆕 | Wizard step 2: inline FundTable in create-only mode. Guided labels, tooltip on each field. "Add another fund" link. |
| `CommitmentSetupStep` | 🆕 | Wizard step 3: CommitmentTable for the fund just created. Pre-fills fund name. |
| `FirstDocumentStep` | 🆕 | Wizard step 4: DocumentUploadZone with instructional copy: "Upload a capital call notice or LP statement from any of your fund managers." |
| `ExtractionReviewStep` | 🆕 | Wizard step 5: if extraction produced results, show a simplified ReconciliationDiffView. Single "Looks good — save" CTA. |
| `LiquidityPreviewStep` | 🆕 | Wizard step 6: render a 6-month mini LiquidityCashFlowChart from the data just entered. "This is your liquidity position. See the full 24-month projection →". |

---

### SETTINGS PAGE (adapts existing)

| Component | Status | Description |
|-----------|--------|-------------|
| `WorkspaceSettingsForm` | ✅ | Keep existing. Add: base_currency selector, liquidity_buffer_amount field, reconciliation_variance_threshold (%) field, capital_call_alert_days field. |
| `BriefingScheduleConfig` | ✅ | Keep existing day/time picker for weekly briefing. Add: recipient management (see BriefingRecipientConfig). |
| `TeamManagementTable` | ✅ | Existing user invite/role table. Reuse as-is. |
| `AlertRulesConfig` | 🆕 | (Listed above under Alerts — same component surfaced in Settings tab.) |
| `ApiKeysTable` | ✅ | Existing API key management. Reuse as-is. |

---

### COMPONENT SUMMARY

| Category | New | Adapt | Reuse |
|----------|-----|-------|-------|
| Shared / Primitives | 6 | 1 | 4 |
| Navigation & Shell | 1 | 2 | 0 |
| Dashboard | 7 | 1 | 0 |
| Holdings View | 5 | 0 | 0 |
| Fund / Commitment Tables | 4 | 3 | 2 |
| Capital Events | 3 | 0 | 0 |
| Liquidity Projection | 5 | 0 | 0 |
| Document Management | 6 | 4 | 0 |
| Deal Pipeline | 6 | 0 | 0 |
| Weekly Briefing | 2 | 3 | 0 |
| Alerts | 3 | 0 | 0 |
| Onboarding | 4 | 1 | 0 |
| Settings | 1 | 4 | 2 |
| **Total** | **53** | **19** | **8** |

**53 new components, 19 adaptations, 8 reused as-is.**

The highest-priority components to build first (Phase 3 in build order):
1. `LiquidityCashFlowChart` — the "aha" feature, must land with Phase 3
2. `UpcomingCapitalCallsCard` — the first thing an analyst looks at Monday morning
3. `ReconciliationDiffView` — gating feature for document ingestion to be trusted
4. `AlertBanner` + `AlertBadge` — needed everywhere before any page ships

---

## File Reference

- Full product spec: `MVP2_SPEC.md`
- Design system: `frontend-design-ideal/DESIGN.md` (use for all visual decisions)
- Existing codebase: `mvp-demo` branch
- This file: `MVP2_STATUS.md`
