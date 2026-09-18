from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

from app.core.config import Settings, get_settings


class SiglipJewelleryClassifier:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        model_dir = self.settings.path(self.settings.siglip_model_dir)
        cache = model_dir.parent / "_cache" / "huggingface"
        if not cache.is_dir():
            raise FileNotFoundError("SigLIP2 processor cache missing; run python scripts/download_models.py")
        os.environ["HF_HOME"] = str(cache)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from models.siglip2.jewelry_classifier import JewelryZeroShotClassifier

        import onnxruntime as ort

        available = ort.get_available_providers()
        preference = self.settings.siglip_provider.lower()
        if preference in {"cuda", "auto"} and "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        self.classifier = JewelryZeroShotClassifier(providers=providers)
        self.providers = self.classifier.session.get_providers()
        self._gallery_mtime_ns: int | None = None

    def _refresh_gallery(self) -> None:
        from models.siglip2.jewelry_classifier import CorrectionGallery

        path = self.settings.path(self.settings.correction_gallery_path)
        try:
            mtime_ns = path.stat().st_mtime_ns
        except FileNotFoundError:
            return
        if mtime_ns != self._gallery_mtime_ns:
            self.classifier.gallery = CorrectionGallery(Path(path))
            self._gallery_mtime_ns = mtime_ns

    def classify(self, crop: Image.Image) -> dict:
        self._refresh_gallery()
        prediction = self.classifier.classify_image(crop)
        return {
            "label": prediction.label,
            "classification_score": float(prediction.confidence),
            "gallery_match": bool(prediction.gallery_match),
            "gallery_similarity": float(prediction.gallery_similarity),
            "is_gold_jewelry": bool(prediction.is_gold_jewelry),
            "top_classes": [
                {"label": score.label, "score": float(score.confidence),
                 "cosine_similarity": float(score.similarity)}
                for score in prediction.scores[:3]
            ],
            "_all_scores": {score.label: float(score.confidence) for score in prediction.scores},
        }

    def classify_with_context(self, white_crop: Image.Image, context: Image.Image) -> dict:
        primary = self.classify(white_crop)
        secondary = self.classify(context)
        if secondary["gallery_match"] and (
            not primary["gallery_match"] or
            secondary["gallery_similarity"] > primary["gallery_similarity"] + 0.02
        ):
            selected = secondary
            selected["classification_source"] = "context_gallery"
        else:
            selected = primary
            selected["classification_source"] = "white_crop"
        if primary["label"] != secondary["label"]:
            selected["alternate_label"] = (primary if selected is secondary else secondary)["label"]
        selected.pop("_all_scores", None)
        return selected

    def classify_instance(self, image: Image.Image, mask) -> dict:
        from app.ai.crops import context_crop, white_background_crop

        primary = self.classify(white_background_crop(image, mask, 0.12))
        context = self.classify(context_crop(image, mask, 1.5))
        if context["gallery_match"] and (
            not primary["gallery_match"] or
            context["gallery_similarity"] > primary["gallery_similarity"] + 0.02
        ):
            selected = context
            selected["classification_source"] = "context_gallery"
            if selected["label"] != primary["label"]:
                selected["alternate_label"] = primary["label"]
            selected.pop("_all_scores", None)
            return selected
        margin = (primary["top_classes"][0]["score"] - primary["top_classes"][1]["score"]
                  if len(primary["top_classes"]) > 1 else 1.0)
        if primary["gallery_match"] or (primary["classification_score"] >= 0.55 and margin >= 0.15):
            primary["classification_source"] = "white_crop"
            primary.pop("_all_scores", None)
            return primary
        views = [self.classify(white_background_crop(image, mask, ratio)) for ratio in (0.05, 0.3)]
        views.insert(1, primary)
        labels = set().union(*(view["_all_scores"] for view in views))
        averages = {label: sum(view["_all_scores"].get(label, 0.0) for view in views) / len(views)
                    for label in labels}
        ranked = sorted(averages.items(), key=lambda entry: entry[1], reverse=True)
        result = dict(primary)
        result["label"] = ranked[0][0]
        result["classification_score"] = ranked[0][1]
        result["classification_source"] = "white_crop_ensemble"
        result["top_classes"] = [{"label": label, "score": score} for label, score in ranked[:3]]
        if result["label"] != primary["label"]:
            result["alternate_label"] = primary["label"]
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.10:
            result["needs_review"] = True
        result.pop("_all_scores", None)
        return result
