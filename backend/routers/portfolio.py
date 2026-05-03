from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.portfolio import (
    PortfolioSummaryResponse,
    PositionCreateRequest,
    PositionListResponse,
    PositionMutationResponse,
    PositionResponse,
    PositionUpdateRequest,
    SnapshotResponse,
)
from backend.services.audit.logger import AuditLogger
from backend.services.portfolio import summarize_positions

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _resolve_snapshot(db: Session, workspace_id: str, snapshot_id: Optional[str]) -> PortfolioSnapshot:
    if snapshot_id:
        snapshot = db.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.id == snapshot_id,
                PortfolioSnapshot.workspace_id == workspace_id,
            )
        )
    else:
        snapshot = db.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.workspace_id == workspace_id,
                PortfolioSnapshot.is_current.is_(True),
            )
        )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    return snapshot


def _ensure_current_snapshot(db: Session, workspace_id: str, user_id: str) -> PortfolioSnapshot:
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is not None:
        return snapshot
    snapshot = PortfolioSnapshot(
        id=str(uuid4()),
        workspace_id=workspace_id,
        uploaded_by=user_id,
        source="manual_init",
        position_count=0,
        total_aum_usd=0.0,
        is_current=True,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


@router.get("/snapshot", response_model=SnapshotResponse)
def get_current_snapshot(
    snapshot_id: Optional[str] = Query(default=None),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> SnapshotResponse:
    _, user = auth
    snapshot = _resolve_snapshot(db, user.workspace_id, snapshot_id)
    return SnapshotResponse(
        snapshot_id=snapshot.id,
        source=snapshot.source,
        position_count=snapshot.position_count,
        total_aum_usd=snapshot.total_aum_usd,
        created_at=snapshot.created_at,
        parent_snapshot_id=snapshot.parent_snapshot_id,
    )


@router.get("/summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(
    snapshot_id: Optional[str] = Query(default=None),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> PortfolioSummaryResponse:
    _, user = auth
    snapshot = _resolve_snapshot(db, user.workspace_id, snapshot_id)
    positions = db.scalars(
        select(Position).where(Position.snapshot_id == snapshot.id).order_by(Position.market_value_usd.desc())
    ).all()
    summary = summarize_positions(positions)
    return PortfolioSummaryResponse(snapshot_id=snapshot.id, **summary)


@router.get("/positions", response_model=PositionListResponse)
def list_positions(
    snapshot_id: Optional[str] = Query(default=None),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> PositionListResponse:
    _, user = auth
    snapshot = _resolve_snapshot(db, user.workspace_id, snapshot_id) if snapshot_id else _ensure_current_snapshot(db, user.workspace_id, user.id)
    positions = db.scalars(
        select(Position).where(Position.snapshot_id == snapshot.id).order_by(Position.market_value_usd.desc())
    ).all()
    history_rows = db.scalars(
        select(Position).where(Position.workspace_id == user.workspace_id)
    ).all()
    first_seen_map: dict[tuple[str, str, str, str], object] = {}
    for row in history_rows:
        key = (
            str(row.ticker or "").strip().upper(),
            str(row.name or "").strip().lower(),
            str(row.asset_class or "").strip().lower(),
            str(row.custodian or "").strip().lower(),
        )
        current_first = first_seen_map.get(key)
        if current_first is None or row.created_at < current_first:
            first_seen_map[key] = row.created_at
    items = [
        PositionResponse(
            id=position.id,
            snapshot_id=position.snapshot_id,
            ticker=position.ticker,
            name=position.name,
            quantity=position.quantity,
            price_usd=position.price_usd,
            market_value_usd=position.market_value_usd,
            asset_class=position.asset_class,
            geo_region=position.geo_region,
            sector=position.sector,
            market_segment=position.market_segment,
            factor_asset_class=position.factor_asset_class,
            factor_sector=position.factor_sector,
            factor_subsector=position.factor_subsector,
            factor_country=position.factor_country,
            factor_region=position.factor_region,
            factor_market_segment=position.factor_market_segment,
            factor_tag_source=position.factor_tag_source,
            factor_tag_confidence=position.factor_tag_confidence,
            custodian=position.custodian,
            price_source=position.price_source,
            notes=position.notes,
            created_at=position.created_at,
            first_seen_at=first_seen_map.get((
                str(position.ticker or "").strip().upper(),
                str(position.name or "").strip().lower(),
                str(position.asset_class or "").strip().lower(),
                str(position.custodian or "").strip().lower(),
            )),
            last_modified_at=position.created_at,
        )
        for position in positions
    ]
    return PositionListResponse(snapshot_id=snapshot.id, total=len(items), items=items)


# ---------------------------------------------------------------------------
# Immutable snapshot helper
# ---------------------------------------------------------------------------

def _materialize_successor_snapshot(
    db: Session,
    current_snapshot: PortfolioSnapshot,
    user_id: str,
    source: str = "manual_edit",
) -> tuple[PortfolioSnapshot, dict[str, str]]:
    """Create a successor snapshot, demote the current one, return the new snapshot."""
    # Copy all current positions into memory before demoting
    existing_positions = db.scalars(
        select(Position).where(Position.snapshot_id == current_snapshot.id)
    ).all()

    demoted = db.execute(
        update(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.id == current_snapshot.id,
            PortfolioSnapshot.workspace_id == current_snapshot.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
        .values(is_current=False)
    )
    if demoted.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current snapshot changed during update. Retry the request.",
        )

    new_snapshot = PortfolioSnapshot(
        id=str(uuid4()),
        workspace_id=current_snapshot.workspace_id,
        parent_snapshot_id=current_snapshot.id,
        uploaded_by=user_id,
        source=source,
        position_count=current_snapshot.position_count,
        total_aum_usd=current_snapshot.total_aum_usd,
        is_current=True,
    )
    db.add(new_snapshot)
    db.flush()  # get new_snapshot.id

    # Copy existing positions forward
    copied_position_ids: dict[str, str] = {}
    for pos in existing_positions:
        copied_position_id = str(uuid4())
        copied_position_ids[pos.id] = copied_position_id
        db.add(
            Position(
                id=copied_position_id,
                snapshot_id=new_snapshot.id,
                workspace_id=pos.workspace_id,
                security_id=pos.security_id,
                ticker=pos.ticker,
                name=pos.name,
                position_currency=pos.position_currency,
                quantity=pos.quantity,
                price_local=pos.price_local,
                price_usd=pos.price_usd,
                market_value_local=pos.market_value_local,
                market_value_usd=pos.market_value_usd,
                asset_class=pos.asset_class,
                geo_region=pos.geo_region,
                sector=pos.sector,
                market_segment=pos.market_segment,
                factor_asset_class=pos.factor_asset_class,
                factor_sector=pos.factor_sector,
                factor_subsector=pos.factor_subsector,
                factor_country=pos.factor_country,
                factor_region=pos.factor_region,
                factor_market_segment=pos.factor_market_segment,
                factor_tag_source=pos.factor_tag_source,
                factor_tag_confidence=pos.factor_tag_confidence,
                custodian=pos.custodian,
                price_source=pos.price_source,
                beta_vs_spy=pos.beta_vs_spy,
                daily_return=pos.daily_return,
                notes=pos.notes,
            )
        )

    db.flush()
    return new_snapshot, copied_position_ids


def _recalculate_snapshot_totals(db: Session, snapshot: PortfolioSnapshot) -> None:
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    total_aum = sum(float(p.market_value_usd or 0) for p in positions)
    snapshot.position_count = len(positions)
    snapshot.total_aum_usd = total_aum
    db.flush()


# ---------------------------------------------------------------------------
# POST /portfolio/positions — add a position
# ---------------------------------------------------------------------------

@router.post(
    "/positions",
    response_model=PositionMutationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_cookie_csrf)],
)
def create_position(
    body: PositionCreateRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> PositionMutationResponse:
    _, user = auth
    current = _ensure_current_snapshot(db, user.workspace_id, user.id)
    new_snapshot, _ = _materialize_successor_snapshot(db, current, user.id, source="manual_edit")

    # Derive market_value_usd from price if not provided
    market_value_usd = body.market_value_usd
    if market_value_usd is None and body.price_usd is not None:
        market_value_usd = body.quantity * body.price_usd

    new_position = Position(
        id=str(uuid4()),
        snapshot_id=new_snapshot.id,
        workspace_id=user.workspace_id,
        ticker=body.ticker.upper().strip(),
        name=body.name,
        position_currency=body.position_currency,
        quantity=body.quantity,
        price_usd=body.price_usd,
        market_value_usd=market_value_usd,
        asset_class=body.asset_class,
        geo_region=body.geo_region,
        sector=body.sector,
        market_segment=body.market_segment,
        factor_asset_class=body.factor_asset_class,
        factor_sector=body.factor_sector,
        factor_subsector=body.factor_subsector,
        factor_country=body.factor_country,
        factor_region=body.factor_region,
        factor_market_segment=body.factor_market_segment,
        factor_tag_source=body.factor_tag_source,
        factor_tag_confidence=body.factor_tag_confidence,
        custodian=body.custodian,
        notes=body.notes,
        price_source="manual",
    )
    db.add(new_position)
    db.flush()
    _recalculate_snapshot_totals(db, new_snapshot)

    AuditLogger(db).append_event(
        workspace_id=user.workspace_id,
        actor_user_id=user.id,
        actor_type="user",
        event_type="position",
        action="position.created",
        subject_type="position",
        subject_id=new_position.id,
        detail={"ticker": new_position.ticker, "snapshot_id": new_snapshot.id},
    )
    db.commit()
    return PositionMutationResponse(
        snapshot_id=new_snapshot.id,
        position_id=new_position.id,
        parent_snapshot_id=current.id,
    )


# ---------------------------------------------------------------------------
# PATCH /portfolio/positions/{id} — edit a position
# ---------------------------------------------------------------------------

@router.patch(
    "/positions/{position_id}",
    response_model=PositionMutationResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def update_position(
    position_id: str,
    body: PositionUpdateRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> PositionMutationResponse:
    _, user = auth
    current = _resolve_snapshot(db, user.workspace_id, None)

    # Find the target position in the current snapshot
    target = db.scalar(
        select(Position).where(
            Position.id == position_id,
            Position.snapshot_id == current.id,
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found in current snapshot")

    new_snapshot, copied_position_ids = _materialize_successor_snapshot(db, current, user.id, source="manual_edit")

    copied_target_id = copied_position_ids.get(target.id)
    copied_target = db.get(Position, copied_target_id) if copied_target_id else None
    if copied_target is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to find copied position")

    # Apply updates
    if body.name is not None:
        copied_target.name = body.name
    if body.quantity is not None:
        copied_target.quantity = body.quantity
    if body.market_value_usd is not None:
        copied_target.market_value_usd = body.market_value_usd
    if body.price_usd is not None:
        copied_target.price_usd = body.price_usd
    if body.position_currency is not None:
        copied_target.position_currency = body.position_currency
    if body.asset_class is not None:
        copied_target.asset_class = body.asset_class
    if body.geo_region is not None:
        copied_target.geo_region = body.geo_region
    if body.sector is not None:
        copied_target.sector = body.sector
    if body.market_segment is not None:
        copied_target.market_segment = body.market_segment
    if body.factor_asset_class is not None:
        copied_target.factor_asset_class = body.factor_asset_class
    if body.factor_sector is not None:
        copied_target.factor_sector = body.factor_sector
    if body.factor_subsector is not None:
        copied_target.factor_subsector = body.factor_subsector
    if body.factor_country is not None:
        copied_target.factor_country = body.factor_country
    if body.factor_region is not None:
        copied_target.factor_region = body.factor_region
    if body.factor_market_segment is not None:
        copied_target.factor_market_segment = body.factor_market_segment
    if body.factor_tag_source is not None:
        copied_target.factor_tag_source = body.factor_tag_source
    if body.factor_tag_confidence is not None:
        copied_target.factor_tag_confidence = body.factor_tag_confidence
    if body.custodian is not None:
        copied_target.custodian = body.custodian
    if body.notes is not None:
        copied_target.notes = body.notes

    # Recalculate market_value_usd from price if only price updated
    if body.price_usd is not None and body.market_value_usd is None:
        copied_target.market_value_usd = copied_target.quantity * body.price_usd

    db.flush()
    _recalculate_snapshot_totals(db, new_snapshot)

    AuditLogger(db).append_event(
        workspace_id=user.workspace_id,
        actor_user_id=user.id,
        actor_type="user",
        event_type="position",
        action="position.updated",
        subject_type="position",
        subject_id=copied_target.id,
        detail={"ticker": copied_target.ticker, "snapshot_id": new_snapshot.id, "original_position_id": position_id},
    )
    db.commit()
    return PositionMutationResponse(
        snapshot_id=new_snapshot.id,
        position_id=copied_target.id,
        parent_snapshot_id=current.id,
    )


# ---------------------------------------------------------------------------
# DELETE /portfolio/positions/{id} — remove a position
# ---------------------------------------------------------------------------

@router.delete(
    "/positions/{position_id}",
    response_model=PositionMutationResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def delete_position(
    position_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> PositionMutationResponse:
    _, user = auth
    current = _resolve_snapshot(db, user.workspace_id, None)

    target = db.scalar(
        select(Position).where(
            Position.id == position_id,
            Position.snapshot_id == current.id,
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found in current snapshot")

    ticker_to_remove = target.ticker
    new_snapshot, copied_position_ids = _materialize_successor_snapshot(db, current, user.id, source="manual_edit")

    copied_target_id = copied_position_ids.get(target.id)
    to_delete = db.get(Position, copied_target_id) if copied_target_id else None
    if to_delete:
        db.delete(to_delete)
        db.flush()

    _recalculate_snapshot_totals(db, new_snapshot)

    AuditLogger(db).append_event(
        workspace_id=user.workspace_id,
        actor_user_id=user.id,
        actor_type="user",
        event_type="position",
        action="position.deleted",
        subject_type="position",
        subject_id=position_id,
        detail={"ticker": ticker_to_remove, "snapshot_id": new_snapshot.id},
    )
    db.commit()
    return PositionMutationResponse(
        snapshot_id=new_snapshot.id,
        position_id=position_id,
        parent_snapshot_id=current.id,
    )
