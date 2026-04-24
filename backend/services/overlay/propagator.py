from __future__ import annotations

from collections import defaultdict

from backend.models.overlay import AssetFactorExposure, FactorScore
from backend.models.portfolio import Position


def build_aum_triangulation(
    positions: list[Position],
    exposures: list[AssetFactorExposure],
    factor_scores: list[FactorScore],
) -> dict[str, object]:
    total_aum = sum(float(position.market_value_usd or 0.0) for position in positions)
    positions_by_id = {position.id: position for position in positions}
    scores_by_key = {row.factor_key: row for row in factor_scores}
    factor_totals: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "aum_exposed_usd": 0.0,
            "weighted_risk": 0.0,
            "positions": [],
        }
    )

    for exposure in exposures:
        position = positions_by_id.get(exposure.position_id)
        score = scores_by_key.get(exposure.factor_key)
        if position is None or score is None:
            continue
        exposure_value = float(position.market_value_usd or 0.0) * float(exposure.weight)
        bucket = factor_totals[exposure.factor_key]
        bucket["aum_exposed_usd"] += exposure_value
        bucket["weighted_risk"] += exposure_value * float(score.score)
        bucket["positions"].append(
            {
                "ticker": position.ticker,
                "name": position.name or position.ticker,
                "aum_exposed_usd": round(exposure_value, 2),
            }
        )

    factor_rows: list[dict[str, object]] = []
    for factor_key, bucket in factor_totals.items():
        score = scores_by_key[factor_key]
        aum_exposed_usd = round(float(bucket["aum_exposed_usd"]), 2)
        exposure_pct = round((aum_exposed_usd / total_aum * 100.0), 2) if total_aum else 0.0
        weighted_risk = round(float(bucket["weighted_risk"]), 2)
        factor_rows.append(
            {
                "factor_key": factor_key,
                "label": score.label,
                "factor_type": score.factor_type,
                "risk_score": score.score,
                "direction": score.direction,
                "aum_exposed_usd": aum_exposed_usd,
                "exposure_pct": exposure_pct,
                "weighted_risk": weighted_risk,
                "top_positions": sorted(bucket["positions"], key=lambda item: item["aum_exposed_usd"], reverse=True)[:3],
            }
        )

    factor_rows.sort(key=lambda item: (item["weighted_risk"], item["aum_exposed_usd"]), reverse=True)
    composite_score = round(
        sum(item["weighted_risk"] for item in factor_rows) / total_aum,
        2,
    ) if total_aum else 0.0
    aum_at_risk_usd = round(
        sum(item["aum_exposed_usd"] for item in factor_rows if item["risk_score"] >= 70.0),
        2,
    )
    return {
        "composite_score": composite_score,
        "aum_at_risk_usd": aum_at_risk_usd,
        "factors": factor_rows,
        "top_risk_contributors": factor_rows[:5],
    }
