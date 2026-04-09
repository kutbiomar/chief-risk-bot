from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.overlay import StressScenario


FACTOR_SHOCK_MAP = {
    "equity": {"asset_class:public_equity", "asset_class:private_equity", "asset_class:venture_capital"},
    "technology": {"sector:technology", "asset_class:venture_capital"},
    "venture_capital": {"asset_class:venture_capital"},
    "credit_spread_bps": {"asset_class:fixed_income", "asset_class:private_credit"},
    "real_estate": {"asset_class:real_estate", "asset_class:infrastructure"},
    "renewables": {"sector:energy", "asset_class:infrastructure"},
    "infrastructure": {"asset_class:infrastructure"},
    "energy": {"sector:energy", "asset_class:infrastructure", "asset_class:private_equity"},
    "midstream": {"sector:energy"},
    "consumer": {"sector:consumer"},
    "healthcare": {"sector:healthcare"},
    "em_equity": {"region:latin_america", "region:china", "region:india", "region:southeast_asia"},
    "em_fx": {"region:latin_america", "region:china", "region:india", "region:southeast_asia"},
}


def compute_stress_scenarios(db: Session, triangulation: dict[str, object]) -> list[dict[str, object]]:
    scenarios = db.scalars(
        select(StressScenario)
        .where(StressScenario.is_active.is_(True))
        .order_by(StressScenario.sort_order.asc())
    ).all()
    factors = triangulation["factors"]
    factor_lookup = {row["factor_key"]: row for row in factors}
    results: list[dict[str, object]] = []

    for scenario in scenarios:
        shock_payload = json.loads(scenario.shock_json)
        total_impact = 0.0
        drivers: list[dict[str, object]] = []
        for shock_key, shock_value in shock_payload.items():
            matched_keys = FACTOR_SHOCK_MAP.get(shock_key, {shock_key})
            for factor_key in matched_keys:
                factor = factor_lookup.get(factor_key)
                if factor is None:
                    continue
                shock = float(shock_value)
                normalized = shock if abs(shock) <= 1 else shock / 1000.0
                impact = float(factor["aum_exposed_usd"]) * normalized
                total_impact += impact
                drivers.append(
                    {
                        "factor_key": factor["factor_key"],
                        "label": factor["label"],
                        "impact_usd": round(impact, 2),
                    }
                )

        drivers.sort(key=lambda item: abs(item["impact_usd"]), reverse=True)
        results.append(
            {
                "scenario_key": scenario.scenario_key,
                "name": scenario.name,
                "description": scenario.description,
                "severity": scenario.severity,
                "estimated_impact_usd": round(total_impact, 2),
                "estimated_impact_pct": round(
                    abs(total_impact) / max(float(sum(row["aum_exposed_usd"] for row in factors)), 1.0) * 100.0,
                    2,
                ),
                "top_drivers": drivers[:3],
            }
        )
    return results
