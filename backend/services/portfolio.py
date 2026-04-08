from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from backend.models.portfolio import Position

LIQUID_ASSET_CLASSES = {"public_equity", "fixed_income", "cash"}


def _market_value(position: Position) -> float:
    return float(position.market_value_usd or 0.0)


def summarize_positions(positions: Iterable[Position]) -> dict[str, object]:
    position_list = list(positions)
    total_aum = sum(_market_value(position) for position in position_list)

    def build_dimension(attribute: str) -> list[dict[str, object]]:
        buckets: dict[str, list[Position]] = defaultdict(list)
        for position in position_list:
            label = getattr(position, attribute) or "Unspecified"
            buckets[str(label)].append(position)

        output: list[dict[str, object]] = []
        for label, bucket_positions in sorted(
            buckets.items(),
            key=lambda item: sum(_market_value(position) for position in item[1]),
            reverse=True,
        ):
            bucket_value = sum(_market_value(position) for position in bucket_positions)
            top_holdings = sorted(
                bucket_positions,
                key=_market_value,
                reverse=True,
            )[:3]
            output.append(
                {
                    "label": label,
                    "market_value_usd": round(bucket_value, 2),
                    "pct_of_portfolio": round((bucket_value / total_aum * 100.0), 2)
                    if total_aum
                    else 0.0,
                    "position_count": len(bucket_positions),
                    "top_holdings": [
                        {
                            "ticker": position.ticker,
                            "pct": round((_market_value(position) / total_aum * 100.0), 2)
                            if total_aum
                            else 0.0,
                        }
                        for position in top_holdings
                    ],
                }
            )
        return output

    custodian_distribution: list[dict[str, object]] = []
    for bucket in build_dimension("custodian"):
        custodian_distribution.append(
            {
                "label": bucket["label"],
                "market_value_usd": bucket["market_value_usd"],
                "pct_of_portfolio": bucket["pct_of_portfolio"],
                "position_count": bucket["position_count"],
            }
        )

    liquid_value = sum(
        _market_value(position)
        for position in position_list
        if position.asset_class in LIQUID_ASSET_CLASSES
    )
    sorted_positions = sorted(position_list, key=_market_value, reverse=True)
    top_five_value = sum(_market_value(position) for position in sorted_positions[:5])
    hhi = sum(((_market_value(position) / total_aum) ** 2) for position in position_list) if total_aum else 0.0

    return {
        "total_aum_usd": round(total_aum, 2),
        "liquidity_score_pct": round((liquid_value / total_aum * 100.0), 2) if total_aum else 0.0,
        "hhi_concentration": round(hhi, 6),
        "top_five_concentration_pct": round((top_five_value / total_aum * 100.0), 2)
        if total_aum
        else 0.0,
        "asset_class": build_dimension("asset_class"),
        "geo_region": build_dimension("geo_region"),
        "sector": build_dimension("sector"),
        "market_segment": build_dimension("market_segment"),
        "custodian_distribution": custodian_distribution,
    }
