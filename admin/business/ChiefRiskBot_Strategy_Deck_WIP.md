# ChiefRiskBot — Strategy Deck
*WIP draft · April 2026*

---

## 1 · The Problem

Risk management is broken for the companies that need it most.

Large institutions have Bloomberg terminals, quant teams, and dedicated risk officers. Everyone else — the fund with $200M AUM, the family office managing three generations of wealth, the Series C company with $80M in revenue — manages risk reactively. In spreadsheets. After the fact.

**Three failure modes, same root cause:**

| Failure | What it looks like |
|---|---|
| Setup cost | Building a dashboard requires connecting data sources, defining frameworks, writing formulas. Most never do it. |
| Maintenance cost | Even when a dashboard exists, it degrades. APIs change. Portfolios shift. New risks emerge. Keeping it current is a part-time job nobody has. |
| Interpretation cost | Raw numbers without context are noise. A VaR figure means nothing without knowing what's driving it. |

> The tools that could prevent this either cost too much, require too much expertise, or produce static snapshots that go stale the moment they're generated.

---

## 2 · The Market Moment

Three conditions are converging:

**Demand is unmet and documented.** BNY's 2025 survey: 83% of family offices name AI as a top-5 investment theme — but only 33% use AI internally for operations or analytics. 75% report gaps specifically in private-market analytics.

**The competitive landscape is fragmented.** Geopolitical risk, supply chain risk, credit risk, and portfolio VaR are being addressed by separate point solutions with no integration layer. No single product connects them to a fund's or company's actual positions with an agent that learns.

**Agentic AI is mature enough to build on.** The LLM tool-use, retrieval, and orchestration primitives needed to build a calibrating analyst layer exist today. This product couldn't have been built reliably 18 months ago.

---

## 3 · The Opportunity

**Primary segment: Funds & Family Offices ($50M–$2B AUM)**
- No dedicated risk team
- Multi-custodian, multi-asset portfolios with no consolidated view
- LP and board pressure for formalised risk reporting
- Willingness to pay: $1,000–$3,000/month

**Secondary segment (Phase 2): Startups & Scale-ups (Series B–D)**
- CFO owns risk by default; no structured framework
- Exposure to supply chain, customer credit, FX, runway
- Trigger events: pre-IPO audit, board risk committee, supplier failure
- Willingness to pay: $500–$1,500/month

---

## 4 · The Product

> Connect your data sources once. An agent builds your risk dashboard, keeps it current, and explains what's changing — without a quant team.

**ChiefRiskBot** is an agentic B2B SaaS platform with two operating layers:

**Layer 1 — Infrastructure Agents** (always on)
Monitor data sources → run calculations → detect threshold breaches → generate narratives → dispatch alerts and reports

