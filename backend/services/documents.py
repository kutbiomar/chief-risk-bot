from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.constants import ASSET_CLASS_ALIASES
from backend.models.content import Document, ExtractionArtifact, ExtractionResult
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.storage import read_document, store_document
from backend.services.ingest.pipeline import run_document_pipeline

DOCUMENT_LIMIT_BYTES = 50 * 1024 * 1024
DOCUMENT_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
}
HEADER_ALIASES = {
    "ticker": "ticker",
    "symbol": "ticker",
    "security": "name",
    "security name": "name",
    "name": "name",
    "description": "name",
    "quantity": "quantity",
    "qty": "quantity",
    "shares": "quantity",
    "units": "quantity",
    "market value": "market_value_usd",
    "market value usd": "market_value_usd",
    "market_value_usd": "market_value_usd",
    "value": "market_value_usd",
    "asset class": "asset_class",
    "asset_class": "asset_class",
    "custodian": "custodian",
    "region": "geo_region",
    "geo region": "geo_region",
    "geo_region": "geo_region",
    "sector": "sector",
    "market segment": "market_segment",
    "market_segment": "market_segment",
    "currency": "position_currency",
    "position currency": "position_currency",
    "position_currency": "position_currency",
    "notes": "notes",
}
DEFAULT_EXTRACTED_ROW = {
    "ticker": None,
    "name": None,
    "quantity": None,
    "market_value_usd": None,
    "asset_class": None,
    "custodian": None,
    "geo_region": None,
    "sector": None,
    "market_segment": None,
    "position_currency": "USD",
    "notes": "Manual review required",
    "factor_asset_class": None,
    "factor_sector": None,
    "factor_subsector": None,
    "factor_country": None,
    "factor_region": None,
    "factor_market_segment": None,
    "factor_tag_source": None,
    "factor_tag_confidence": None,
}

