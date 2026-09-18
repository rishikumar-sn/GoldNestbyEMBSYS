from __future__ import annotations

import os
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.ai.instances import DetectedInstance, deduplicate
from app.core.config import Settings, get_settings


class YoloeSegmenter:
    def __init__(self, settings: Settings | None = None) -> None:
        from ultralytics import YOLOE

        self.settings = settings or get_settings()
        checkpoint = self.settings.path(self.settings.yoloe_model)
        encoder = checkpoint.parent / "mobileclip2_b.ts"
        if not checkpoint.is_file() or not encoder.is_file():
            raise FileNotFoundError("YOLOE checkpoint or text encoder missing; run python scripts/download_models.py")
        self.prompts = [item.strip() for item in self.settings.yoloe_prompts.split(",") if item.strip()]
        if not self.prompts:
            raise ValueError("YOLOE_PROMPTS must contain at least one prompt")
        self.model = YOLOE(str(checkpoint))
        self._visual_model = None
        self.visual_root = checkpoint.parent / "visual_prompts"
        previous = Path.cwd()
        try:
            os.chdir(checkpoint.parent)
            self.model.set_classes(self.prompts)
        finally:
            os.chdir(previous)

    def _device(self) -> str:
        device = self.settings.yoloe_device
        if device == "auto":
            import torch

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        return device

    def _extract(self, result, size: tuple[int, int], source: str) -> tuple[list[DetectedInstance], int]:
        raw_count = len(result.boxes) if result.boxes is not None else 0
        if result.masks is None or result.boxes is None:
            return [], raw_count
        instances: list[DetectedInstance] = []
        for raw_mask, confidence in zip(result.masks.data, result.boxes.conf, strict=False):
            mask = raw_mask.cpu().numpy() > 0.5
            if mask.shape != (size[1], size[0]):
                mask = cv2.resize(mask.astype(np.uint8), size,
                                  interpolation=cv2.INTER_NEAREST).astype(bool)
            instances.append(DetectedInstance(mask=mask, confidence=float(confidence), source=source))
        return instances, raw_count

    def segment(self, image: Image.Image) -> tuple[list[DetectedInstance], int]:
        bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        result = self.model.predict(bgr, imgsz=self.settings.yoloe_image_size,
                                    conf=self.settings.yoloe_confidence, device=self._device(),
                                    retina_masks=True, verbose=False)[0]
        instances, raw_count = self._extract(result, image.size, "yoloe")
        return deduplicate(instances, self.settings), raw_count

    def visual_segment(self, image: Image.Image, reference_name: str) -> tuple[list[DetectedInstance], int]:
        from ultralytics import YOLOE
        from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor

        manifest = json.loads((self.visual_root / "references.json").read_text())
        reference = next((item for item in manifest["references"] if item["name"] == reference_name), None)
        if reference is None:
            raise ValueError(f"Unknown visual reference: {reference_name}")
        reference_path = self.visual_root / Path(reference["image"]).name
        if not reference_path.is_file():
            raise FileNotFoundError(f"Visual reference not found: {reference_path}")
        if self._visual_model is None:
            self._visual_model = YOLOE(str(self.settings.path(self.settings.yoloe_model)))
        prompts = {"bboxes": np.asarray(reference["bboxes"], dtype=np.float32),
                   "cls": np.asarray(reference["cls"], dtype=np.int64)}
        bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        result = self._visual_model.predict(bgr,
            refer_image=str(reference_path), visual_prompts=prompts,
            predictor=YOLOEVPSegPredictor, imgsz=self.settings.yoloe_image_size,
            conf=self.settings.visual_prompt_confidence, device=self._device(),
            retina_masks=True, verbose=False)[0]
        raw, count = self._extract(result, image.size, "yoloe_visual")
        return deduplicate(raw, self.settings), count

    def segment_with_visual(self, image: Image.Image, mode: str) -> tuple[list[DetectedInstance], dict[str, int]]:
        text_instances, text_raw = self.segment(image)
        combined = list(text_instances)
        counts = {"text_raw": text_raw, "visual_raw": 0}
        if self.settings.visual_prompts_enabled and (mode == "group" or not text_instances or
                                                      max(item.confidence for item in text_instances) < 0.35):
            for reference in ("earring_and_bangle", "finger_ring"):
                visual, raw = self.visual_segment(image, reference)
                combined.extend(visual)
                counts["visual_raw"] += raw
        return deduplicate(combined, self.settings), counts
