from __future__ import annotations

import json
from collections import defaultdict
from statistics import fmean, pstdev

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models.overlay import AssetFactorExposure, FactorScore, ProxyBasket
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.auth.session import utc_now
from backend.services.overlay.proxy_baskets import load_proxy_baskets
from backend.services.overlay.sentiment_agent import apply_sentiment_modifier, score_factor_sentiment


def normalize_factor_token(value: str | None, default: str = "unspecified") -> str:
    if not value:
        return default
    return value.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def humanize_factor_key(factor_key: str) -> str:
    _, _, tail = factor_key.partition(":")
    tokens = [token.replace("_", " ") for token in tail.split(":") if token]
    return " / ".join(token.title() for token in tokens) or factor_key.title()


def _position_factor_dimensions(position: Position) -> list[tuple[str, str, str, float]]:
    rows: list[tuple[str, str, str, float]] = []
    asset_class = normalize_factor_token(position.factor_asset_class or position.asset_class)
    sector = normalize_factor_token(position.factor_sector or position.sector, default="")
    subsector = normalize_factor_token(position.factor_subsector, default="")
    region = normalize_factor_token(position.factor_region or position.geo_region)
    segment = normalize_factor_token(position.factor_market_segment or position.market_segment)
    rows.append((f"asset_class:{asset_class}", "asset_class", humanize_factor_key(f"asset_class:{asset_class}"), 0.4))
    if sector:
        rows.append((f"sector:{sector}", "sector", humanize_factor_key(f"sector:{sector}"), 0.3))
    if subsector:
        rows.append((f"sector:{sector}:{subsector}", "sector", humanize_factor_key(f"sector:{sector}:{subsector}"), 0.15))
    rows.append((f"region:{region}", "region", humanize_factor_key(f"region:{region}"), 0.15))
    rows.append((f"segment:{segment}", "market_segment", humanize_factor_key(f"segment:{segment}"), 0.15))
    total_weight = sum(weight for _, _, _, weight in rows)
    return [(factor_key, factor_type, label, round(weight / total_weight, 4)) for factor_key, factor_type, label, weight in rows]


def sync_asset_factor_exposures(
    db: Session,
    snapshot: PortfolioSnapshot,
    positions: list[Position],
    *,
    as_of_date,
) -> list[AssetFactorExposure]:
    db.execute(
        delete(AssetFactorExposure).where(
            AssetFactorExposure.workspace_id == snapshot.workspace_id,
            AssetFactorExposure.snapshot_id == snapshot.id,
            AssetFactorExposure.as_of_date == as_of_date,
        )
    )
    exposures: list[AssetFactorExposure] = []
    for position in positions:
        for factor_key, factor_type, _, weight in _position_factor_dimensions(position):
            exposure = AssetFactorExposure(
                workspace_id=snapshot.workspace_id,
                snapshot_id=snapshot.id,
                position_id=position.id,
                factor_key=factor_key,
                factor_type=factor_type,
                weight=weight,
                source="inferred",
                confidence=0.7,
                as_of_date=as_of_date,
            )
            db.add(exposure)
            exposures.append(exposure)
    db.flush()
    return exposures


def _weighted_basket_return_series(
    basket: ProxyBasket,
    price_histories: dict[str, list[dict[str, object]]],
) -> list[float]:
    from backend.services.overlay.proxy_baskets import build_weighted_return_series

    return build_weighted_return_series(price_histories, basket)


def _score_from_z(z_score: float) -> float:
    if z_score <= -2.0:
        return 90.0
    if z_score <= -0.5:
        return 70.0
    if z_score < 0.5:
        return 50.0
    if z_score < 2.0:
        return 30.0
    return 10.0


def _macro_environment_score(macro_payload: dict[str, object]) -> tuple[float, str]:
    vix = float(macro_payload.get("vix", 18.0) or 18.0)
    credit = float(macro_payload.get("ig_spread_bps") or macro_payload.get("hy_spread_bps") or 150.0)
    if vix > 28 or credit > 250:
        return 85.0, "vix"
    if vix >= 18 or credit >= 150:
        return 65.0, "credit_spread_bps" if credit >= 150 else "vix"
    return 35.0, "baseline"


