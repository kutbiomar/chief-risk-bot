from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.analytics import MacroCache, RiskFlag, RiskScore, VarResult
from backend.models.auth import WorkspaceSetting
from backend.models.jobs import AsyncJob
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.jobs import AsyncJobService
from backend.services.portfolio import summarize_positions

logger = logging.getLogger(__name__)


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))

PROMPT_VERSION = "risk-v2"

AGENT_DEFINITIONS = [
    {
        "agent": "concentration",
        "dimension": "concentration",
        "label": "Concentration Risk Analyst",
        "focus": (
            "Analyze portfolio concentration risk. Focus on: single-name exposure (HHI, top-5 "
            "concentration), asset class concentration, geographic concentration. Score 1-10 where "
            "10 is extreme concentration risk. A well-diversified family office should score 3-5."
        ),
    },
    {
        "agent": "liquidity",
        "dimension": "liquidity",
        "label": "Liquidity Risk Analyst",
        "focus": (
            "Analyze portfolio liquidity risk. Focus on: T+1 liquidation capacity, proportion of "
            "illiquid assets (private equity, real estate, alternatives), time-to-liquidity mismatch "
            "vs likely cash needs. Score 1-10 where 10 is severe liquidity risk."
        ),
    },
    {
        "agent": "macro",
        "dimension": "macro",
        "label": "Macro & Geopolitical Risk Analyst",
        "focus": (
            "Analyze macro and geopolitical risk. Focus on: VIX level and trend, interest rate "
            "environment (10Y yield), dollar strength (DXY), inflation (CPI trend), geographic "
            "exposure to high-risk regions. Score 1-10 where 10 is extreme macro risk."
        ),
    },
    {
        "agent": "fx",
        "dimension": "fx",
        "label": "FX & Currency Risk Analyst",
        "focus": (
            "Analyze FX and currency risk. Focus on: non-USD allocation by currency, concentration "
            "in any single foreign currency, unhedged FX exposure relative to total AUM. "
            "Score 1-10 where 10 is severe unhedged FX risk."
        ),
    },
    {
        "agent": "tail",
        "dimension": "tail",
        "label": "Tail Risk Analyst",
        "focus": (
            "Analyze tail risk. Focus on: 1-day 95%/99% VaR as percentage of AUM, CVaR, worst "
            "historical scenario, model coverage (what fraction of AUM is modeled). "
            "Score 1-10 where 10 is extreme tail risk."
        ),
    },
]


def _severity_for_score(score: int) -> str:
    if score >= 8:
        return "priority"
    if score >= 5:
        return "elevated"
    return "watch"


def _build_agent_payload(
    definition: dict[str, str],
    summary: dict[str, Any],
    macro_payload: dict[str, Any],
    var_result: VarResult | None,
    positions: list[Position],
) -> dict[str, Any]:
    """Build a structured, injection-safe payload for each agent."""
    top_positions = sorted(positions, key=lambda p: float(p.market_value_usd or 0), reverse=True)[:10]
    position_summary = [
        {
            "ticker": p.ticker,
            "asset_class": p.asset_class,
            "geo_region": p.geo_region,
            "currency": p.position_currency,
            "market_value_usd": round(float(p.market_value_usd or 0), 0),
            "pct_of_aum": round(
                float(p.market_value_usd or 0) / max(float(summary["total_aum_usd"]), 1) * 100, 2
            ),
        }
        for p in top_positions
    ]

    currency_breakdown: dict[str, float] = {}
    for p in positions:
        ccy = p.position_currency or "USD"
        currency_breakdown[ccy] = currency_breakdown.get(ccy, 0.0) + float(p.market_value_usd or 0)

    asset_class_breakdown: dict[str, float] = {}
    for p in positions:
        ac = p.asset_class or "other"
        asset_class_breakdown[ac] = asset_class_breakdown.get(ac, 0.0) + float(p.market_value_usd or 0)

    geo_breakdown: dict[str, float] = {}
    for p in positions:
        geo = p.geo_region or "unknown"
        geo_breakdown[geo] = geo_breakdown.get(geo, 0.0) + float(p.market_value_usd or 0)

    var_section: dict[str, Any] = {}
    if var_result:
        var_section = {
            "var_1d_95_usd": round(var_result.var_1d_95, 0),
            "var_1d_95_pct_aum": round(
                var_result.var_1d_95 / max(float(summary["total_aum_usd"]), 1) * 100, 3
            ),
            "var_1d_99_usd": round(var_result.var_1d_99, 0),
            "cvar_1d_95_usd": round(var_result.cvar_1d_95, 0),
            "worst_scenario_date": str(var_result.worst_scenario_date),
            "worst_scenario_loss_usd": round(var_result.worst_scenario_loss, 0),
            "model_coverage_pct": round(var_result.model_coverage_pct, 1),
            "effective_lookback_days": var_result.effective_lookback_days,
        }

    return {
        "portfolio": {
            "total_aum_usd": round(float(summary["total_aum_usd"]), 0),
            "position_count": len(positions),
            "hhi_concentration": round(float(summary["hhi_concentration"]), 4),
            "top_five_concentration_pct": round(float(summary["top_five_concentration_pct"]), 2),
            "liquidity_score_pct": round(float(summary["liquidity_score_pct"]), 2),
            "top_positions": position_summary,
            "currency_breakdown": {k: round(v, 0) for k, v in currency_breakdown.items()},
            "asset_class_breakdown": {k: round(v, 0) for k, v in asset_class_breakdown.items()},
            "geo_breakdown": {k: round(v, 0) for k, v in geo_breakdown.items()},
        },
        "macro": macro_payload,
        "var": var_section,
        "analyst_role": definition["label"],
        "focus": definition["focus"],
    }


