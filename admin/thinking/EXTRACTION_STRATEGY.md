# Document Extraction & Classification Strategy

**Context:** ChiefRiskBot — AI-powered risk briefing platform for family office CIOs  
**Date:** April 2026  
**Scope:** The "Data Ingestion" layer — converting raw financial documents into structured portfolio data

---

## The Core Problem

A family office CIO's risk picture is only as good as the data feeding it. The friction isn't a lack of VaR calculators — it's that the inputs are locked inside:

- `GP Quarterly Report - Q4 2025.pdf` (attached to an email)
- A Dropbox folder shared by the GP
- An investor portal behind a login
- A K-1 mailed as a physical PDF scan

Fixing this is the moat. Every competitor either ignores it (assumes clean data) or solves it badly (simple OCR that turns tables into word soup).

---

## Document Priority: Start with Private Markets

**Why Private Markets first:**
- Higher operational pain — 20+ K-1s, 30+ capital call notices per quarter, all manual today
- No Bloomberg/Advent solving it — unlike public portfolios, there's no incumbent API
- Higher willingness to pay — CIOs will pay to eliminate this specific drudgery
- Smaller document universe — 5-6 document types cover 80% of the workflow

**Phase 1 document types (MVP):**
1. Capital Call Notices
2. NAV / Quarterly Fund Statements
3. Distribution Notices

**Phase 2 (after moat is proven):**
4. K-1 Tax Forms
5. Audited Financial Statements
6. Side Letter Amendments

---

## Architecture: The Agent Factory

A single prompt cannot reliably handle a 60-page financial statement. The solution is a pipeline of specialized agents — a "factory line" where each station does one job well.

### Overview

```
Input Inbox
    │
    ▼
[1. Librarian Agent]  ←── Classifies document type
    │
    ▼
[2. Layout Parser]    ←── Azure Document Intelligence / LLMWhisperer
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
[3a. Accountant Agent]    [3b. Risk Officer Agent]    [3c. Treasury Agent]
  (NAV, Commitments,         (Holdings, Sector,          (Due Dates,
   Distributions)             Concentration)             Wire Instructions)
    │                                  │
    └──────────────────────────────────┘
                      │
                      ▼
            [4. Reconciliation Agent]
                      │
             ┌────────┴────────┐
             ▼                 ▼
       Confidence ≥ 0.85    Confidence < 0.85
             │                 │
             ▼                 ▼
      Commit to DB        HITL Review Queue
                      │
                      ▼
            [5. Synthesis Agent]
                      │
                      ▼
            Monday Morning Risk Brief
```

---

## Agent Specifications

### 1. Librarian Agent (Triage & Classification)

**Role:** Monitor input inboxes and classify documents — nothing more.

**Input:** Raw file (PDF, XLSX, email attachment)  
**Output:** `{ doc_type, gp_name, fund_name, period, confidence }`

**Why it's separate:** Each document type needs different extraction logic. Routing wrong wastes tokens and produces garbage. The Librarian doesn't extract — it dispatches.

**Classification targets:**
- `CAPITAL_CALL` — triggers Treasury Agent priority
- `NAV_STATEMENT` — triggers Accountant + Risk fan-out
- `DISTRIBUTION_NOTICE` — triggers Treasury Agent
- `K1_TAX` — Phase 2
- `LEGAL_AMENDMENT` — flag for human, don't process
- `UNKNOWN` — always routes to HITL

**Model:** `claude-sonnet-4-6` (classification is cheap; save Opus for reconciliation)

---

### 2. Layout-Aware Parser

**Role:** Handle the "physics" of the document before any LLM sees it.

**The problem:** Financial statements are dense tables. A row's meaning depends on its column header, and a column header may be on a different page. Standard text extraction destroys this spatial context — turning structured data into "word soup."

**Solution:** Run the document through **Azure Document Intelligence** (or LLMWhisperer as fallback) first. This preserves:
- Table cell coordinates (row × column)
- Page headers and footers (critical for multi-page tables)
- Font weight (bold = total/subtotal rows)
- Reading order across columns

**Output:** Structured markdown with table semantics intact, passed to extraction agents.

**Note:** This is not an LLM step. It's a preprocessing step. Claude should never fight PDF layout physics.

---

### 3. Extraction Specialist Agents (Parallel Fan-Out)

These run in parallel after the parser completes. Each receives the same parsed document but extracts a different "vertical."

#### 3a. The Accountant Agent

**Extracts:** The financial numbers.

```python
class AccountingExtraction(BaseModel):
    nav_ending: float
    nav_beginning: float
    total_commitment: float
    funded_commitment: float
    unfunded_commitment: float
    distributions_ytd: float
    distributions_inception: float
    irr: Optional[float]
    moic: Optional[float]
    as_of_date: date
    currency: str
    confidence: float  # 0.0 – 1.0
```

