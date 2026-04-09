from __future__ import annotations

import re
from typing import Any


DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/20\d{2})\b")


def _find_first_amount(text: str) -> float | None:
    match = re.search(r"\$?\s?([0-9][0-9,]*(?:\.\d{1,2})?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _clean_wire_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.lstrip("|:- ").strip() or None


def extract_treasury(parsed_layout: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    raw_text = parsed_layout["raw_text"]
    lower = raw_text.lower()
    date_matches = DATE_PATTERN.findall(raw_text)
    due_date = date_matches[0] if date_matches else None
    call_amount = _find_first_amount(raw_text) if classification["doc_type"] == "CAPITAL_CALL" else None
    distribution_amount = _find_first_amount(raw_text) if classification["doc_type"] == "DISTRIBUTION_NOTICE" else None

    wire_bank = None
    wire_account = None
    wire_routing = None
    if "wire" in lower or "routing" in lower or "aba" in lower:
        bank_match = re.search(r"bank[:\s]+([^\n\r]+)", raw_text, flags=re.IGNORECASE)
        account_match = re.search(r"account(?: number)?[:\s]+([^\n\r]+)", raw_text, flags=re.IGNORECASE)
        routing_match = re.search(r"(?:routing|aba)[:\s]+([^\n\r]+)", raw_text, flags=re.IGNORECASE)
        wire_bank = _clean_wire_value(bank_match.group(1)) if bank_match else "Present in source"
        wire_account = _clean_wire_value(account_match.group(1)) if account_match else None
        wire_routing = _clean_wire_value(routing_match.group(1)) if routing_match else None

    confidence = 0.88 if classification["doc_type"] in {"CAPITAL_CALL", "DISTRIBUTION_NOTICE"} else 0.72
    if wire_bank:
        confidence = min(confidence, 0.7)
    return {
        "call_amount": call_amount,
        "call_due_date": due_date if classification["doc_type"] == "CAPITAL_CALL" else None,
        "distribution_amount": distribution_amount,
        "distribution_date": due_date if classification["doc_type"] == "DISTRIBUTION_NOTICE" else None,
        "wire_bank": wire_bank,
        "wire_account": wire_account,
        "wire_routing": wire_routing,
        "wire_reference": None,
        "contact_name": None,
        "contact_email": None,
        "confidence": confidence,
    }