FRIENDLY_PARSE_ERRORS = {
    "pdf": "Unable to parse this PDF - it may be corrupted, password-protected, or not a valid PDF.",
    "docx": "Unable to parse this DOCX file - it may be corrupted, password-protected, or not a valid Word document.",
    "xlsx": "Unable to parse this XLSX file - it may be corrupted, password-protected, or not a valid Excel workbook.",
}


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_header(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    slug = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return HEADER_ALIASES.get(slug, HEADER_ALIASES.get(slug.replace(" ", "_")))


def _parse_float(value: object) -> float | None:
    text = _normalize_text(value)
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
    cleaned = cleaned.replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_asset_class(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return ASSET_CLASS_ALIASES.get(text.lower(), text.lower().replace(" ", "_"))


def _looks_like_ticker(value: str | None) -> bool:
    if value is None:
        return False
    return bool(re.fullmatch(r"[A-Z0-9.\-]{1,12}", value.upper()))


def _is_pdf_encrypted(payload: bytes) -> bool:
    return b"/Encrypt" in payload[:4096] or b"/Encrypt" in payload


def _validate_magic_bytes(extension: str, payload: bytes) -> None:
    if extension == ".pdf" and not payload.startswith(b"%PDF"):
        raise ValueError("PDF upload failed signature validation")
    if extension == ".docx" and not payload.startswith(b"PK"):
        raise ValueError("DOCX upload failed signature validation")
    if extension == ".xlsx" and not payload.startswith(b"PK"):
        raise ValueError("XLSX upload failed signature validation")


def validate_document_upload(filename: str, payload: bytes) -> tuple[str, str, str]:
    normalized = Path(filename).name
    extension = Path(normalized).suffix.lower()
    if extension not in DOCUMENT_TYPES:
        raise ValueError("Only PDF, DOCX, and XLSX files are accepted")
    if len(payload) > DOCUMENT_LIMIT_BYTES:
        raise ValueError("Document exceeds the 50MB upload limit")
    if ".." in normalized or "/" in normalized or "\\" in normalized:
        raise ValueError("Filename contains invalid traversal semantics")
    if extension == ".pdf" and _is_pdf_encrypted(payload):
        raise ValueError("Encrypted PDF files are not supported")
    _validate_magic_bytes(extension, payload)
    return normalized, DOCUMENT_TYPES[extension], extension


def create_document(db: Session, *, workspace_id: str, uploaded_by: str, filename: str, payload: bytes, folder: str) -> Document:
    normalized, file_type, extension = validate_document_upload(filename, payload)
    digest, storage_path = store_document(
        workspace_id=workspace_id,
        payload=payload,
        extension=extension,
    )
    document = Document(
        workspace_id=workspace_id,
        uploaded_by=uploaded_by,
        filename=normalized,
        file_type=file_type,
        file_size_bytes=len(payload),
        sha256=digest,
        storage_path=storage_path,
        folder=folder,
        malware_scan_status="clean",
        extraction_status="pending",
    )
    db.add(document)
    db.flush()
    return document


def _load_extraction_or_raise(db: Session, document: Document) -> ExtractionResult:
    if document.extraction_result_id is None:
        raise ValueError("Document must be parsed before review")
    extraction = db.get(ExtractionResult, document.extraction_result_id)
    if extraction is None:
        raise ValueError("Extraction result not found")
    return extraction


def _load_confidence_payload(extraction: ExtractionResult) -> dict[str, object]:
    payload = json.loads(extraction.confidence_json)
    if isinstance(payload, list):
        return {
            "rows": payload,
            "classification": {},
            "risk": {},
            "treasury": {},
            "reconciliation": {
                "overall_confidence": 0.0,
                "errors": [],
                "field_reviews": [],
                "model": extraction.model,
            },
        }
    return payload


def _artifact_payloads(db: Session, extraction: ExtractionResult) -> dict[str, object]:
    rows = db.scalars(
        select(ExtractionArtifact).where(ExtractionArtifact.extraction_result_id == extraction.id)
    ).all()
    return {row.artifact_type: json.loads(row.payload_json) for row in rows}


def _replace_extraction_artifacts(db: Session, extraction: ExtractionResult, artifacts: dict[str, object]) -> None:
    db.execute(delete(ExtractionArtifact).where(ExtractionArtifact.extraction_result_id == extraction.id))
    for artifact_type, payload in artifacts.items():
        db.add(
            ExtractionArtifact(
                extraction_result_id=extraction.id,
                artifact_type=artifact_type,
                payload_json=json.dumps(payload, sort_keys=True),
            )
        )
    db.flush()


def _reviewed_position_confidence(positions: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, position in enumerate(positions, start=1):
        ticker = _normalize_text(position.get("ticker"))
        quantity = _parse_float(position.get("quantity"))
        market_value = _parse_float(position.get("market_value_usd"))
        asset_class = _normalize_text(position.get("asset_class"))
        confidence = 0.95
        issues: list[str] = []
        if ticker is None:
            confidence = min(confidence, 0.35)
            issues.append("ticker missing")
        if quantity is None:
            confidence = min(confidence, 0.35)
            issues.append("quantity missing")
        if market_value is None:
            confidence = min(confidence, 0.7)
            issues.append("market value missing")
        if asset_class is None:
            confidence = min(confidence, 0.82)
            issues.append("asset class missing")
        rows.append({"row": index, "confidence": round(confidence, 2), "issues": issues})
    return rows


def _normalize_review_positions(positions: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized_positions: list[dict[str, object]] = []
    for position in positions:
        normalized_positions.append(
            {
                "ticker": _normalize_text(position.get("ticker")),
                "name": _normalize_text(position.get("name")),
                "quantity": _parse_float(position.get("quantity")),
                "market_value_usd": _parse_float(position.get("market_value_usd")),
                "asset_class": _normalize_asset_class(position.get("asset_class")),
                "custodian": _normalize_text(position.get("custodian")),
                "geo_region": _normalize_text(position.get("geo_region")),
                "sector": _normalize_text(position.get("sector")),
                "market_segment": _normalize_text(position.get("market_segment")),
                "position_currency": (_normalize_text(position.get("position_currency")) or "USD").upper(),
                "notes": _normalize_text(position.get("notes")),
                "source_ref": position.get("source_ref"),
                "factor_asset_class": _normalize_text(position.get("factor_asset_class")),
                "factor_sector": _normalize_text(position.get("factor_sector")),
                "factor_subsector": _normalize_text(position.get("factor_subsector")),
                "factor_country": _normalize_text(position.get("factor_country")),
                "factor_region": _normalize_text(position.get("factor_region")),
                "factor_market_segment": _normalize_text(position.get("factor_market_segment")),
                "factor_tag_source": _normalize_text(position.get("factor_tag_source")),
                "factor_tag_confidence": _parse_float(position.get("factor_tag_confidence")),
            }
        )
    return normalized_positions


def _normalize_review_treasury(
    treasury: dict[str, object] | None,
    *,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized = dict(existing or {})
    if treasury is None:
        return normalized
    normalized.update(
        {
            "call_amount": _parse_float(treasury.get("call_amount")),
            "call_due_date": _normalize_text(treasury.get("call_due_date")),
            "distribution_amount": _parse_float(treasury.get("distribution_amount")),
            "distribution_date": _normalize_text(treasury.get("distribution_date")),
            "wire_bank": _normalize_text(treasury.get("wire_bank")),
            "wire_account": _normalize_text(treasury.get("wire_account")),
            "wire_routing": _normalize_text(treasury.get("wire_routing")),
            "wire_reference": _normalize_text(treasury.get("wire_reference")),
            "contact_name": _normalize_text(treasury.get("contact_name")),
            "contact_email": _normalize_text(treasury.get("contact_email")),
        }
    )
    return normalized


def _recalculate_review_state(
    *,
    extraction: ExtractionResult,
    document: Document,
    positions: list[dict[str, object]],
    confidence_payload: dict[str, object],
) -> None:
    confidence_rows = confidence_payload.get("rows", [])
    if not isinstance(confidence_rows, list):
        confidence_rows = []
    field_reviews = confidence_payload.setdefault("reconciliation", {}).get("field_reviews", [])
    if not isinstance(field_reviews, list):
        field_reviews = []
        confidence_payload["reconciliation"]["field_reviews"] = field_reviews

    unresolved_field_reviews = [
        item for item in field_reviews if not bool(item.get("resolved"))
    ]
    importable_positions = [
        position for position in positions if position.get("ticker") and position.get("quantity") is not None
    ]
    low_confidence_rows = [
        row for row in confidence_rows if float(row.get("confidence", 0.0)) < 0.75
    ]
    overall_confidence = round(
        sum(float(row.get("confidence", 0.0)) for row in confidence_rows) / len(confidence_rows),
        2,
    ) if confidence_rows else 0.0

    reconciliation = confidence_payload.setdefault("reconciliation", {})
    existing_errors = reconciliation.get("errors", [])
    if not isinstance(existing_errors, list):
        existing_errors = []
    errors = [
        error
        for error in existing_errors
        if error not in {"confidence_below_threshold", "no_positions_extracted"}
    ]
    if not importable_positions:
        errors.append("no_positions_extracted")
    if overall_confidence < 0.85:
        errors.append("confidence_below_threshold")

    reconciliation["errors"] = errors
    reconciliation["overall_confidence"] = overall_confidence
    needs_review_count = len(unresolved_field_reviews) + len(low_confidence_rows)
    extraction.needs_review_count = needs_review_count
    extraction.extracted_row_count = len(positions)
    extraction.positions_json = json.dumps(positions, sort_keys=True)
    extraction.confidence_json = json.dumps(confidence_rows, sort_keys=True)
    document.extraction_status = "needs_review" if errors or unresolved_field_reviews or low_confidence_rows else "done"


def get_document_review(db: Session, document: Document) -> dict[str, object]:
    extraction = _load_extraction_or_raise(db, document)
    artifacts = _artifact_payloads(db, extraction)
    confidence_payload = _load_confidence_payload(extraction)
    reconciliation = artifacts.get("reconciliation", confidence_payload.get("reconciliation", {}))
    field_reviews = reconciliation.get("field_reviews", []) if isinstance(reconciliation, dict) else []
    return {
        "id": extraction.id,
        "positions": json.loads(extraction.positions_json),
        "confidence": confidence_payload.get("rows", []) if isinstance(confidence_payload, dict) else confidence_payload,
        "needs_review_count": extraction.needs_review_count,
        "raw_text_truncated": extraction.raw_text_truncated,
        "layout": artifacts.get("layout", {}),
        "classification": artifacts.get("classification", confidence_payload.get("classification", {})),
        "risk": artifacts.get("risk", confidence_payload.get("risk", {})),
        "treasury": artifacts.get("treasury", confidence_payload.get("treasury", {})),
        "reconciliation": reconciliation if isinstance(reconciliation, dict) else {},
        "field_reviews": field_reviews if isinstance(field_reviews, list) else [],
    }


def update_document_review(
    db: Session,
    document: Document,
    *,
    positions: list[dict[str, object]] | None,
    treasury: dict[str, object] | None,
    resolved_fields: list[str] | None,
) -> ExtractionResult:
    extraction = _load_extraction_or_raise(db, document)
    confidence_payload = _load_confidence_payload(extraction)
    if not isinstance(confidence_payload, dict):
        confidence_payload = {"rows": confidence_payload}
    current_positions = json.loads(extraction.positions_json)
    artifacts = _artifact_payloads(db, extraction)

    if positions is not None:
        current_positions = _normalize_review_positions(positions)
        confidence_payload["rows"] = _reviewed_position_confidence(current_positions)

    current_treasury = artifacts.get("treasury", {})
    if not isinstance(current_treasury, dict):
        current_treasury = {}
    if treasury is not None:
        artifacts["treasury"] = _normalize_review_treasury(treasury, existing=current_treasury)

    reconciliation = artifacts.get("reconciliation", {})
    if not isinstance(reconciliation, dict):
        reconciliation = {}
    field_reviews = reconciliation.setdefault("field_reviews", [])
    if isinstance(field_reviews, list):
        resolved_set = set(resolved_fields or [])
        for item in field_reviews:
            if item.get("field") in resolved_set:
                item["resolved"] = True
                item["resolution_note"] = "resolved_in_review"

    _recalculate_review_state(
        extraction=extraction,
        document=document,
        positions=current_positions,
        confidence_payload={**confidence_payload, "reconciliation": reconciliation},
    )
    _replace_extraction_artifacts(
        db,
        extraction,
        {
            **artifacts,
            "reconciliation": reconciliation,
        },
    )
    db.flush()
    return extraction


async def parse_document(db: Session, document: Document) -> ExtractionResult:
    payload = read_document(document.storage_path)
    try:
        pipeline = await run_document_pipeline(
            filename=document.filename,
            file_type=document.file_type,
            payload=payload,
        )
    except ValueError as exc:
        raise exc
    except Exception as exc:
        raise ValueError(FRIENDLY_PARSE_ERRORS.get(document.file_type, "Unable to parse document")) from exc

    reconciliation = pipeline["reconciliation"]
    positions = reconciliation["positions"]
    confidence = reconciliation["confidence_rows"]
    raw_text = pipeline["layout"]["raw_text"]
    truncated = pipeline["layout"]["raw_text_truncated"]
    page_count = pipeline["layout"]["page_count"]

    if not positions:
        positions = [dict(DEFAULT_EXTRACTED_ROW, notes=f"Manual review required for {document.file_type} extraction")]
        confidence = [{"row": 1, "confidence": 0.25, "issues": ["no structured positions extracted"]}]

    needs_review = sum(
        1 for item in confidence if float(item.get("confidence", 0.0)) < 0.75
    )
    needs_review += len(reconciliation["field_reviews"])
    extraction = ExtractionResult(
        document_id=document.id,
        positions_json=json.dumps(positions, sort_keys=True),
        raw_text=raw_text or f"Parsed preview for {document.filename}",
        confidence_json=json.dumps(confidence, sort_keys=True),
        needs_review_count=needs_review,
        raw_text_truncated=truncated,
        extracted_row_count=len(positions),
        model=f"{pipeline['layout']['parser']}|{pipeline['classification']['model']}|{reconciliation['reconciliation_model']}",
        input_tokens=0,
        output_tokens=0,
    )
    db.add(extraction)
    db.flush()
    _replace_extraction_artifacts(
        db,
        extraction,
        {
            "layout": pipeline["layout"].get("layout_artifact", {}),
            "classification": pipeline["classification"],
            "risk": pipeline["risk"],
            "treasury": pipeline["treasury"],
            "reconciliation": {
                "overall_confidence": reconciliation["overall_confidence"],
                "errors": reconciliation["errors"],
                "field_reviews": reconciliation["field_reviews"],
                "model": reconciliation["reconciliation_model"],
            },
        },
    )
    document.extraction_result_id = extraction.id
    document.extraction_status = "needs_review" if reconciliation["needs_review"] else "done"
    document.page_count = page_count
    document.tag = pipeline["classification"]["doc_type"].lower()
    db.flush()
    return extraction


def _clone_snapshot_from_positions(
    db: Session,
    *,
    workspace_id: str,
    uploaded_by: str,
    source: str,
    source_ref: str,
    positions: list[dict[str, object]],
) -> PortfolioSnapshot:
    current_snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if current_snapshot is not None:
        demoted = db.execute(
            update(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.id == current_snapshot.id,
                PortfolioSnapshot.workspace_id == workspace_id,
                PortfolioSnapshot.is_current.is_(True),
            )
            .values(is_current=False)
        )
        if demoted.rowcount != 1:
            raise ValueError("Current snapshot changed during document approval. Retry the request.")

    total_aum = round(
        sum(float(position.get("market_value_usd") or 0.0) for position in positions),
        2,
    )
    snapshot = PortfolioSnapshot(
        workspace_id=workspace_id,
        parent_snapshot_id=current_snapshot.id if current_snapshot is not None else None,
        uploaded_by=uploaded_by,
        source=source,
        source_ref=source_ref,
        position_count=len(positions),
        total_aum_usd=total_aum,
        is_current=True,
    )
    db.add(snapshot)
    db.flush()

    for position in positions:
        quantity = float(position.get("quantity") or 0.0)
        market_value = position.get("market_value_usd")
        market_value_usd = float(market_value) if market_value is not None else None
        db.add(
            Position(
                id=str(uuid4()),
                snapshot_id=snapshot.id,
                workspace_id=workspace_id,
                ticker=str(position.get("ticker") or "UNKNOWN").upper(),
                name=_normalize_text(position.get("name")),
                position_currency=str(position.get("position_currency") or "USD"),
                quantity=quantity,
                market_value_usd=market_value_usd,
                asset_class=str(position.get("asset_class") or "alternative"),
                geo_region=_normalize_text(position.get("geo_region")),
                sector=_normalize_text(position.get("sector")),
                market_segment=_normalize_text(position.get("market_segment")),
                factor_asset_class=_normalize_text(position.get("factor_asset_class")),
                factor_sector=_normalize_text(position.get("factor_sector")),
                factor_subsector=_normalize_text(position.get("factor_subsector")),
                factor_country=_normalize_text(position.get("factor_country")),
                factor_region=_normalize_text(position.get("factor_region")),
                factor_market_segment=_normalize_text(position.get("factor_market_segment")),
                factor_tag_source=_normalize_text(position.get("factor_tag_source")),
                factor_tag_confidence=_parse_float(position.get("factor_tag_confidence")),
                custodian=_normalize_text(position.get("custodian")),
                price_source="document_approved",
                notes=_normalize_text(position.get("notes")),
            )
        )

    db.flush()
    return snapshot


def approve_document_extraction(db: Session, document: Document) -> PortfolioSnapshot:
    extraction = _load_extraction_or_raise(db, document)

    raw_positions = json.loads(extraction.positions_json)
    approved_positions = [
        position
        for position in raw_positions
        if position.get("ticker") and position.get("quantity") is not None
    ]
    if not approved_positions:
        raise ValueError("No importable positions found in extraction result")

    snapshot = _clone_snapshot_from_positions(
        db,
        workspace_id=document.workspace_id,
        uploaded_by=document.uploaded_by,
        source="document_approved",
        source_ref=document.filename,
        positions=approved_positions,
    )
    document.tag = "reconciled"
    db.flush()
    return snapshot