AGENT_SYSTEM_PROMPT = """You are {analyst_role} at a family office risk committee. You are rigorous, direct, and data-driven.

Your job is to analyze the provided portfolio data and produce a structured risk assessment.

IMPORTANT RULES:
- Base your analysis ONLY on the structured data provided. Do not invent figures.
- Respond with valid JSON only. No prose outside the JSON object.
- Score on a 1-10 scale where 10 is extreme risk.
- Evidence must be specific data points from the provided payload (e.g., "AAPL at 18.3% of AUM").
- Conversation prompt should be a single question a CIO could ask at a committee meeting.

Respond with this exact JSON structure:
{{
  "score": <integer 1-10>,
  "severity": "<watch|elevated|priority>",
  "headline": "<one-sentence risk headline>",
  "reasoning": "<2-3 sentence explanation referencing specific data>",
  "evidence": ["<data point 1>", "<data point 2>", "<data point 3>"],
  "conversation_prompt": "<one question for the CIO>",
  "risk_flags": [
    {{
      "rule": "<snake_case_rule_name>",
      "severity": "<watch|elevated|priority>",
      "ticker": "<ticker or null>",
      "value": <float>,
      "threshold": <float>,
      "description": "<one sentence>"
    }}
  ]
}}"""


async def _run_single_agent(
    definition: dict[str, str],
    payload: dict[str, Any],
    snapshot_id: str,
    workspace_id: str,
    job_id: str,
    model_name: str,
) -> dict[str, Any]:
    """Run a single risk agent via Claude. Returns a result dict."""
    settings = get_settings()
    agent = definition["agent"]
    start_ms = int(time.monotonic() * 1000)

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — using deterministic fallback for agent %s", agent)
        return _deterministic_agent_result(definition, payload)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        user_content = json.dumps(payload, indent=2, sort_keys=True)

        response = await asyncio.wait_for(
            client.messages.create(
                model=model_name,
                max_tokens=1500,
                system=AGENT_SYSTEM_PROMPT.format(analyst_role=definition["label"]),
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze the following portfolio data and produce your risk assessment:\n\n{user_content}",
                    }
                ],
            ),
            timeout=30.0,
        )

        latency_ms = int(time.monotonic() * 1000) - start_ms
        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        parsed = json.loads(raw_text)
        return {
            "status": "succeeded",
            "score": int(parsed.get("score", 5)),
            "severity": parsed.get("severity", "watch"),
            "headline": parsed.get("headline", ""),
            "reasoning": parsed.get("reasoning", ""),
            "evidence": parsed.get("evidence", []),
            "conversation_prompt": parsed.get("conversation_prompt", ""),
            "risk_flags": parsed.get("risk_flags", []),
            "model": model_name,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "latency_ms": latency_ms,
        }

    except asyncio.TimeoutError:
        logger.error("Agent %s timed out after 30s", agent)
        return {"status": "timeout", "error_message": "Agent timed out after 30s"}
    except json.JSONDecodeError as exc:
        logger.error("Agent %s returned invalid JSON: %s", agent, exc)
        return {"status": "schema_error", "error_message": f"Invalid JSON: {exc}"}
    except Exception as exc:
        logger.error("Agent %s failed: %s", agent, exc)
        # Retry once for transient errors
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            user_content = json.dumps(payload, indent=2, sort_keys=True)
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model_name,
                    max_tokens=1500,
                    system=AGENT_SYSTEM_PROMPT.format(analyst_role=definition["label"]),
                    messages=[
                        {
                            "role": "user",
                            "content": f"Analyze the following portfolio data and produce your risk assessment:\n\n{user_content}",
                        }
                    ],
                ),
                timeout=30.0,
            )
            latency_ms = int(time.monotonic() * 1000) - start_ms
            raw_text = response.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            parsed = json.loads(raw_text)
            return {
                "status": "succeeded",
                "score": int(parsed.get("score", 5)),
                "severity": parsed.get("severity", "watch"),
                "headline": parsed.get("headline", ""),
                "reasoning": parsed.get("reasoning", ""),
                "evidence": parsed.get("evidence", []),
                "conversation_prompt": parsed.get("conversation_prompt", ""),
                "risk_flags": parsed.get("risk_flags", []),
                "model": model_name,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": latency_ms,
            }
        except Exception as retry_exc:
            logger.error("Agent %s retry failed: %s", agent, retry_exc)
            return {"status": "failed", "error_message": str(retry_exc)}


