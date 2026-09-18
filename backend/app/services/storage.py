from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageProvider(Protocol):
    def write(self, job_id: str, name: str, data: bytes) -> str: ...
    def read(self, job_id: str, name: str) -> bytes: ...


class LocalStorageProvider:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().path(get_settings().storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str, name: str) -> Path:
        from uuid import UUID

        UUID(job_id)
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Invalid artifact name")
        return self.root / job_id / name

    def write(self, job_id: str, name: str, data: bytes) -> str:
        path = self._path(job_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return name

    def read(self, job_id: str, name: str) -> bytes:
        return self._path(job_id, name).read_bytes()

