from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.analytics import MacroCache, RiskFlag, RiskScore, VarResult
from backend.models.content import BriefingRun
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.paths import STORAGE_ROOT
from backend.services.auth.session import utc_now
from backend.services.liquidity import get_liquidity_summary
from backend.services.portfolio import summarize_positions

logger = logging.getLogger(__name__)

QUALITY_GATE_LABELS = {
    "deterministic_fallback": "Deterministic fallback was used",
    "insufficient_agent_coverage": "Too few risk agents completed successfully",
    "thin_risk_content": "Generated risk coverage is too thin",
    "thin_recommendations": "Generated recommendations are incomplete",
    "low_var_coverage": "VaR model coverage is below the preferred threshold",
    "missing_liquidity_context": "Liquidity context is missing from the briefing payload",
}


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))

BRIEFING_MODEL = "claude-sonnet-4-6"
PROMPT_VERSION = "briefing-v1"

BRIEFING_SYSTEM_PROMPT = """You are the Chief Risk Officer of a family office. You are writing the weekly risk briefing for the CIO. Your writing is:
- Precise and data-driven (cite specific numbers)
- Concise (a CIO reads this in 5 minutes)
- Action-oriented (each section ends with implications or questions for the committee)
- Written in the tone of a trusted senior advisor, not a compliance report

You will receive structured data about the portfolio, risk scores, and macro environment. Base everything on the data provided. Do not fabricate numbers.

Respond with valid JSON only, using this exact structure:
{
  "executive_summary": "<2-3 sentence overview of the week's risk picture>",
  "market_context": "<2-3 sentences on macro environment and what it means for this portfolio>",
  "portfolio_risks": [
    {
      "risk_area": "<name>",
      "severity": "<watch|elevated|priority>",
      "finding": "<1-2 sentences describing the risk with specific data>",
      "implication": "<1 sentence on what the committee should consider>"
    }
  ],
  "recommendations": [
    "<specific, actionable recommendation>",
    "<specific, actionable recommendation>"
  ],
  "data_caveats": ["<caveat if any data is incomplete or modeled with assumptions>"]
}"""

SCOPE_SYSTEM_OVERRIDES: dict[str, str] = {
    "risk": (
        "Focus ONLY on risk: portfolio_risks (all of them, with full detail), market_context, and one or two "
        "targeted recommendations. Set executive_summary to a single sentence. data_caveats as needed."
    ),
    "assets": (
        "Focus ONLY on assets and valuations: executive_summary covering AUM and composition changes, "
        "market_context on asset-level macro drivers, and recommendations specific to allocation. "
        "portfolio_risks: include only risks directly tied to asset concentration or valuation."
    ),
    "liquidity": (
        "Focus ONLY on liquidity: executive_summary on cash position and near-term flows, "
        "recommendations specific to liquidity management. "
        "portfolio_risks: include only liquidity-related risks. market_context: liquidity macro only."
    ),
    "scenarios": (
        "Focus ONLY on stress scenarios and tail risks: portfolio_risks should enumerate scenario impacts, "
        "recommendations should address scenario mitigation. executive_summary: one sentence on tail risk posture."
    ),
    "daily": (
        "This is the daily home-screen briefing. Be comprehensive but scannable: cover asset movements, "
        "risk regime, and liquidity in executive_summary (3-4 sentences). Populate all sections fully."
    ),
}


def _week_label(value: datetime) -> str:
    iso = value.isocalendar()
    return f"week-{iso.week}-{iso.year}"


def _build_briefing_payload(
    snapshot: PortfolioSnapshot,
    positions: list[Position],
    summary: dict,
    scores: list[RiskScore],
    flags: list[RiskFlag],
    var_result: VarResult | None,
    macro: MacroCache | None,
    liquidity_summary: dict | None,
) -> dict:
    macro_payload = json.loads(macro.payload_json) if macro else {}

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

    scores_summary = [
        {
            "agent": s.agent,
            "severity": s.severity,
            "score": s.score,
            "headline": s.headline,
            "reasoning": s.reasoning,
        }
        for s in sorted(scores, key=lambda x: x.score or 0, reverse=True)
    ]

    flags_summary = [
        {"rule": f.rule, "severity": f.severity, "ticker": f.ticker, "description": f.description}
        for f in flags
    ]

    var_section: dict = {}
    if var_result:
        var_section = {
            "var_1d_95_usd": round(var_result.var_1d_95, 0),
            "var_1d_95_pct_aum": round(
                var_result.var_1d_95 / max(float(summary["total_aum_usd"]), 1) * 100, 3
            ),
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
        },
        "risk_scores": scores_summary,
        "risk_flags": flags_summary,
        "var": var_section,
        "macro": macro_payload,
        "liquidity": liquidity_summary or {},
    }


