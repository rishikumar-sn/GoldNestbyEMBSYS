"""Persist human reviewed examples in a replaceable SigLIP correction gallery."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

from filelock import FileLock
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.annotation import render_result_image
from app.ai.instances import DetectedInstance
from app.ai.siglip import SiglipJewelleryClassifier
from app.core.config import Settings, get_settings
from app.db.models import AnalysisJob, JewelConfirmation, utcnow
from app.services.storage import LocalStorageProvider


LABELS = ("Bangle", "Bracelet", "Chain / Necklace", "Earrings / Nosepin",
          "Finger Ring", "Mattal", "Other Gold Jewellery")


@lru_cache(maxsize=1)
def get_feedback_classifier() -> SiglipJewelleryClassifier:
    return SiglipJewelleryClassifier(get_settings())


def _embedding(crop: bytes) -> np.ndarray:
    with Image.open(BytesIO(crop)) as image:
        vector = get_feedback_classifier().classifier.embedding_for_image(image.convert("RGB"))
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    if vector.size == 0 or not np.isfinite(vector).all():
        raise ValueError("Invalid SigLIP embedding")
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("Zero SigLIP embedding")
    return vector / norm


def rebuild_gallery(session: Session, settings: Settings | None = None) -> Path:
    """Use the seed and latest DB confirmations; write an atomic NPZ for workers."""
    settings = settings or get_settings()
    seed = settings.path(settings.siglip_model_dir) / "jewelry_correction_gallery.npz"
    output = settings.path(settings.correction_gallery_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output) + ".lock", timeout=30):
        with np.load(seed, allow_pickle=False) as data:
            embeddings = np.asarray(data["embeddings"], dtype=np.float32)
            labels = [str(label) for label in data["labels"].tolist()]
        if embeddings.ndim != 2 or embeddings.shape[0] != len(labels):
            raise ValueError("Seed correction gallery is malformed")
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        if not np.isfinite(embeddings).all() or np.any(norms == 0):
            raise ValueError("Seed correction gallery has invalid embeddings")
        embeddings = embeddings / norms
        from models.siglip2.jewelry_classifier import canonicalize_jewelry_label

        labels = [canonicalize_jewelry_label(label) for label in labels]
        rows = session.scalars(select(JewelConfirmation).order_by(JewelConfirmation.confirmed_at,
                                                                  JewelConfirmation.job_id,
                                                                  JewelConfirmation.instance_number)).all()
        for row in rows:
            vector = np.frombuffer(row.embedding, dtype=np.float32)
            if (vector.shape != (embeddings.shape[1],) or not np.isfinite(vector).all()
                    or np.linalg.norm(vector) == 0):
                raise ValueError(f"Invalid confirmation embedding for {row.job_id}:{row.instance_number}")
            vector = vector / np.linalg.norm(vector)
            # The latest human confirmation takes precedence over an identical
            # seed example or an earlier contradictory confirmation.
            matching = embeddings @ vector >= 0.9995
            conflicts = matching & np.array([label != row.confirmed_label for label in labels], dtype=bool)
            if conflicts.any():
                embeddings = embeddings[~conflicts]
                labels = [label for index, label in enumerate(labels) if not conflicts[index]]
            same = np.array([label == row.confirmed_label for label in labels], dtype=bool)
            if same.any() and np.max(embeddings[same] @ vector) >= 0.9995:
                continue
            embeddings = np.vstack((embeddings, vector))
            labels.append(row.confirmed_label)
        temporary = output.with_name(f".{output.stem}.{uuid4().hex}.npz")
        try:
            np.savez_compressed(temporary, embeddings=embeddings,
                                labels=np.asarray(labels, dtype=str))
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return output


def confirm_job(session: Session, job: AnalysisJob, user_id: str,
                selected: dict[int, str], storage: LocalStorageProvider | None = None) -> dict:
    storage = storage or LocalStorageProvider()
    lock_path = get_settings().path(get_settings().correction_gallery_path).parent / f"{job.id}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(lock_path), timeout=30):
        session.refresh(job)
        if job.status != "completed" or job.result_json is None:
            raise ValueError("Result is not ready")
        result = dict(job.result_json)
        items = [dict(item) for item in result.get("instances", [])]
        if not items or set(selected) != {item["instance_number"] for item in items}:
            raise ValueError("Confirm every detected piece exactly once")
        rows = {row.instance_number: row for row in session.scalars(
            select(JewelConfirmation).where(JewelConfirmation.job_id == job.id)).all()}
        confirmed_at = utcnow()
        for item in items:
            number = item["instance_number"]
            label = selected[number]
            classification = dict(item["classification"])
            predicted = classification.get("predicted_label") or classification["label"]
            row = rows.get(number)
            if row is None:
                crop = storage.read(job.id, item["artifacts"]["crop"])
                row = JewelConfirmation(job_id=job.id, instance_number=number,
                                        predicted_label=predicted, confirmed_label=label,
                                        embedding=_embedding(crop).tobytes(),
                                        confirmed_by_user_id=user_id, confirmed_at=confirmed_at)
                session.add(row)
            elif row.confirmed_label != label:
                row.confirmed_label = label
                row.confirmed_by_user_id = user_id
                row.confirmed_at = confirmed_at
            classification.update(label=label, predicted_label=predicted,
                                  confirmed_label=label, confirmed_at=row.confirmed_at.isoformat(),
                                  confirmed=True, needs_review=False)
            item["classification"] = classification
            for db_item in job.instances:
                if db_item.instance_number == number:
                    db_item.classification = classification
                    break
        result["instances"] = items
        result["type_counts"] = dict(Counter(item["classification"]["label"] for item in items))
        result["confirmed_at"] = confirmed_at.isoformat()
        result["warnings"] = [warning for warning in result.get("warnings", [])
                              if not warning.startswith("Review jewellery type for piece ")]
        original = Image.open(BytesIO(storage.read(job.id, job.original_artifact))).convert("RGB")
        detected = []
        for item in items:
            mask = np.asarray(Image.open(BytesIO(storage.read(job.id, item["artifacts"]["mask"]))).convert("L")) > 0
            segmentation = item["segmentation"]
            detected.append(DetectedInstance(mask=mask, confidence=segmentation["score"],
                                             source=segmentation["source"],
                                             refined_with_inspyrenet=segmentation.get("refined_with_inspyrenet", False)))
        captured = datetime.fromisoformat(result["captured_at"])
        annotated = render_result_image(original, detected,
                                        [item["classification"]["label"] for item in items],
                                        [item["classification"]["classification_score"] for item in items],
                                        captured, result["display_timezone"], result["type_counts"],
                                        confirmed=[True] * len(items))
        artifact = f"annotated_confirmed_{uuid4().hex}.jpg"
        storage.write(job.id, artifact, annotated)
        result["artifacts"] = {**result["artifacts"], "annotated": artifact}
        job.annotated_artifact = artifact
        job.result_json = result
        session.commit()
        rebuild_gallery(session)
        return result
