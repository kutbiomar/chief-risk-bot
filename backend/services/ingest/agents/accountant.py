from __future__ import annotations

import re
from typing import Any

from backend.constants import ASSET_CLASS_ALIASES

HEADER_ALIASES = {
    "ticker": "ticker",
    "symbol": "ticker",
    "security": "name",
    "security name": "name",
    "name": "name",
    "description": "name",
    "quantity": "quantity",
    "qty": "quantity",
    "shares": "quantity",
    "units": "quantity",
    "market value": "market_value_usd",
    "market value usd": "market_value_usd",
    "market_value_usd": "market_value_usd",
    "value": "market_value_usd",
    "asset class": "asset_class",
    "asset_class": "asset_class",
    "custodian": "custodian",
    "region": "geo_region",
    "geo region": "geo_region",
    "geo_region": "geo_region",
    "sector": "sector",
    "market segment": "market_segment",
    "market_segment": "market_segment",
    "currency": "position_currency",
    "position currency": "position_currency",
    "position_currency": "position_currency",
    "notes": "notes",
}
def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_header(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    slug = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return HEADER_ALIASES.get(slug, HEADER_ALIASES.get(slug.replace(" ", "_")))


def _parse_float(value: object) -> float | None:
    text = _normalize_text(value)
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_asset_class(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return ASSET_CLASS_ALIASES.get(text.lower(), text.lower().replace(" ", "_"))


def _looks_like_ticker(value: str | None) -> bool:
    if value is None:
        return False
    return bool(re.fullmatch(r"[A-Z0-9.\-]{1,12}", value.upper()))


def _build_position(record: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    ticker = _normalize_text(record.get("ticker"))
    ticker = ticker.upper() if ticker else None
    name = _normalize_text(record.get("name"))
    quantity = _parse_float(record.get("quantity"))
    market_value = _parse_float(record.get("market_value_usd"))
    asset_class = _normalize_asset_class(record.get("asset_class"))
    position_currency = (_normalize_text(record.get("position_currency")) or "USD").upper()

    confidence = 0.2
    issues: list[str] = []
    if ticker and _looks_like_ticker(ticker):
        confidence += 0.35
    elif ticker:
        issues.append("ticker format uncertain")
    else:
        issues.append("ticker missing")
    if quantity is not None:
        confidence += 0.2
    else:
        issues.append("quantity missing")
    if market_value is not None:
        confidence += 0.15
    else:
        issues.append("market value missing")
    if asset_class:
        confidence += 0.1
    if name:
        confidence += 0.05

    notes = _normalize_text(record.get("notes"))
    if issues:
        notes = f"{notes}; {'; '.join(issues)}" if notes else "; ".join(issues)

    return {
        "ticker": ticker,
        "name": name,
        "quantity": quantity,
        "market_value_usd": market_value,
        "asset_class": asset_class,
        "custodian": _normalize_text(record.get("custodian")),
        "geo_region": _normalize_text(record.get("geo_region")),
        "sector": _normalize_text(record.get("sector")),
        "market_segment": _normalize_text(record.get("market_segment")),
        "position_currency": position_currency,
        "notes": notes,
    }, {
        "confidence": round(min(confidence, 0.95), 2),
        "issues": issues,
    }


def extract_accounting(parsed_layout: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    rows = parsed_layout["rows"]
    header_map: list[str | None] | None = None
    positions: list[dict[str, object]] = []
    confidence_rows: list[dict[str, object]] = []

    for source_index, raw in enumerate(rows):
        source_ref = None
        if source_index < len(parsed_layout.get("row_refs", [])):
            source_ref = parsed_layout["row_refs"][source_index]
        if not any(cell.strip() for cell in raw):
            continue
        normalized_headers = [_normalize_header(cell) for cell in raw]
        if header_map is None and sum(1 for cell in normalized_headers if cell) >= 2:
            header_map = normalized_headers
            continue
        if header_map is None:
            continue
        record: dict[str, object] = {}
        for index, key in enumerate(header_map):
            if key is None or index >= len(raw):
                continue
            record[key] = raw[index]
        position, confidence = _build_position(record)
        if any(position[field] is not None for field in ("ticker", "name", "quantity", "market_value_usd")):
            if source_ref is not None:
                position["source_ref"] = source_ref
            confidence["row"] = len(positions) + 1
            positions.append(position)
            confidence_rows.append(confidence)

    total_value = round(sum(float(item.get("market_value_usd") or 0.0) for item in positions), 2)
    overall_confidence = round(
        sum(item["confidence"] for item in confidence_rows) / len(confidence_rows),
        2,
    ) if confidence_rows else 0.25

    return {
        "positions": positions,
        "row_confidence": confidence_rows,
        "nav_ending": total_value if classification["doc_type"] == "NAV_STATEMENT" else None,
        "total_commitment": total_value if classification["doc_type"] != "UNKNOWN" else None,
        "currency": "USD",
        "confidence": overall_confidence,
    }
