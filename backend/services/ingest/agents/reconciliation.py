from __future__ import annotations

import json
import os
from typing import Any

from backend.config import get_settings


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _deterministic_reconciliation(
    classification: dict[str, Any],
    accounting: dict[str, Any],
    risk: dict[str, Any],
    treasury: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    field_reviews: list[dict[str, Any]] = []
    positions = accounting["positions"]

    if classification["doc_type"] == "UNKNOWN":
        errors.append("unknown_document_type")
    if not positions and classification["doc_type"] == "NAV_STATEMENT":
        errors.append("no_positions_extracted")
    if sum(risk.get("sector_exposures", {}).values()) > 100.5:
        errors.append("sector_weights_exceed_100")
    if treasury.get("wire_bank"):
        field_reviews.append({"field": "wire_instructions", "reason": "wire_instructions_require_hitl", "confidence": treasury["confidence"]})

    combined_confidence = round(
        (
            float(classification.get("confidence", 0.0))
            + float(accounting.get("confidence", 0.0))
            + float(risk.get("confidence", 0.0))
            + float(treasury.get("confidence", 0.0))
        ) / 4.0,
        2,
    )
    if combined_confidence < 0.85:
        errors.append("confidence_below_threshold")

    row_confidence = accounting["row_confidence"]
    for row in row_confidence:
        issues = list(row.get("issues", []))
        if classification["doc_type"] == "CAPITAL_CALL":
            issues.append("document_type_capital_call")
        if treasury.get("wire_bank"):
            issues.append("wire_instruction_hitl")
        row["issues"] = issues

    return {
        "doc_type": classification["doc_type"],
        "positions": positions,
        "confidence_rows": row_confidence,
        "field_reviews": field_reviews,
        "overall_confidence": combined_confidence,
        "errors": errors,
        "needs_review": bool(errors or field_reviews),
        "reconciliation_model": "deterministic-reconciliation",
    }


def _parse_json_text(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Reconciliation response must be a JSON object")
    return parsed


def _reconcile_with_claude(
    classification: dict[str, Any],
    accounting: dict[str, Any],
    risk: dict[str, Any],
    treasury: dict[str, Any],
    fallback: dict[str, Any],
) -> dict[str, Any] | None:
    settings = get_settings()
    if _is_test_runtime() or not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "classification": classification,
            "accounting": accounting,
            "risk": risk,
            "treasury": treasury,
            "fallback": fallback,
        }
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1800,
            system=(
                "You are the reconciliation agent for financial document extraction. "
                "Return only JSON. Preserve all detected wire instructions as human-in-the-loop review items. "
                "Do not remove private holdings or reduce required review flags. "
                "Output keys: doc_type, overall_confidence, errors, field_reviews."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Reconcile the extraction outputs. Keep the existing positions and confidence rows unless there "
                        "is a clear reason to add an error flag. Return strict JSON only.\n\n"
                        f"{json.dumps(payload, indent=2, sort_keys=True)}"
                    ),
                }
            ],
        )
        parsed = _parse_json_text(response.content[0].text)
    except Exception:
        return None

    return {
        "doc_type": str(parsed.get("doc_type") or fallback["doc_type"]),
        "positions": fallback["positions"],
        "confidence_rows": fallback["confidence_rows"],
        "field_reviews": parsed.get("field_reviews", fallback["field_reviews"]),
        "overall_confidence": float(parsed.get("overall_confidence", fallback["overall_confidence"])),
        "errors": parsed.get("errors", fallback["errors"]),
        "needs_review": bool(parsed.get("needs_review", True)),
        "reconciliation_model": "claude-opus-4-6",
    }


def reconcile_extraction(
    classification: dict[str, Any],
    accounting: dict[str, Any],
    risk: dict[str, Any],
    treasury: dict[str, Any],
) -> dict[str, Any]:
    fallback = _deterministic_reconciliation(classification, accounting, risk, treasury)
    provider_result = _reconcile_with_claude(classification, accounting, risk, treasury, fallback)
    if provider_result is None:
        return fallback
    provider_result["needs_review"] = bool(provider_result["errors"] or provider_result["field_reviews"])
    return provider_result
