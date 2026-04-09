from __future__ import annotations

from dataclasses import dataclass


MAX_SENTIMENT_MODIFIER_PCT = 10.0

NEGATIVE_SECTOR_BIAS = {
    "financials": -4.0,
    "real_estate": -3.0,
    "private_equity": -2.5,
    "consumer_discretionary": -1.5,
}

POSITIVE_SECTOR_BIAS = {
    "technology": 4.0,
    "health_care": 2.0,
    "industrials": 1.5,
    "energy": 1.0,
}


@dataclass(frozen=True)
class SentimentSignal:
    modifier_pct: float
    driver: str
    confidence: float


def clamp_sentiment_modifier(modifier_pct: float) -> float:
    return round(max(-MAX_SENTIMENT_MODIFIER_PCT, min(MAX_SENTIMENT_MODIFIER_PCT, modifier_pct)), 2)


def apply_sentiment_modifier(base_score: float, modifier_pct: float) -> float:
    adjusted = base_score * (1.0 + clamp_sentiment_modifier(modifier_pct) / 100.0)
    return round(max(0.0, min(100.0, adjusted)), 2)


def score_factor_sentiment(
    factor_key: str,
    *,
    macro_payload: dict[str, object],
    latest_returns: dict[str, float],
) -> SentimentSignal:
    if factor_key.startswith("sector:"):
        sector_key = factor_key.split(":", 1)[1]
    elif factor_key.startswith("asset_class:"):
        sector_key = factor_key.split(":", 1)[1]
    else:
        sector_key = ""

    modifier_pct = 0.0
    driver = "neutral_rss_fallback"
    if sector_key in NEGATIVE_SECTOR_BIAS:
        modifier_pct += NEGATIVE_SECTOR_BIAS[sector_key]
        driver = f"sector_bias:{sector_key}"
    if sector_key in POSITIVE_SECTOR_BIAS:
        modifier_pct += POSITIVE_SECTOR_BIAS[sector_key]
        driver = f"sector_bias:{sector_key}"

    vix = float(macro_payload.get("vix", 18.0) or 18.0)
    dxy = float(macro_payload.get("dxy", 100.0) or 100.0)
    oil_return = float(latest_returns.get("CL=F", 0.0) or 0.0)

    if sector_key in {"financials", "real_estate", "private_equity"} and vix >= 18.0:
        modifier_pct -= 2.0
        driver = f"{driver}|macro_risk_off"
    if sector_key in {"technology", "industrials"} and dxy < 102.0:
        modifier_pct += 1.5
        driver = f"{driver}|usd_tailwind"
    if sector_key == "energy" and oil_return > 0:
        modifier_pct += 2.0
        driver = f"{driver}|oil_momentum"

    modifier_pct = clamp_sentiment_modifier(modifier_pct)
    confidence = 0.55 if modifier_pct else 0.35
    return SentimentSignal(modifier_pct=modifier_pct, driver=driver, confidence=confidence)
