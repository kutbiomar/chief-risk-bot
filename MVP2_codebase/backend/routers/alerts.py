from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import CurrentUser, get_current_user, get_db
from ..schemas.private_markets import AlertListResponse
from ..services.alerts import build_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    items = build_alerts(user.workspace_id, db)
    return AlertListResponse(total=len(items), items=items)
