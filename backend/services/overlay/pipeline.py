from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.analytics import VarResult
from backend.models.jobs import AsyncJob
from backend.models.portfolio import PortfolioSnapshot, Workspace
from backend.services.analytics.factor_var import compute_overlay_var_for_snapshot
from backend.services.jobs import AsyncJobService
from backend.services.overlay import ensure_overlay_state
from backend.services.overlay.alert_engine import compute_overlay_alerts
from backend.services.overlay.stress_scenarios import compute_stress_scenarios
from backend.services.var import compute_var_for_snapshot


@dataclass
class OverlayRunResult:
    job: AsyncJob
    summary: dict[str, object]


def run_overlay_for_snapshot(
    db: Session,
    snapshot: PortfolioSnapshot,
    *,
    created_by: str | None,
) -> OverlayRunResult:
    jobs = AsyncJobService(db)
    job = jobs.create_job(
        workspace_id=snapshot.workspace_id,
        job_type="overlay_refresh",
        created_by=created_by,
        resource_type="snapshot",
        resource_id=snapshot.id,
        request_payload={"snapshot_id": snapshot.id},
    )
    jobs.mark_running(job, started_children=4)

    overlay_state = ensure_overlay_state(db, snapshot)
    var_result = compute_var_for_snapshot(db, snapshot)
    db.flush()
    db.refresh(var_result)
    stress = compute_stress_scenarios(db, overlay_state["triangulation"])
    alerts = compute_overlay_alerts(overlay_state["triangulation"], overlay_state["regime"], var_result)

    summary = {
        "as_of_date": str(overlay_state["as_of_date"]),
        "regime": overlay_state["regime"].regime,
        "composite_score": overlay_state["triangulation"]["composite_score"],
        "factor_count": len(overlay_state["factor_scores"]),
        "stress_count": len(stress),
        "alert_count": len(alerts),
        "snapshot_id": snapshot.id,
        "var_1d_95": var_result.var_1d_95,
    }
    jobs.mark_finished(
        job,
        status="succeeded",
        result_payload=summary,
        succeeded_children=4,
        failed_children=0,
    )
    db.flush()
    return OverlayRunResult(job=job, summary=summary)


def run_workspace_overlay_cycle(
    workspace_id: str,
    *,
    db_factory: Callable[[], Session] = SessionLocal,
) -> dict[str, object]:
    db = db_factory()
    try:
        workspace = db.get(Workspace, workspace_id)
        if workspace is None or workspace.deleted_at is not None:
            return {"status": "skipped", "detail": "Workspace not found"}
        snapshot = db.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.workspace_id == workspace_id,
                PortfolioSnapshot.is_current.is_(True),
            )
        )
        if snapshot is None:
            return {"status": "skipped", "detail": "No current portfolio snapshot"}
        result = run_overlay_for_snapshot(db, snapshot, created_by=None)
        db.commit()
        return {"status": "succeeded", **result.summary, "job_id": result.job.id}
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "detail": str(exc)}
    finally:
        db.close()
