from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.analytics import FxCache, MacroCache, PriceCache
from backend.models.portfolio import Position
from backend.services.auth.session import ensure_utc, utc_now

logger = logging.getLogger(__name__)


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _load_price_cache_map(db: Session, tickers: set[str]) -> dict[str, PriceCache]:
    if not tickers:
        return {}
    rows = db.scalars(select(PriceCache).where(PriceCache.ticker.in_(sorted(tickers)))).all()
    return {row.ticker: row for row in rows}


def _is_cache_stale(fetched_at: datetime | None, ttl_hours: int | None) -> bool:
    if fetched_at is None:
        return True
    return ensure_utc(fetched_at) <= utc_now() - timedelta(hours=max(ttl_hours or CACHE_TTL_HOURS, 1))

# Macro series: {key_in_payload: FRED series id}
FRED_SERIES = {
    "vix": "VIXCLS",
    "ust10y": "DGS10",
    "cpi_yoy": "CPIAUCSL",
    "dxy": "DTWEXBGS",
}

CACHE_TTL_HOURS: int = 4  # shared TTL for price, FX, and macro caches

# FX pairs to fetch: base_currency -> yfinance symbol
FX_PAIRS: dict[str, str] = {
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "JPY": "JPYUSD=X",
    "CHF": "CHFUSD=X",
    "CAD": "CADUSD=X",
    "AUD": "AUDUSD=X",
}


# ---------------------------------------------------------------------------
# Deterministic fallback (used when live data unavailable)
# ---------------------------------------------------------------------------

def _ticker_seed(ticker: str) -> int:
    return sum(ord(char) for char in ticker.upper())


def _generate_return_series(ticker: str, lookback_days: int = 252) -> list[float]:
    seed = _ticker_seed(ticker)
    series: list[float] = []
    for index in range(lookback_days):
        base = ((seed % 17) - 8) / 1000.0
        cycle = ((index % 21) - 10) / 1500.0
        shock = (((seed + index * 7) % 11) - 5) / 2000.0
        series.append(round(base + cycle + shock, 6))
    return series


def _build_price_cache_deterministic(position: Position, lookback_days: int = 252) -> PriceCache:
    now = utc_now()
    price_usd = float(
        position.price_usd
        or position.price_local
        or (position.market_value_usd or 0.0) / max(position.quantity, 1.0)
    )
    series = _generate_return_series(position.ticker, lookback_days=lookback_days)
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
        ticker=position.ticker,
        currency=position.position_currency,
        price_local=round(float(position.price_local or price_usd), 4),
        price_usd=round(price_usd, 4),
        daily_return_local=series[-1],
        daily_return_usd=series[-1],
        weekly_return_usd=round(sum(series[-5:]), 6),
        history_json=json.dumps(list(reversed(history)), sort_keys=True),
        fetched_at=now,
        ttl_hours=CACHE_TTL_HOURS,
    )


# ---------------------------------------------------------------------------
# Live yfinance price fetch
# ---------------------------------------------------------------------------

def _fetch_price_cache_yfinance(position: Position, lookback_days: int = 252) -> PriceCache | None:
    if _is_test_runtime():
        return None
    try:
        import yfinance as yf

        ticker_obj = yf.Ticker(position.ticker)
        hist = ticker_obj.history(period=f"{lookback_days + 10}d", timeout=5)
        if hist.empty or len(hist) < 5:
            return None

        hist = hist.tail(lookback_days)
        closes = hist["Close"].dropna()
        if closes.empty:
            return None

        returns = closes.pct_change().dropna()
        price_usd = float(closes.iloc[-1])
        daily_return = float(returns.iloc[-1]) if len(returns) > 0 else 0.0
        weekly_return = float(returns.iloc[-5:].sum()) if len(returns) >= 5 else daily_return
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
            ticker=position.ticker,
            currency=position.position_currency,
            price_local=round(price_usd, 4),
            price_usd=round(price_usd, 4),
            daily_return_local=round(daily_return, 6),
            daily_return_usd=round(daily_return, 6),
            weekly_return_usd=round(weekly_return, 6),
            history_json=json.dumps(history, sort_keys=True),
            fetched_at=now,
            ttl_hours=CACHE_TTL_HOURS,
        )
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", position.ticker, exc)
        return None


# ---------------------------------------------------------------------------
# Live FX rates via yfinance
# ---------------------------------------------------------------------------

