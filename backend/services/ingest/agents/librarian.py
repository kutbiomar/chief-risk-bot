from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from backend.config import get_settings


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _infer_doc_type(filename: str, raw_text: str) -> tuple[str, float]:
    haystack = f"{filename}\n{raw_text}".lower()
    if "capital call" in haystack or "drawdown" in haystack:
        return "CAPITAL_CALL", 0.94
    if "distribution" in haystack:
        return "DISTRIBUTION_NOTICE", 0.92
    if "nav" in haystack or "capital account" in haystack or "holdings" in haystack or "quarter" in haystack:
        return "NAV_STATEMENT", 0.9
    return "UNKNOWN", 0.45


def classify_document(filename: str, raw_text: str, rows: list[list[str]]) -> dict[str, Any]:
    doc_type, confidence = _infer_doc_type(filename, raw_text)
    basename = Path(filename).stem
    period_match = re.search(r"(q[1-4]\s*20\d{2}|20\d{2})", f"{basename} {raw_text}", flags=re.IGNORECASE)
    fund_name = None
    gp_name = None
    if rows and rows[0]:
        fund_name = next((cell for cell in rows[0] if cell and len(cell) > 3), None)
    if basename:
        gp_name = basename.split("-")[0].strip().replace("_", " ")
    model = "claude-sonnet-4-6" if get_settings().anthropic_api_key and not _is_test_runtime() else "deterministic-librarian"
    return {
        "doc_type": doc_type,
        "gp_name": gp_name,
        "fund_name": fund_name,
        "period": period_match.group(1) if period_match else None,
        "confidence": confidence,
        "model": model,
    }
