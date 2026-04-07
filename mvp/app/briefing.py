"""Claude briefing generator.

The core insight from the office-hours session: this is a narrative
rationalization tool, not a risk dashboard. The output is language the
family office CIO can carry into an investment committee conversation.

Structure:
  1. Portfolio snapshot — what you own, where concentration sits
  2. Top 3 risks this week — each with reasoning and evidence
  3. Talking points — language for the IC / LP / banker conversation

One Claude API call. No tool use. Deterministic template.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from typing import Any

from anthropic import Anthropic

log = logging.getLogger("riskpilot.briefing")

SYSTEM_PROMPT = """You are the RiskPilot briefing analyst. You write weekly risk briefings for family office CIOs who will carry your output into investment committee conversations.

Your job is NOT to tell them what to do. Your job is to surface the conversation they should already be having, with the evidence to have it credibly. A briefing is a starting point, not a recommendation.

Voice rules:
- Plain language, no jargon. A smart non-quant family council member should follow every sentence.
- Be specific. Reference actual positions, actual sector concentration, actual macro levels by number.
- Be direct about uncertainty. If the data is thin, say so. Never invent numbers.
- No hedging filler. No "it may be worth considering." State what you see.
- No recommendations to buy or sell. Frame everything as "questions worth raising" or "themes to discuss."

Output format: return STRICT JSON with this exact schema and no other text:

{
  "headline": "One sentence capturing the most important thing this week.",
  "portfolio_snapshot": {
    "total_market_value_usd": number,
    "top_concentrations": [
      {"label": "string", "pct_of_portfolio": number, "why_it_matters": "string"}
    ],
    "asset_class_mix": [
      {"asset_class": "string", "pct": number}
    ]
  },
  "top_risks": [
    {
      "title": "Short risk label (5-8 words)",
      "severity": "watch" | "elevated" | "priority",
      "evidence": ["2-4 bullet strings with specific numbers or holdings"],
      "reasoning": "2-3 sentences explaining why this matters for THIS portfolio right now.",
      "conversation_prompt": "One question the CIO should put to the committee."
    }
  ],
  "talking_points": [
    "3-5 ready-to-use sentences the CIO can say verbatim in a committee meeting."
  ],
  "data_caveats": [
    "Any fields where data was missing or stale. Empty list if none."
  ]
}

Produce exactly 3 top_risks. Never more, never fewer.
"""


def _summarize_portfolio(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute deterministic portfolio stats so Claude doesn't have to do math."""
    total_mv = 0.0
    by_asset_class: dict[str, float] = defaultdict(float)
    by_custodian: dict[str, float] = defaultdict(float)
    position_mvs: list[tuple[str, float]] = []

    for p in positions:
        mv = p.get("market_value")
        if mv is None:
            continue
        total_mv += mv
        by_asset_class[p["asset_class"]] += mv
        custodian = p.get("custodian") or "unknown"
        by_custodian[custodian] += mv
        position_mvs.append((p["ticker"], mv))

    def _pct(v: float) -> float:
        return round((v / total_mv) * 100, 2) if total_mv > 0 else 0.0

    top_positions = sorted(position_mvs, key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_market_value_usd": round(total_mv, 2),
        "position_count": len(positions),
        "asset_class_mix": [
            {"asset_class": k, "pct": _pct(v), "mv_usd": round(v, 2)}
            for k, v in sorted(by_asset_class.items(), key=lambda x: x[1], reverse=True)
        ],
        "custodian_mix": [
            {"custodian": k, "pct": _pct(v), "mv_usd": round(v, 2)}
            for k, v in sorted(by_custodian.items(), key=lambda x: x[1], reverse=True)
        ],
        "top_positions": [
            {"ticker": t, "pct": _pct(mv), "mv_usd": round(mv, 2)} for t, mv in top_positions
        ],
    }


def _build_user_prompt(
    positions: list[dict[str, Any]],
    summary: dict[str, Any],
    macro: dict[str, Any],
    concerns: str | None,
    client_name: str,
) -> str:
    concerns_block = f"\n\nSPECIFIC CONCERNS from {client_name}:\n{concerns}\n" if concerns else ""
    return (
        f"CLIENT: {client_name}\n"
        f"BRIEFING DATE: this week\n"
        f"{concerns_block}\n"
        f"PORTFOLIO SUMMARY (computed deterministically — use these numbers, do not recompute):\n"
        f"{json.dumps(summary, indent=2)}\n\n"
        f"POSITIONS (enriched with live market data):\n"
        f"{json.dumps(positions, indent=2, default=str)}\n\n"
        f"MACRO CONTEXT (latest available):\n"
        f"{json.dumps(macro, indent=2, default=str)}\n\n"
        f"Write the briefing as JSON matching the schema in the system prompt. "
        f"Be specific. Reference actual tickers, actual percentages, actual macro numbers. "
        f"Remember: the CIO is taking this into a conversation with their investment committee. "
        f"Every sentence should be something they can say out loud without embarrassment."
    )


def generate_briefing(
    positions: list[dict[str, Any]],
    macro: dict[str, Any],
    concerns: str | None = None,
    client_name: str = "Family Office",
) -> dict[str, Any]:
    """Call Claude to generate the briefing. Returns parsed JSON + metadata."""
    summary = _summarize_portfolio(positions)
    prompt = _build_user_prompt(positions, summary, macro, concerns, client_name)

    client = Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

    log.info("calling %s for briefing (%d positions, total_mv=%.2f)", model, len(positions), summary["total_market_value_usd"])

    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")

    # Strip possible markdown fences defensively
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        briefing = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.error("briefing JSON parse failed. raw text: %s", text[:500])
        raise RuntimeError(f"Model did not return valid JSON: {e}")

    return {
        "briefing": briefing,
        "portfolio_summary": summary,
        "model": model,
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        },
    }
