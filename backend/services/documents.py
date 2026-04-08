from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.models.content import Document, ExtractionResult

DOCUMENT_LIMIT_BYTES = 50 * 1024 * 1024
DOCUMENT_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
}


def validate_document_upload(filename: str, payload: bytes) -> tuple[str, str]:
    normalized = Path(filename).name
    extension = Path(normalized).suffix.lower()
    if extension not in DOCUMENT_TYPES:
        raise ValueError("Only PDF, DOCX, and XLSX files are accepted")
    if len(payload) > DOCUMENT_LIMIT_BYTES:
        raise ValueError("Document exceeds the 50MB demo limit")
    if ".." in normalized or "/" in normalized or "\\" in normalized:
        raise ValueError("Filename contains invalid traversal semantics")
    return normalized, DOCUMENT_TYPES[extension]


def create_document(db: Session, *, workspace_id: str, uploaded_by: str, filename: str, payload: bytes, folder: str) -> Document:
    normalized, file_type = validate_document_upload(filename, payload)
    document = Document(
        workspace_id=workspace_id,
        uploaded_by=uploaded_by,
        filename=normalized,
        file_type=file_type,
        file_size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        storage_path=f"storage/documents/{workspace_id}/pending/{hashlib.sha256(payload).hexdigest()[:16]}",
        folder=folder,
        malware_scan_status="clean",
        extraction_status="pending",
    )
    db.add(document)
    db.flush()
    return document


def parse_document(db: Session, document: Document) -> ExtractionResult:
    raw_text = f"Parsed preview for {document.filename}"
    positions = [
        {
            "ticker": None,
            "security_id": None,
            "quantity": None,
            "asset_class": None,
            "notes": "Manual review required for deterministic document parser",
        }
    ]
    extraction = ExtractionResult(
        document_id=document.id,
        positions_json=json.dumps(positions, sort_keys=True),
        raw_text=raw_text,
        confidence_json=json.dumps([{"row": 1, "confidence": 0.35}], sort_keys=True),
        needs_review_count=1,
        raw_text_truncated=False,
        extracted_row_count=1,
    )
    db.add(extraction)
    db.flush()
    document.extraction_result_id = extraction.id
    document.extraction_status = "done"
    db.flush()
    return extraction
