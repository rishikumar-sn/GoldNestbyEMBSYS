from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import numpy as np
from PIL import Image

from app.ai import feedback
from app.core.config import get_settings
from app.db.models import AnalysisJob, JewelConfirmation, JewelInstance
from app.db.session import get_session
from app.services.storage import LocalStorageProvider
from test_jobs import auth, client, image_bytes


def _png(color):
    buffer = BytesIO()
    Image.new("RGB", (100, 100), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_confirm_overwrite_and_rebuild_gallery(client, tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    np.savez(model_dir / "jewelry_correction_gallery.npz",
             embeddings=np.array([[1., 0., 0.]], dtype=np.float32), labels=np.array(["Bangle"]))
    monkeypatch.setenv("SIGLIP_MODEL_DIR", str(model_dir))
    monkeypatch.setenv("CORRECTION_GALLERY_PATH", str(tmp_path / "learned.npz"))
    get_settings.cache_clear()
    samples = iter((np.array([1., 0., 0.], dtype=np.float32),
                    np.array([0., 0., 1.], dtype=np.float32)))
    monkeypatch.setattr(feedback, "_embedding", lambda _: next(samples))
    alice, bob = auth(client, "alice"), auth(client, "bob")
    assert client.get("/api/v1/jobs/labels", headers=alice).json()["labels"] == list(feedback.LABELS)
    job_id = client.post("/api/v1/jobs", headers=alice, json={"mode": "group"}).json()["job_id"]
    client.post(f"/api/v1/jobs/{job_id}/images", headers=alice,
                files={"file": ("original.jpg", image_bytes(), "image/jpeg")})
    storage = LocalStorageProvider()
    mask = Image.new("L", (100, 100))
    for number in (1, 2):
        storage.write(job_id, f"crop_{number}.png", _png("gold"))
        mask.paste(255, (number * 20, 20, number * 20 + 12, 32))
        buffer = BytesIO()
        mask.save(buffer, format="PNG")
        storage.write(job_id, f"mask_{number}.png", buffer.getvalue())
    items = []
    with get_session() as session:
        job = session.get(AnalysisJob, job_id)
        for number, label in ((1, "Bangle"), (2, "Bracelet")):
            classification = {"label": label, "classification_score": .7,
                              "gallery_match": False, "gallery_similarity": .0,
                              "is_gold_jewelry": True, "top_classes": [],
                              "classification_source": "white_crop", "needs_review": True}
            item = {"instance_id": str(uuid4()), "instance_number": number,
                    "bbox": {"x1": number * 20, "y1": 20, "x2": number * 20 + 12, "y2": 32},
                    "segmentation": {"source": "test", "score": .8},
                    "classification": classification,
                    "artifacts": {"crop": f"crop_{number}.png", "mask": f"mask_{number}.png"}}
            items.append(item)
            session.add(JewelInstance(id=item["instance_id"], job_id=job_id,
                                      instance_number=number, bbox=item["bbox"],
                                      segmentation=item["segmentation"],
                                      classification=classification,
                                      crop_artifact=item["artifacts"]["crop"],
                                      mask_artifact=item["artifacts"]["mask"]))
        job.status = "completed"
        job.result_json = {"job_id": job_id, "mode": "group", "status": "completed",
                           "captured_at": datetime.now(timezone.utc).isoformat(),
                           "display_timezone": "Asia/Kolkata", "instances": items,
                           "physical_jewel_count": 2, "type_counts": {"Bangle": 1, "Bracelet": 1},
                           "warnings": ["Review jewellery type for piece 1."],
                           "artifacts": {"original": "original.jpg", "annotated": "annotated.jpg"}}
        session.commit()
    endpoint = f"/api/v1/jobs/{job_id}/confirm"
    choices = {"items": [{"instance_number": 1, "label": "Finger Ring"},
                         {"instance_number": 2, "label": "Bracelet"}]}
    assert client.post(endpoint, headers=bob, json=choices).status_code == 404
    assert client.post(endpoint, headers=alice, json={"items": choices["items"][:1]}).status_code == 409
    assert client.post(endpoint, headers=alice, json={"items": [
        {"instance_number": 1, "label": "Invalid"}, choices["items"][1]]}).status_code == 422
    first = client.post(endpoint, headers=alice, json=choices)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["type_counts"] == {"Finger Ring": 1, "Bracelet": 1}
    assert result["instances"][0]["classification"]["predicted_label"] == "Bangle"
    assert result["instances"][0]["classification"]["confirmed_label"] == "Finger Ring"
    artifact = result["artifacts"]["annotated"]
    assert client.get(f"/api/v1/jobs/{job_id}/artifacts/{artifact}", headers=alice).status_code == 200
    with np.load(tmp_path / "learned.npz") as data:
        assert list(data["labels"]) == ["Finger Ring", "Bracelet"]
    assert client.post(endpoint, headers=alice, json=choices).status_code == 200
    choices["items"][0]["label"] = "Mattal"
    assert client.post(endpoint, headers=alice, json=choices).status_code == 200
    with np.load(tmp_path / "learned.npz") as data:
        assert list(data["labels"]) == ["Mattal", "Bracelet"]
    with get_session() as session:
        rows = session.query(JewelConfirmation).filter_by(job_id=job_id).all()
        assert len(rows) == 2
        assert session.get(AnalysisJob, job_id).result_json["type_counts"]["Mattal"] == 1
