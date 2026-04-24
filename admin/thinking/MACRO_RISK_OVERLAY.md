# Macro Risk Overlay Strategy

**Context:** ChiefRiskBot — family office risk briefing platform  
**Date:** April 2026  
**Scope:** A daily-run layer that assigns macro risk scores by asset class, sector/subsector,
market segment, and country — enabling AUM triangulation and enhanced VaR

---

## The Problem This Solves

Private fund NAVs arrive quarterly, with a 45–90 day lag. A family office CIO whose
portfolio has 60% in private markets is effectively flying blind between report dates.

The Macro Risk Overlay fixes this. By ingesting live public market signals and mapping
them to each portfolio position's factor exposures, you can estimate the risk *now* —
not when the GP gets around to reporting it. Every private asset has a public market
analogue. Find it. Track it. That's the proxy risk signal.

**The core loop:**

```
Public signals (daily) → Factor scores → Asset factor map → Risk-adjusted NAV proxy → VaR
```

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SIGNAL COLLECTION                      │
│  Equity Indices │ Commodity Prices │ Policy │ Sentiment  │
└────────────────────────┬────────────────────────────────┘
                         │ daily
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FACTOR SCORING ENGINE                   │
│   Asset Class │ Sector+Subsector │ Geography │ Segment   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              ASSET-TO-FACTOR MAPPING                     │
│  (Each holding tagged at extraction time)               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              RISK SIGNAL PROPAGATION                     │
│  Asset → Fund → Portfolio  (weighted by AUM)            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   VaR ENGINE                             │
│  Parametric (public) │ Factor-Proxy (private)           │
└─────────────────────────────────────────────────────────┘
```

---

## 1. The Factor Taxonomy

Every portfolio position is tagged across four dimensions. These tags are the bridge
between a macro signal and a specific holding.

### Dimension 1: Asset Class

```
├── Private Equity
├── Venture Capital
├── Private Credit / Direct Lending
├── Real Estate
│   ├── Commercial
│   ├── Residential
│   └── Industrial / Logistics
├── Infrastructure
│   ├── Energy Infrastructure
│   ├── Transport
│   └── Digital (Data Centres, Fibre)
├── Public Equity
├── Fixed Income
├── Commodities
└── Cash / Equivalents
```

### Dimension 2: Sector + Subsector

Use a simplified GICS-inspired hierarchy tuned for private markets:

```
Energy
├── Upstream (E&P, Oil & Gas Extraction)
├── Midstream (Pipelines, LNG, Storage)
├── Downstream (Refining, Petrochemicals, Distribution)
├── Renewables
│   ├── Solar
│   ├── Wind (Onshore / Offshore)
│   ├── Hydro / Storage
│   └── Transition Technology (Green Hydrogen, CCS)
└── Energy Services

Industrials
├── Aerospace & Defence
├── Manufacturing
├── Logistics & Supply Chain
└── Waste & Environmental Services

Technology
├── Enterprise SaaS
├── Fintech
├── Cybersecurity
├── AI / Data Infrastructure
└── Semiconductors

Healthcare
├── Biotech / Pharma
├── Medical Devices
├── Healthcare Services
└── Digital Health

Consumer
├── Staples
├── Discretionary
└── Luxury

Financials
├── Asset Management
├── Insurance
└── Banking / Lending

Real Assets
├── Commodities
└── Timberland / Agriculture
```

### Dimension 3: Market Segment

```
├── Large Cap (> $10B)
├── Mid Cap ($2B – $10B)
├── Small Cap ($300M – $2B)
├── Micro Cap / Early Stage (< $300M)
├── Emerging Markets (EM)
└── Frontier Markets
```

### Dimension 4: Country / Region

```
Americas
├── US
├── Canada
└── Latin America (EM)

Europe
├── Western Europe (UK, France, Germany, Nordics, Benelux)
├── Southern Europe (Spain, Italy, Portugal)
└── CEE / Eastern Europe

Middle East & Africa
├── GCC (Saudi Arabia, UAE, Qatar)
└── Sub-Saharan Africa

