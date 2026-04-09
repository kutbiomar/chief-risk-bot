from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.overlay import ProxyBasket, StressScenario
from backend.models.portfolio import Position


PRIVATE_ASSET_CLASSES = {
    "private_equity",
    "venture_capital",
    "private_credit",
    "real_estate",
    "infrastructure",
    "alternative",
    "real_assets",
}

DEFAULT_PROXY_BASKETS = [
    {
        "basket_key": "private_equity_buyout",
        "factor_key": "asset_class:private_equity",
        "name": "Private Equity Buyout",
        "asset_class": "private_equity",
        "sector": None,
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["IWM", "SPY", "HYG"]',
        "proxy_weights_json": "[0.55, 0.25, 0.20]",
        "illiquidity_scalar": 1.3,
        "notes": "Broad US buyout proxy basket",
        "is_active": True,
    },
    {
        "basket_key": "venture_capital_growth",
        "factor_key": "asset_class:venture_capital",
        "name": "Venture Capital Growth",
        "asset_class": "venture_capital",
        "sector": "technology",
        "region": None,
        "market_segment": "micro_cap",
        "proxy_tickers_json": '["QQQ", "SOXX", "ARKK"]',
        "proxy_weights_json": "[0.5, 0.25, 0.25]",
        "illiquidity_scalar": 1.5,
        "notes": "VC growth proxy basket",
        "is_active": True,
    },
    {
        "basket_key": "private_credit_direct_lending",
        "factor_key": "asset_class:private_credit",
        "name": "Private Credit Direct Lending",
        "asset_class": "private_credit",
        "sector": "financials",
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["BKLN", "HYG", "LQD"]',
        "proxy_weights_json": "[0.4, 0.35, 0.25]",
        "illiquidity_scalar": 1.2,
        "notes": "Direct lending proxy basket",
        "is_active": True,
    },
    {
        "basket_key": "real_estate_core",
        "factor_key": "asset_class:real_estate",
        "name": "Real Estate Core",
        "asset_class": "real_estate",
        "sector": "real_assets",
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["VNQ", "IYR", "XLRE"]',
        "proxy_weights_json": "[0.5, 0.25, 0.25]",
        "illiquidity_scalar": 1.3,
        "notes": "Core real estate proxy basket",
        "is_active": True,
    },
    {
        "basket_key": "infrastructure_energy",
        "factor_key": "asset_class:infrastructure",
        "name": "Infrastructure Energy",
        "asset_class": "infrastructure",
        "sector": "energy",
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["XLE", "AMLP", "BND"]',
        "proxy_weights_json": "[0.45, 0.35, 0.20]",
        "illiquidity_scalar": 1.1,
        "notes": "Energy infrastructure proxy basket",
        "is_active": True,
    },
    {
        "basket_key": "public_equity_core",
        "factor_key": "asset_class:public_equity",
        "name": "Public Equity Core",
        "asset_class": "public_equity",
        "sector": None,
        "region": None,
        "market_segment": "large_cap",
        "proxy_tickers_json": '["SPY", "QQQ", "IWM"]',
        "proxy_weights_json": "[0.5, 0.3, 0.2]",
        "illiquidity_scalar": 1.0,
        "notes": "Core public equity basket",
        "is_active": True,
    },
    {
        "basket_key": "fixed_income_core",
        "factor_key": "asset_class:fixed_income",
        "name": "Fixed Income Core",
        "asset_class": "fixed_income",
        "sector": None,
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["AGG", "LQD", "IEF"]',
        "proxy_weights_json": "[0.45, 0.3, 0.25]",
        "illiquidity_scalar": 1.0,
        "notes": "Core fixed income basket",
        "is_active": True,
    },
    {
        "basket_key": "energy_renewables",
        "factor_key": "sector:energy",
        "name": "Energy Renewables",
        "asset_class": "private_equity",
        "sector": "energy",
        "region": None,
        "market_segment": None,
        "proxy_tickers_json": '["XLE", "TAN", "FAN"]',
        "proxy_weights_json": "[0.35, 0.4, 0.25]",
        "illiquidity_scalar": 1.25,
        "notes": "Energy and renewables subsector basket",
        "is_active": True,
    },
]