def _generate_briefing_deterministic(payload: dict) -> dict:
    """Fallback briefing when Anthropic API key is absent."""
    scores = payload.get("risk_scores", [])
    var = payload.get("var", {})
    portfolio = payload.get("portfolio", {})
    macro = payload.get("macro", {})
    total_aum = portfolio.get("total_aum_usd", 0)
    var_pct = var.get("var_1d_95_pct_aum", 0)
    priority = [s for s in scores if s.get("severity") == "priority"]
    elevated = [s for s in scores if s.get("severity") == "elevated"]

    def deterministic_implication(agent: str) -> str:
      implications = {
          "concentration": "The committee should review whether the largest holdings still match the intended risk budget.",
          "liquidity": "Near-term cash needs should be checked against the current mix of liquid and illiquid assets.",
          "macro": "Macro sensitivity should be revisited before the next committee meeting.",
          "fx": "Cross-currency exposures should be confirmed against the base-currency objective.",
          "tail": "Stress scenarios should be revisited before increasing risk.",
      }
      return implications.get(agent, "The committee should review whether this risk is still within tolerance.")

    def deterministic_finding(score: dict) -> str:
      agent = str(score.get("agent") or "portfolio").replace("_", " ")
      severity = str(score.get("severity") or "watch")
      rating = score.get("score")
      lead = f"{agent.title()} risk is {severity}"
      if rating is not None:
          lead += f" (score {rating}/10)."
      else:
          lead += "."
      details = {
          "concentration": "The portfolio's largest holdings account for an outsized share of AUM and deserve explicit sizing review.",
          "liquidity": "Liquidity is uneven across holdings, with private or less-liquid assets reducing flexibility under stress.",
          "macro": "Current macro readings suggest a cautious backdrop for rate-sensitive and cyclical exposures.",
          "fx": "Foreign-currency positions can amplify headline moves when the dollar regime shifts.",
          "tail": "Scenario analysis indicates the downside tail is shaped by a small set of correlated exposures.",
      }
      return f"{lead} {details.get(str(score.get('agent') or ''), score.get('headline') or 'The portfolio should be reviewed closely.')}"

    portfolio_risks = []
    for score in scores[:4]:
        portfolio_risks.append({
            "risk_area": score.get("agent", "").replace("_", " ").title(),
            "severity": score.get("severity", "watch"),
            "finding": deterministic_finding(score),
            "implication": deterministic_implication(str(score.get("agent") or "")),
        })

    market_bits = []
    if macro.get("vix") is not None:
        market_bits.append(f"VIX at {float(macro['vix']):.1f}")
    if macro.get("ust10y") is not None:
        market_bits.append(f"10Y at {float(macro['ust10y']):.2f}%")
    if macro.get("dxy") is not None:
        market_bits.append(f"DXY at {float(macro['dxy']):.1f}")
    macro_sentence = ", ".join(market_bits) if market_bits else "Macro readings are in line with the current market backdrop"
    risk_tone = "cautious" if priority else "balanced"

    return {
        "executive_summary": (
            f"Portfolio AUM of ${total_aum:,.0f}. "
            f"1-day 95% VaR is {var_pct:.2f}% of AUM. "
            f"{len(priority)} priority and {len(elevated)} elevated risk findings this week."
        ),
        "market_context": f"{macro_sentence}. {risk_tone.capitalize()} macro backdrop for the portfolio.",
        "portfolio_risks": portfolio_risks,
        "recommendations": [
            "Review the highest-concentration positions before the next committee meeting.",
            "Validate whether current liquidity aligns with near-term cash needs.",
            "Use the VaR result as a sizing discipline, not as a standalone limit.",
        ],
        "data_caveats": [],
    }


def _quality_message(reason: str) -> str:
    return QUALITY_GATE_LABELS.get(reason, reason.replace("_", " "))


