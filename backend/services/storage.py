from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.config import get_settings
from backend.paths import STORAGE_ROOT


def is_supabase_storage_enabled() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key and settings.supabase_storage_bucket)


def _local_document_path(workspace_id: str, digest: str, extension: str) -> Path:
    root = STORAGE_ROOT / "documents" / workspace_id
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{digest[:16]}{extension}"


def _supabase_storage_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def _ensure_supabase_bucket(bucket: str) -> None:
    settings = get_settings()
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket",
        data=f'{{"id":"{bucket}","name":"{bucket}","public":false}}'.encode("utf-8"),
        headers={
            **_supabase_storage_headers(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20):
            return
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 409 or "Duplicate" in detail or "already exists" in detail:
            return
        raise ValueError(detail or "Unable to create Supabase Storage bucket") from exc
    except URLError as exc:
        raise ValueError("Unable to reach Supabase Storage") from exc


def _upload_supabase_object(*, bucket: str, object_key: str, payload: bytes) -> None:
    settings = get_settings()
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{quote(object_key)}",
        data=payload,
        headers={
            **_supabase_storage_headers(),
            "Content-Type": "application/octet-stream",
            "x-upsert": "true",
        },
        method="POST",
    )
    with urlopen(request, timeout=20):
        pass


def store_document(*, workspace_id: str, payload: bytes, extension: str) -> tuple[str, str]:
    digest = hashlib.sha256(payload).hexdigest()

    if is_supabase_storage_enabled():
        settings = get_settings()
        object_key = f"{workspace_id}/{digest[:16]}{extension}"
        try:
            _upload_supabase_object(
                bucket=settings.supabase_storage_bucket,
                object_key=object_key,
                payload=payload,
            )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 400 and "Bucket not found" in detail:
                _ensure_supabase_bucket(settings.supabase_storage_bucket)
                _upload_supabase_object(
                    bucket=settings.supabase_storage_bucket,
                    object_key=object_key,
                    payload=payload,
                )
                return digest, f"supabase://{settings.supabase_storage_bucket}/{object_key}"
            raise ValueError(detail or "Unable to upload document to Supabase Storage") from exc
        except URLError as exc:
            raise ValueError("Unable to reach Supabase Storage") from exc
        return digest, f"supabase://{settings.supabase_storage_bucket}/{object_key}"

    path = _local_document_path(workspace_id, digest, extension)
    path.write_bytes(payload)
    return digest, f"file://{path}"


def read_document(storage_path: str) -> bytes:
    if storage_path.startswith("supabase://"):
        settings = get_settings()
        _, _, remainder = storage_path.partition("supabase://")
        bucket, _, object_key = remainder.partition("/")
        request = Request(
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{quote(object_key)}",
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(detail or "Unable to read document from Supabase Storage") from exc
        except URLError as exc:
            raise ValueError("Unable to reach Supabase Storage") from exc

    if storage_path.startswith("file://"):
        return Path(storage_path.removeprefix("file://")).read_bytes()
    return Path(storage_path).read_bytes()
