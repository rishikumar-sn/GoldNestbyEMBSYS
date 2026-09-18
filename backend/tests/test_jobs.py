from io import BytesIO
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image

from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_engine, get_session
from app.main import app
from app.services.queue import SQLiteQueueProvider
from app.workers.jobs import process_one


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'jobs.sqlite3').as_posix()}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-hs256")
    get_settings.cache_clear()
    get_engine.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    with get_session() as session:
        session.add_all([User(username="alice", password_hash=hash_password("password-long-enough")),
                         User(username="bob", password_hash=hash_password("password-long-enough"))])
        session.commit()
    with TestClient(app) as api:
        yield api
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


def auth(client, username):
    data = client.post("/api/v1/auth/login", json={"username": username, "password": "password-long-enough",
                "installation_id": str(uuid4()), "platform": "android"}).json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def image_bytes():
    image = Image.new("RGB", (100, 100), "gold")
    output = BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def test_job_lifecycle_and_ownership(client):
    alice = auth(client, "alice")
    bob = auth(client, "bob")
    created = client.post("/api/v1/jobs", headers=alice, json={"mode": "group"})
    assert created.status_code == 201
    job_id = created.json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job_id}", headers=bob).status_code == 404
    assert client.post(f"/api/v1/jobs/{job_id}/submit", headers=alice).status_code == 409
    assert client.post(f"/api/v1/jobs/{job_id}/images", headers=alice,
                       files={"file": ("bad.jpg", b"bad", "image/jpeg")}).status_code == 422
    upload = client.post(f"/api/v1/jobs/{job_id}/images", headers=alice,
                         files={"file": ("input.jpg", image_bytes(), "image/jpeg")})
    assert upload.status_code == 200, upload.text
    assert client.get(f"/api/v1/jobs/{job_id}/artifacts/original.jpg", headers=bob).status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}/artifacts/original.jpg", headers=alice).status_code == 200
    assert client.post(f"/api/v1/jobs/{job_id}/submit", headers=alice).json()["status"] == "queued"
    assert client.post(f"/api/v1/jobs/{job_id}/submit", headers=alice).status_code == 409

    def dummy(job):
        return {"job_id": job.id, "mode": job.mode, "status": "completed", "physical_jewel_count": 0,
                "instances": [], "artifacts": {}, "analysis_engine": "test_dummy"}

    assert process_one(dummy)
    assert not process_one(dummy)
    result = client.get(f"/api/v1/jobs/{job_id}/result", headers=alice)
    assert result.status_code == 200
    assert result.json()["physical_jewel_count"] == 0
    assert client.get(f"/api/v1/jobs/{job_id}/result", headers=bob).status_code == 404
    assert len(client.get("/api/v1/jobs", headers=alice).json()) == 1
    assert not client.get("/api/v1/jobs", headers=bob).json()


def test_claim_once_and_failure(client):
    headers = auth(client, "alice")
    job_id = client.post("/api/v1/jobs", headers=headers, json={"mode": "single"}).json()["job_id"]
    client.post(f"/api/v1/jobs/{job_id}/images", headers=headers,
                files={"file": ("input.jpg", image_bytes(), "image/jpeg")})
    client.post(f"/api/v1/jobs/{job_id}/submit", headers=headers)
    with get_session() as session:
        assert SQLiteQueueProvider().claim(session).id == job_id
    with get_session() as session:
        assert SQLiteQueueProvider().claim(session) is None
    assert client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()["status"] == "processing"


def test_failed_job_is_visible(client):
    headers = auth(client, "alice")
    job_id = client.post("/api/v1/jobs", headers=headers, json={"mode": "single"}).json()["job_id"]
    client.post(f"/api/v1/jobs/{job_id}/images", headers=headers,
                files={"file": ("input.jpg", image_bytes(), "image/jpeg")})
    client.post(f"/api/v1/jobs/{job_id}/submit", headers=headers)

    def fails(_job):
        raise RuntimeError("inference failed")

    assert process_one(fails)
    status = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
    assert status["status"] == "failed"
    assert status["error_message"] == "inference failed"
    assert client.get(f"/api/v1/jobs/{job_id}/result", headers=headers).status_code == 409
