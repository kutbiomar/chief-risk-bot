from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models.auth import User, WorkspaceSetting
from backend.models.content import BriefingRun
from backend.models.portfolio import PortfolioSnapshot, Workspace
from backend.services.auth.session import utc_now
from backend.services.briefings import PdfExportUnavailableError, export_briefing_pdf, generate_briefing
from backend.services.overlay.pipeline import run_workspace_overlay_cycle
from backend.services.risk import run_risk_analysis
from backend.services.var import compute_var_for_snapshot

logger = logging.getLogger(__name__)

DAY_TO_CRON = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
}


@dataclass
class SchedulerRunResult:
    status: str
    detail: str
    briefing_id: str | None = None
    snapshot_id: str | None = None
    exported_path: str | None = None


def _job_id(workspace_id: str) -> str:
    return f"weekly-briefing:{workspace_id}"


def _overlay_job_id(workspace_id: str) -> str:
    return f"overlay-refresh:{workspace_id}"


def _parse_schedule(day: str, time_value: str, timezone_name: str) -> CronTrigger:
    day_token = DAY_TO_CRON.get(day.strip().lower())
    if day_token is None:
        raise ValueError(f"Unsupported briefing day: {day}")
    try:
        hour_text, minute_text = time_value.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except Exception as exc:
        raise ValueError(f"Invalid briefing time: {time_value}") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid briefing time: {time_value}")
    return CronTrigger(
        day_of_week=day_token,
        hour=hour,
        minute=minute,
        timezone=ZoneInfo(timezone_name),
    )


def _get_workspace_settings(db: Session, workspace_id: str) -> WorkspaceSetting:
    settings = db.get(WorkspaceSetting, workspace_id)
    if settings is not None:
        return settings
    return WorkspaceSetting(
        workspace_id=workspace_id,
        briefing_day="Monday",
        briefing_time="06:00",
        briefing_recipients="",
        briefing_auto_publish=False,
        briefing_send_pdf=False,
        briefing_include_audit_footer=False,
        ai_model="claude-opus-4-6",
        ai_risk_tone="conservative",
        ai_allow_trade_actions=False,
        sso_mode="disabled",
        updated_at=utc_now(),
    )


def run_workspace_briefing_cycle(
    workspace_id: str,
    *,
    db_factory: Callable[[], Session] = SessionLocal,
) -> SchedulerRunResult:
    db = db_factory()
    try:
        workspace = db.get(Workspace, workspace_id)
        if workspace is None or workspace.deleted_at is not None:
            return SchedulerRunResult(status="skipped", detail="Workspace not found")

        settings = _get_workspace_settings(db, workspace_id)
        snapshot = db.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.workspace_id == workspace_id,
                PortfolioSnapshot.is_current.is_(True),
            )
        )
        if snapshot is None:
            return SchedulerRunResult(status="skipped", detail="No current portfolio snapshot")

        owner = db.scalar(
            select(User)
            .where(User.workspace_id == workspace_id, User.disabled_at.is_(None))
            .order_by(User.created_at.asc())
        )

        compute_var_for_snapshot(db, snapshot)
        run_risk_analysis(db, snapshot, owner.id if owner is not None else None)
        briefing = generate_briefing(db, snapshot, owner.id if owner is not None else None)

        detail = "Scheduled briefing run completed"
        if settings.briefing_auto_publish:
            if briefing.model == "deterministic-demo-briefing":
                detail = "Scheduled briefing generated but not auto-published because deterministic fallback was used"
            else:
                briefing.status = "published"
                briefing.published_at = utc_now()
                briefing.published_by = owner.id if owner is not None else None

        exported_path = None
        if settings.briefing_send_pdf:
            try:
                exported_path = export_briefing_pdf(db, briefing, workspace_id)
            except PdfExportUnavailableError as exc:
                logger.warning("Scheduled briefing PDF export unavailable for workspace %s: %s", workspace_id, exc)
                detail = f"{detail}. {exc}" if detail != "Scheduled briefing run completed" else str(exc)

        db.commit()
        return SchedulerRunResult(
            status="succeeded",
            detail=detail,
            briefing_id=briefing.id,
            snapshot_id=snapshot.id,
            exported_path=exported_path,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Scheduled briefing cycle failed for workspace %s", workspace_id)
        return SchedulerRunResult(status="failed", detail=str(exc))
    finally:
        db.close()


class BriefingSchedulerManager:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        db_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.scheduler_enabled if enabled is None else enabled
        self.db_factory = db_factory
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.started = False

    def start(self) -> None:
        if not self.enabled or self.started:
            return
        self.scheduler.start()
        self.started = True
        self.sync_all_jobs()
        logger.info("Briefing scheduler started")

    def shutdown(self) -> None:
        if not self.started:
            return
        self.scheduler.shutdown(wait=False)
        self.started = False
        logger.info("Briefing scheduler stopped")

    def sync_workspace_job(self, workspace_id: str) -> None:
        if not self.enabled:
            return
        db = self.db_factory()
        try:
            workspace = db.get(Workspace, workspace_id)
            if workspace is None or workspace.deleted_at is not None:
                self.scheduler.remove_job(_job_id(workspace_id))
                return
            settings = _get_workspace_settings(db, workspace_id)
            trigger = _parse_schedule(settings.briefing_day, settings.briefing_time, workspace.timezone)
            self.scheduler.add_job(
                run_workspace_briefing_cycle,
                trigger=trigger,
                kwargs={"workspace_id": workspace_id},
                id=_job_id(workspace_id),
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=3600,
            )
            self.scheduler.add_job(
                run_workspace_overlay_cycle,
                trigger=CronTrigger(
                    hour=17,
                    minute=0,
                    timezone=ZoneInfo("America/New_York"),
                ),
                kwargs={"workspace_id": workspace_id},
                id=_overlay_job_id(workspace_id),
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=3600,
            )
        except Exception:
            logger.exception("Failed to sync scheduler job for workspace %s", workspace_id)
        finally:
            db.close()

    def sync_all_jobs(self) -> None:
        if not self.enabled:
            return
        db = self.db_factory()
        try:
            workspace_ids = db.scalars(
                select(Workspace.id).where(Workspace.deleted_at.is_(None))
            ).all()
        finally:
            db.close()

        active_ids = {
            identifier
            for workspace_id in workspace_ids
            for identifier in (_job_id(workspace_id), _overlay_job_id(workspace_id))
        }
        for workspace_id in workspace_ids:
            self.sync_workspace_job(workspace_id)
        for job in list(self.scheduler.get_jobs()):
            if (job.id.startswith("weekly-briefing:") or job.id.startswith("overlay-refresh:")) and job.id not in active_ids:
                self.scheduler.remove_job(job.id)


_scheduler_manager: BriefingSchedulerManager | None = None


def get_scheduler_manager() -> BriefingSchedulerManager:
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = BriefingSchedulerManager()
    return _scheduler_manager
