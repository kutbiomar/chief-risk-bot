from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, get_current_user, get_db
from ..models.capital import CapitalEvent
from ..models.funds import Commitment, Fund
from ..models.holdings import Holding
from ..schemas.private_markets import (
    CapitalEventCreateRequest,
    CapitalEventListResponse,
    CapitalEventResponse,
    CapitalEventUpdateRequest,
    CommitmentCreateRequest,
    CommitmentListResponse,
    CommitmentResponse,
    CommitmentUpdateRequest,
    FundCreateRequest,
    FundListResponse,
    FundResponse,
    FundUpdateRequest,
    HoldingCreateRequest,
    HoldingListResponse,
    HoldingResponse,
    HoldingUpdateRequest,
    LiquidityProjectionResponse,
    PortfolioSummaryResponse,
)
from ..services.bootstrap import get_or_create_workspace_settings
from ..services.liquidity import generate_cash_flow_ladder
from ..services.portfolio.aggregations import summarize_capital_events, summarize_funds

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _get_fund_or_404(db: Session, workspace_id: str, fund_id: str) -> Fund:
    fund = db.scalar(
        select(Fund).where(Fund.id == fund_id, Fund.workspace_id == workspace_id, Fund.deleted_at.is_(None))
    )
    if fund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found")
    return fund


def _get_commitment_or_404(db: Session, workspace_id: str, commitment_id: str) -> Commitment:
    commitment = db.scalar(
        select(Commitment).where(
            Commitment.id == commitment_id,
            Commitment.workspace_id == workspace_id,
            Commitment.deleted_at.is_(None),
        )
    )
    if commitment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found")
    return commitment


def _get_capital_event_or_404(db: Session, workspace_id: str, capital_event_id: str) -> CapitalEvent:
    event = db.scalar(
        select(CapitalEvent).where(
            CapitalEvent.id == capital_event_id,
            CapitalEvent.workspace_id == workspace_id,
            CapitalEvent.deleted_at.is_(None),
        )
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capital event not found")
    return event


def _get_holding_or_404(db: Session, workspace_id: str, holding_id: str) -> Holding:
    holding = db.scalar(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.workspace_id == workspace_id,
            Holding.deleted_at.is_(None),
        )
    )
    if holding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    return holding


def _fund_response(fund: Fund) -> FundResponse:
    return FundResponse(
        id=fund.id,
        name=fund.name,
        type=fund.type,
        manager_name=fund.manager_name,
        vintage_year=fund.vintage_year,
        fund_size=fund.fund_size,
        currency=fund.currency,
        jurisdiction=fund.jurisdiction,
        created_at=fund.created_at,
        updated_at=fund.updated_at,
    )


def _commitment_response(commitment: Commitment) -> CommitmentResponse:
    return CommitmentResponse(
        id=commitment.id,
        fund_id=commitment.fund_id,
        committed_amount=commitment.committed_amount,
        commitment_currency=commitment.commitment_currency,
        committed_amount_base=commitment.committed_amount_base,
        called_capital=commitment.called_capital,
        called_capital_base=commitment.called_capital_base,
        uncalled_capital=commitment.uncalled_capital,
        uncalled_capital_base=commitment.uncalled_capital_base,
        nav=commitment.nav,
        nav_base=commitment.nav_base,
        nav_date=commitment.nav_date,
        nav_is_estimated=commitment.nav_is_estimated,
        nav_confidence_pct=commitment.nav_confidence_pct,
        distributions_received=commitment.distributions_received,
        distributions_received_base=commitment.distributions_received_base,
        management_fee_rate=commitment.management_fee_rate,
        carry_rate=commitment.carry_rate,
        remaining_fund_life_months=commitment.remaining_fund_life_months,
        created_at=commitment.created_at,
        updated_at=commitment.updated_at,
    )


def _capital_event_response(event: CapitalEvent) -> CapitalEventResponse:
    return CapitalEventResponse(
        id=event.id,
        fund_id=event.fund_id,
        commitment_id=event.commitment_id,
        type=event.type,
        amount=event.amount,
        currency=event.currency,
        amount_base=event.amount_base,
        notice_date=event.notice_date,
        due_date=event.due_date,
        effective_date=event.effective_date,
        source_document_id=event.source_document_id,
        notes=event.notes,
        is_confirmed=event.is_confirmed,
        recall_period_days=event.recall_period_days,
        recall_expires_at=event.recall_expires_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _holding_response(holding: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=holding.id,
        fund_id=holding.fund_id,
        commitment_id=holding.commitment_id,
        asset_name=holding.asset_name,
        asset_type=holding.asset_type,
        geo_region=holding.geo_region,
        sector=holding.sector,
        currency=holding.currency,
        quantity=holding.quantity,
        unit_cost=holding.unit_cost,
        current_value=holding.current_value,
        current_value_base=holding.current_value_base,
        current_value_date=holding.current_value_date,
        current_value_source=holding.current_value_source,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
    )


@router.post("/funds", response_model=FundResponse, status_code=status.HTTP_201_CREATED)
def create_fund(
    body: FundCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FundResponse:
    fund = Fund(workspace_id=user.workspace_id, **body.model_dump())
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return _fund_response(fund)


@router.get("/funds", response_model=FundListResponse)
def list_funds(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FundListResponse:
    funds = db.scalars(
        select(Fund).where(Fund.workspace_id == user.workspace_id, Fund.deleted_at.is_(None)).order_by(Fund.name)
    ).all()
    return FundListResponse(total=len(funds), items=[_fund_response(fund) for fund in funds])


@router.get("/funds/{fund_id}", response_model=FundResponse)
def get_fund(
    fund_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FundResponse:
    return _fund_response(_get_fund_or_404(db, user.workspace_id, fund_id))


@router.put("/funds/{fund_id}", response_model=FundResponse)
def update_fund(
    fund_id: str,
    body: FundUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FundResponse:
    fund = _get_fund_or_404(db, user.workspace_id, fund_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(fund, key, value)
    db.commit()
    db.refresh(fund)
    return _fund_response(fund)


@router.delete("/funds/{fund_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fund(
    fund_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    fund = _get_fund_or_404(db, user.workspace_id, fund_id)
    from datetime import datetime, timezone

    fund.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/commitments", response_model=CommitmentResponse, status_code=status.HTTP_201_CREATED)
def create_commitment(
    body: CommitmentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommitmentResponse:
    _get_fund_or_404(db, user.workspace_id, body.fund_id)
    commitment = Commitment(workspace_id=user.workspace_id, **body.model_dump())
    db.add(commitment)
    db.commit()
    db.refresh(commitment)
    return _commitment_response(commitment)


@router.get("/commitments", response_model=CommitmentListResponse)
def list_commitments(
    fund_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommitmentListResponse:
    query = select(Commitment).where(
        Commitment.workspace_id == user.workspace_id,
        Commitment.deleted_at.is_(None),
    )
    if fund_id:
        query = query.where(Commitment.fund_id == fund_id)
    items = db.scalars(query.order_by(Commitment.created_at.desc())).all()
    return CommitmentListResponse(total=len(items), items=[_commitment_response(item) for item in items])


@router.put("/commitments/{commitment_id}", response_model=CommitmentResponse)
def update_commitment(
    commitment_id: str,
    body: CommitmentUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommitmentResponse:
    commitment = _get_commitment_or_404(db, user.workspace_id, commitment_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(commitment, key, value)
    db.commit()
    db.refresh(commitment)
    return _commitment_response(commitment)


@router.delete("/commitments/{commitment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commitment(
    commitment_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    commitment = _get_commitment_or_404(db, user.workspace_id, commitment_id)
    from datetime import datetime, timezone

    commitment.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/capital-events", response_model=CapitalEventResponse, status_code=status.HTTP_201_CREATED)
def create_capital_event(
    body: CapitalEventCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CapitalEventResponse:
    _get_fund_or_404(db, user.workspace_id, body.fund_id)
    event = CapitalEvent(workspace_id=user.workspace_id, **body.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _capital_event_response(event)


@router.get("/capital-events", response_model=CapitalEventListResponse)
def list_capital_events(
    fund_id: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CapitalEventListResponse:
    query = select(CapitalEvent).where(
        CapitalEvent.workspace_id == user.workspace_id,
        CapitalEvent.deleted_at.is_(None),
    )
    if fund_id:
        query = query.where(CapitalEvent.fund_id == fund_id)
    if event_type:
        query = query.where(CapitalEvent.type == event_type)
    items = db.scalars(query.order_by(CapitalEvent.due_date, CapitalEvent.created_at.desc())).all()
    return CapitalEventListResponse(total=len(items), items=[_capital_event_response(item) for item in items])


@router.put("/capital-events/{capital_event_id}", response_model=CapitalEventResponse)
def update_capital_event(
    capital_event_id: str,
    body: CapitalEventUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CapitalEventResponse:
    event = _get_capital_event_or_404(db, user.workspace_id, capital_event_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return _capital_event_response(event)


@router.delete("/capital-events/{capital_event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_capital_event(
    capital_event_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    event = _get_capital_event_or_404(db, user.workspace_id, capital_event_id)
    from datetime import datetime, timezone

    event.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
def create_holding(
    body: HoldingCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldingResponse:
    holding = Holding(workspace_id=user.workspace_id, **body.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return _holding_response(holding)


@router.get("/holdings", response_model=HoldingListResponse)
def list_holdings(
    fund_id: Optional[str] = Query(default=None),
    asset_type: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldingListResponse:
    query = select(Holding).where(Holding.workspace_id == user.workspace_id, Holding.deleted_at.is_(None))
    if fund_id:
        query = query.where(Holding.fund_id == fund_id)
    if asset_type:
        query = query.where(Holding.asset_type == asset_type)
    items = db.scalars(query.order_by(Holding.created_at.desc())).all()
    return HoldingListResponse(total=len(items), items=[_holding_response(item) for item in items])


@router.put("/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(
    holding_id: str,
    body: HoldingUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldingResponse:
    holding = _get_holding_or_404(db, user.workspace_id, holding_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(holding, key, value)
    db.commit()
    db.refresh(holding)
    return _holding_response(holding)


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    holding_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    holding = _get_holding_or_404(db, user.workspace_id, holding_id)
    from datetime import datetime, timezone

    holding.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioSummaryResponse:
    summary = summarize_funds(user.workspace_id, db)
    event_summary = summarize_capital_events(user.workspace_id, db)
    return PortfolioSummaryResponse(**summary, **event_summary)


@router.get("/liquidity", response_model=LiquidityProjectionResponse)
def get_liquidity_projection(
    scenario: str = Query(default="base"),
    base_currency: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LiquidityProjectionResponse:
    workspace_settings = get_or_create_workspace_settings(db, user.workspace_id)
    projection = generate_cash_flow_ladder(
        user.workspace_id,
        db,
        scenario=scenario,
        base_currency=base_currency or workspace_settings.base_currency,
        liquidity_buffer=workspace_settings.liquidity_buffer_default or 0,
    )
    return LiquidityProjectionResponse(**projection)
