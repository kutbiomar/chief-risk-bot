from __future__ import annotations

import json
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.analytics import PriceCache
from backend.models.overlay import FactorScore, ProxyBasket, RiskRegime
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.overlay import ensure_overlay_state
from backend.services.overlay.proxy_baskets import (
    build_weighted_return_series,
    load_proxy_baskets,
    position_uses_proxy_basket,
    select_proxy_basket_for_position,
)


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, int((len(sorted_values) - 1) * p)))
    return sorted_values[index]


def _price_return_series(cache: PriceCache) -> list[float]:
    history = json.loads(cache.history_json)
    closes = [float(point["close_usd"]) for point in history if point.get("close_usd") is not None]
    returns: list[float] = []
    for index in range(1, len(closes)):
        previous = closes[index - 1]
        current = closes[index]
        returns.append((current / previous) - 1.0 if previous else 0.0)
    return returns


def _synthetic_return_series(seed_text: str, lookback_days: int = 252) -> list[float]:
    seed = sum(ord(char) for char in seed_text.upper())
    return [
        (((seed + index * 7) % 17) - 8) / 1800.0
        for index in range(lookback_days)
    ]


def _private_multiplier(position: Position, basket: ProxyBasket | None, factor_scores: dict[str, FactorScore], regime: RiskRegime) -> float:
    scalar = float(basket.illiquidity_scalar if basket is not None else 1.25)
    dominant_score = 50.0
    if basket is not None:
        score = factor_scores.get(basket.factor_key)
        if score is not None:
            dominant_score = float(score.score)
    if dominant_score > 70:
        scalar *= 1.0 + ((dominant_score - 70.0) / 100.0)
    if regime.regime == "stress":
        scalar *= 1.1
    elif regime.regime == "crisis":
        scalar *= 1.25
    return scalar


def compute_overlay_var_for_snapshot(db: Session, snapshot: PortfolioSnapshot) -> dict[str, object]:
    overlay_state = ensure_overlay_state(db, snapshot)
    positions: list[Position] = overlay_state["positions"]
    price_histories = overlay_state["signals"]["price_histories"]
    factor_scores = {score.factor_key: score for score in overlay_state["factor_scores"]}
    regime: RiskRegime = overlay_state["regime"]
    baskets = load_proxy_baskets(db)

    scenario_losses: list[tuple[int, float]] = []
    contributions: dict[str, float] = {}
    contribution_meta: dict[str, dict[str, str]] = {}
    total_aum = float(snapshot.total_aum_usd or 0.0)
    histories: dict[str, list[float]] = {}
    modeled_value_usd = 0.0

    for position in positions:
        if position_uses_proxy_basket(position):
            basket = select_proxy_basket_for_position(position, baskets)
            if basket is None:
                continue
            basket_returns = build_weighted_return_series(price_histories, basket)
            if not basket_returns:
                basket_returns = _synthetic_return_series(f"{position.ticker}:{basket.basket_key}")
            multiplier = _private_multiplier(position, basket, factor_scores, regime)
            histories[position.id] = [daily_return * multiplier for daily_return in basket_returns]
            contribution_meta[position.id] = {
                "method": "Estimated — proxy basket method",
                "proxy_basket": basket.name,
            }
        else:
            cache = db.get(PriceCache, position.ticker)
            if cache is None:
                cache = db.scalar(select(PriceCache).where(PriceCache.ticker == position.ticker))
            if cache is None:
                price_returns = _synthetic_return_series(position.ticker)
            else:
                price_returns = _price_return_series(cache)
            if not price_returns:
                price_returns = _synthetic_return_series(position.ticker)
            histories[position.id] = price_returns
            contribution_meta[position.id] = {
                "method": "historical_scenario_additive",
                "proxy_basket": "",
            }
        modeled_value_usd += float(position.market_value_usd or 0.0)

    effective_lookback_days = min((len(series) for series in histories.values()), default=0)
    for scenario_index in range(effective_lookback_days):
        scenario_loss = 0.0
        for position in positions:
            history = histories.get(position.id)
            if not history or scenario_index >= len(history):
                continue
            scenario_return = history[scenario_index]
            loss = float(position.market_value_usd or 0.0) * scenario_return
            scenario_loss += loss
            contributions[position.id] = contributions.get(position.id, 0.0) + loss
        scenario_losses.append((scenario_index, scenario_loss))

    ordered_losses = sorted(loss for _, loss in scenario_losses)
    var_95 = abs(_percentile(ordered_losses, 0.05))
    var_99 = abs(_percentile(ordered_losses, 0.01))
    cvar_95 = abs(mean(ordered_losses[: max(1, int(len(ordered_losses) * 0.05))])) if ordered_losses else 0.0
    cvar_99 = abs(mean(ordered_losses[: max(1, int(len(ordered_losses) * 0.01))])) if ordered_losses else 0.0
    worst_index, worst_loss = min(scenario_losses, key=lambda item: item[1]) if scenario_losses else (0, 0.0)
    contribution_sum = abs(sum(contributions.values()))
    contribution_rows = []
    for position in positions:
        aggregate_loss = contributions.get(position.id, 0.0)
        meta = contribution_meta.get(position.id, {"method": "historical_scenario_additive", "proxy_basket": ""})
        contribution_rows.append(
            {
                "ticker": position.ticker,
                "security_id": position.security_id,
                "contribution_pct": round((abs(aggregate_loss) / contribution_sum * 100.0), 2) if contribution_sum else 0.0,
                "contribution_usd": round(abs(aggregate_loss), 2),
                "method": meta["method"],
            }
        )

    return {
        "var_1d_95": round(var_95, 2),
        "var_1d_99": round(var_99, 2),
        "cvar_1d_95": round(cvar_95, 2),
        "cvar_1d_99": round(cvar_99, 2),
        "worst_index": worst_index,
        "worst_loss": round(abs(worst_loss), 2),
        "effective_lookback_days": effective_lookback_days,
        "model_coverage_pct": round((modeled_value_usd / total_aum * 100.0), 2) if total_aum else 0.0,
        "unmodeled_value_usd": round(max(0.0, total_aum - modeled_value_usd), 2),
        "position_contributions": contribution_rows,
        "assumptions": {
            "coverage_warning": None if total_aum else "empty portfolio",
            "fx_pairs_used": ["USDUSD"],
            "tickers_modeled": sorted({position.ticker for position in positions}),
            "overlay_regime": regime.regime,
            "overlay_trigger": regime.trigger_signal,
        },
    }