DEFAULT_STRESS_SCENARIOS = [
    {
        "scenario_key": "gfc_2008",
        "name": "2008 GFC",
        "description": "Global credit seizure and equity collapse",
        "severity": "red",
        "sort_order": 10,
        "shock_json": '{"equity": -0.5, "credit_spread_bps": 500, "real_estate": -0.4}',
        "is_active": True,
    },
    {
        "scenario_key": "covid_2020",
        "name": "COVID Crash",
        "description": "Fast shock to growth and consumer demand",
        "severity": "red",
        "sort_order": 20,
        "shock_json": '{"equity": -0.35, "consumer": -0.6, "healthcare": 0.1}',
        "is_active": True,
    },
    {
        "scenario_key": "rate_shock_2022",
        "name": "2022 Rate Shock",
        "description": "Rates higher for longer with growth compression",
        "severity": "amber",
        "sort_order": 30,
        "shock_json": '{"ust10y_bps": 300, "technology": -0.5, "venture_capital": -0.6}',
        "is_active": True,
    },
    {
        "scenario_key": "renewables_policy_reversal",
        "name": "Renewables Policy Reversal",
        "description": "Policy rollback hits transition assets",
        "severity": "amber",
        "sort_order": 40,
        "shock_json": '{"renewables": -0.4, "infrastructure": -0.2}',
        "is_active": True,
    },
    {
        "scenario_key": "energy_price_collapse",
        "name": "Energy Price Collapse",
        "description": "Oil and gas demand shock",
        "severity": "amber",
        "sort_order": 50,
        "shock_json": '{"wti": -0.6, "energy": -0.45, "midstream": -0.25}',
        "is_active": True,
    },
    {
        "scenario_key": "em_contagion",
        "name": "EM Contagion",
        "description": "Broad EM selloff and FX drawdown",
        "severity": "amber",
        "sort_order": 60,
        "shock_json": '{"em_equity": -0.4, "em_fx": -0.25}',
        "is_active": True,
    },
]


def ensure_overlay_seed_data(db: Session) -> None:
    if db.scalar(select(ProxyBasket.id).limit(1)) is None:
        for row in DEFAULT_PROXY_BASKETS:
            db.add(ProxyBasket(**row))
    if db.scalar(select(StressScenario.id).limit(1)) is None:
        for row in DEFAULT_STRESS_SCENARIOS:
            db.add(StressScenario(**row))
    db.flush()


def load_proxy_baskets(db: Session) -> list[ProxyBasket]:
    ensure_overlay_seed_data(db)
    return db.scalars(select(ProxyBasket).where(ProxyBasket.is_active.is_(True))).all()


def select_proxy_basket_for_position(position: Position, baskets: list[ProxyBasket]) -> ProxyBasket | None:
    exact_matches: list[ProxyBasket] = []
    fallback_matches: list[ProxyBasket] = []
    position_sector = (position.factor_sector or position.sector or "").strip().lower()
    position_asset_class = (position.factor_asset_class or position.asset_class or "").strip().lower()
    position_segment = (position.factor_market_segment or position.market_segment or "").strip().lower()

    for basket in baskets:
        basket_asset_class = (basket.asset_class or "").strip().lower()
        basket_sector = (basket.sector or "").strip().lower()
        basket_segment = (basket.market_segment or "").strip().lower()
        if basket_asset_class == position_asset_class:
            fallback_matches.append(basket)
            sector_ok = not basket_sector or basket_sector == position_sector
            segment_ok = not basket_segment or basket_segment == position_segment
            if sector_ok and segment_ok:
                exact_matches.append(basket)

    if exact_matches:
        return exact_matches[0]
    if fallback_matches:
        return fallback_matches[0]
    return next((basket for basket in baskets if basket.factor_key == f"asset_class:{position_asset_class}"), None)


def build_weighted_return_series(
    price_histories: dict[str, list[dict[str, object]]],
    basket: ProxyBasket,
) -> list[float]:
    tickers = json.loads(basket.proxy_tickers_json)
    weights = json.loads(basket.proxy_weights_json)
    weighted_returns: list[float] = []
    aligned_histories: list[list[float]] = []
    for ticker in tickers:
        history = price_histories.get(ticker, [])
        closes = [float(point["close_usd"]) for point in history if point.get("close_usd") is not None]
        returns: list[float] = []
        for index in range(1, len(closes)):
            previous = closes[index - 1]
            current = closes[index]
            returns.append((current / previous) - 1.0 if previous else 0.0)
        aligned_histories.append(returns)
    if not aligned_histories:
        return weighted_returns
    series_length = min(len(series) for series in aligned_histories)
    for index in range(series_length):
        basket_return = 0.0
        for series, weight in zip(aligned_histories, weights):
            basket_return += float(weight) * float(series[index])
        weighted_returns.append(basket_return)
    return weighted_returns


def position_uses_proxy_basket(position: Position) -> bool:
    return (position.factor_asset_class or position.asset_class or "").strip().lower() in PRIVATE_ASSET_CLASSES