Asia-Pacific
├── Japan / South Korea / Australia (Developed)
├── China
├── India
└── Southeast Asia (EM)
```

---

## 2. Signal Sources (Daily Ingestion)

### 2a. Public Equity Indices

The primary quantitative signal. These are your real-time proxies for private asset classes.

| Signal | Source | Maps To |
|---|---|---|
| S&P 500, Russell 2000 | yfinance | US PE/VC broadly |
| MSCI World / EM | yfinance | Global PE, GPs with broad mandates |
| S&P Energy Select Sector (XLE) | yfinance | Energy PE (all sub-sectors) |
| Invesco Solar ETF (TAN) | yfinance | Renewables — Solar |
| First Trust Wind Energy ETF (FAN) | yfinance | Renewables — Wind |
| Alerian MLP Index | yfinance | Midstream Energy |
| VNQ (Real Estate REIT ETF) | yfinance | Real Estate broadly |
| PHLX Semiconductor Index (SOX) | yfinance | Technology — Semiconductors |
| MSCI Emerging Markets | yfinance | EM-focused funds |
| Bloomberg Global Aggregate Bond | FRED | Credit / Fixed Income |
| Cambridge Associates PE Index | Quarterly only — lagged benchmark |

**Data already in stack:** yfinance is live. FRED is live. These cover 80% of needed signals.

### 2b. Commodity Prices

Commodities have direct pass-through to infrastructure, energy, and real asset valuations.

| Signal | Source | Maps To |
|---|---|---|
| WTI / Brent Crude | yfinance (CL=F, BZ=F) | Upstream, Midstream, Downstream |
| Natural Gas (Henry Hub) | FRED (DHHNGSP) | Midstream, LNG, Power |
| Gold | yfinance (GC=F) | Portfolio hedge / store of value |
| Copper | yfinance (HG=F) | Infrastructure, EV, Renewables |
| Lithium (BATT ETF proxy) | yfinance | Battery tech, EV supply chain |
| Agricultural commodities | FRED | Agri / Timberland funds |

### 2c. Macro / Policy Signals

These are slower-moving but directionally powerful. Run via LLM synthesis daily.

| Signal | Source | Interpretation |
|---|---|---|
| Fed Funds Rate | FRED (FEDFUNDS) | Discount rate → private market valuations |
| 10Y Treasury Yield | FRED (DGS10) | Risk-free rate, credit spreads |
| Credit Spreads (IG / HY) | FRED (BAMLC0A0CM, BAMLH0A0HYM2) | Private credit stress signal |
| USD Index (DXY) | yfinance | EM and cross-border fund performance |
| VIX | yfinance (^VIX) | Market-wide risk regime |
| Policy scanner | LLM agent (news API) | Regulatory changes, tax policy, tariffs |

### 2d. Analyst Sentiment

Qualitative signal — LLM processed, not price data.

**Sources:** Financial Times headlines, Bloomberg terminal excerpts (if user provides),
earnings call transcripts (public companies as proxies), SEC filings sentiment.

**Processing:** A dedicated Sentiment Agent runs each morning, ingesting the past 24h of
relevant news for each sector in the portfolio. Output is a directional score:
`{ sector, sentiment: "positive" | "neutral" | "cautious" | "negative", trigger_phrases: [...] }`

Sentiment is a *modifier*, not a primary signal. It adjusts factor scores ± 10%.

---

## 3. Factor Scoring Engine

### Daily Score Computation

Each factor gets a **Risk Score** (0–100, higher = more risk) and a **Direction** 
(improving / stable / deteriorating). These update every trading day.

```python
class FactorScore(BaseModel):
    factor_key: str          # e.g. "sector:energy:renewables:solar"
    score: float             # 0–100
    direction: str           # "improving" | "stable" | "deteriorating"
    z_score: float           # deviation from 90-day rolling mean
    primary_driver: str      # which signal drove today's score
    as_of_date: date
    confidence: float        # 0–1, lower when proxy is thin