def _commodity_score(factor_key: str, latest_returns: dict[str, float]) -> float:
    if "energy" in factor_key:
        return 60.0 if latest_returns.get("CL=F", 0.0) < 0 else 40.0
    if "real_assets" in factor_key or "real_estate" in factor_key:
        return 55.0 if latest_returns.get("GC=F", 0.0) < 0 else 45.0
    return 50.0


def compute_factor_scores(
    db: Session,
    snapshot: PortfolioSnapshot,
    positions: list[Position],
    *,
    signals: dict[str, object],
    as_of_date,
) -> list[FactorScore]:
    baskets = load_proxy_baskets(db)
    basket_by_factor = {basket.factor_key: basket for basket in baskets}
    factor_catalog: dict[str, tuple[str, str]] = {}
    exposure_weights: dict[str, float] = defaultdict(float)
    total_aum = sum(float(position.market_value_usd or 0.0) for position in positions) or 1.0
    for position in positions:
        position_weight = float(position.market_value_usd or 0.0) / total_aum
        for factor_key, factor_type, label, factor_weight in _position_factor_dimensions(position):
            factor_catalog[factor_key] = (factor_type, label)
            exposure_weights[factor_key] += position_weight * factor_weight

    db.execute(
        delete(FactorScore).where(
            FactorScore.workspace_id == snapshot.workspace_id,
            FactorScore.as_of_date == as_of_date,
        )
    )

    macro_payload = signals["macro"]
    macro_score, macro_driver = _macro_environment_score(macro_payload)
    rows: list[FactorScore] = []
    for factor_key, (factor_type, label) in sorted(factor_catalog.items()):
        basket = basket_by_factor.get(factor_key) or next(
            (
                candidate
                for candidate in baskets
                if candidate.factor_key == factor_key
                or (
                    candidate.asset_class == factor_key.removeprefix("asset_class:")
                    and factor_key.startswith("asset_class:")
                )
            ),
            None,
        )
        series = _weighted_basket_return_series(basket, signals["price_histories"]) if basket else []
        trailing = series[-90:] if len(series) >= 90 else series
        latest = trailing[-1] if trailing else 0.0
        mean_return = fmean(trailing) if trailing else 0.0
        stdev = pstdev(trailing) if len(trailing) > 1 else 0.0
        z_score = 0.0 if not stdev else (latest - mean_return) / stdev
        equity_proxy_score = _score_from_z(z_score)
        commodity_score = _commodity_score(factor_key, signals["latest_returns"])
        base_score = (
            0.50 * equity_proxy_score
            + 0.25 * macro_score
            + 0.15 * commodity_score
            + 0.10 * 50.0
        )
        sentiment_signal = score_factor_sentiment(
            factor_key,
            macro_payload=signals["macro"],
            latest_returns=signals["latest_returns"],
        )
        sentiment_modifier = sentiment_signal.modifier_pct
        score = apply_sentiment_modifier(base_score, sentiment_modifier)
        direction = "stable"
        if z_score <= -0.5:
            direction = "deteriorating"
        elif z_score >= 0.5:
            direction = "improving"
        primary_driver = basket.name if basket is not None else macro_driver
        confidence = min(0.95, max(0.45, 0.55 + exposure_weights[factor_key] / 2.0))
        row = FactorScore(
            workspace_id=snapshot.workspace_id,
            factor_key=factor_key,
            factor_type=factor_type,
            label=label,
            score=round(score, 2),
            direction=direction,
            z_score=round(z_score, 4),
            primary_driver=primary_driver,
            confidence=round(confidence, 4),
            sentiment_modifier=sentiment_modifier,
            signal_payload_json=json.dumps(
                {
                    "exposure_weight": round(exposure_weights[factor_key], 4),
                    "base_score": round(base_score, 2),
                    "macro_score": macro_score,
                    "equity_proxy_score": equity_proxy_score,
                    "commodity_score": commodity_score,
                    "sentiment_modifier_pct": sentiment_modifier,
                    "sentiment_driver": sentiment_signal.driver,
                    "sentiment_confidence": sentiment_signal.confidence,
                },
                sort_keys=True,
            ),
            as_of_date=as_of_date,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows
