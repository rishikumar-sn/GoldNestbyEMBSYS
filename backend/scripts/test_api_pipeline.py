from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise the real model pipeline through the authenticated API")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    image_path = args.image.resolve()
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    # Application settings deliberately use backend-relative paths. Set that
    # base explicitly so invoking this file from the repository root is safe.
    os.chdir(ROOT)

    with ExitStack() as cleanup:
        directory = cleanup.enter_context(TemporaryDirectory(prefix="goldnest-api-pipeline-"))
        temporary = Path(directory)
        os.environ["DATABASE_URL"] = f"sqlite:///{(temporary / 'test.sqlite3').as_posix()}"
        os.environ["STORAGE_ROOT"] = str(temporary / "storage")
        os.environ["JWT_SECRET"] = "phase-eight-integration-test-secret"

        from alembic import command
        from alembic.config import Config
        from fastapi.testclient import TestClient
        from PIL import Image
        from io import BytesIO

        from app.ai.pipeline import AnalysisPipeline
        from app.auth.security import hash_password
        from app.db.models import User
        from app.db.session import get_engine, get_session
        from app.main import app
        from app.workers.jobs import process_one

        cleanup.callback(get_engine().dispose)

        alembic_config = Config(str(ROOT / "alembic.ini"))
        # Alembic resolves ``script_location`` relative to the caller's current
        # directory by default. This CLI is intentionally runnable from either
        # the repository root or ``backend/``.
        alembic_config.set_main_option("script_location", str(ROOT / "migrations"))
        command.upgrade(alembic_config, "head")
        with get_session() as session:
            session.add(User(username="phase8", password_hash=hash_password("integration-test-password")))
            session.commit()

        with TestClient(app) as client:
            login = client.post("/api/v1/auth/login", json={
                "username": "phase8", "password": "integration-test-password",
                "installation_id": str(uuid4()), "platform": "android",
            })
            assert login.status_code == 200, login.text
            auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

            created = client.post("/api/v1/jobs", headers=auth, json={
                "mode": "group", "captured_at": "2026-08-25T16:12:41+05:30",
            })
            assert created.status_code == 201, created.text
            job_id = created.json()["job_id"]
            upload = client.post(f"/api/v1/jobs/{job_id}/images", headers=auth,
                                 files={"file": (image_path.name, image_bytes, mime)})
            assert upload.status_code == 200, upload.text
            assert upload.json()["artifact"] == ("original.png" if mime == "image/png" else "original.jpg")
            submitted = client.post(f"/api/v1/jobs/{job_id}/submit", headers=auth)
            assert submitted.status_code == 200 and submitted.json()["status"] == "queued", submitted.text

            assert process_one(AnalysisPipeline())
            status = client.get(f"/api/v1/jobs/{job_id}", headers=auth)
            assert status.status_code == 200 and status.json()["status"] == "completed", status.text
            response = client.get(f"/api/v1/jobs/{job_id}/result", headers=auth)
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["physical_jewel_count"] == args.expected_count, result
            assert sum(result["type_counts"].values()) == args.expected_count
            assert len(result["instances"]) == args.expected_count
            assert result["captured_at"] == "2026-08-25T10:42:41Z"
            assert "weight" not in json.dumps(result).lower()

            artifact_ids = [result["artifacts"]["annotated"]]
            for instance in result["instances"]:
                artifact_ids.extend(instance["artifacts"].values())
            for artifact_id in artifact_ids:
                artifact = client.get(f"/api/v1/jobs/{job_id}/artifacts/{artifact_id}", headers=auth)
                assert artifact.status_code == 200, (artifact_id, artifact.text)
                with Image.open(BytesIO(artifact.content)) as image:
                    image.verify()
            assert client.get(f"/api/v1/jobs/{job_id}/artifacts/unknown.jpg", headers=auth).status_code == 404
            print(json.dumps({
                "job_id": job_id, "status": status.json()["status"],
                "physical_jewel_count": result["physical_jewel_count"],
                "type_counts": result["type_counts"], "artifact_count": len(artifact_ids),
                "warnings": result["warnings"],
            }, indent=2))


if __name__ == "__main__":
    main()
