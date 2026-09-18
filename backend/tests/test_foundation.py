from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import LocalStorageProvider


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_storage(tmp_path):
    store = LocalStorageProvider(tmp_path)
    job_id = str(uuid4())
    assert store.write(job_id, "original.jpg", b"image") == "original.jpg"
    assert store.read(job_id, "original.jpg") == b"image"

