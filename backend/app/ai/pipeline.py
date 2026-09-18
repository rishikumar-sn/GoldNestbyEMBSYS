from __future__ import annotations

from collections import Counter
from datetime import timezone
from io import BytesIO
from time import perf_counter
from uuid import uuid4

import numpy as np
from PIL import Image

from app.ai.annotation import render_result_image
from app.ai.crops import white_background_crop
from app.ai.segmentation import JewellerySegmenter
from app.ai.siglip import SiglipJewelleryClassifier
from app.core.config import Settings, get_settings
from app.db.models import AnalysisJob, utcnow
from app.schemas.result import AnalysisResult
from app.services.storage import LocalStorageProvider


class AnalysisPipeline:
    def __init__(self, settings: Settings | None = None,
                 segmenter: JewellerySegmenter | None = None,
                 classifier: SiglipJewelleryClassifier | None = None,
                 storage: LocalStorageProvider | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or LocalStorageProvider()
        self.segmenter = segmenter or JewellerySegmenter(self.settings)
        self.classifier = classifier or SiglipJewelleryClassifier(self.settings)

    def __call__(self, job: AnalysisJob) -> dict:
        started = perf_counter()
        if not job.original_artifact:
            raise ValueError("Job has no uploaded image")
        original = Image.open(BytesIO(self.storage.read(job.id, job.original_artifact))).convert("RGB")
        loaded = perf_counter()
        detected, warnings, prompt_counts = self.segmenter.segment(original, job.mode)
        segmented = perf_counter()
        instances = []
        accepted_masks = []
        labels = []
        scores = []
        for detected_item in detected:
            classification = self.classifier.classify_instance(original, detected_item.mask)
            if not classification["is_gold_jewelry"]:
                warnings.append("A detected object was excluded because jewellery verification failed.")
                continue
            number = len(instances) + 1
            labels.append(classification["label"])
            scores.append(classification["classification_score"])
            accepted_masks.append(detected_item)
            if classification.get("needs_review"):
                warnings.append(f"Review jewellery type for piece {number}.")
            crop = white_background_crop(original, detected_item.mask)
            crop_data = BytesIO()
            crop.save(crop_data, format="PNG")
            crop_name = f"crop_{number}.png"
            mask_name = f"mask_{number}.png"
            self.storage.write(job.id, crop_name, crop_data.getvalue())
            mask_data = BytesIO()
            Image.fromarray(detected_item.mask.astype(np.uint8) * 255).save(mask_data, format="PNG")
            self.storage.write(job.id, mask_name, mask_data.getvalue())
            x1, y1, x2, y2 = detected_item.bbox
            instances.append({
                "instance_id": str(uuid4()), "instance_number": number,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "segmentation": {"source": detected_item.source, "score": detected_item.confidence,
                                 "refined_with_inspyrenet": detected_item.refined_with_inspyrenet},
                "classification": classification,
                "artifacts": {"crop": crop_name, "mask": mask_name},
            })
        classified = perf_counter()
        if job.mode == "single" and len(instances) > 1:
            warnings.append("Multiple jewellery pieces detected. Single-item mode expected one object.")
        type_counts = dict(Counter(labels))
        captured = job.captured_at or job.created_at
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        annotated = render_result_image(original, accepted_masks, labels, scores,
                                        captured, self.settings.display_timezone, type_counts)
        self.storage.write(job.id, "annotated.jpg", annotated)
        annotated_at = perf_counter()
        if not instances:
            warnings.append("No jewellery was confirmed in this image.")
        result = AnalysisResult.model_validate({
            "job_id": job.id, "mode": job.mode, "captured_at": captured,
            "completed_at": utcnow(), "display_timezone": self.settings.display_timezone,
            "physical_jewel_count": len(instances), "type_counts": type_counts,
            "count_confidence": round(min((item.confidence for item in accepted_masks), default=0.0), 4),
            "instances": instances, "warnings": list(dict.fromkeys(warnings)),
            "timings_ms": {
                "image_load": round((loaded - started) * 1000, 1),
                "segmentation": round((segmented - loaded) * 1000, 1),
                "siglip_total": round((classified - segmented) * 1000, 1),
                "annotation": round((annotated_at - classified) * 1000, 1),
                "total": round((annotated_at - started) * 1000, 1),
            },
            "model_versions": {
                "yoloe": self.settings.yoloe_model.name,
                "yoloe_prompts": self.settings.yoloe_prompts,
                "yoloe_text_raw": str(prompt_counts.get("text_raw", 0)),
                "yoloe_visual_raw": str(prompt_counts.get("visual_raw", 0)),
                "inspyrenet": self.settings.inspyrenet_model.name,
                "siglip": self.classifier.classifier.onnx_model_path.name,
                "siglip_prompt_hash": self.classifier.classifier.prompt_hash,
                "siglip_provider": ",".join(self.classifier.providers),
            },
            "artifacts": {"original": job.original_artifact, "annotated": "annotated.jpg"},
        })
        return result.model_dump(mode="json")

