# Claude Agent Platform Spec

_Last updated: 2026-04-15_

## Goal

Define how ChiefRiskBot should move its agentic system onto Anthropic's Claude agent platform without breaking the current MVP architecture:

- Supabase remains the source of identity, DB, and storage.
- FastAPI remains the business-logic and authorization layer.
- Claude agents become reusable, versioned workers for document extraction, risk analysis, and narrative generation.

This spec is based on:

- the current codebase implementation in `backend/services/ingest/agents/`, `backend/services/risk.py`, `backend/services/briefings.py`, and `backend/services/overlay/sentiment_agent.py`
- Anthropic Managed Agents and Agent SDK docs reviewed on 2026-04-15

## What Exists Today

### Document pipeline

Current orchestration lives in `backend/services/ingest/pipeline.py` and fans out across:

- `librarian.py`
  - classifies document type and basic metadata
  - currently deterministic with optional Claude model naming only
- `accountant.py`
  - extracts rows into candidate holdings
  - deterministic normalization and confidence scoring
- `risk_officer.py`
  - derives sector/region exposure, red flags, and factor tags
  - deterministic
- `treasury.py`
  - extracts capital-call or distribution fields plus wire hints
  - deterministic
- `reconciliation.py`
  - reconciles outputs, assigns review flags, and optionally calls Claude
  - currently the only document-stage agent with a real Claude call

### Risk pipeline

Current orchestration lives in `backend/services/risk.py`.

- Five specialist analysts are defined in `AGENT_DEFINITIONS`:
  - concentration
  - liquidity
  - macro
  - fx
  - tail
- Each agent receives a structured payload built by `_build_agent_payload(...)`.
- Each agent is called through the Claude Messages API with a JSON-only prompt contract.
- Validation is lightweight and mostly manual:
  - JSON parse
  - field extraction
  - persistence into `risk_scores` / `risk_flags`

### Briefings

`backend/services/briefings.py` synthesizes outputs into a committee memo. It is agentic in behavior, but not yet modeled as a first-class reusable agent definition.

### Overlay / sentiment

`backend/services/overlay/sentiment_agent.py` is currently deterministic scoring logic. It should remain local for now.

## Current Schema Gaps

The agentic system is functional, but not yet platform-ready.

### Gap 1: agent outputs are mostly untyped dicts

The outer API responses are typed in `backend/schemas/analytics.py` and `backend/schemas/content.py`, but the inner agent contracts are mostly informal dictionaries.

Examples:

- document classification output
- accountant extraction output
- treasury extraction output
- reconciliation output
- raw risk-agent result JSON

### Gap 2: there is no shared agent registry

Agent definitions are spread across:

- deterministic Python functions in `backend/services/ingest/agents/`
- inline dictionaries in `backend/services/risk.py`
- briefing prompt logic in `backend/services/briefings.py`

There is no single registry containing:

- stable agent ID
- current version
- model
- schema version
- timeout
- tool policy
- persistence target

### Gap 3: tool boundaries are implicit

Today the app passes large structured payloads directly into prompts. That works, but it does not map cleanly onto the Claude platform's reusable-agent model. Platform agents need explicit capabilities and tool boundaries.

### Gap 4: observability is app-local, not agent-native

The app persists risk scores and document review artifacts, but it does not yet persist:

- agent version used
- session / event correlation ID
- tool-call trace
- token usage per reusable platform agent

## Recommendation

### Core decision

Adopt **Claude Managed Agents** as the target platform abstraction for reusable production agents.

Use them for:

- reusable versioned agent definitions
- session-level observability
- controlled multi-agent composition
- MCP-based access to internal application tools

Do **not** move everything into the platform.

Keep these parts local in FastAPI:

- Supabase auth and workspace authorization
- database writes
- storage writes
- layout parsing
- VaR and liquidity math
- deterministic normalization
- final validation against app-owned schemas

In practical terms:

- FastAPI remains the orchestrator of record.
- Managed Agents become specialized reasoning workers called by FastAPI.
- Internal app actions are exposed to agents through a private MCP layer, not through unrestricted shell/browser access.

## Target Runtime Model

### 1. Reusable agent definitions