def _fetch_fx_cache_yfinance(base_currency: str, yf_symbol: str) -> FxCache | None:
    if _is_test_runtime():
        return None
    try:
        import yfinance as yf

        ticker_obj = yf.Ticker(yf_symbol)
        hist = ticker_obj.history(period="252d", timeout=5)
        if hist.empty or len(hist) < 5:
            return None

        closes = hist["Close"].dropna()
        spot_rate = float(closes.iloc[-1])
        now = utc_now()

        history = [
            {
                "date": idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10],
                "rate": round(float(rate), 6),
            }
            for idx, rate in zip(closes.index, closes.values)
        ]

        pair = f"{base_currency}USD"
        return FxCache(
            pair=pair,
            base_currency=base_currency,
            quote_currency="USD",
            spot_rate=round(spot_rate, 6),
            history_json=json.dumps(history, sort_keys=True),
            fetched_at=now,
            ttl_hours=CACHE_TTL_HOURS,
        )
    except Exception as exc:
        logger.warning("yfinance FX fetch failed for %s: %s", yf_symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Live FRED macro fetch
# ---------------------------------------------------------------------------

def _fetch_macro_payload_fred(workspace_id: str) -> dict[str, object] | None:
    if _is_test_runtime():
        return None
    settings = get_settings()
    if not settings.fred_api_key:
        logger.warning("FRED_API_KEY not set — skipping FRED macro fetch")
        return None
    try:
        from fredapi import Fred

        fred = Fred(api_key=settings.fred_api_key)
        payload: dict[str, object] = {}
        for key, series_id in FRED_SERIES.items():
            try:
                series = fred.get_series(series_id, observation_start="2020-01-01")
                if series is not None and not series.empty:
                    latest = float(series.dropna().iloc[-1])
                    payload[key] = round(latest, 4)
            except Exception as exc:
                logger.warning("FRED series %s failed: %s", series_id, exc)

        # Also try SPX via yfinance (FRED SP500 series is weekly)
        try:
            import yfinance as yf

            spx = yf.Ticker("^GSPC").history(period="5d", timeout=5)
            if not spx.empty:
                payload["spx"] = round(float(spx["Close"].dropna().iloc[-1]), 2)
        except Exception as exc:
            logger.warning("SPX fetch failed: %s", exc)

        return payload if payload else None
    except Exception as exc:
        logger.warning("FRED macro fetch failed: %s", exc)
        return None


def _fallback_macro_payload() -> dict[str, object]:
    return {
        "vix": 18.4,
        "move": 102.0,
        "ust10y": 4.18,
        "dxy": 103.2,
        "hy_spread_bps": 365,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def ensure_enrichment_for_positions(
    db: Session, workspace_id: str, positions: list[Position]
) -> dict[str, object]:
    now = utc_now()
    cached_tickers: set[str] = set()
    modeled_value = 0.0
    existing_prices = _load_price_cache_map(db, {position.ticker for position in positions})

    for position in positions:
        existing = existing_prices.get(position.ticker)
        if existing is None or _is_cache_stale(existing.fetched_at, existing.ttl_hours):
            cache_entry = _fetch_price_cache_yfinance(position)
            if cache_entry is None:
                logger.info("No yfinance data for %s — using deterministic fallback", position.ticker)
                cache_entry = _build_price_cache_deterministic(position)
            db.merge(cache_entry)
            existing_prices[position.ticker] = cache_entry
        cached_tickers.add(position.ticker)
        modeled_value += float(position.market_value_usd or 0.0)

    # FX: always ensure USD identity pair
    usd_pair = db.get(FxCache, "USDUSD")
    if usd_pair is None or _is_cache_stale(usd_pair.fetched_at, usd_pair.ttl_hours):
        db.merge(
            FxCache(
                pair="USDUSD",
                base_currency="USD",
                quote_currency="USD",
                spot_rate=1.0,
                history_json=json.dumps(
                    [{"date": (now.date() - timedelta(days=i)).isoformat(), "rate": 1.0} for i in range(252)],
                    sort_keys=True,
                ),
                fetched_at=now,
                ttl_hours=CACHE_TTL_HOURS,
            )
        )

    # FX: fetch non-USD pairs for currencies in the portfolio
    currencies_in_portfolio = {
        pos.position_currency for pos in positions if pos.position_currency and pos.position_currency != "USD"
    }
    for currency in currencies_in_portfolio:
        pair = f"{currency}USD"
        existing_fx = db.get(FxCache, pair)
        if existing_fx is None or _is_cache_stale(existing_fx.fetched_at, existing_fx.ttl_hours):
            yf_symbol = FX_PAIRS.get(currency)
            fx_entry = _fetch_fx_cache_yfinance(currency, yf_symbol) if yf_symbol else None
            if fx_entry is None:
                # Fallback: synthetic 1.0 rate (will show as unmodeled)
                fx_entry = FxCache(
                    pair=pair,
                    base_currency=currency,
                    quote_currency="USD",
                    spot_rate=1.0,
                    history_json=json.dumps(
                        [{"date": (now.date() - timedelta(days=i)).isoformat(), "rate": 1.0} for i in range(252)],
                        sort_keys=True,
                    ),
                    fetched_at=now,
                    ttl_hours=CACHE_TTL_HOURS,
                )
            db.merge(fx_entry)

    # Macro: refresh if no entry exists or the latest one is stale
    macro = (
        db.query(MacroCache)
        .filter(MacroCache.workspace_id == workspace_id)
        .order_by(MacroCache.fetched_at.desc())
        .first()
    )
    if macro is None or _is_cache_stale(macro.fetched_at, CACHE_TTL_HOURS):
        payload = _fetch_macro_payload_fred(workspace_id) or _fallback_macro_payload()
        if macro is None:
            db.add(
                MacroCache(
                    workspace_id=workspace_id,
                    payload_json=json.dumps(payload, sort_keys=True),
                    fetched_at=now,
                )
            )
        else:
            macro.payload_json = json.dumps(payload, sort_keys=True)
            macro.fetched_at = now

    db.flush()
    return {"tickers": sorted(cached_tickers), "modeled_value_usd": round(modeled_value, 2)}
