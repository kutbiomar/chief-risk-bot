from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.models.jobs import AsyncJob


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AsyncJobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        *,
        workspace_id: str,
        job_type: str,
        created_by: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request_payload: Optional[dict[str, Any]] = None,
    ) -> AsyncJob:
        job = AsyncJob(
            workspace_id=workspace_id,
            job_type=job_type,
            status="queued",
            created_by=created_by,
            resource_type=resource_type,
            resource_id=resource_id,
            request_json=json.dumps(request_payload or {}, sort_keys=True),
            attempt_count=0,
            progress_pct=0,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def mark_running(self, job: AsyncJob, *, started_children: Optional[int] = None) -> AsyncJob:
        job.status = "running"
        job.started_at = utc_now()
        if started_children is not None:
            job.started_children = started_children
        self.db.flush()
        return job

    def mark_finished(
        self,
        job: AsyncJob,
        *,
        status: str,
        result_payload: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        progress_pct: Optional[int] = 100,
        succeeded_children: Optional[int] = None,
        failed_children: Optional[int] = None,
    ) -> AsyncJob:
        job.status = status
        job.completed_at = utc_now()
        job.result_json = json.dumps(result_payload or {}, sort_keys=True)
        job.error_message = error_message
        if progress_pct is not None:
            job.progress_pct = progress_pct
        if succeeded_children is not None:
            job.succeeded_children = succeeded_children
        if failed_children is not None:
            job.failed_children = failed_children
        self.db.flush()
        return job

    def get_job(self, job_id: str) -> Optional[AsyncJob]:
        return self.db.get(AsyncJob, job_id)