```

### Score Formula

For each factor, aggregate its mapped signals using a weighted combination:

```
factor_score = (
    0.50 × equity_proxy_score     # primary quantitative signal
  + 0.25 × macro_environment_score  # rates, credit spreads, VIX
  + 0.15 × commodity_score          # if relevant (energy, real assets)
  + 0.10 × sentiment_score          # LLM-processed modifier
)
```

**Equity proxy score** is derived from the index's rolling z-score vs. 90-day mean:
- z < -2: score → 80–100 (elevated risk)
- z -2 to -0.5: score → 60–80
- z -0.5 to +0.5: score → 40–60 (neutral)
- z +0.5 to +2: score → 20–40
- z > +2: score → 0–20 (low risk, market pricing in good news)

**Score inheritance:** Parent factors inherit a weighted average of children.
`sector:energy` score = weighted average of upstream + midstream + downstream + renewables
(weighted by portfolio AUM exposure in each subsector, not equally weighted).

---

## 4. Asset-to-Factor Mapping

This is the bridge between the extraction pipeline and the risk overlay.

### How Tags Are Assigned

Tags come from three sources, in priority order:

1. **Extracted from documents** (Extraction Pipeline → Risk Officer Agent)
   - "Top 5 Holdings" tables give direct company names → classify via LLM
   - "Sector Allocation" tables give explicit weights
   - GP narrative descriptions of strategy ("we focus on US renewable energy assets")

2. **Inferred from fund metadata** (fund type + vintage + manager mandate)
   - A "2021 Sequoia Growth Fund" → VC → US → Technology (inferred from known manager)
   - User can override at any time

3. **Manual tagging** (fallback via HITL / table editor)
   - When extraction confidence < 0.7 on sector tags, route to analyst for manual entry

### The Factor Map Schema

```python
class AssetFactorMap(BaseModel):
    holding_id: str
    asset_class: str
    sector: str
    subsector: Optional[str]
    market_segment: str
    country: str
    region: str
    
    # Exposure weights (sum to 1.0 — the "look-through")
    factor_exposures: list[FactorExposure]

class FactorExposure(BaseModel):
    factor_key: str          # matches FactorScore.factor_key
    weight: float            # 0.0–1.0, portion of asset exposed to this factor
    source: str              # "extracted" | "inferred" | "manual"
    confidence: float
```

**Example — a PE fund holding a US solar developer:**
```json
{
  "holding_id": "hold_abc123",
  "asset_class": "private_equity",
  "sector": "energy",
  "subsector": "renewables:solar",
  "market_segment": "mid_cap",
  "country": "US",
  "factor_exposures": [
    {"factor_key": "sector:energy:renewables:solar", "weight": 0.70},
    {"factor_key": "sector:energy:renewables", "weight": 0.20},
    {"factor_key": "macro:rates:10y_treasury", "weight": 0.10}
  ]
}
```

The 10Y treasury exposure is explicit because solar project IRRs are highly rate-sensitive
(long-duration cash flows, financed with debt).

---

## 5. Risk Signal Propagation

### From Asset → Fund → Portfolio

```python
def compute_portfolio_risk_signal(portfolio_id: str, date: date) -> PortfolioRisk:
    holdings = get_holdings(portfolio_id)
    total_aum = sum(h.current_value for h in holdings)
    
    portfolio_factor_scores = defaultdict(float)
    
    for holding in holdings:
        weight = holding.current_value / total_aum
        factor_map = get_factor_map(holding.id)
        
        for exposure in factor_map.factor_exposures:
            factor_score = get_factor_score(exposure.factor_key, date)
            # Each holding contributes its factor score × its AUM weight × its factor exposure weight
            portfolio_factor_scores[exposure.factor_key] += (
                weight × exposure.weight × factor_score.score
            )
    
    return PortfolioRisk(
        date=date,
        composite_score=weighted_average(portfolio_factor_scores),
        factor_breakdown=portfolio_factor_scores,
        top_risk_contributors=sorted(portfolio_factor_scores, reverse=True)[:5],
        aum_at_risk=compute_aum_at_risk(portfolio_factor_scores, total_aum),
    )
