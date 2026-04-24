from __future__ import annotations

from backend.models.analytics import VarResult
from backend.models.overlay import RiskRegime


def compute_overlay_alerts(
    triangulation: dict[str, object],
    regime: RiskRegime,
    var_result: VarResult | None,
) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    factors = triangulation["factors"]

    for factor in factors:
        if factor["risk_score"] > 85 and factor["exposure_pct"] > 5:
            alerts.append(
                {
                    "kind": "overlay",
                    "severity": "priority",
                    "headline": f"{factor['label']} risk is red",
                    "description": f"{factor['label']} scores {factor['risk_score']:.0f} with {factor['exposure_pct']:.1f}% AUM exposure.",
                    "rule": "overlay_factor_red",
                    "value": factor["risk_score"],
                    "threshold": 85.0,
                }
            )
        elif factor["risk_score"] > 75 and factor["exposure_pct"] > 10:
            alerts.append(
                {
                    "kind": "overlay",
                    "severity": "elevated",
                    "headline": f"{factor['label']} risk is elevated",
                    "description": f"{factor['label']} scores {factor['risk_score']:.0f} with {factor['exposure_pct']:.1f}% AUM exposure.",
                    "rule": "overlay_factor_amber",
                    "value": factor["risk_score"],
                    "threshold": 75.0,
                }
            )

    if regime.regime in {"stress", "crisis"}:
        alerts.append(
            {
                "kind": "overlay",
                "severity": "priority" if regime.regime == "crisis" else "elevated",
                "headline": f"Risk regime is {regime.regime}",
                "description": regime.methodology_note,
                "rule": "overlay_regime_change",
                "value": regime.vix_level,
                "threshold": 18.0,
            }
        )

    if var_result is not None:
        top_factor = next(iter(triangulation["top_risk_contributors"]), None)
        if top_factor and top_factor["weighted_risk"] > 0 and triangulation["composite_score"] > 0:
            total_weighted_risk = sum(item["weighted_risk"] for item in triangulation["factors"]) or 1.0
            concentration_pct = top_factor["weighted_risk"] / total_weighted_risk * 100.0
            if concentration_pct > 50.0:
                alerts.append(
                    {
                        "kind": "overlay",
                        "severity": "elevated",
                        "headline": f"{top_factor['label']} dominates portfolio risk",
                        "description": f"{top_factor['label']} contributes {concentration_pct:.1f}% of weighted overlay risk.",
                        "rule": "overlay_factor_concentration",
                        "value": concentration_pct,
                        "threshold": 50.0,
                    }
                )
    return alerts
