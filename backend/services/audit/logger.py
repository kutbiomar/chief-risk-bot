from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.audit import AuditEvent


def _canonical_detail(detail: Optional[dict[str, object]]) -> str:
    return json.dumps(detail or {}, sort_keys=True, separators=(",", ":"))


class AuditLogger:
    """Append-only audit logger with workspace-local sequencing and hash chaining."""

    def __init__(self, db: Session):
        self.db = db

    def append_event(
        self,
        *,
        workspace_id: str,
        actor_type: str,
        event_type: str,
        action: str,
        subject_type: str,
        subject_id: str,
        actor_user_id: Optional[str] = None,
        detail: Optional[dict[str, object]] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> AuditEvent:
        previous = self.db.scalar(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace_id)
            .order_by(desc(AuditEvent.sequence_no))
            .limit(1)
        )
        sequence_no = 1 if previous is None else previous.sequence_no + 1
        prev_hash = "GENESIS" if previous is None else previous.event_hash
        timestamp = datetime.now(timezone.utc)
        detail_json = _canonical_detail(detail)
        event_id = str(uuid4())
        payload = f"{event_id}|{timestamp.isoformat()}|{action}|{prev_hash}|{detail_json}"
        event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        event = AuditEvent(
            id=event_id,
            workspace_id=workspace_id,
            sequence_no=sequence_no,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            event_type=event_type,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            detail_json=detail_json,
            ip_address=ip_address,
            device_info=device_info,
            prev_hash=prev_hash,
            event_hash=event_hash,
            created_at=timestamp,
        )
        self.db.add(event)
        self.db.flush()
        return event
