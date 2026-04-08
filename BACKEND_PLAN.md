# ChiefRiskBot — Backend MVP Plan
*April 2026. Demo-first. Family office CIO audience.*

---

## Why This MVP Works for a CIO Demo

Family office CIOs have a specific problem: they sit on multi-custodian, multi-asset portfolios
with no consolidated risk view. Their current process is Excel + a quarterly call with an
external advisor. They are not impressed by dashboards — they have seen many. What stops them
is credibility. The question in the room is always: "Can I trust the numbers?"

This MVP answers that question in a single demo session:

1. **They bring their own data.** Upload a CSV or a custodian statement PDF. Their numbers,
   not sample data. That eliminates the "nice demo, doesn't apply to us" objection.

2. **They see their portfolio understood.** AUM sliced by asset class, geography, sector, and
   market segment — instantly, from their file. Not a template. Their portfolio.

3. **They see risk scored with reasoning.** Not just "VaR = $12M." A panel of analyst agents
   each scoring a different lens: concentration, geopolitical, credit, liquidity. Each with
   a plain-language paragraph explaining *why*. This is the demo moment: the CIO sees language
   they would have written themselves, derived from their positions.

4. **They see a number they already know how to defend.** 1-day historical VaR at 95/99% is
   the universal risk number. Every LP, every auditor, every investment committee already asks
   for it. Showing it computed automatically — from their CSV, with the methodology transparent
   — is the close.

5. **The full cockpit is live.** They can click the dashboard they just watched get populated.
   That makes it a product, not a slideshow.

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app, route registration
├── config.py                # Settings, env vars, API keys
├── database.py              # SQLite (demo) / Postgres (prod) setup via SQLAlchemy
│
├── models/                  # SQLAlchemy ORM models
│   ├── portfolio.py         # PortfolioSnapshot, Position
│   ├── risk.py              # RiskScore, RiskFlag
│   └── briefing.py          # BriefingRun
│
├── routers/                 # FastAPI route modules
│   ├── ingest.py            # POST /ingest/csv, POST /ingest/document
│   ├── portfolio.py         # GET /portfolio/summary, GET /portfolio/positions
│   ├── risk.py              # GET /risk/scores, GET /risk/flags, POST /risk/run
│   ├── var.py               # POST /var/compute
│   ├── market.py            # GET /market/prices, GET /market/macro
│   └── briefing.py          # POST /briefing/generate, GET /briefings
│
├── services/
│   ├── ingest/
│   │   ├── csv_parser.py    # CSV → normalized Position list
│   │   └── doc_parser.py    # PDF/DOCX → position extraction via Claude
│   ├── enrichment/
│   │   ├── market_data.py   # yfinance price fetch + caching
│   │   ├── macro_data.py    # FRED API: rates, VIX, inflation
│   │   └── classifier.py    # Ticker → geo / sector / market segment mapping
│   ├── analytics/
│   │   ├── aggregator.py    # AUM by dimension (asset class, geo, sector, segment)
│   │   ├── var_engine.py    # Historical VaR / CVaR computation
│   │   └── concentration.py # HHI, top-N, single-name, sector cap
│   ├── agents/
│   │   ├── base_analyst.py  # Shared agent scaffolding (prompt, schema, call)
│   │   ├── concentration_analyst.py
│   │   ├── geo_analyst.py
│   │   ├── credit_analyst.py
│   │   ├── liquidity_analyst.py
│   │   └── macro_analyst.py
│   └── briefing/
│       └── generator.py     # Orchestrates analysts → final briefing narrative
│
└── lib/
    ├── cache.py             # Simple in-memory + file cache for market data
    └── schema.py            # Pydantic request/response schemas
