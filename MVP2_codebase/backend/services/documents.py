from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..models.content import Document, ExtractionResult
from ..services.extraction.classifier import classify_document
from ..services.extraction.extractors import extract_document
from ..services.extraction.reconciler import reconcile_document_data


def create_document(
    db: Session,
    *,
    workspace_id: str,
    uploaded_by_user_id: str,
    filename: str,
    payload: bytes,
    provider_name: Optional[str] = None,
) -> Document:
    runtime_dir = Path("MVP2_codebase/backend/runtime/uploads") / workspace_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    storage_path = runtime_dir / filename
    storage_path.write_bytes(payload)

    document = Document(
        workspace_id=workspace_id,
        uploaded_by_user_id=uploaded_by_user_id,
        filename=filename,
        file_type=filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt",
        file_size_bytes=len(payload),
        storage_path=str(storage_path),
        provider_name=provider_name,
        auto_category="other",
        processing_status="pending",
        extracted_data={},
        reconciliation_flags=[],
    )
    db.add(document)
    db.flush()
    return document


def parse_document(db: Session, document: Document) -> ExtractionResult:
    raw_text = Path(document.storage_path).read_text(errors="ignore")
    classification = classify_document(raw_text, document.filename)
    extracted = extract_document(classification["document_type"], raw_text)

    result = ExtractionResult(
        workspace_id=document.workspace_id,
        document_id=document.id,
        document_type=classification["document_type"],
        classification_confidence=classification["confidence"],
        raw_text=raw_text,
        extracted_json=extracted,
        confidence_json=extracted.get("confidence", {}),
        needs_review_count=sum(
            1 for value in extracted.get("confidence", {}).values() if isinstance(value, int) and value < 85
        ),
        raw_text_truncated=False,
        model="deterministic-fallback",
        input_tokens=0,
        output_tokens=0,
    )
    db.add(result)
    db.flush()

    document.auto_category = classification["document_type"]
    document.processing_status = "needs_review" if result.needs_review_count else "done"
    document.extraction_result_id = result.id
    document.extracted_data = extracted
    document.needs_review = result.needs_review_count > 0

    flags = reconcile_document_data(
        workspace_id=document.workspace_id,
        document_id=document.id,
        document_type=classification["document_type"],
        extracted_data=extracted,
        db=db,
    )
    document.reconciliation_flags = [
        {
            "id": flag.id,
            "field_name": flag.field_name,
            "severity": flag.severity,
            "status": flag.status,
        }
        for flag in flags
    ]
    return result


def apply_reconciliation_decision(
    db: Session,
    *,
    workspace_id: str,
    document: Document,
    resolution: dict,
) -> list[str]:
    from ..models.reconciliation import ReconciliationFlag

    updated: list[str] = []
    flag_ids = resolution.get("flag_ids", [])
    action = resolution.get("action", "resolved")
    notes = resolution.get("notes")
    flags = db.query(ReconciliationFlag).filter(
        ReconciliationFlag.workspace_id == workspace_id,
        ReconciliationFlag.document_id == document.id,
        ReconciliationFlag.id.in_(flag_ids),
    )
    for flag in flags:
        if action == "reopen":
            flag.status = "open"
        else:
            flag.status = "overridden" if action == "override" else "resolved"
        flag.resolution_notes = notes
        updated.append(flag.id)
    if updated and action == "reopen":
        document.processing_status = "needs_review"
        document.needs_review = True
    elif updated:
        document.processing_status = "done"
        document.needs_review = False
    return updated
