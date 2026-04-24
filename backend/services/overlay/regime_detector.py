from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DetectedRegime:
    regime: str
    trigger_signal: str
    vix_level: float
    credit_spread_bps: float
    methodology_note: str


def detect_risk_regime(macro_payload: dict[str, object]) -> DetectedRegime:
    vix = float(macro_payload.get("vix", 18.0) or 18.0)
    credit_spread = float(
        macro_payload.get("ig_spread_bps")
        or macro_payload.get("credit_spread_bps")
        or macro_payload.get("hy_spread_bps")
        or 150.0
    )
    if vix > 28 or credit_spread > 250:
        return DetectedRegime(
            regime="crisis",
            trigger_signal="vix" if vix > 28 else "credit_spread_bps",
            vix_level=vix,
            credit_spread_bps=credit_spread,
            methodology_note="Crisis regime detected. Private proxy volatility widened and scenario floor applied.",
        )
    if vix >= 18 or credit_spread >= 150:
        return DetectedRegime(
            regime="stress",
            trigger_signal="vix" if vix >= 18 else "credit_spread_bps",
            vix_level=vix,
            credit_spread_bps=credit_spread,
            methodology_note="Stress regime detected. Recent market stress is elevated.",
        )
    return DetectedRegime(
        regime="normal",
        trigger_signal="baseline",
        vix_level=vix,
        credit_spread_bps=credit_spread,
        methodology_note="Normal regime detected. Overlay uses baseline volatility assumptions.",
    )