Per Anthropic's Managed Agents model, an agent is a reusable, versioned configuration containing:

- `name`
- `model`
- `system`
- `tools`
- optional `mcp_servers`
- optional `skills`
- optional `callable_agents`
- `description`
- `metadata`

ChiefRiskBot should create and version these agent definitions once, then reference them by ID from FastAPI when starting sessions.

### 2. Session-per-run execution

FastAPI should create a fresh Claude session for each bounded unit of work:

- one document parse / reconcile run
- one risk run
- one briefing generation run

FastAPI should:

1. create or reference the agent definition
2. create a session with the chosen `agent` and `environment_id`
3. stream events
4. satisfy tool calls through MCP or custom tool handlers
5. validate final output locally
6. persist only validated results into Postgres

### 3. Private MCP boundary

The right long-term tool boundary is an internal MCP service for ChiefRiskBot domain actions.

Examples:

- `get_workspace_snapshot`
- `get_document_layout`
- `get_document_extraction_context`
- `get_macro_context`
- `list_recent_briefings`
- `persist_reconciliation_review`
- `persist_risk_scores`
- `persist_briefing_draft`

This keeps business rules in FastAPI while allowing Claude agents to access only sanctioned operations.

## Agent Catalog

### Document family

#### `crb-document-librarian`

- Purpose: classify uploaded files and identify period / GP / fund metadata
- Model: `claude-sonnet-4-6`
- Input: parsed layout metadata, filename, sampled header rows
- Output schema: `DocumentClassificationV1`
- Tools: read-only MCP tools only
- Notes: may remain deterministic in MVP; useful first migration target only if classification quality becomes a bottleneck

#### `crb-document-accountant`

- Purpose: extract candidate holdings and basic financial fields
- Model: `claude-sonnet-4-6`
- Input: normalized layout blocks, row refs, doc classification
- Output schema: `AccountingExtractionV1`
- Tools: no broad tools; read-only layout/context MCP only
- Notes: all extracted positions remain provisional until reconciliation plus HITL

#### `crb-document-risk-officer`

- Purpose: extract sector / geography / red-flag context from private-market documents
- Model: `claude-sonnet-4-6`
- Input: classification + accounting output + parsed layout
- Output schema: `RiskExtractionV1`
- Tools: read-only MCP only

#### `crb-document-treasury`

- Purpose: extract capital call / distribution timing and wire-related fields
- Model: `claude-sonnet-4-6`
- Input: parsed layout + classification
- Output schema: `TreasuryExtractionV1`
- Tools: read-only MCP only
- Requirement: wire fields remain `human_review_required = true`

#### `crb-document-reconciliation`

- Purpose: merge specialist outputs, assign confidence, and create review flags
- Model: `claude-opus-4-6`
- Input: outputs from the four document specialists
- Output schema: `ReconciliationResultV1`
- Tools: read-only context MCP plus optional `persist_reconciliation_review` write tool gated by FastAPI
- Requirement: may not silently remove required review flags or downgrade treasury HITL

### Risk family

#### `crb-risk-concentration`
#### `crb-risk-liquidity`
#### `crb-risk-macro`
#### `crb-risk-fx`
#### `crb-risk-tail`

- Purpose: score one risk dimension each for the current portfolio snapshot
- Model: default `claude-sonnet-4-6`
- Input: structured portfolio summary payload only
- Output schema: `RiskAgentOutputV1`
- Tools: no general-purpose tools required for MVP
- Notes:
  - these are already structured enough to migrate cleanly
  - keep payload building local in FastAPI

### Content family

#### `crb-briefing-composer`

- Purpose: synthesize committee-ready narrative from validated risk/document/liquidity outputs
- Model: `claude-opus-4-6`
- Input: risk scores, flags, liquidity summary, approved document findings, settings
- Output schema: `BriefingDraftV1`
- Tools: read-only MCP for reference material; write/publish stays in FastAPI

## Required App-Owned Schemas

Before broader migration, define explicit Pydantic models for every agent result.

### New schema modules to add

- `backend/schemas/agents_documents.py`
- `backend/schemas/agents_risk.py`
- `backend/schemas/agents_briefings.py`

