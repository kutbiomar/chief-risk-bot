from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.analytics import FxCache, MacroCache, PriceCache
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.routers.auth import require_session

router = APIRouter(prefix="/market", tags=["market"])


def _get_current_snapshot(db: Session, workspace_id: str) -> Optional[PortfolioSnapshot]:
    return db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )


@router.get("/prices")
def get_market_prices(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[dict]:
    _, user = auth
    snapshot = _get_current_snapshot(db, user.workspace_id)
    if snapshot is None:
        return []

    tickers = db.scalars(
        select(Position.ticker).where(Position.snapshot_id == snapshot.id).distinct()
    ).all()

    rows = []
    for ticker in tickers:
        cache = db.get(PriceCache, ticker)
        if cache:
            rows.append(
                {
                    "ticker": cache.ticker,
                    "currency": cache.currency,
                    "price_usd": cache.price_usd,
                    "price_local": cache.price_local,
                    "daily_return_usd": cache.daily_return_usd,
                    "weekly_return_usd": cache.weekly_return_usd,
                    "fetched_at": cache.fetched_at.isoformat() if cache.fetched_at else None,
                }
            )
    return rows


@router.get("/macro")
def get_macro(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    macro = (
        db.query(MacroCache)
        .filter(MacroCache.workspace_id == user.workspace_id)
        .order_by(MacroCache.fetched_at.desc())
        .first()
    )
    if macro is None:
        return {}
    import json

    payload = json.loads(macro.payload_json)
    payload["fetched_at"] = macro.fetched_at.isoformat() if macro.fetched_at else None
    return payload


@router.get("/movers")
def get_movers(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Top 5 movers by daily return, with daily P&L derived from market_value_usd * daily_return."""
    _, user = auth
    snapshot = _get_current_snapshot(db, user.workspace_id)
    if snapshot is None:
        return []

    positions = db.scalars(
        select(Position).where(Position.snapshot_id == snapshot.id)
    ).all()

    movers = []
    for pos in positions:
        cache = db.get(PriceCache, pos.ticker)
        daily_return = cache.daily_return_usd if cache else 0.0
        market_value = float(pos.market_value_usd or 0)
        daily_pnl = market_value * (daily_return or 0.0)
        movers.append(
            {
                "ticker": pos.ticker,
                "name": pos.name,
                "market_value_usd": round(market_value, 2),
                "daily_return_usd": round(daily_return or 0.0, 6),
                "daily_pnl_usd": round(daily_pnl, 2),
                "asset_class": pos.asset_class,
                "geo_region": pos.geo_region,
            }
        )

    # Sort by absolute daily return, return top 5
    movers.sort(key=lambda x: abs(x["daily_return_usd"]), reverse=True)
    return movers[:5]
