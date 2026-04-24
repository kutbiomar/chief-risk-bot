from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = BACKEND_ROOT / "runtime"
STORAGE_ROOT = RUNTIME_ROOT / "storage"