def _deterministic_agent_result(definition: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """Fallback deterministic result when API key is absent."""
    agent = definition["agent"]
    portfolio = payload.get("portfolio", {})
    macro = payload.get("macro", {})
    var = payload.get("var", {})

    hhi = float(portfolio.get("hhi_concentration", 0))
    liquidity = float(portfolio.get("liquidity_score_pct", 100))
    vix = float(macro.get("vix", 15))

    if agent == "concentration":
        score = 9 if hhi > 0.25 else 6 if hhi > 0.15 else 3
    elif agent == "liquidity":
        score = 9 if liquidity < 50 else 5 if liquidity < 65 else 3
    elif agent == "macro":
        score = 6 if vix >= 20 else 3
    elif agent == "fx":
        non_usd = sum(v for k, v in portfolio.get("currency_breakdown", {}).items() if k != "USD")
        total = max(float(portfolio.get("total_aum_usd", 1)), 1)
        fx_pct = non_usd / total * 100
        score = 7 if fx_pct > 30 else 4 if fx_pct > 10 else 2
    else:  # tail
        var_pct = float(var.get("var_1d_95_pct_aum", 0))
        score = 7 if var_pct > 3 else 4 if var_pct > 1.5 else 3

    severity = _severity_for_score(score)
    return {
        "status": "succeeded",
        "score": score,
        "severity": severity,
        "headline": f"{definition['label']}: {severity} risk (score {score}/10)",
        "reasoning": f"Deterministic assessment from portfolio aggregates. API key not configured.",
        "evidence": [f"{agent} score computed from current snapshot"],
        "conversation_prompt": f"What should the committee discuss about {agent} risk?",
        "risk_flags": [],
        "model": "deterministic-demo-engine",
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 5,
    }


def _persist_agent_result(
    db: Session,
    definition: dict[str, str],
    result: dict[str, Any],
    snapshot_id: str,
    workspace_id: str,
    job_id: str,
) -> RiskScore:
    score = RiskScore(
        snapshot_id=snapshot_id,
        workspace_id=workspace_id,
        async_job_id=job_id,
        agent=definition["agent"],
        dimension=definition["dimension"],
        status=result.get("status", "failed"),
        score=result.get("score"),
        severity=result.get("severity"),
        headline=result.get("headline"),
        reasoning=result.get("reasoning"),
        evidence_json=json.dumps(result.get("evidence", []), sort_keys=True),
        conversation_prompt=result.get("conversation_prompt"),
        data_sources_json=json.dumps(["portfolio.summary", "macro_cache", "var_results"], sort_keys=True),
        model=result.get("model"),
        prompt_version=PROMPT_VERSION,
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
        latency_ms=result.get("latency_ms"),
        error_message=result.get("error_message"),
    )
    db.add(score)
    return score


def _make_flags_from_agents(
    db: Session,
    snapshot: PortfolioSnapshot,
    summary: dict[str, Any],
    positions: list[Position],
    agent_results: list[dict[str, Any]],
) -> list[RiskFlag]:
    db.execute(delete(RiskFlag).where(RiskFlag.snapshot_id == snapshot.id))
    flags: list[RiskFlag] = []

    # Flags from agent outputs
    for result in agent_results:
        for raw_flag in result.get("risk_flags", []):
            try:
                flag = RiskFlag(
                    snapshot_id=snapshot.id,
                    workspace_id=snapshot.workspace_id,
                    rule=str(raw_flag.get("rule", "unknown")),
                    severity=str(raw_flag.get("severity", "watch")),
                    ticker=raw_flag.get("ticker") or None,
                    value=float(raw_flag.get("value", 0)),
                    threshold=float(raw_flag.get("threshold", 0)),
                    description=str(raw_flag.get("description", "")),
                )
                db.add(flag)
                flags.append(flag)
            except Exception as exc:
                logger.warning("Failed to persist agent risk flag: %s", exc)

    # Hard-coded structural flags (always applied)
    top_position = max(positions, key=lambda p: float(p.market_value_usd or 0), default=None)
    if top_position and snapshot.total_aum_usd:
        pct = float(top_position.market_value_usd or 0) / float(snapshot.total_aum_usd) * 100.0
        if pct > 10.0:
            flag = RiskFlag(
                snapshot_id=snapshot.id,
                workspace_id=snapshot.workspace_id,
                rule="single_name_concentration",
                severity="elevated",
                ticker=top_position.ticker,
                value=round(pct, 2),
                threshold=10.0,
                description=f"{top_position.ticker} exceeds 10% of portfolio at {pct:.1f}%",
            )
            db.add(flag)
            flags.append(flag)

    if float(summary["liquidity_score_pct"]) < 50.0:
        flag = RiskFlag(
            snapshot_id=snapshot.id,
            workspace_id=snapshot.workspace_id,
            rule="illiquidity",
            severity="priority",
            ticker=None,
            value=float(summary["liquidity_score_pct"]),
            threshold=50.0,
            description="T+1 liquidity coverage is below 50%",
        )
        db.add(flag)
        flags.append(flag)

    db.flush()
    return flags


async def _run_agents_async(
    definitions: list[dict[str, str]],
    payloads: list[dict[str, Any]],
    snapshot_id: str,
    workspace_id: str,
    job_id: str,
    model_name: str,
) -> list[dict[str, Any]]:
    tasks = [
        _run_single_agent(defn, payload, snapshot_id, workspace_id, job_id, model_name)
        for defn, payload in zip(definitions, payloads)
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for i, r in enumerate(raw_results):
        if isinstance(r, Exception):
            logger.error("Agent %s raised exception: %s", definitions[i]["agent"], r)
            results.append({"status": "failed", "error_message": str(r)})
        else:
            results.append(r)
    return results


def run_risk_analysis(
    db: Session, snapshot: PortfolioSnapshot, created_by: str | None
) -> tuple[AsyncJob, list[RiskScore], list[RiskFlag]]:
    workspace_settings = db.get(WorkspaceSetting, snapshot.workspace_id)
    model_name = (
        workspace_settings.ai_model
        if workspace_settings is not None and workspace_settings.ai_model
        else "claude-sonnet-4-6"
    )
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    summary = summarize_positions(positions)
    macro = (
        db.query(MacroCache)
        .filter(MacroCache.workspace_id == snapshot.workspace_id)
        .order_by(MacroCache.fetched_at.desc())
        .first()
    )
    macro_payload = json.loads(macro.payload_json) if macro else {}
    var_result = db.scalar(
        select(VarResult)
        .where(VarResult.snapshot_id == snapshot.id)
        .order_by(VarResult.computed_at.desc())
    )

    job_service = AsyncJobService(db)
    job = job_service.create_job(
        workspace_id=snapshot.workspace_id,
        job_type="risk_run",
        created_by=created_by,
        resource_type="snapshot",
        resource_id=snapshot.id,
        request_payload={"snapshot_id": snapshot.id},
    )
    job_service.mark_running(job, started_children=len(AGENT_DEFINITIONS))

    db.execute(delete(RiskScore).where(RiskScore.snapshot_id == snapshot.id))

    payloads = [
        _build_agent_payload(defn, summary, macro_payload, var_result, list(positions))
        for defn in AGENT_DEFINITIONS
    ]

    if _is_test_runtime() or not get_settings().anthropic_api_key:
        agent_results = [
            _deterministic_agent_result(defn, payload)
            for defn, payload in zip(AGENT_DEFINITIONS, payloads)
        ]
    else:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            agent_results = asyncio.run(
                _run_agents_async(
                    AGENT_DEFINITIONS,
                    payloads,
                    snapshot.id,
                    snapshot.workspace_id,
                    job.id,
                    model_name,
                )
            )
        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _run_agents_async(
                        AGENT_DEFINITIONS,
                        payloads,
                        snapshot.id,
                        snapshot.workspace_id,
                        job.id,
                        model_name,
                    ),
                )
                agent_results = future.result(timeout=120)

    scores: list[RiskScore] = []
    for defn, result in zip(AGENT_DEFINITIONS, agent_results):
        score = _persist_agent_result(db, defn, result, snapshot.id, snapshot.workspace_id, job.id)
        scores.append(score)

    flags = _make_flags_from_agents(db, snapshot, summary, list(positions), agent_results)

    succeeded = sum(1 for r in agent_results if r.get("status") == "succeeded")
    job_service.mark_finished(
        job,
        status="succeeded" if succeeded >= 4 else "failed",
        result_payload={"score_count": len(scores), "flag_count": len(flags), "succeeded_agents": succeeded},
        succeeded_children=succeeded,
        failed_children=len(agent_results) - succeeded,
    )
    db.flush()
    return job, scores, flags