**Layer 2 — Analyst Agents** (daily cycle)
A bench of specialized agents — by asset class and by geography — that synthesize market data, news signals, and third-party ratings (S&P, Fitch, Moody's) into structured daily ratings with plain-language rationale. They function like a research team that never sleeps.

```
[ Data Connectors ]
        ↓
[ Normalization & Storage ]
        ↓
[ Analyst Agent Layer ]  ←  S&P / Fitch / GDELT / ACLED / market data
        ↓
[ Infrastructure Agent Layer ]  ←  calculations, narratives, alerts
        ↓
[ Dashboard + Q&A + Reports ]
```

---

## 5 · The Analyst Agent Layer

Each analyst agent is specialized by **asset class** or **geography**.

**Asset class analysts:** Public Equities · Fixed Income & Credit · Private Markets · FX & Macro · Commodities

**Geography analysts:** North America · Western Europe · EM Asia · MENA · EM LATAM

**Daily output per analyst:**
- Risk score 1–5
- Confidence: Low / Medium / High
- Outlook: Improving / Stable / Deteriorating
- Top 3 drivers
- Plain-language rationale (3–5 sentences)
- Delta from prior day

**Ratings are global** (computed once, shared across tenants). **Application is portfolio-specific** (holdings mapped to relevant analysts, weighted by exposure size).

When analysts diverge — e.g. EM Asia Analyst rates Taiwan 4/5 on geopolitical risk; Fixed Income Analyst rates Taiwan government bonds 2/5 on credit fundamentals — the divergence is surfaced explicitly. Neither view is suppressed. The narrative synthesizes: *"Elevated geopolitical risk alongside strong credit fundamentals suggests asymmetric tail risk, not near-term default probability."*

---

## 6 · The Calibration Engine — The Real Moat

The calibration engine is what makes the platform compound rather than stay static.

**Loop 1: External Calibration (live)**

Every analyst rating is continuously compared against external signals as they arrive — sovereign rating changes, VIX regime shifts, CDS spread movements, ACLED conflict event materialization.

Outcomes are classified: **early detection** (agent saw it before consensus), **contemporaneous**, **miss**, or **false positive**. Each outcome is recorded. Pattern of misses and false positives drives signal weight adjustment and confidence recalibration.

Key principle: most of these signals are already in the platform's data layer. No additional data spend required.

**Loop 2: Internal Calibration (T+7, T+30, T+90)**

Every rating is scheduled for retrospective review. The calibration agent asks: what did we say, what happened, were the stated drivers the ones that mattered?

Failures trigger structured post-mortems. Learning is incorporated through:
1. **Retrieval-augmented memory** — calibration records indexed and retrieved before each new rating run. Agents reference their own track record.
2. **Signal weight adjustment** — structured, auditable parameter updates traceable to specific calibration events.
3. **Confidence recalibration** — Brier scores computed per analyst per quarter.

**Why this is the moat:**

Every week that passes makes the analyst agents more accurate. Longer-tenured customers benefit from more calibrated agents. This creates compounding switching costs that have nothing to do with data lock-in. The agents genuinely get better the longer you're on the platform.

**Customer-facing:** "Analyst Track Record" UI shows rating accuracy over 12 months, notable early detections, and calibration grade (A/B/C). A fund CIO who sees that the EM Asia Analyst called 7 of the last 9 major geopolitical moves before the rating agencies did will trust and act on its next alert.

---

## 7 · Private Markets Handling

A significant portion of family office portfolios sits in PE, VC, and real estate — with no API.

**Approach:**
1. User uploads quarterly reports, capital call statements, or valuation documents (PDF or CSV)
2. LLM extraction normalizes holdings into the position store
3. User reviews extracted allocations before they feed into risk calculations (required checkpoint — no silent errors in position data)
4. Private Markets Analyst applies daily ratings using sector comps, vintage analysis, and macro signals as proxies
5. Quarterly upload triggers re-rating of all affected holdings

---

## 8 · Data Architecture

**MVP data connectors (Tier 1):**
- Interactive Brokers API — position data
- Polygon.io — market data (~$200/month)
- FRED — macro data (free)
- GDELT — news/event signals (free)
- ACLED — conflict event data (commercial license required; significantly cheaper than GeoQuant)
- Manual CSV/PDF upload — private markets, OTC positions

**Geopolitical risk: build vs. buy**

GeoQuant is the premium provider but enterprise-only priced ($50K–$150K/year estimated — pricing not publicly disclosed). Not passable to SMB customers at our price point.

**Recommended path:** GDELT + ACLED + LLM synthesis for MVP and Pro tiers (research shows combined models achieve 87–94% AUC for conflict prediction). GeoQuant as optional bring-your-own or enterprise reseller arrangement.

**Third-party ratings (post-MVP):**
S&P Global, Moody's Analytics, Fitch Connect — all available via API, enterprise-priced. Ingested as one input signal to analyst agents, not as the final answer.

---

## 9 · Competitive Landscape

The space is being attacked from four angles. Nobody has assembled the integrated portfolio risk dashboard with an agentic analyst layer and calibration engine.

**Closest — but different problem:**

| Company | What they do | Why they're not a direct competitor |
|---|---|---|
| **Vantager** | AI due diligence for LPs and family offices; $100B AUM on platform | Pre-investment DD, not live portfolio risk monitoring. Risk: they expand into this space. |
| **RiskFront** | Agentic risk OS for financial crime / AML; $3.3M pre-seed Jan 2026 | Different buyer (compliance officer at bank), different use case |

**Geopolitical risk — becoming infrastructure, not a product:**

| Company | What they do | Status |
|---|---|---|
| **Seerist** | Geo risk intelligence; 44% new logo ARR growth; powers Bloomberg's company-level geo risk scores | Becoming a data layer embedded in Bloomberg Terminal — not a standalone dashboard for fund managers |
| **Mantis Analytics** | AI agents for geopolitical forecasting; launched Sept 2025 | Early stage, intelligence consumers not investment risk |
| **Recorded Future** | Established threat intelligence | Enterprise-priced, primarily cyber, not targeting fund managers |

**Supply chain risk — right approach, wrong segment:**

| Company | What they do | Status |
|---|---|---|
| **Resilinc** | Gartner Magic Quadrant Leader; just launched agentic AI platform for supplier risk | Manufacturing/supply chain buyer (COO/procurement), not CFO/CIO |
| **Lema AI** | Supply chain security, $24M Series A Feb 2026 (Team8 + Salesforce Ventures) | Cyber-adjacent, vendor risk angle |

**The gap:** Seerist's Bloomberg deal validates enterprise demand for automated geo risk scoring — but that scoring lives inside a $25K/year terminal with no connection to a fund's actual portfolio or a learning analyst layer. ChiefRiskBot is the integration and the intelligence.

---

## 10 · The B2B2C Distribution Angle

The product serves two distinct surfaces built on one engine.

**One engine, two surfaces:**

The analyst agents, calibration engine, and connector framework are shared infrastructure. What differs is the front-end and the information hierarchy it exposes.

| Surface | User | Interface | Language | Depth |
|---|---|---|---|---|
| **Professional dashboard** | Fund manager, family office CIO | Desktop-first | Technical, methodology-visible | Full — Greeks, correlation matrices, drill-down |
| **Consumer view** | HNW individual | Mobile-first | Plain language, actionable | Curated — surfaces only what's material, explains it in 2 sentences |

**Why direct B2C is the wrong route:**

Selling to HNW individuals direct requires consumer marketing, consumer support expectations, a very different trust-building cycle, and potential regulatory complications around investment advice. The acquisition cost is high and the sales motion is slow.

**The B2B2C route — private banks as distributors:**

Private bankers have a structural problem: their clients hold assets at multiple institutions, and the banker advises on only the fraction they can see. A consolidated risk view — white-labeled and delivered to clients through the private bank — solves the banker's job (retention, wallet consolidation, advisory differentiation) and the client's job (consolidated visibility) simultaneously.

The bank sells it. ChiefRiskBot gets per-client recurring revenue without owning the consumer relationship, the regulatory surface, or the support burden.

```
ChiefRiskBot (engine + professional dashboard)
        ↓
White-label API + consumer view
        ↓
Private Bank / MFO (distributes to their client base)
        ↓
HNW individual (receives mobile-friendly risk view)
```

**What makes this work:**

The document ingestion capability — LLM extraction from quarterly PE and private banking PDFs — is the unlock. Private banks struggle with exactly this: clients have capital at other institutions and nobody has a consolidated risk view. If ChiefRiskBot can reliably ingest a Julius Bär quarterly statement and a Carlyle LP report and produce an accurate consolidated position, that's the product. The risk view follows from the positions.

**Target distribution partners (priority order):**
1. Independent multi-family offices (Bessemer, Pathstone, Threshold) — smaller, faster to close, motivated to differentiate
2. Boutique private banks (Julius Bär, Pictet, Lombard Odier) — relationship-driven, open to technology partnerships
3. Large private banks (UBS Wealth, JPMorgan Private Bank) — longer sales cycle but much larger client base per deal

**Revenue model for the distribution layer:**

Per-client seat fee ($50–$150/client/month) paid by the institution, passed through or absorbed as a service cost. A mid-size private bank with 500 HNW clients = $25K–$75K MRR from a single partnership.

---

## 11 · Business Model

| Tier | Price | Target customer | Channel |
|---|---|---|---|
| **Starter** | $499/month | Early-stage funds, small family offices | Direct |
| **Pro** | $1,499/month | Mid-size funds, established family offices | Direct |
| **Enterprise** | $3,000+/month | Larger funds, multi-family offices | Direct |
| **Distribution** | $50–$150/client/month | Private banks, MFOs (per end-client) | B2B2C partnership |

**Revenue mechanics:**
- Expansion via adding modules and data connectors (NRR > 110% target)
- Distribution partnerships: high ACV, low marginal sales cost once signed
- Stickiness through calibration: the longer a customer stays, the more calibrated their analyst agents, the harder to leave

**Go-to-market sequence:**
1. Direct sales to funds/family offices $50M–$500M AUM — LP networks, FINTRX, family office associations
2. Independent MFO partnerships (white-label / distribution channel)
3. Boutique private bank partnerships (B2B2C, per-client revenue)
4. Bottom-up via startup CFOs (Phase 2, lower ACV, higher volume)
5. Large private bank distribution (Phase 3, long cycle, highest scale)

---

## 11 · MVP Scope

**Guiding principle:** Prove that an agent can build and maintain a useful risk dashboard with less effort than a human, for a paying customer who would not have had one otherwise.

**In scope:**
- Segment A only (Funds & Family Offices)
- 3 risk modules: Portfolio VaR · Concentration risk · Geopolitical exposure
- 3 MVP analyst agents: Geopolitical · Market Risk · Credit Risk
- 2 data connectors: IB API + Polygon.io (+ CSV upload fallback)
- Dashboard: summary card, VaR trend, concentration heatmap, geo map, narrative panel
- Alert agent (email) + daily digest
- Limited Q&A (5 pre-defined question types)
- Calibration engine v1: T+7 retrospective + external signal ingestion + retrieval-augmented memory

**Cut from MVP:**
Startup segment · CVaR / liquidity / counterparty modules · Slack · PDF report agent · Multi-user RBAC · Open-ended Q&A · White-label · Time machine

**Build sequence (16 weeks):**

```
Weeks 1–3   Foundation: infra, auth, IB connector, Polygon connector, CSV upload
Weeks 4–6   Calculation engine: VaR, concentration, rating store data model
Weeks 7–9   Infrastructure agents: monitor, calculate, narrative, alert
Weeks 8–10  MVP analyst agents: Geopolitical, Market Risk, Credit Risk (parallel)
Weeks 10–12 Dashboard + onboarding wizard + limited Q&A
Weeks 11–13 Calibration engine v1 (parallel): T+7 scheduler, external signal ingestion, RAG memory
Weeks 14–16 Alpha: 3–5 design partners, QA, narrative tuning, Analyst Track Record UI
```

**Definition of done:**
- Fund PM connects IB account → dashboard auto-generated → alert fires on threshold breach, without writing code or formulas
- Agent narrative accuracy rated ≥ 80% positive by design partners
- Time to first dashboard < 30 minutes
- Calibration engine has completed one full T+7 cycle across all 3 analyst agents
- ≥ 2 design partners willing to pay post-alpha

---

## 12 · Key Risks & Open Questions

**Technical:**
- Narrative accuracy: LLM grounded in tool use, not general knowledge. Strict output validation required.
- VaR precision: Calculation engine needs quant sign-off before customer-facing use.
- Calibration feedback loop quality: External signals need careful mapping to avoid spurious calibration events.

**Business:**
- Vantager expansion risk: They own the family office AI positioning for DD. If they expand into live risk monitoring, they have a head start on relationships.
- Buying cycle at funds: SOC 2 and data residency questions will come early. Build compliance posture into roadmap, not as an afterthought.
- Design partner identification: The MVP's definition of done requires paying design partners. This is the most important near-term action.

**Open:**
- Does the calibration track record surface (Analyst Track Record UI) become a public marketing asset? ("Our EM Asia Analyst has outperformed S&P by X days on average.") High upside but requires care around liability positioning.
- Regulatory scope: Form PF, AIFMD assistance would be a strong wedge for fund customers — significant expansion but worth scoping as a v2 module.
- Pricing for family offices with large private markets allocations: the manual upload + LLM extraction workflow has higher ops cost than a pure API-connected portfolio. May need a private markets add-on tier.

---

*Next actions: design partner outreach · IB API connector prototype · ACLED commercial license inquiry · narrative agent prompt engineering*