```

### AUM Triangulation

The "triangulation" view answers: *"Of my $500M AUM, how much is exposed to each risk factor, and what's the current risk score on that exposure?"*

| Factor | AUM Exposed | % of Portfolio | Current Risk Score | Direction |
|---|---|---|---|---|
| US Large Cap Equity | $145M | 29% | 42 (neutral) | stable |
| Energy — Renewables | $82M | 16.4% | 71 (elevated) | deteriorating |
| Energy — Midstream | $34M | 6.8% | 55 (moderate) | stable |
| Real Estate — Commercial | $61M | 12.2% | 68 (elevated) | deteriorating |
| EM — India | $28M | 5.6% | 49 (moderate) | improving |
| Private Credit — US | $47M | 9.4% | 61 (elevated) | stable |
| Cash / Equivalents | $38M | 7.6% | 10 (low) | stable |

This table updates every trading day. It becomes the spine of the Monday Morning Brief.

---

## 6. VaR Integration (The Side Question — Answered in Full)

This is the hardest part and deserves careful treatment. The core challenge:
**private assets don't have daily price series.** You cannot run standard VaR on a
quarterly NAV. The macro overlay is the solution.

### Two Separate Problems

**Problem A:** Public holdings — standard VaR, solved.  
**Problem B:** Private holdings — factor-proxy VaR, the new approach.

---

### Public Holdings VaR (Parametric / Historical)

Nothing novel here, but do it right:

```python
# Historical VaR (preferred — captures fat tails)
def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    return returns.quantile(1 - confidence)

# For portfolio VaR (accounts for correlations):
# 1. Get daily returns for each public holding
# 2. Build correlation matrix
# 3. Use portfolio weights to compute portfolio variance
# σ²_portfolio = wᵀΣw
# VaR = -μ + z × σ (parametric) or empirical percentile (historical)
```

**Enhancement with factor overlay:** Instead of just using price history, decompose each
public holding's returns into factor returns (Fama-French style). This gives you:
- A more stable covariance matrix (less noise)
- Factor attribution for "what drove VaR today"
- Consistent methodology with private asset VaR

---

### Private Holdings VaR: Three Approaches

#### Approach 1: Public Proxy Basket (Recommended for MVP)

**Concept:** Every private asset has a public market analogue. Find it, track it.

```
Private Asset: US Midstream PE Fund (Vintage 2022)
Proxy Basket:
  - 60% Alerian MLP Index (midstream pure-play)
  - 25% S&P Energy Select Sector (broad energy)
  - 15% 10Y Treasury Yield (financing costs, rate sensitivity)

Private VaR ≈ VaR(proxy basket) × illiquidity_scalar
```

**Illiquidity scalar:** Private assets have lower observed volatility than their public proxies
(due to smoothed quarterly reporting), but *higher true risk* (due to illiquidity, leverage,
concentration). Apply a scalar of 1.2–1.5× depending on fund type:

| Asset Class | Illiquidity Scalar | Rationale |
|---|---|---|
| PE Buyout | 1.3× | Leverage amplifies; smoothed NAVs understate |
| VC | 1.5× | Extreme skew, binary outcomes |
| Private Credit | 1.2× | Lower vol, but credit default risk |
| Infrastructure | 1.1× | Regulated cash flows, lower correlation |
| Real Estate | 1.3× | Illiquid; cap rate moves lag market |

**Pro:** Simple, uses existing yfinance stack, auditable, explainable to CIO.  
**Con:** Proxy correlation breaks down in stress scenarios.

---

#### Approach 2: Factor Sensitivity Model (Phase 2)

**Concept:** Estimate each private asset's beta to each macro risk factor. Compute portfolio
VaR from the factor covariance matrix.

```
σ²_asset = βᵀ Σ_factors β + σ²_idiosyncratic

Where:
  β = vector of factor betas for this asset
  Σ_factors = factor covariance matrix (from daily factor score history)
  σ²_idiosyncratic = residual risk not explained by factors (estimated as % of proxy VaR)
