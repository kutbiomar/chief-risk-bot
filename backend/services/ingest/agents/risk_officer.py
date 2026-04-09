from __future__ import annotations

from collections import defaultdict
from typing import Any


def _normalize_factor_token(value: str | None, default: str = "unspecified") -> str:
    if not value:
        return default
    return value.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def extract_risk(parsed_layout: dict[str, Any], classification: dict[str, Any], accounting: dict[str, Any]) -> dict[str, Any]:
    sector_totals: dict[str, float] = defaultdict(float)
    region_totals: dict[str, float] = defaultdict(float)
    top_holdings: list[dict[str, Any]] = []
    red_flags: list[str] = []

    for position in accounting["positions"]:
        sector = position.get("sector") or "Unspecified"
        region = position.get("geo_region") or "Unspecified"
        value = float(position.get("market_value_usd") or 0.0)
        sector_totals[str(sector)] += value
        region_totals[str(region)] += value
        top_holdings.append(
            {
                "name": position.get("name") or position.get("ticker"),
                "ticker": position.get("ticker"),
                "sector": sector,
                "weight": value,
            }
        )
        position["factor_asset_class"] = _normalize_factor_token(position.get("asset_class"))
        position["factor_sector"] = _normalize_factor_token(position.get("sector"))
        position["factor_subsector"] = None
        position["factor_country"] = None
        position["factor_region"] = _normalize_factor_token(position.get("geo_region"))
        position["factor_market_segment"] = _normalize_factor_token(position.get("market_segment"))
        position["factor_tag_source"] = "extracted"
        position["factor_tag_confidence"] = 0.82

    raw_text = parsed_layout["raw_text"].lower()
    for phrase in ("write-down", "liquidity issue", "key man", "restatement", "breach"):
        if phrase in raw_text:
            red_flags.append(phrase)

    total = sum(sector_totals.values()) or 1.0
    sector_exposures = {key: round(value / total * 100.0, 2) for key, value in sector_totals.items()}
    geography = {key: round(value / total * 100.0, 2) for key, value in region_totals.items()}
    return {
        "top_holdings": sorted(top_holdings, key=lambda item: item["weight"], reverse=True)[:5],
        "sector_exposures": sector_exposures,
        "geography": geography,
        "leverage_ratio": None,
        "liquidity_profile": None,
        "red_flags": red_flags,
        "confidence": 0.82 if accounting["positions"] else 0.35,
    }
