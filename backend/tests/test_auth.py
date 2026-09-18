from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.models import RefreshToken, User
from app.db.session import get_engine, get_session
from app.main import app
from scripts.generate_lan_certificate import generate


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'auth.sqlite3').as_posix()}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-hs256")
    get_settings.cache_clear()
    get_engine.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    with get_session() as session:
        session.add(User(username="alice", password_hash=hash_password("password-long-enough")))
        session.commit()
    with TestClient(app) as api:
        yield api
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_login_refresh_logout_and_device(client):
    body = {"username": "alice", "password": "password-long-enough", "installation_id": str(uuid4()),
            "platform": "android", "app_version": "1.0"}
    assert client.post("/api/v1/auth/login", json={**body, "password": "wrong"}).status_code == 401
    login = client.post("/api/v1/auth/login", json=body)
    assert login.status_code == 200, login.text
    first = login.json()
    assert client.get("/api/v1/devices/me", headers={"Authorization": f"Bearer {first['access_token']}"}).status_code == 200
    with get_session() as session:
        token = session.scalar(select(RefreshToken))
        assert token.token_hash != first["refresh_token"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    second = refreshed.json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": second["refresh_token"]}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401
    assert client.get("/api/v1/devices/me").status_code == 401


def test_device_revocation(client):
    login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password-long-enough",
        "installation_id": str(uuid4()), "platform": "android"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.post("/api/v1/devices/revoke", headers=headers).status_code == 200
    assert client.get("/api/v1/devices/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401


def test_certificate(tmp_path):
    cert, key = generate(["127.0.0.1", "192.168.1.20"], tmp_path)
    assert b"BEGIN CERTIFICATE" in cert.read_bytes()
    assert b"BEGIN PRIVATE KEY" in key.read_bytes()
    with pytest.raises(FileExistsError):
        generate(["127.0.0.1"], tmp_path)