def assess_briefing_quality(
    output: dict[str, Any],
    *,
    model_used: str,
    scores: list[RiskScore],
    var_result: VarResult,
    liquidity_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    succeeded_agents = sum(1 for score in scores if score.status == "succeeded")
    risk_count = len(output.get("portfolio_risks") or [])
    recommendation_count = len(output.get("recommendations") or [])
    coverage_pct = float(var_result.model_coverage_pct or 0.0)

    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if model_used == "deterministic-demo-briefing":
        blocking_reasons.append("deterministic_fallback")
    if succeeded_agents < 4:
        blocking_reasons.append("insufficient_agent_coverage")
    if risk_count < 2:
        blocking_reasons.append("thin_risk_content")
    if recommendation_count < 2:
        blocking_reasons.append("thin_recommendations")
    if coverage_pct < 60.0:
        warnings.append("low_var_coverage")
    if not liquidity_summary:
        warnings.append("missing_liquidity_context")

    score = max(0, 100 - len(blocking_reasons) * 25 - len(warnings) * 10)
    publish_ready = not blocking_reasons

    return {
        "publish_ready": publish_ready,
        "score": score,
        "summary": "Publish ready" if publish_ready else "Manual review required",
        "blocking_reasons": blocking_reasons,
        "blocking_messages": [_quality_message(reason) for reason in blocking_reasons],
        "warnings": warnings,
        "warning_messages": [_quality_message(reason) for reason in warnings],
        "agent_success_count": succeeded_agents,
        "expected_agent_count": len(scores),
        "risk_item_count": risk_count,
        "recommendation_count": recommendation_count,
        "var_model_coverage_pct": round(coverage_pct, 1),
    }


def generate_briefing(db: Session, snapshot: PortfolioSnapshot, user_id: str | None, scope: str = "full") -> BriefingRun:
    settings = get_settings()
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    summary = summarize_positions(list(positions))

    var_result = db.scalar(
        select(VarResult).where(VarResult.snapshot_id == snapshot.id).order_by(VarResult.computed_at.desc())
    )
    if var_result is None:
        raise ValueError("VaR must be computed before generating a briefing")

    scores = db.scalars(select(RiskScore).where(RiskScore.snapshot_id == snapshot.id)).all()
    flags = db.scalars(select(RiskFlag).where(RiskFlag.snapshot_id == snapshot.id)).all()
    macro = (
        db.query(MacroCache)
        .filter(MacroCache.workspace_id == snapshot.workspace_id)
        .order_by(MacroCache.fetched_at.desc())
        .first()
    )
    liquidity_summary = get_liquidity_summary(snapshot.workspace_id, db)
    now = utc_now()
    current_version = (
        db.scalar(
            select(func.max(BriefingRun.version)).where(
                BriefingRun.workspace_id == snapshot.workspace_id,
                BriefingRun.week_label == _week_label(now),
            )
        )
        or 0
    )

    payload = _build_briefing_payload(
        snapshot, list(positions), summary, list(scores), list(flags), var_result, macro, liquidity_summary
    )

    model_used = "deterministic-demo-briefing"
    input_tokens = 0
    output_tokens = 0

    if settings.anthropic_api_key and not _is_test_runtime():
        try:
            import anthropic

            scope_override = SCOPE_SYSTEM_OVERRIDES.get(scope, "")
            system_prompt = (
                f"{BRIEFING_SYSTEM_PROMPT}\n\nScope instructions: {scope_override}"
                if scope_override
                else BRIEFING_SYSTEM_PROMPT
            )

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            user_content = json.dumps(payload, indent=2, sort_keys=True)
            response = client.messages.create(
                model=BRIEFING_MODEL,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate the weekly risk briefing based on the following portfolio data:\n\n{user_content}",
                    }
                ],
            )
            raw_text = response.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            output = json.loads(raw_text)
            model_used = BRIEFING_MODEL
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
        except Exception as exc:
            logger.error("Briefing Claude call failed: %s — falling back to deterministic", exc)
            output = _generate_briefing_deterministic(payload)
    else:
        logger.warning("ANTHROPIC_API_KEY not set — using deterministic briefing")
        output = _generate_briefing_deterministic(payload)

    # Enrich output with metadata
    output["headline"] = f"Weekly Risk Briefing — {_week_label(now)}"
    output["portfolio_snapshot"] = {
        "snapshot_id": snapshot.id,
        "position_count": snapshot.position_count,
        "total_aum_usd": snapshot.total_aum_usd,
    }
    output["agents_used"] = [
        {"agent": s.agent, "model": s.model, "status": s.status}
        for s in scores
    ]
    if var_result:
        output["var_commentary"] = (
            f"1-day 95% VaR is ${var_result.var_1d_95:,.0f} "
            f"({var_result.var_1d_95 / max(float(snapshot.total_aum_usd), 1) * 100:.2f}% of AUM) "
            f"on a ${snapshot.total_aum_usd:,.0f} portfolio."
        )
    if liquidity_summary:
        next_due = liquidity_summary.get("next_call_due_date") or "no scheduled call"
        next_amount = float(liquidity_summary.get("next_call_amount_usd") or 0.0)
        output["liquidity_snapshot"] = liquidity_summary
        output["liquidity_commentary"] = (
            f"Next capital call: {next_due}"
            f"{f' for ${next_amount:,.0f}' if next_amount else ''}. "
            f"Expected 90-day distributions: ${float(liquidity_summary.get('expected_distributions_usd') or 0.0):,.0f}. "
            f"Net 90-day liquidity: ${float(liquidity_summary.get('net_liquidity_usd') or 0.0):,.0f}. "
            f"{'Buffer breach projected.' if liquidity_summary.get('buffer_breach') else 'Buffer remains intact.'}"
        )
    output["quality_gate"] = assess_briefing_quality(
        output,
        model_used=model_used,
        scores=list(scores),
        var_result=var_result,
        liquidity_summary=liquidity_summary,
    )

    briefing = BriefingRun(
        workspace_id=snapshot.workspace_id,
        snapshot_id=snapshot.id,
        var_result_id=var_result.id,
        generated_by=user_id,
        version=current_version + 1,
        status="draft",
        week_label=_week_label(now),
        output_json=json.dumps(output, sort_keys=True),
        model=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(briefing)
    db.flush()
    return briefing


# ---------------------------------------------------------------------------
# PDF export via WeasyPrint
# ---------------------------------------------------------------------------

_PDF_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter Tight', 'Inter', Arial, sans-serif;
      font-size: 10pt;
      color: #1a1a1a;
      background: #fff8f6;
      padding: 36pt 48pt;
      line-height: 1.5;
    }}

    h1 {{
      font-family: 'Fraunces', Georgia, serif;
      font-size: 22pt;
      font-weight: 700;
      color: #1B2B5E;
      margin-bottom: 4pt;
    }}

    h2 {{
      font-family: 'Fraunces', Georgia, serif;
      font-size: 13pt;
      font-weight: 600;
      color: #1B2B5E;
      margin-top: 18pt;
      margin-bottom: 6pt;
      border-bottom: 1pt solid #1B2B5E22;
      padding-bottom: 3pt;
    }}

    .subtitle {{
      font-size: 9pt;
      color: #666;
      margin-bottom: 24pt;
    }}

    p {{
      margin-bottom: 8pt;
    }}

    .risk-item {{
      margin-bottom: 10pt;
      padding: 8pt 10pt;
      border-left: 3pt solid #ccc;
      background: #fff;
    }}

    .risk-item.priority {{ border-color: #c0392b; }}
    .risk-item.elevated {{ border-color: #e67e22; }}
    .risk-item.watch {{ border-color: #27ae60; }}

    .risk-label {{
      font-weight: 600;
      font-size: 9pt;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 3pt;
    }}
    .risk-label.priority {{ color: #c0392b; }}
    .risk-label.elevated {{ color: #e67e22; }}
    .risk-label.watch {{ color: #27ae60; }}

    .risk-area {{
      font-family: 'Fraunces', Georgia, serif;
      font-weight: 600;
      font-size: 11pt;
      color: #1B2B5E;
    }}

    .risk-implication {{
      font-size: 9pt;
      color: #555;
      margin-top: 4pt;
    }}

    ul {{
      padding-left: 14pt;
    }}

    li {{
      margin-bottom: 5pt;
    }}

    .num {{
      font-family: 'JetBrains Mono', 'Courier New', monospace;
    }}

    .var-box {{
      background: #fff;
      border: 1pt solid #1B2B5E22;
      border-radius: 4pt;
      padding: 10pt 14pt;
      margin-bottom: 12pt;
    }}

    .var-box .label {{
      font-size: 8pt;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: #888;
    }}

    .var-box .value {{
      font-family: 'JetBrains Mono', 'Courier New', monospace;
      font-size: 14pt;
      font-weight: 500;
      color: #1B2B5E;
    }}

    .caveat {{
      font-size: 8pt;
      color: #888;
      font-style: italic;
      margin-top: 18pt;
    }}

    .footer {{
      margin-top: 24pt;
      padding-top: 8pt;
      border-top: 0.5pt solid #ccc;
      font-size: 8pt;
      color: #aaa;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>

<h1>{headline}</h1>
<div class="subtitle">
  AUM <span class="num">${total_aum}</span> &nbsp;·&nbsp;
  {position_count} positions &nbsp;·&nbsp;
  {week_label}
</div>

<h2>Executive Summary</h2>
<p>{executive_summary}</p>

<h2>Market Context</h2>
<p>{market_context}</p>

{var_block}

{liquidity_block}

<h2>Portfolio Risks</h2>
{risks_html}

<h2>Recommendations</h2>
<ul>
{recommendations_html}
</ul>

{caveats_html}

<div class="footer">
  <span>ChiefRiskBot — Confidential</span>
  <span>{generated_at}</span>
</div>

</body>
</html>"""


def _render_briefing_html(briefing: BriefingRun) -> str:
    body = json.loads(briefing.output_json)

    total_aum_raw = body.get("portfolio_snapshot", {}).get("total_aum_usd", 0)
    position_count = body.get("portfolio_snapshot", {}).get("position_count", 0)
    try:
        total_aum = f"{float(total_aum_raw):,.0f}"
    except (ValueError, TypeError):
        total_aum = "—"

    var_commentary = body.get("var_commentary", "")
    var_block = ""
    if var_commentary:
        var_block = f"""<h2>Value at Risk</h2>
<div class="var-box">
  <div class="label">1-Day 95% VaR Commentary</div>
  <div style="margin-top: 6pt">{var_commentary}</div>
</div>"""

    liquidity_commentary = body.get("liquidity_commentary", "")
    liquidity_block = ""
    if liquidity_commentary:
        liquidity_block = f"""<h2>Liquidity Snapshot</h2>
<div class="var-box">
  <div class="label">Next 90 Days Cash Flow</div>
  <div style="margin-top: 6pt">{liquidity_commentary}</div>
</div>"""

    risks_html_parts = []
    for risk in body.get("portfolio_risks", []):
        sev = risk.get("severity", "watch")
        area = risk.get("risk_area", "")
        finding = risk.get("finding", "")
        implication = risk.get("implication", "")
        risks_html_parts.append(
            f"""<div class="risk-item {sev}">
  <div class="risk-label {sev}">{sev.upper()}</div>
  <div class="risk-area">{area}</div>
  <p style="margin-top:4pt">{finding}</p>
  {f'<div class="risk-implication">→ {implication}</div>' if implication else ''}
</div>"""
        )

    recommendations_html = "\n".join(
        f"<li>{rec}</li>" for rec in body.get("recommendations", [])
    )

    caveats = body.get("data_caveats", [])
    caveats_html = ""
    if caveats:
        caveat_items = " ".join(f"<li>{c}</li>" for c in caveats)
        caveats_html = f'<div class="caveat"><strong>Data caveats:</strong><ul>{caveat_items}</ul></div>'

    return _PDF_HTML_TEMPLATE.format(
        headline=body.get("headline", "Weekly Risk Briefing"),
        total_aum=total_aum,
        position_count=position_count,
        week_label=briefing.week_label,
        executive_summary=body.get("executive_summary", ""),
        market_context=body.get("market_context", ""),
        var_block=var_block,
        liquidity_block=liquidity_block,
        risks_html="\n".join(risks_html_parts),
        recommendations_html=recommendations_html,
        caveats_html=caveats_html,
        generated_at=utc_now().strftime("%Y-%m-%d %H:%M UTC"),
    )


class PdfExportUnavailableError(RuntimeError):
    pass


def export_briefing_pdf(db: Session, briefing: BriefingRun, workspace_id: str) -> str:
    export_dir = STORAGE_ROOT / "briefings" / workspace_id
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{briefing.id}_v{briefing.version}.pdf"

    html_content = _render_briefing_html(briefing)

    try:
        from weasyprint import HTML

        HTML(string=html_content).write_pdf(str(export_path))
        logger.info("WeasyPrint PDF written to %s", export_path)
    except Exception as exc:
        logger.error("WeasyPrint failed: %s", exc)
        raise PdfExportUnavailableError(
            "PDF export unavailable — WeasyPrint system libraries not installed"
        ) from exc

    briefing.pdf_path = str(export_path)
    db.flush()
    return str(export_path)