**Confidence rules:** Flag < 0.85 if:
- Any value extrapolated vs. directly stated
- Sum of sub-items doesn't match stated total
- Currency ambiguous

#### 3b. The Risk Officer Agent

**Extracts:** Look-through exposure data from narrative text and summary tables.

```python
class RiskExtraction(BaseModel):
    top_holdings: list[Holding]  # name, weight, sector
    sector_exposures: dict[str, float]  # sector → % of NAV
    geography: dict[str, float]  # region → % of NAV
    leverage_ratio: Optional[float]
    liquidity_profile: Optional[str]  # "Quarterly redemption", "2028 lock-up", etc.
    red_flags: list[str]  # narrative mentions of losses, write-downs, key-man events
    confidence: float
```

**Important:** Sector weights must sum to ≤ 100%. If they don't, the agent self-corrects before returning. This is not delegated to the Reconciliation agent.

#### 3c. The Treasury Agent

**Extracts:** Dates and payment mechanics — the "action items."

```python
class TreasuryExtraction(BaseModel):
    call_amount: Optional[float]
    call_due_date: Optional[date]
    distribution_amount: Optional[float]
    distribution_date: Optional[date]
    wire_bank: Optional[str]
    wire_account: Optional[str]
    wire_routing: Optional[str]
    wire_reference: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    confidence: float
```

**Wire instruction handling:** Never auto-populate wire instructions into a payment system. Always surface to HITL for confirmation regardless of confidence score. Wire fraud is a real attack vector.

**Model for all three:** `claude-sonnet-4-6` in parallel. Switch to `claude-opus-4-6` if confidence repeatedly falls below threshold for a specific GP.

---

### 4. Reconciliation & Auditor Agent

**Role:** The most important agent. The one that makes the system trustworthy.

**Input:** Outputs from all three extraction agents + historical data from DB  
**Output:** `ReconciliationResult` with final confidence and error flags

**Checks performed:**

| Check | Logic |
|---|---|
| **Period continuity** | `Q4 NAV_beginning == Q3 NAV_ending` (cross-document) |
| **Internal arithmetic** | `funded + unfunded == total_commitment` |
| **Sector weight sanity** | Sum of sector weights ≤ 100% |
| **Distribution vs. NAV** | Distribution amount < NAV (sanity bound) |
| **Wire instruction change detection** | Flag if wire details differ from last known instructions for this GP |
| **Duplicate detection** | Check if this document period already exists in DB |
| **Date sanity** | `as_of_date` within expected reporting window for this fund |

**Self-correction loop:**

```python
if not reconciled:
    # Send specific error back to the relevant extraction agent
    corrected = await re_extract(agent, document, error_context, attempt=2)
    if not corrected:
        flag_for_human_review(result, reason=error_context)
```

Maximum 2 re-extraction attempts before routing to HITL. No infinite loops.

**Model:** `claude-opus-4-6` — this is the agent that catches hallucinations. Don't skimp.

---

### 5. Synthesis & Briefing Agent

**Role:** Take structured JSON and produce human insight — not just data, but *change*.

**Key logic:** Compares new extraction against current portfolio state.

**Output examples:**
- "New Q4 data from Blackstone PE VI received. Your total Commercial Real Estate exposure has drifted from 12.0% to 14.5%, crossing your Amber threshold (14%)."
- "Capital call of $2.3M due in 14 days from Sequoia Growth Fund. Unfunded commitment balance will drop to $8.7M post-call."
- "KKR Infrastructure Fund IV — NAV declined 8.2% QoQ. Narrative cites write-down of 2 portfolio companies. Flagged for Monday Brief."

**Model:** `claude-opus-4-6` — this is the CIO-facing output. Quality matters.

---

## Technical Stack

### What to use

| Layer | Choice | Rationale |
|---|---|---|
| **LLM** | Anthropic Claude API | claude-opus-4-6 for Reconciliation + Synthesis, claude-sonnet-4-6 for Triage + Extraction |
| **Orchestration** | FastAPI + `asyncio.gather()` | Don't add LangGraph/CrewAI until you hit a stateful loop requirement you can't handle with plain Python |
| **Document parsing** | Azure Document Intelligence | Best layout preservation; falls back to LLMWhisperer for scanned PDFs |
| **Structured output** | Claude JSON mode + Pydantic schemas | Hard contract between agents; validation happens at each step |
| **Task queue** | Celery + Redis (or simple asyncio for MVP) | Background processing; retry logic for transient failures |
| **HITL UI** | Purpose-built review screen in frontend | PDF viewer + extracted fields side-by-side; one-click approve/correct |
| **Storage** | PostgreSQL (existing) | Structured extraction results; no vector DB needed for Phase 1 |

