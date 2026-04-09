from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.analytics import RiskFlag, RiskScore
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.analytics import RiskFlagResponse, RiskRunResponse, RiskScoreResponse
from backend.services.risk import run_risk_analysis

router = APIRouter(prefix="/risk", tags=["risk"])


def _serialize_score(score: RiskScore) -> RiskScoreResponse:
    return RiskScoreResponse(
        id=score.id,
        agent=score.agent,
        dimension=score.dimension,
        status=score.status,
        score=score.score,
        severity=score.severity,
        headline=score.headline,
        reasoning=score.reasoning,
        evidence=json.loads(score.evidence_json),
        conversation_prompt=score.conversation_prompt,
        model=score.model,
    )


def _serialize_flag(flag: RiskFlag) -> RiskFlagResponse:
    return RiskFlagResponse(
        id=flag.id,
        rule=flag.rule,
        severity=flag.severity,
        ticker=flag.ticker,
        value=flag.value,
        threshold=flag.threshold,
        description=flag.description,
    )


@router.post("/run", response_model=RiskRunResponse, dependencies=[Depends(require_cookie_csrf)])
def run_risk(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> RiskRunResponse:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    job, scores, flags = run_risk_analysis(db, snapshot, user.id)
    db.commit()
    return RiskRunResponse(
        job_id=job.id,
        snapshot_id=snapshot.id,
        warnings=[],
        scores=[_serialize_score(score) for score in scores],
        flags=[_serialize_flag(flag) for flag in flags],
    )


@router.get("/scores", response_model=list[RiskScoreResponse])
def get_scores(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[RiskScoreResponse]:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        return []
    scores = db.scalars(select(RiskScore).where(RiskScore.snapshot_id == snapshot.id)).all()
    return [_serialize_score(score) for score in scores]


@router.get("/flags", response_model=list[RiskFlagResponse])
def get_flags(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[RiskFlagResponse]:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        return []
    flags = db.scalars(select(RiskFlag).where(RiskFlag.snapshot_id == snapshot.id)).all()
    return [_serialize_flag(flag) for flag in flags]


@router.get("/register", response_model=list[dict])
def get_register(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[dict]:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        return []
    scores = db.scalars(select(RiskScore).where(RiskScore.snapshot_id == snapshot.id)).all()
    flags = db.scalars(select(RiskFlag).where(RiskFlag.snapshot_id == snapshot.id)).all()
    register = [
        {"kind": "agent", "severity": score.severity, "headline": score.headline, "agent": score.agent}
        for score in scores
    ] + [
        {"kind": "flag", "severity": flag.severity, "headline": flag.description, "rule": flag.rule}
        for flag in flags
    ]
    severity_rank = {"priority": 0, "elevated": 1, "watch": 2, None: 3}
    return sorted(register, key=lambda item: severity_rank.get(item["severity"], 3))
