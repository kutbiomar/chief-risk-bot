from __future__ import annotations

import json
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.analytics import MacroCache, PriceCache
from backend.models.overlay import ProxyBasket
from backend.services.auth.session import utc_now

logger = logging.getLogger(__name__)


def _ticker_seed(ticker: str) -> int:
    return sum(ord(char) for char in ticker.upper())


def _generate_return_series(ticker: str, lookback_days: int = 252) -> list[float]:
    seed = _ticker_seed(ticker)
    series: list[float] = []
    for index in range(lookback_days):
        base = ((seed % 17) - 8) / 1000.0
        cycle = ((index % 19) - 9) / 1700.0
        shock = (((seed * 3 + index * 11) % 13) - 6) / 2200.0
        series.append(round(base + cycle + shock, 6))
    return series


def _build_price_cache_deterministic(ticker: str, lookback_days: int = 252) -> PriceCache:
    now = utc_now()
    price_usd = 50.0 + (_ticker_seed(ticker) % 120)
    series = _generate_return_series(ticker, lookback_days)
    history = []
    close_usd = price_usd
    for offset, daily_return in enumerate(reversed(series)):
        close_usd = close_usd / (1.0 + daily_return) if (1.0 + daily_return) else close_usd
        history.append(
            {
                "date": (now.date() - timedelta(days=offset + 1)).isoformat(),
                "close_local": round(close_usd, 4),
                "fx_to_usd": 1.0,
                "close_usd": round(close_usd, 4),
            }
        )
    return PriceCache(
        ticker=ticker,
        currency="USD",
        price_local=round(price_usd, 4),
        price_usd=round(price_usd, 4),
        daily_return_local=series[-1],
        daily_return_usd=series[-1],
        weekly_return_usd=round(sum(series[-5:]), 6),
        history_json=json.dumps(list(reversed(history)), sort_keys=True),
        fetched_at=now,
        ttl_hours=4,
    )


def _fetch_price_cache_yfinance(ticker: str, lookback_days: int = 252) -> PriceCache | None:
    try:
        import yfinance as yf

        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=f"{lookback_days + 10}d")
        if hist.empty or len(hist) < 5:
            return None
        closes = hist["Close"].dropna().tail(lookback_days)
        if closes.empty:
            return None
        returns = closes.pct_change().dropna()
        now = utc_now()
        history = [
            {
                "date": idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10],
                "close_local": round(float(price), 4),
                "fx_to_usd": 1.0,
                "close_usd": round(float(price), 4),
            }
            for idx, price in zip(closes.index, closes.values)
        ]
        return PriceCache(
            ticker=ticker,
            currency="USD",
            price_local=round(float(closes.iloc[-1]), 4),
            price_usd=round(float(closes.iloc[-1]), 4),
            daily_return_local=round(float(returns.iloc[-1]) if len(returns) else 0.0, 6),
            daily_return_usd=round(float(returns.iloc[-1]) if len(returns) else 0.0, 6),
            weekly_return_usd=round(float(returns.iloc[-5:].sum()) if len(returns) >= 5 else 0.0, 6),
            history_json=json.dumps(history, sort_keys=True),
            fetched_at=now,
            ttl_hours=4,
        )
    except Exception as exc:
        logger.warning("overlay yfinance fetch failed for %s: %s", ticker, exc)
        return None


def _fallback_macro_payload() -> dict[str, float]:
    return {
        "vix": 18.4,
        "ust10y": 4.18,
        "dxy": 103.2,
        "ig_spread_bps": 145.0,
        "hy_spread_bps": 365.0,
        "wti": 78.0,
        "gold": 2240.0,
        "copper": 4.15,
    }


def _load_macro_payload(db: Session, workspace_id: str) -> dict[str, float]:
    macro = db.scalar(
        select(MacroCache)
        .where(MacroCache.workspace_id == workspace_id)
        .order_by(MacroCache.fetched_at.desc())
    )
    if macro is None:
        payload = _fallback_macro_payload()
        db.add(MacroCache(workspace_id=workspace_id, payload_json=json.dumps(payload, sort_keys=True), fetched_at=utc_now()))
        db.flush()
        return payload
    payload = json.loads(macro.payload_json)
    for key, value in _fallback_macro_payload().items():
        payload.setdefault(key, value)
    return payload


def _ensure_price_cache(db: Session, ticker: str) -> PriceCache:
    existing = db.get(PriceCache, ticker)
    if existing is not None:
        return existing
    cache_entry = _build_price_cache_deterministic(ticker)
    db.merge(cache_entry)
    db.flush()
    return db.get(PriceCache, ticker) or cache_entry


def collect_overlay_signals(db: Session, workspace_id: str) -> dict[str, object]:
    baskets = db.scalars(select(ProxyBasket).where(ProxyBasket.is_active.is_(True))).all()
    proxy_tickers: set[str] = set()
    for basket in baskets:
        proxy_tickers.update(json.loads(basket.proxy_tickers_json))
    price_histories: dict[str, list[dict[str, object]]] = {}
    latest_returns: dict[str, float] = {}
    for ticker in sorted(proxy_tickers):
        cache_entry = _ensure_price_cache(db, ticker)
        history = json.loads(cache_entry.history_json)
        price_histories[ticker] = history
        latest_returns[ticker] = float(cache_entry.daily_return_usd)
    macro_payload = _load_macro_payload(db, workspace_id)
    return {
        "as_of_date": utc_now().date(),
        "macro": macro_payload,
        "price_histories": price_histories,
        "latest_returns": latest_returns,
    }
