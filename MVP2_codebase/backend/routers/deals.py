from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, get_current_user, get_db
from ..models.deals import Deal
from ..schemas.private_markets import DealCreateRequest, DealListResponse, DealResponse, DealUpdateRequest

router = APIRouter(prefix="/deals", tags=["deals"])


def _get_deal_or_404(db: Session, workspace_id: str, deal_id: str) -> Deal:
    deal = db.scalar(
        select(Deal).where(Deal.id == deal_id, Deal.workspace_id == workspace_id, Deal.deleted_at.is_(None))
    )
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return deal


def _response(deal: Deal) -> DealResponse:
    return DealResponse(
        id=deal.id,
        name=deal.name,
        stage=deal.stage,
        asset_type=deal.asset_type,
        target_commitment=deal.target_commitment,
        target_commitment_currency=deal.target_commitment_currency,
        target_commitment_base=deal.target_commitment_base,
        target_close_date=deal.target_close_date,
        lead_analyst_id=deal.lead_analyst_id,
        notes=deal.notes,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    body: DealCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealResponse:
    deal = Deal(workspace_id=user.workspace_id, **body.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return _response(deal)


@router.get("", response_model=DealListResponse)
def list_deals(
    stage: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealListResponse:
    query = select(Deal).where(Deal.workspace_id == user.workspace_id, Deal.deleted_at.is_(None))
    if stage:
        query = query.where(Deal.stage == stage)
    items = db.scalars(query.order_by(Deal.target_close_date, Deal.created_at.desc())).all()
    return DealListResponse(total=len(items), items=[_response(item) for item in items])


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: str,
    body: DealUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealResponse:
    deal = _get_deal_or_404(db, user.workspace_id, deal_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(deal, key, value)
    db.commit()
    db.refresh(deal)
    return _response(deal)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deal = _get_deal_or_404(db, user.workspace_id, deal_id)
    deal.deleted_at = datetime.now(timezone.utc)
    db.commit()