```

**How to estimate β for private assets:**
- Use historical NAV updates (quarterly) regressed against factor returns over same period
- For new funds with no history, use peer-group betas from comparable funds
- Calibrate annually as more NAV data accumulates

**Pro:** Consistent methodology across public and private. Captures cross-factor correlations.  
**Con:** Requires 2+ years of NAV history to calibrate well. Overkill for MVP.

---

#### Approach 3: Scenario-Based Stress VaR (Run Alongside Both)

**Concept:** Instead of a statistical VaR number, simulate what happens to portfolio NAV
under defined historical and hypothetical scenarios.

| Scenario | Trigger Factors | Private Market Impact |
|---|---|---|
| 2008 GFC | Credit spreads +500bps, Equity −50%, Real Estate −40% | PE NAV −35%, RE −30%, Credit write-downs |
| COVID Crash (2020) | Equity −35%, VIX → 80, Consumer −60% | VC −40%, Consumer PE −30%, Healthcare +10% |
| 2022 Rate Shock | 10Y yield +300bps, Tech −50%, VC −60% | VC NAV −50%, RE cap rate expansion, PE debt cost +40% |
| Renewables Policy Reversal | IRA repeal proxy, Solar ETF −40% | Renewables infra NAV −25% |
| Energy Price Collapse | WTI −60%, Gas −70% | Energy PE −45%, Midstream −25% |
| EM Contagion | MSCI EM −40%, EM FX −25% | EM-focused funds −35% |

**Output:** "Under the 2022 Rate Shock scenario, portfolio NAV would decline by an estimated
$47M (−9.4%). Primary impact: VC holdings (−$28M) and Real Estate (−$12M)."

**Pro:** Intuitive, directly actionable, no statistical assumptions needed.  
**Con:** Not a probability-weighted number. Doesn't replace VaR, but is a vital complement.

---

### Connecting the Overlay to VaR: The Full Picture

The macro overlay's daily factor scores feed into VaR in two ways:

**1. Dynamic proxy beta adjustment**

When a factor score spikes (e.g., Renewables risk score moves from 45 → 78), automatically
widen the proxy basket volatility estimate for all holdings tagged to that factor:

```python
def adjusted_proxy_volatility(base_vol: float, factor_score: float) -> float:
    # When factor score is elevated, increase volatility estimate
    if factor_score > 70:
        multiplier = 1.0 + (factor_score - 70) / 100  # up to 1.30× at score=100
    else:
        multiplier = 1.0
    return base_vol * multiplier
```

**2. Regime detection → VaR method switching**

| VIX Level | Credit Spread | Regime | VaR Method |
|---|---|---|---|
| < 18 | IG < 150bps | Normal | Historical VaR (90-day window) |
| 18–28 | IG 150–250bps | Stress | Historical VaR (30-day window, recent data weighted 2×) |
| > 28 | IG > 250bps | Crisis | Scenario VaR (GFC scenario, floor on proxy VaR) |

In a crisis regime, the system automatically switches private holdings to scenario-floor
VaR and flags this in the brief: *"Risk model operating in Crisis regime. Private market
VaR estimates based on GFC scenario floors."*

---

### Final VaR Output Schema

```python
class PortfolioVaR(BaseModel):
    date: date
    confidence_level: float          # 0.95 or 0.99
    horizon_days: int                # 1 or 10
    
    # Public holdings (precise)
    public_var: float
    public_var_method: str           # "historical_95d_window"
    
    # Private holdings (estimated)
    private_var: float
    private_var_method: str          # "proxy_basket_1.3x_illiquidity"
    private_var_confidence: float    # model confidence 0–1
    
    # Portfolio total
    total_var: float
    diversification_benefit: float   # public_var + private_var - total_var
    
    # Factor attribution
    top_var_contributors: list[VaRContributor]  # factor, $ VaR contribution, % of total
    
    # Regime
    risk_regime: str                 # "normal" | "stress" | "crisis"
    regime_trigger: Optional[str]    # what triggered regime change
    
    # Stress overlay
    stress_scenarios: dict[str, float]  # scenario_name → estimated portfolio impact $
```

---

## 7. Agent Design

### The Macro Overlay Agent

**Trigger:** Daily at market close (or on-demand)  
**Runtime:** ~90 seconds  
**Model:** claude-sonnet-4-6 for index scoring; claude-opus-4-6 for sentiment synthesis

```python
async def run_macro_overlay(date: date, portfolio_id: str):
    # 1. Fetch all market data
    signals = await asyncio.gather(
        fetch_equity_indices(date),
        fetch_commodity_prices(date),
        fetch_macro_indicators(date),      # FRED
        fetch_sentiment(date),             # LLM news agent
    )
    
    # 2. Score each factor
    factor_scores = await score_all_factors(signals)
    
    # 3. Detect regime change
    regime = detect_risk_regime(factor_scores)
    
    # 4. Propagate to portfolio
    portfolio_risk = propagate_risk_to_portfolio(portfolio_id, factor_scores)
    
    # 5. Compute VaR
    var_result = compute_var(portfolio_id, factor_scores, regime)
    
    # 6. Generate alerts
    alerts = detect_threshold_breaches(portfolio_risk, var_result)
    
    # 7. Commit to DB + trigger brief update if material
    await commit_daily_risk_snapshot(date, portfolio_risk, var_result, alerts)
    if alerts:
        await notify_analyst(alerts)
