from __future__ import annotations

import asyncio
from typing import Any

from backend.services.ingest.agents import (
    classify_document,
    extract_accounting,
    extract_risk,
    extract_treasury,
    reconcile_extraction,
)
from backend.services.ingest.layout_parser import parse_document_layout


async def _fan_out(parsed_layout: dict[str, Any], classification: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    accountant = extract_accounting(parsed_layout, classification)
    risk = extract_risk(parsed_layout, classification, accountant)
    treasury = extract_treasury(parsed_layout, classification)
    return accountant, risk, treasury


async def run_document_pipeline(*, filename: str, file_type: str, payload: bytes) -> dict[str, Any]:
    parsed_layout = parse_document_layout(file_type, payload)
    classification = classify_document(filename, parsed_layout["raw_text"], parsed_layout["rows"])
    accountant, risk, treasury = await _fan_out(parsed_layout, classification)
    reconciliation = reconcile_extraction(classification, accountant, risk, treasury)
    return {
        "layout": parsed_layout,
        "classification": classification,
        "accounting": accountant,
        "risk": risk,
        "treasury": treasury,
        "reconciliation": reconciliation,
    }