```

---

## Phase 1 — Ingest & Portfolio Aggregation

**Goal:** Accept a CSV or PDF, normalize it into positions, enrich with live prices,
return AUM sliced by every dimension the cockpit needs.

### 1A. CSV Ingestion

**Endpoint:** `POST /ingest/csv`

**Input:** Multipart file upload. Accepted columns:
```
ticker, quantity, asset_class, custodian, geo_region, sector, market_segment, notes
```
Minimum required: `ticker`, `quantity`. All other columns are optional — the classifier
fills gaps from ticker lookup.

**Processing pipeline:**
0. Security gate before parsing:
   - allow-list content types and extensions
   - verify magic bytes where applicable
   - reject oversized payloads (demo default 25MB for CSV, lower than document cap)
   - normalize filename for display only; never use it as a filesystem path
1. Parse CSV with `pandas` — handle common variants (semicolon, tab, extra whitespace)
2. Validate: reject rows missing both ticker and quantity, flag but keep rows missing price
3. Normalize asset class values to a controlled vocabulary:
   `public_equity | fixed_income | private_equity | real_estate | commodity | cash | alternative`
4. Persist raw upload to `PortfolioSnapshot` with `source=csv`, `raw_bytes`, `uploaded_at`
5. Persist normalized rows to `Position` table linked to snapshot
6. Kick off enrichment (Phase 2) synchronously for demo; async job in prod

**CSV injection rule:**
- Any cell value that begins with `=`, `+`, `-`, or `@` must be neutralized before the platform
  ever re-exports it to CSV/XLSX or renders it into spreadsheet-compatible downloads
- Preserve the original raw upload for audit, but keep a sanitized/export-safe representation for downstream exports

**Output:**
```json
{
  "snapshot_id": "uuid",
  "position_count": 12,
  "warnings": ["TSM: geo_region not provided, inferred from ticker"],
  "ready_for_enrichment": true
}
```

### 1B. Document Ingestion (PDF / DOCX custodian statements)

**Endpoint:** `POST /ingest/document`

**Input:** PDF or DOCX file.

**Processing pipeline:**
1. Security gate before parsing:
   - allow-list PDF/DOCX/XLSX only
   - verify MIME + magic bytes agreement
   - reject encrypted/password-protected files in demo mode
   - quarantine upload until scan/validation completes
   - cap file size (demo default 50MB) and page count
2. Extract text: `pdfplumber` for PDFs, `python-docx` for DOCX
3. Enforce extraction bounds before model use:
   - max raw text bytes
   - max extracted table rows/pages sent to the model
   - truncate and mark for manual review if exceeded
4. Send extracted text to Claude with a structured extraction prompt:
   - Identify each position: ticker/ISIN, quantity, market value, asset class
   - Flag ambiguous rows for review
   - Return structured JSON matching the Position schema
5. Persist extracted positions to a new `PortfolioSnapshot` with `source=document`
6. Store extraction confidence per row — used to flag "needs review" in the UI

**Document security rules:**
- Never trust embedded filenames, paths, hyperlinks, or metadata from the document
- Do not feed raw extracted text into downstream risk/briefing agents; convert to typed extraction output first
- Files that fail validation or scanning remain blocked and never reach extraction
- Approval is required before low-confidence or truncated extraction results can be bulk-imported into the portfolio

**Why include this:** Many family offices receive Schwab/Pershing PDF statements monthly.
This makes the demo work with a real document they already have.

**Storage rule:**
All uploaded files are stored under server-generated workspace/document ids. `storage_path`
must be derived from trusted ids, not user-controlled filenames, to prevent traversal and overwrite issues.

### 1C. Portfolio Aggregation

**Endpoint:** `GET /portfolio/summary?snapshot_id=...`

**Aggregation dimensions:**
- Asset class (public_equity, fixed_income, etc.)
- Geography (US, Europe, EM Asia, EM Latam, Frontier, Global)
- Sector (GICS level-1: Technology, Financials, Healthcare, etc.)
- Market segment (Large Cap, Mid Cap, Small Cap, Sovereign, IG Credit, HY Credit, etc.)

**Per-dimension output:**
```json
{
  "label": "Public Equity",
  "market_value_usd": 487000000,
  "pct_of_portfolio": 39.1,
  "position_count": 7,
  "top_holdings": [{"ticker": "SPY", "pct": 12.4}]
}
```

**Also computed:**
- Total AUM
- Liquidity score: % of portfolio in T+1 liquid instruments (listed equities + gov bonds)
- HHI concentration index
- Single-name top-5 concentration
- Custodian distribution

All aggregation outputs are cached on the snapshot ID. Recomputed on re-upload only.

---

## Phase 2 — Market Data Enrichment

**Goal:** Every position gets a current price, daily return, native currency, and 1-year of
price history in both local and reporting-currency terms.
Macro context (rates, VIX, credit spreads) is fetched once per session.

### 2A. Position Enrichment

**Service:** `services/enrichment/market_data.py`

**Per ticker:**
- Current price and market value: `yfinance.Ticker.fast_info`
- 1-year daily close history: `yfinance.download` — used for VaR
- Native quote currency
- Daily return, 7D return
- Beta vs SPY (rolling 252-day)

**FX handling:**
- For non-USD securities, fetch 1-year FX history into the workspace reporting currency
- Persist both local-price history and reporting-currency history
- Portfolio VaR always runs in the workspace `reporting_currency`, not raw local returns

**Caching:** Results cached to disk (JSON per ticker, TTL = 4 hours). Demo runs never
re-fetch the same ticker twice in a session.

**Fallback:** If yfinance fails for a ticker (private asset, ISIN not recognized):
- Use manual market_value from the CSV if provided
- Mark the position with `price_source=manual`, surface caveat in the briefing
- Attempt proxy mapping by asset class / sector / region / benchmark if the asset is risk-bearing
  but not directly priced
- If no defensible proxy exists, exclude it from modeled VaR, track it as unmodeled exposure,
  and disclose the excluded market value in the VaR result

### 2B. Macro Context

**Service:** `services/enrichment/macro_data.py`

**Fetched series (FRED API):**
| Series | Label |
|---|---|
| DFF | Fed Funds Rate |
| DGS10 | 10Y Treasury Yield |
| T10YIE | 10Y Breakeven Inflation |
| BAMLH0A0HYM2 | HY Credit Spread (OAS) |
| VIXCLS | VIX |
| DTWEXBGS | USD Broad Trade-Weighted Index |

**Also via yfinance:**
- SPY, AGG, GLD, EEM 7D performance (benchmark reference)

**Output:** Single `macro_context` dict attached to the snapshot, used by all analyst agents
and the VaR engine.

### 2C. Ticker Classifier

**Service:** `services/enrichment/classifier.py`

Fills in `geo_region`, `sector`, `market_segment` for tickers that didn't have them in
the uploaded CSV.

**Method:**
1. Static lookup table for the 500 most common tickers (embedded JSON)
2. For misses: call `yfinance.Ticker.info` fields (`country`, `sector`, `quoteType`)
3. Final fallback: Claude micro-call with ticker + name → classify to controlled vocabulary

This ensures the aggregation in Phase 1C always has dimension data, even for sparse uploads.

---

## Phase 3 — VaR Engine

**Goal:** Compute 1-day historical VaR and CVaR at 95% and 99% confidence, with explicit
coverage and assumption reporting for illiquid or non-priced assets.
Methodology is transparent and defensible to a CIO or LP.

### VaR Computation

**Service:** `services/analytics/var_engine.py`

**Methodology: Historical Simulation (target 252-day lookback)**

Why historical simulation over parametric:
- No normality assumption — captures fat tails, which matter for family office portfolios
  with EM and credit exposure
- Methodology is explainable to a non-quant CIO in one sentence
- No covariance matrix inversion required — avoids singularity issues with small portfolios
- Output is auditable: you can show the actual loss distribution

**Data preparation rules:**
- Use current holdings and current market values, but replay them through historical daily return
  scenarios in the workspace reporting currency
- Build the scenario set from the common overlapping history across all modeled positions and FX
  series; store both `lookback_days=252` target and `effective_lookback_days`
- Require a minimum modeled coverage threshold before returning a production-grade VaR number:
  default 70% of portfolio market value for demo, 85%+ for production
- Track excluded or proxied holdings explicitly so the result can never look fully modeled when it is not

**Private / illiquid asset policy:**
- Level 1: if the holding has reliable traded history, model directly
- Level 2: if not traded directly but there is a defensible liquid proxy, map to a proxy basket
  and record the mapping in assumptions
- Level 3: if neither is available, exclude from VaR, include in `unmodeled_value_usd`, and
  surface a coverage warning in the API/UI
- Do not forward-fill stale private marks into daily return history; that creates false low volatility

**FX / non-USD policy:**
- Compute each non-USD holding's daily return in reporting currency as:
  local asset return + FX return + interaction term
- For cash balances or bonds held directly in foreign currency, model the FX series even if
  the asset price is otherwise flat
- The final VaR number is always in workspace reporting currency

**Steps:**
1. Fetch 1-year of daily price history for all modeled positions and corresponding FX history where needed
2. Convert each return series into the workspace reporting currency
3. Build aligned scenario dates using only the overlapping history window across included series
4. For each historical day, compute portfolio daily P&L as the sum of current position market value × that scenario's reporting-currency return
5. Sort the scenario P&L distribution from worst loss to best gain
6. VaR(95%) = absolute loss at the 5th percentile scenario
7. VaR(99%) = absolute loss at the 1st percentile scenario
8. CVaR(95%) = mean loss of scenarios worse than or equal to VaR(95%)
9. Persist modeled coverage, excluded value, and assumptions alongside the result

**Output:**
```json
{
  "var_1d_95": 14200000,
  "var_1d_99": 18700000,
  "cvar_1d_95": 17100000,
  "cvar_1d_99": 23400000,
  "lookback_days": 252,
  "effective_lookback_days": 241,
  "methodology": "historical_simulation",
  "model_coverage_pct": 82.7,
  "unmodeled_value_usd": 96400000,
  "assumptions": [
    "Blackstone PE Fund III excluded from modeled VaR due to no daily price history",
    "Nestle SA modeled in CHF local returns translated to USD using CHFUSD history",
    "EM private credit sleeve proxied to EMB for demo purposes"
  ],
  "worst_scenario_date": "2025-08-05",
  "worst_scenario_loss": 31200000,
  "position_var_contribution": [
    {"ticker": "QQQ", "contribution_pct": 18.4, "contribution_usd": 5740000, "method": "scenario"},
    {"ticker": "BABA", "contribution_pct": 14.1, "contribution_usd": 4390000, "method": "scenario"}
  ]
}
```

**Position-level VaR contribution**

Do not define the UI number as "VaR with and without the position." That is expensive, unstable,
and non-additive.

Instead:
- Define the default contribution as scenario contribution on the selected VaR breach day:
  each position's contribution = current market value × that scenario day's reporting-currency return
- Normalize those values into `contribution_pct` so the top drivers sum to 100% of modeled loss
- Optionally compute leave-one-out VaR deltas offline for deeper analysis, but do not use that
  as the primary cockpit metric

This keeps the contribution breakdown additive, explainable, and cheap enough for interactive use.

**Max drawdown:**
Also compute 1-year rolling max drawdown for the modeled portfolio in reporting currency.
If coverage is below threshold, display max drawdown with the same coverage warning applied to VaR.

---

## Phase 4 — Agentic Risk Scoring

**Goal:** A panel of five specialist analyst agents, each scoring a different risk dimension,
each producing a structured score (1–10) plus a plain-language rationale paragraph.

The agents do not generate the briefing. They generate structured ratings that are inputs
to the briefing. This separation matters: it makes the reasoning auditable.

### Agent Architecture

**Base class:** `services/agents/base_analyst.py`

Each analyst agent:
1. Receives a standardized context payload (portfolio summary, relevant positions, macro context)
2. Has a specialized system prompt defining its domain, scoring rubric, and output schema
3. Makes one Claude API call
4. Returns a structured `RiskScore` object

All five agents run in parallel behind one `risk_run` async job, but orchestration must be
bounded and failure-tolerant rather than a bare `asyncio.gather`.

**Orchestration contract:**
- Create one parent `async_jobs` row with `job_type=risk_run`
- Launch five child tasks concurrently with per-agent timeout, token cap, and schema validation
- Record one `risk_scores` row per agent with `status=succeeded|failed|timed_out|skipped`
- Mark the parent job:
  - `succeeded` if at least 4 of 5 agents complete and the missing agent is not required for the page to render
  - `failed` if fewer than 4 agents complete or the orchestrator itself errors
- Return partial results plus a warnings array instead of failing the entire risk page for one bad agent

**Failure handling rules:**
- Use `asyncio.gather(..., return_exceptions=True)` or equivalent so one failing call does not cancel its siblings
- Retry at most once for retryable failures (rate limit, transient upstream 5xx, timeout)
- Do not retry prompt-validation failures or schema-validation failures; mark those rows failed immediately
- Persist `error_message`, `latency_ms`, and token usage per agent for later review
- The cockpit should render completed agents first and show an explicit degraded-state banner when any agent failed

**Token budget policy:**
- Set a hard max input token budget per agent payload and trim deterministically before the model call
- Prefer precomputed metrics and top-N slices over raw position dumps
- Default budgets for demo:
  - concentration / geo / credit / liquidity agents: 6k input tokens max each
  - macro agent: 3k input tokens max
  - 1.2k output tokens max per agent
- If a portfolio is too large, pass summarized tables plus only the top risk-relevant positions for that agent
- Persist `input_tokens` and `output_tokens` so budget assumptions can be tuned with real runs

**Prompt injection defense:**
- Never pass raw CSV rows, raw document text, or user-supplied notes directly into an agent prompt as trusted instructions
- Treat uploaded content as untrusted data and serialize it into typed fields only
- Strip control-like content from extracted text before it reaches agent prompts, including strings that try to override system behavior
- Prefer a schema-first payload:
  - portfolio metrics
  - normalized positions
  - macro facts
  - explicit caveats / missing data flags
- Keep the system prompt authoritative and include a rule that uploaded portfolio data is evidence, not instruction
- Store prompt templates in code with versioning; never compose prompts by concatenating raw uploaded text

**Context shaping rules:**
- Concentration agent gets portfolio summary + top positions + concentration metrics, not full raw holdings
- Geo agent gets country/region aggregates + EM-sensitive names + macro regime facts
- Credit agent gets fixed-income sleeve summary + spread/duration metrics
- Liquidity agent gets liquidity buckets + largest illiquid positions + lockup metadata where available
- Macro agent gets only macro data and benchmark context; no raw document excerpts

**Schema (shared across all agents):**
```json
{
  "agent": "concentration_analyst",
  "dimension": "concentration",
  "status": "succeeded",
  "score": 7,
  "severity": "elevated",
  "headline": "Tech + Taiwan double concentration warrants committee discussion",
  "evidence": [
    "QQQ + TSM represent 22.3% of portfolio",
    "Taiwan Strait sensitivity: TSM + BABA contribute 31% of EM equity sleeve"
  ],
  "reasoning": "Two-paragraph plain-language explanation of the risk.",
  "conversation_prompt": "The question to put to the investment committee.",
  "data_sources_used": ["positions.summary", "portfolio.top_positions", "macro.vix", "yfinance.TSM"],
  "prompt_version": "risk-v1",
  "latency_ms": 8421,
  "input_tokens": 4180,
  "output_tokens": 612
}
```

### The Five Analysts

**1. Concentration Analyst**
- Inputs: HHI, top-5 single names, sector weights, custodian distribution
- Scoring rubric: HHI > 0.25 = priority; 0.15–0.25 = elevated; < 0.15 = watch
- Flags: single name > 10%, sector > 35%, single custodian > 60%

**2. Geopolitical / Geographic Analyst**
- Inputs: geo breakdown, EM exposure, country-level positions (TSM → Taiwan, BABA → China)
- Scoring rubric: explicit EM single-country exposure > 5% + elevated geopolitical signal
- Data augmentation: macro context (DXY, EM spreads) + static country risk taxonomy
- Demo value: This is the agent that surfaces "Taiwan Strait" — the kind of insight no
  Excel sheet provides

**3. Credit / Fixed Income Analyst**
- Inputs: fixed income positions, HY credit spread (BAMLH0A0HYM2), duration
- Scoring rubric: HY spread widening + HY allocation > 20% = elevated
- Flags: EM sovereign debt exposure, long duration in rising rate environment

**4. Liquidity Analyst**
- Inputs: liquidity classification per position (listed equity = T+1, PE = illiquid, etc.)
- Scoring rubric: < 50% T+1 liquid = priority; 50–65% = elevated; > 65% = watch
- Flags: illiquid sleeve > 30%, single illiquid position > 15%

**5. Macro Regime Analyst**
- Inputs: all macro context (VIX, rates, credit spreads, DXY, benchmark returns)
- Role: interprets the macro environment and assesses whether current portfolio positioning
  is aligned or misaligned with the regime
- This agent has no position-level inputs — it scores the macro backdrop, not the portfolio.
  The briefing layer correlates its output with the portfolio.

### Risk Flag Engine

**Service:** `services/analytics/concentration.py` + rules in each analyst

Alongside agent-generated scores, a deterministic rules engine generates binary `RiskFlag`
records for well-defined threshold breaches:

| Rule | Condition | Severity |
|---|---|---|
| Single name concentration | Any ticker > 10% of portfolio | elevated |
| Sector concentration | Any GICS sector > 30% | elevated |
| Custodian concentration | Any custodian > 60% of AUM | watch |
| Illiquidity | Illiquid assets > 30% | priority |
| HY credit spread | BAMLH0A0HYM2 > 400bps | elevated |
| VIX spike | VIX > 25 | watch |
| EM single-country | Any EM country > 8% of portfolio | elevated |

These flags feed the "Active Risks" KPI tile and the risk register list on the cockpit.

**Operational note:**
The risk register should merge deterministic `RiskFlag` rows with agent outputs even when one
or more agents fail. Deterministic flags are not blocked on model availability.

---

## Phase 5 — Briefing Generation

**Goal:** Synthesize the five analyst scores into a single, committee-ready briefing document.

### Orchestration

**Service:** `services/briefing/generator.py`

**Input:**
- Portfolio summary (Phase 1C)
- All five analyst `RiskScore` objects (Phase 4)
- VaR result (Phase 3)
- Macro context (Phase 2B)
- Optional: CIO concerns text field

**Claude call structure:**
- System prompt: briefing writer persona (same quality as existing briefing.py, enhanced)
- User prompt: structured dump of all analyst outputs + portfolio summary + VaR
- Instruction: synthesize into a briefing; do not invent new risks; only elevate what the
  analysts already found; write for IC presentation

**Output schema:**
```json
{
  "headline": "string",
  "portfolio_snapshot": { ... },
  "risk_summary": {
    "priority_count": 1,
    "elevated_count": 3,
    "watch_count": 2,
    "top_risks": [ ... ]
  },
  "var_commentary": "Plain-language VaR interpretation for the IC",
  "talking_points": ["3–5 verbatim sentences"],
  "data_caveats": ["..."]
}
```

**Persistence:** Each briefing run stores:
- `snapshot_id` (input)
- Full JSON output
- Model used, token usage, timestamp
- All five analyst scores (linked)

---

## Phase 6 — API Surface (What the Frontend Calls)

All endpoints return JSON. CORS enabled for localhost. No auth in demo mode.

```
POST   /ingest/csv                   Upload CSV → snapshot_id
POST   /ingest/document              Upload PDF/DOCX → snapshot_id
GET    /portfolio/summary            AUM by all dimensions
GET    /portfolio/positions          Full position table
GET    /portfolio/positions/:id      Single position detail
POST   /risk/run                     Trigger all agents → risk scores
GET    /risk/scores                  All agent scores for current snapshot
GET    /risk/flags                   Rules-based flag list
POST   /var/compute                  VaR / CVaR / max drawdown
GET    /market/prices                Enriched position prices
GET    /market/macro                 Macro context payload
POST   /briefing/generate            Run briefing synthesis
GET    /briefings                    List of past briefing runs
GET    /briefings/:id                Full briefing + analyst scores
```

---

## Data Layer

**Demo:** SQLite (`chiefrisktbot.db` in project root). Zero-config, portable, works on a laptop.

**Prod path:** Swap SQLite for Postgres by changing `DATABASE_URL` env var. SQLAlchemy
abstracts this — no code changes required.

**Tables:**
- `portfolio_snapshots` — one row per upload (id, source, created_at, aum, position_count)
- `positions` — one row per holding (snapshot_id, ticker, quantity, market_value, asset_class,
  geo_region, sector, market_segment, price_source, enriched_at)
- `risk_scores` — one row per agent per run (snapshot_id, agent, dimension, score, severity,
  headline, reasoning, evidence JSON, created_at)
- `risk_flags` — deterministic rule breaches (snapshot_id, rule, severity, value, threshold)
- `var_results` — one row per computation (snapshot_id, var_95, var_99, cvar_95, cvar_99,
  methodology, effective_lookback_days, model_coverage_pct, unmodeled_value_usd,
  assumptions JSON, computed_at, position_contributions JSON)
- `briefing_runs` — one row per briefing (snapshot_id, output JSON, model, tokens, created_at)

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Framework | FastAPI | Async, auto OpenAPI docs, already implied by existing code |
| ORM | SQLAlchemy 2.0 + Alembic | Clean, Postgres-ready, migration support |
| DB (demo) | SQLite | Zero-config, portable |
| Market data | yfinance | Already in stack, free, covers all listed tickers |
| Macro data | FRED API (`fredapi`) | Free, authoritative, covers all required series |
| PDF extraction | pdfplumber | Best text extraction for financial statements |
| DOCX extraction | python-docx | Standard |
| Data processing | pandas | Required for CSV, VaR computation |
| AI | Anthropic SDK | Already in stack |
| Async | asyncio + httpx | Parallel agent calls |
| Config | pydantic-settings | 12-factor, env-var driven |

---

## Build Sequence

Build in this order. Each phase is independently testable before the next begins.

```
Phase 1A  CSV ingest + Position persistence
Phase 1C  Portfolio aggregation (asset class, geo, sector, segment)
Phase 2A  Market data enrichment (prices, returns, history)
Phase 2B  Macro context fetch
Phase 3   VaR engine
Phase 4   Five analyst agents (parallel)
Phase 1B  Document ingest (PDF/DOCX via Claude extraction)
Phase 5   Briefing synthesis
Phase 6   API route cleanup + CORS + error handling
```

Phase 1B (document ingest) is deliberately placed after VaR and agents. The CSV path
gives a working demo faster. Documents are the impressive second act.

---

## Demo Script (What the CIO Sees)

1. **Upload their CSV** (or use the sample $1.2B portfolio) → positions appear in the table
2. **Portfolio aggregates** render immediately: AUM by asset class, geo donut, sector heatmap
3. **"Run Risk Analysis"** button → five analyst agents score in parallel (10–15 seconds)
4. **Cockpit populates**: KPI strip (AUM, VaR, Active Risks, HHI, Liquidity), risk register
5. **Click any risk** → see the analyst's evidence + reasoning paragraph
6. **VaR tile** shows 1-day 99% VaR with contribution breakdown by position
7. **"Generate Briefing"** → 30-second narrative synthesis → full IC-ready document
8. **Upload their PDF statement** → positions extracted, portfolio updates, analysis re-runs

The demo proves: their data in, their risk out, their language back to them.
That is the close.