```

### The Sentiment Agent (sub-agent)

Runs within the overlay pipeline. Inputs: sector tags from current portfolio.
Outputs: sentiment scores per sector.

```
Prompt pattern:
"You are a financial news analyst. Based on the following headlines from the past 24 hours,
assess the sentiment for [SECTOR] investments. Focus on: regulatory changes, demand signals,
commodity impacts, and analyst upgrades/downgrades. Output: {sentiment, confidence, key_phrases}"
```

---

## 8. Alert Thresholds

| Condition | Alert Level | Action |
|---|---|---|
| Any factor score > 75 with > 10% AUM exposure | Amber | Inline alert on dashboard |
| Any factor score > 85 with > 5% AUM exposure | Red | Push notification + brief flag |
| Portfolio composite score moves > 10 points in 1 day | Amber | "Market conditions changed materially" |
| Risk regime switches (normal → stress, or stress → crisis) | Red | Immediate notification + VaR recompute |
| VaR exceeds user-configured limit | Red | Prominent briefing banner |
| Single factor > 50% of total portfolio VaR | Amber | Concentration alert |

---

## 9. Technical Stack

| Component | Choice | Notes |
|---|---|---|
| **Market data** | yfinance + FRED (existing) | Covers 90% of signals. Add Quandl or Refinitiv later if needed |
| **Factor score storage** | PostgreSQL (time-series table) | `factor_scores(factor_key, date, score, z_score, direction)` |
| **Overlay scheduler** | Celery beat (existing) | Daily trigger at 5pm ET (after market close) |
| **Sentiment agent** | Claude API + news scraping | Financial Times, Reuters, WSJ headlines via RSS or News API |
| **VaR computation** | Python (numpy, scipy) | No external library needed for proxy basket approach |
| **Proxy basket definitions** | Static config + DB table | `proxy_baskets(asset_class, sector, tickers, weights)` — editable by admin |
| **Factor taxonomy** | DB table + seed migration | Version-controlled; adding new factors is a migration |

---

## 10. Build Order

1. **Factor taxonomy schema + DB migration** — define the factor tree, store in DB
2. **Signal collection** — yfinance + FRED daily fetch, store raw signals
3. **Factor scoring engine** — z-score computation + weighted aggregation
4. **Proxy basket definitions** — map 6–8 key fund types to proxy baskets
5. **Asset-to-factor tagging** — integrate with extraction pipeline (Risk Officer Agent already extracts sector data)
6. **Risk propagation** — AUM triangulation table (the "factor exposure" view)
7. **Public VaR** — historical VaR using existing price data
8. **Private proxy VaR** — proxy basket × illiquidity scalar
9. **Regime detection** — VIX + credit spread → regime classifier
10. **Sentiment agent** — last, because it's additive not foundational
11. **Stress scenarios** — define 5 core scenarios, implement as config-driven shocks

**Don't start the sentiment agent until steps 1–7 are solid.** Sentiment is a 10%
modifier on scores that already need to be working. Sequence matters.

---

## What This Is Not

- Not a hedge fund risk system (no Greeks, no gamma, no real-time tick data)
- Not a replacement for a Bloomberg PORT subscription for public portfolios
- Not regulatory VaR (not calibrated for Basel III / Solvency II compliance)
- The private VaR numbers carry model risk — this must be disclosed clearly in the UI:
  *"Private market VaR is estimated using public proxy baskets. Actual losses may differ."*

The value is **directional accuracy and daily freshness** — not statistical precision.
A CIO who knows their Renewables exposure is "elevated risk, deteriorating" today, rather
than waiting 90 days for the GP's quarterly, has a material information advantage.
