from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.deps import get_db
from backend.models.onboarding import OnboardingProgress
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_cookie_csrf, require_session

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Steps in order
ONBOARDING_STEPS = [
    "workspace_created",
    "portfolio_uploaded",
    "enrichment_run",
    "risk_run",
    "briefing_generated",
]


class OnboardingStateResponse(BaseModel):
    workspace_id: str
    current_step: int
    total_steps: int
    completed_steps: List[str]
    is_complete: bool
    next_step: Optional[str] = None


class OnboardingStepRequest(BaseModel):
    step: str


class OnboardingStepResponse(BaseModel):
    workspace_id: str
    step: str
    current_step: int
    is_complete: bool


@router.get("/state", response_model=OnboardingStateResponse)
def get_onboarding_state(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> OnboardingStateResponse:
    _, user = auth
    progress = db.get(OnboardingProgress, user.workspace_id)

    if progress is None:
        return OnboardingStateResponse(
            workspace_id=user.workspace_id,
            current_step=0,
            total_steps=len(ONBOARDING_STEPS),
            completed_steps=[],
            is_complete=False,
            next_step=ONBOARDING_STEPS[0] if ONBOARDING_STEPS else None,
        )

    completed = json.loads(progress.completed_steps_json)
    remaining = [s for s in ONBOARDING_STEPS if s not in completed]
    return OnboardingStateResponse(
        workspace_id=user.workspace_id,
        current_step=progress.current_step,
        total_steps=progress.total_steps,
        completed_steps=completed,
        is_complete=progress.completed_at is not None,
        next_step=remaining[0] if remaining else None,
    )


@router.get("/status")
def get_onboarding_status(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    total = snapshot.position_count if snapshot is not None else 0
    enriched = total if snapshot is not None and snapshot.enriched_at is not None else 0
    return {
        "state": "complete" if total and enriched >= total else "pending",
        "enriched": enriched,
        "total": total,
        "snapshot_id": snapshot.id if snapshot is not None else None,
    }


@router.post("/step", response_model=OnboardingStepResponse, dependencies=[Depends(require_cookie_csrf)])
def complete_onboarding_step(
    body: OnboardingStepRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> OnboardingStepResponse:
    _, user = auth
    now = datetime.now(timezone.utc)

    progress = db.get(OnboardingProgress, user.workspace_id)
    if progress is None:
        progress = OnboardingProgress(
            workspace_id=user.workspace_id,
            current_step=0,
            completed_steps_json="[]",
            total_steps=len(ONBOARDING_STEPS),
        )
        db.add(progress)
        db.flush()

    completed = json.loads(progress.completed_steps_json)
    if body.step not in completed:
        completed.append(body.step)
        progress.completed_steps_json = json.dumps(completed)
        progress.last_step_completed_at = now

        # Advance current_step to index of next incomplete step
        for i, step in enumerate(ONBOARDING_STEPS):
            if step not in completed:
                progress.current_step = i
                break
        else:
            progress.current_step = len(ONBOARDING_STEPS)

        if len(completed) >= len(ONBOARDING_STEPS):
            progress.completed_at = now

    db.commit()
    is_complete = progress.completed_at is not None
    return OnboardingStepResponse(
        workspace_id=user.workspace_id,
        step=body.step,
        current_step=progress.current_step,
        is_complete=is_complete,
    )
