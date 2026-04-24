from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.funds import Commitment
from ...models.reconciliation import ReconciliationFlag


def reconcile_document_data(
    *,
    workspace_id: str,
    document_id: str,
    document_type: str,
    extracted_data: dict,
    db: Session,
    variance_threshold_pct: Decimal = Decimal("2.0"),
) -> list[ReconciliationFlag]:
    flags: list[ReconciliationFlag] = []

    if document_type == "lp_statement":
        commitments = db.scalars(
            select(Commitment).where(
                Commitment.workspace_id == workspace_id,
                Commitment.deleted_at.is_(None),
            )
        ).all()
        if commitments and extracted_data.get("nav"):
            system_nav = commitments[0].nav or Decimal("0")
            document_nav = Decimal(str(extracted_data["nav"]))
            variance_pct = Decimal("0")
            if system_nav:
                variance_pct = abs((document_nav - system_nav) / system_nav) * Decimal("100")
            if not system_nav or variance_pct > variance_threshold_pct:
                flags.append(
                    ReconciliationFlag(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        entity_type="commitment",
                        entity_id=commitments[0].id if commitments else None,
                        field_name="nav",
                        document_value=str(document_nav),
                        system_value=str(system_nav),
                        variance_pct=variance_pct,
                        severity="high",
                        flagged_at=datetime.now(timezone.utc),
                        status="open",
                    )
                )

    if document_type == "capital_call" and extracted_data.get("due_date"):
        flags.append(
            ReconciliationFlag(
                workspace_id=workspace_id,
                document_id=document_id,
                entity_type="capital_event",
                entity_id=None,
                field_name="due_date",
                document_value=str(extracted_data["due_date"]),
                system_value=None,
                variance_pct=None,
                severity="critical",
                flagged_at=datetime.now(timezone.utc),
                status="open",
                resolution_notes="Capital call due date requires review",
            )
        )

    for flag in flags:
        db.add(flag)
    return flags