### What to skip (for now)

- **LangGraph / CrewAI** — unnecessary complexity before extraction is working. Plain Python `asyncio` handles the fan-out.
- **Vector DB** — GP formatting patterns don't need embeddings. A lookup table keyed by `gp_name` works and is auditable.
- **Fine-tuning** — not needed. Prompt engineering with strong schemas and few-shot examples outperforms fine-tuning for structured extraction at this scale.

---

## Implementation Skeleton

```python
# backend/extraction/pipeline.py

import asyncio
from anthropic import AsyncAnthropic
from .parsers import azure_parse_document
from .agents import (
    classify_document,
    extract_accounting,
    extract_risk,
    extract_treasury,
    reconcile,
    synthesize,
)
from .models import ExtractionResult
from .hitl import queue_for_human_review
from .db import commit_extraction

client = AsyncAnthropic()

async def run_extraction_pipeline(
    document_bytes: bytes,
    filename: str,
    portfolio_id: str,
) -> ExtractionResult:

    # Step 1: Classify
    classification = await classify_document(client, document_bytes, filename)
    if classification.doc_type == "UNKNOWN":
        return queue_for_human_review(classification, reason="Unknown document type")

    # Step 2: Layout parse
    parsed = await azure_parse_document(document_bytes)

    # Step 3: Parallel extraction
    accounting, risk, treasury = await asyncio.gather(
        extract_accounting(client, parsed, classification),
        extract_risk(client, parsed, classification),
        extract_treasury(client, parsed, classification),
    )

    # Step 4: Reconcile
    historical = await get_historical_context(portfolio_id, classification)
    reconciliation = await reconcile(
        client, accounting, risk, treasury, historical
    )

    if reconciliation.confidence < 0.85:
        return queue_for_human_review(reconciliation, reason=reconciliation.errors)

    # Step 5: Commit + Synthesize
    await commit_extraction(portfolio_id, reconciliation)
    brief = await synthesize(client, reconciliation, portfolio_id)

    return ExtractionResult(reconciliation=reconciliation, brief=brief)
```

---

## The HITL Review Screen

This is not an afterthought — it's a core feature.

**Design:** Split-screen.
- Left: PDF viewer with the exact page and cell highlighted (from Azure Document Intelligence coordinates)
- Right: Extracted fields with confidence scores

**Interactions:**
- One-click approve (routes to DB commit)
- Inline field correction (user types correct value, that correction is logged and used to improve future prompts for that GP)
- Reject (document returns to inbox, user notified)

**Trust mechanism:** Every value in the final Risk Brief should be traceable to a source document page. A CIO should be able to click any number in the brief and see the original PDF cell it came from. This is your audit trail.

---

## Confidence Score Design

| Score | Meaning | Action |
|---|---|---|
| ≥ 0.92 | High confidence | Auto-commit, no review |
| 0.85 – 0.91 | Moderate confidence | Commit, flag in brief ("Reviewed automatically — verify if material") |
| 0.70 – 0.84 | Low confidence | HITL queue with specific fields highlighted |
| < 0.70 | Very low | HITL queue, document marked as "Requires review before inclusion in brief" |

Confidence is computed per-field, not per-document. A document can be 0.96 overall but have a single wire instruction field at 0.60 — that field goes to HITL while the rest commits.

---

## Competitive Moat

The value isn't reading PDFs — it's **standardization**.

50 GPs all report "Net Exposure" differently. Some call it "Funded Commitment," some "Net Asset Value," some "Capital Account Balance." Your system maps all of them to a single clean schema. Once you've done that normalization for 20 GPs, you have:

1. **A data asset** — a proprietary GP-formatting knowledge base
2. **A switching cost** — migrating away means re-normalizing everything
3. **A compounding advantage** — each new document refines the extraction prompts for that GP

This is the real product. The Risk Brief is the UI layer on top.

---

## Phase 1 Build Order

1. **Azure Document Intelligence integration** — get layout-aware parsing working on real sample documents
2. **Accountant Agent + schema** — extract NAV and commitments from 3 real GP statements
3. **Reconciliation Agent (period continuity check only)** — the most critical check first
4. **HITL review screen** — needed before any real data goes near a CIO
5. **Librarian Agent** — once you have 2-3 doc types working, add classification
6. **Treasury Agent** — capital call due dates and amounts
7. **Risk Officer Agent** — look-through exposure (requires more GP-specific tuning)
8. **Synthesis Agent** — once the data layer is clean

Don't build the Synthesis Agent until steps 1-4 are solid. A beautifully written brief built on hallucinated NAV numbers is worse than no brief at all.
