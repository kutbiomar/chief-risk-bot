"""Market data fetchers.

Two sources:
- yfinance (bulk download) for equity/ETF prices, 30-day vol, 90-day return
- pandas-datareader for FRED macro series (no API key needed)

Both sources can be flaky. We degrade gracefully: a missing field is logged
but never kills the briefing. The Claude layer handles "we don't know" well.

Important: we use yf.download() (batched) rather than per-ticker Ticker().history
because Yahoo rate-limits per-ticker calls hard. One HTTP call for all tickers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

log = logging.getLogger("riskpilot.data")

# FRED series we care about for a family office briefing.
# Keyed by short label → (FRED series id, compute_yoy_from_level)
FRED_SERIES: dict[str, tuple[str, bool]] = {
    "fed_funds_rate": ("DFF", False),
    "ten_year_yield": ("DGS10", False),
    "two_year_yield": ("DGS2", False),
    "core_cpi_yoy": ("CPILFESL", True),  # Raw is an index level; we compute YoY %
    "unemployment": ("UNRATE", False),
    "dollar_index": ("DTWEXBGS", False),
}


def _bulk_download(tickers: list[str], days: int = 120) -> pd.DataFrame:
    """Single batched yfinance call. Returns MultiIndex DataFrame keyed by ticker."""
    if not tickers:
        return pd.DataFrame()
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    try:
        data = yf.download(
            tickers=tickers,
            start=start.date().isoformat(),
            end=end.date().isoformat(),
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
        )
        return data
    except Exception as e:
        log.warning("yf.download failed for batch: %s", e)
        return pd.DataFrame()


def _extract_ticker_closes(bulk: pd.DataFrame, ticker: str) -> pd.Series | None:
    """Pull a Close series for one ticker out of the bulk MultiIndex frame."""
    if bulk is None or bulk.empty:
        return None
    try:
        if isinstance(bulk.columns, pd.MultiIndex):
            if ticker in bulk.columns.levels[0]:
                s = bulk[ticker]["Close"].dropna()
                return s if not s.empty else None
        else:
            # Single-ticker case: flat columns
            if "Close" in bulk.columns:
                s = bulk["Close"].dropna()
                return s if not s.empty else None
    except Exception as e:
        log.warning("extract closes failed for %s: %s", ticker, e)
    return None


def enrich_positions(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Add current price, 30d vol, 90d return for each position.

    Failures per-ticker are swallowed (we return what we could get).
    Uses a single bulk yf.download() to avoid rate limits.
    """
    raw_tickers = [str(t).strip().upper() for t in df["ticker"]]
    # yfinance uses BRK-B as BRK-B, but some chars need special handling
    tickers_to_fetch = list({t for t in raw_tickers if t})
    log.info("bulk downloading %d tickers", len(tickers_to_fetch))
    bulk = _bulk_download(tickers_to_fetch)

    enriched: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        qty = float(row["quantity"])
        asset_class = str(row["asset_class"]).strip()
        custodian = str(row.get("custodian", "") or "").strip()
        notes = str(row.get("notes", "") or "").strip()

        item: dict[str, Any] = {
            "ticker": ticker,
            "quantity": qty,
            "asset_class": asset_class,
            "custodian": custodian,
            "notes": notes,
            "price": None,
            "market_value": None,
            "vol_30d_annualized": None,
            "return_90d_pct": None,
            "data_error": None,
        }

        closes = _extract_ticker_closes(bulk, ticker)
        if closes is None or closes.empty:
            item["data_error"] = "no price data from bulk download"
            log.warning("no price data for %s", ticker)
            enriched.append(item)
            continue

        last_px = float(closes.iloc[-1])
        item["price"] = round(last_px, 4)
        item["market_value"] = round(last_px * qty, 2)

        # Annualized 30-day realized vol
        tail = closes.tail(30)
        if len(tail) >= 5:
            daily_rets = tail.pct_change().dropna()
            if not daily_rets.empty:
                vol = float(daily_rets.std() * (252 ** 0.5))
                item["vol_30d_annualized"] = round(vol, 4)

        # 90-day return (approx — use 60 trading days)
        if len(closes) >= 60:
            base = float(closes.iloc[-60])
            if base > 0:
                item["return_90d_pct"] = round(((last_px / base) - 1) * 100, 2)

        enriched.append(item)

    return enriched


def fetch_macro_context() -> dict[str, Any]:
    """Pull FRED macro series + ^VIX.

    Returns a dict of label → {value, as_of, delta_30d, unit} where available.
    Missing fields come back as None, never raise.
    """
    out: dict[str, Any] = {}

    try:
        from pandas_datareader import data as pdr

        end = datetime.utcnow()
        # Wider window for YoY computation on CPI
        start = end - timedelta(days=500)
        for label, (series_id, yoy_from_level) in FRED_SERIES.items():
            try:
                s = pdr.DataReader(series_id, "fred", start, end).dropna()
                if s.empty:
                    out[label] = None
                    continue
                series = s.iloc[:, 0]
                as_of = s.index[-1].date().isoformat()

                if yoy_from_level:
                    # CPI is released monthly. YoY = (current / 12-months-ago) - 1
                    if len(series) >= 13:
                        latest_level = float(series.iloc[-1])
                        year_ago_level = float(series.iloc[-13])
                        if year_ago_level > 0:
                            yoy = ((latest_level / year_ago_level) - 1) * 100
                            # delta vs prior month's YoY
                            prior_latest = float(series.iloc[-2])
                            prior_year_ago = float(series.iloc[-14]) if len(series) >= 14 else None
                            prior_yoy = (
                                ((prior_latest / prior_year_ago) - 1) * 100
                                if prior_year_ago and prior_year_ago > 0
                                else None
                            )
                            delta_30d = round(yoy - prior_yoy, 3) if prior_yoy is not None else None
                            out[label] = {
                                "value": round(yoy, 2),
                                "as_of": as_of,
                                "delta_30d": delta_30d,
                                "unit": "percent_yoy",
                            }
                            continue
                    out[label] = None
                    continue

                latest = float(series.iloc[-1])
                delta = None
                if len(series) > 20:
                    prior = float(series.iloc[-21])
                    delta = round(latest - prior, 4)
                out[label] = {
                    "value": round(latest, 4),
                    "as_of": as_of,
                    "delta_30d": delta,
                    "unit": "percent" if "yield" in label or "rate" in label or "unemployment" in label else "level",
                }
            except Exception as e:
                log.warning("FRED fetch failed for %s: %s", series_id, e)
                out[label] = None
    except Exception as e:
        log.warning("pandas-datareader unavailable: %s", e)

    # VIX via yfinance bulk download (same pattern as positions)
    try:
        vix_bulk = _bulk_download(["^VIX"], days=90)
        vix_closes = _extract_ticker_closes(vix_bulk, "^VIX")
        if vix_closes is not None and not vix_closes.empty:
            latest = float(vix_closes.iloc[-1])
            delta = None
            if len(vix_closes) > 20:
                delta = round(latest - float(vix_closes.iloc[-21]), 4)
            out["vix"] = {
                "value": round(latest, 2),
                "as_of": vix_closes.index[-1].date().isoformat(),
                "delta_30d": delta,
                "unit": "index_level",
            }
        else:
            out["vix"] = None
    except Exception as e:
        log.warning("VIX fetch failed: %s", e)
        out["vix"] = None

    return out