### Minimum schema set

- `DocumentClassificationV1`
- `AccountingPositionV1`
- `AccountingExtractionV1`
- `RiskExtractionV1`
- `TreasuryExtractionV1`
- `ReconciliationFieldReviewV1`
- `ReconciliationResultV1`
- `RiskFlagV1`
- `RiskAgentOutputV1`
- `BriefingDraftV1`

### Validation rule

No agent output should be written to DB unless:

1. the agent session completes successfully
2. the output validates against the current local Pydantic schema
3. the workspace/user authorization still passes in FastAPI

## Agent Creation Standard

Each Claude-managed agent should be created with:

- stable `name`
- clear `description`
- explicit `metadata`
  - `agent_family`
  - `schema_version`
  - `prompt_version`
  - `owner_service`
- least-privilege `tools`
- private `mcp_servers` only where required

### Example creation payload

```json
{
  "name": "CRB Reconciliation Agent",
  "model": "claude-opus-4-6",
  "description": "Reconciles document extraction outputs and returns review-safe JSON for ChiefRiskBot.",
  "system": "You are the reconciliation agent for ChiefRiskBot. Preserve review flags, never invent holdings, and return JSON only.",
  "mcp_servers": [
    {
      "type": "url",
      "name": "crb_api",
      "url": "https://api.chiefriskbot.com/mcp"
    }
  ],
  "tools": [
    {
      "type": "mcp_toolset",
      "mcp_server_name": "crb_api"
    }
  ],
  "metadata": {
    "agent_family": "documents",
    "schema_version": "reconciliation_v1",
    "prompt_version": "2026-04-15",
    "owner_service": "backend.services.ingest"
  }
}
```

## Tool and Permission Policy

### MVP default

Use least privilege by default:

- no open-ended shell
- no open web browsing
- no unrestricted filesystem tools
- internal MCP only

### Why

ChiefRiskBot is a financial workflow product. The important capability is not broad autonomy; it is controlled access to:

- workspace data
- approved documents
- risk summaries
- persistence endpoints

### Policy matrix

- document agents: read-only MCP
- risk agents: no tools or read-only MCP only
- briefing composer: read-only MCP
- publish / approve actions: never direct from agent without FastAPI re-validation

## Multi-Agent Composition

Use multi-agent composition only where the task is naturally decomposable.

### Good fits

- five parallel risk analysts
- document specialists feeding reconciliation

### Not a good fit for MVP

- turning every screen interaction into an agent
- moving deterministic calculations into Claude
- replacing CRUD or authorization with agent calls

### Proposed composition boundary

- FastAPI orchestrates fan-out/fan-in
- callable sub-agents are optional later, not required for MVP cutover
- if Anthropic callable agents are adopted later, use them only for the document family first

## Observability and Audit

For every managed-agent session, persist:

- `workspace_id`
- `agent_name`
- `agent_version`
- `schema_version`
- `session_id`
- `job_id`
- start/end timestamps
- token usage
- final status
- validation result
- any `session.error` or tool failure summary

Do not persist raw confidential prompt bodies unnecessarily. Persist references and summarized trace metadata where possible.

## Rollout Plan

### Phase 1

- Introduce typed agent schema modules
- create internal agent registry in the app
- keep Claude calls on current Messages API runtime

### Phase 2

- Stand up internal MCP service for read-only domain tools
- migrate `crb-risk-*` agents first

### Phase 3

- migrate `crb-document-reconciliation`
- add session/event observability

### Phase 4

- migrate briefing composition
- evaluate whether document specialists also move to Managed Agents or remain app-local

## Explicit Non-Goals

- No replacement of Supabase auth with Claude sessions
- No direct DB writes from the agent runtime
- No general-purpose autonomous browsing inside the production financial workflow
- No second parallel "demo-only" agent runtime

## Implementation Recommendation for MVP

If only one agent family is migrated first, migrate the **risk analysts** first.

Reason:

- their inputs are already well-structured
- they have the clearest existing role definitions
- they require the fewest tools
- they benefit most from reusable versioning and observability

Document specialists can follow once typed schemas and the MCP boundary are in place.
