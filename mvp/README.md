# ChiefRiskBot MVP

A weekly risk briefing generator for family office CIOs.

Upload a CSV of positions, get a structured briefing that the CIO can carry into their investment committee meeting. Not a dashboard. Not a recommendation engine. A briefing artifact that surfaces the conversations worth having, with the evidence to have them credibly.

This is the 48-hour prototype from the office-hours session. The goal is not to be complete. The goal is to sit down with one real family office operator, show them the briefing generated from their actual positions, and find out whether they would forward it to their investment committee.

---

## What's inside

```
mvp/
├── app/
│   ├── main.py              FastAPI app (one endpoint: POST /api/briefing)
│   ├── data.py              yfinance + FRED fetchers
│   ├── briefing.py          Claude prompt + API call
│   └── static/index.html    Single-page upload UI
├── sample_portfolio.csv     12-position family-office-shaped sample
├── requirements.txt
├── run.sh                   Boot script (creates venv on first run)
└── .env.example             Copy to .env and fill in ANTHROPIC_API_KEY
```

No database. No auth. No build step. One Python process, one HTML page.

---

## Run it

```bash
cp .env.example .env
# add your ANTHROPIC_API_KEY to .env

./run.sh
```

Then open http://127.0.0.1:8000 and upload `sample_portfolio.csv`.

First run installs deps into `.venv/` (takes ~30 seconds).

---

## What it does

1. Parses your CSV (required columns: `ticker,quantity,asset_class`).
2. Enriches each position with current price, 30-day annualized vol, 90-day return, sector via `yfinance`.
3. Pulls macro context from FRED (10Y yield, Fed Funds, CPI, unemployment, DXY) plus `^VIX`.
4. Computes deterministic portfolio math (total MV, concentrations, asset-class mix) in Python so Claude doesn't have to.
5. Sends everything to Claude in a single API call with a strict JSON schema.
6. Returns a briefing with:
   - A one-line headline
   - Portfolio snapshot
   - **Top 3 risks** (severity, evidence, reasoning, a question for the committee)
   - **Talking points** — sentences the CIO can say verbatim in a meeting
   - Data caveats

The output renders as a printable briefing. "Print / Save as PDF" and "Copy as text" buttons ship in v1.

---

## CSV format

```csv
ticker,quantity,asset_class,custodian,notes
SPY,2500,public_equity,Schwab,Core US equity sleeve
TLT,1500,fixed_income,Schwab,Long duration treasury
```

- **ticker** — any Yahoo Finance ticker (SPY, BRK-B, TSM, ^GSPC, etc)
- **quantity** — shares/units, float
- **asset_class** — free text (public_equity, fixed_income, commodity, real_estate, etc). Used for concentration math.
- **custodian** — optional, used to surface multi-custodian concentration
- **notes** — optional, free text fed to Claude for context

`sample_portfolio.csv` ships with 12 positions designed to trigger real concentration and macro observations.

---

## What's deliberately missing

Everything. This is the 48-hour version.

| Missing | Why |
|---|---|
| Auth | One user, local only. |
| Database | Flat requests, no history. |
| Live refresh | Briefings are generated on demand. |
| Alert thresholds | The product is a briefing, not a monitor. |
| Analyst agents | Phase 2. First prove the briefing format resonates. |
| Calibration engine | Needs months of data. Phase 3. |
| Multi-user / RBAC | Single operator. |
| Private markets ingestion | Phase 2. CSV is enough for day one. |
| PDF generation server-side | `window.print()` → save as PDF works. |

---

## The success criterion

Sit with one family office CIO or small fund manager. Show them the briefing generated from their actual positions. Watch what they do.

- **Forwards it or screenshots it →** product-market fit signal
- **Suggests specific improvements →** you have a design partner
- **Shrugs →** the template is wrong. Rebuild the template, not the stack.

---

## Next decisions (after first user session)

1. Does the briefing format resonate? Fix the template.
2. Which concentration + risk observations felt "obvious but useful" vs "wrong" vs "I already knew that"? That's your calibration signal.
3. What data would they wish the briefing had that it doesn't? That's your data connector roadmap.
4. Would they pay $500/month for this? $1,500? This conversation is the whole point.

---

*Built from the office-hours design doc: `~/.gstack/projects/garrytan-gstack/20260406-1510-design-riskpilot-office-hours.md`*
