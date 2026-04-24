from __future__ import annotations

import re
from typing import Any, Optional, Tuple


AMOUNT_RE = re.compile(r"(?P<currency>USD|EUR|GBP|CHF)?\s*\$?(?P<amount>[0-9][0-9,]*(?:\.[0-9]{1,2})?)")
DATE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")


def _find_amount(text: str) -> Tuple[Optional[str], Optional[str]]:
    match = AMOUNT_RE.search(text)
    if not match:
        return None, None
    return match.group("currency") or "USD", match.group("amount").replace(",", "")


def _find_date(text: str) -> Optional[str]:
    match = DATE_RE.search(text)
    return match.group("date") if match else None


def extract_capital_call(text: str) -> dict[str, Any]:
    currency, amount = _find_amount(text)
    due_date = _find_date(text)
    return {
        "fund_name": None,
        "amount": amount,
        "currency": currency,
        "due_date": due_date,
        "notice_date": due_date,
        "wire_instructions": None,
        "confidence": {
            "amount": 78 if amount else 0,
            "currency": 75 if currency else 0,
            "due_date": 70 if due_date else 0,
        },
    }


def extract_lp_statement(text: str) -> dict[str, Any]:
    currency, amount = _find_amount(text)
    statement_date = _find_date(text)
    return {
        "fund_name": None,
        "nav": amount,
        "nav_date": statement_date,
        "called_capital": None,
        "uncalled": None,
        "distributions": None,
        "commitment_balance": None,
        "confidence": {
            "nav": 72 if amount else 0,
            "nav_date": 68 if statement_date else 0,
        },
    }


def extract_quarterly_report(text: str) -> dict[str, Any]:
    return {
        "fund_name": None,
        "nav": None,
        "nav_date": _find_date(text),
        "underlying_holdings": [],
        "key_metrics": {},
        "confidence": {"nav_date": 65 if _find_date(text) else 0},
    }


def extract_dd_document(text: str) -> dict[str, Any]:
    return {"tags": ["dd_document"], "confidence": {"classification": 80}}


def extract_document(document_type: str, text: str) -> dict[str, Any]:
    if document_type == "capital_call":
        return extract_capital_call(text)
    if document_type == "lp_statement":
        return extract_lp_statement(text)
    if document_type == "quarterly_report":
        return extract_quarterly_report(text)
    if document_type == "dd_document":
        return extract_dd_document(text)
    return {"raw_excerpt": text[:500], "confidence": {}}
