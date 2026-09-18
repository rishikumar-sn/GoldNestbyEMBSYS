from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

from app.ai.instances import DetectedInstance, order_instances
from app.core.config import Settings, get_settings


log = logging.getLogger(__name__)


class InspyrenetSegmenter:
    def __init__(self, settings: Settings | None = None) -> None:
        from transparent_background import Remover

        self.settings = settings or get_settings()
        checkpoint = self.settings.path(self.settings.inspyrenet_model)
        if not checkpoint.is_file():
            raise FileNotFoundError("InSPyReNet checkpoint missing; run python scripts/download_models.py")
        device = self.settings.inspyrenet_device
        if device == "auto":
            import torch

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.remover = Remover(mode="fast", device=device, ckpt=str(checkpoint))

    def map(self, image: Image.Image) -> np.ndarray:
        try:
            result = self.remover.process(image.convert("RGB"), type="map")
        except RuntimeError as exc:
            if "out of memory" not in str(exc).lower() or not self.device.startswith("cuda"):
                raise
            log.warning("InSPyReNet CUDA OOM; retrying once on CPU")
            import torch
            from transparent_background import Remover

            torch.cuda.empty_cache()
            checkpoint = self.settings.path(self.settings.inspyrenet_model)
            self.remover = Remover(mode="fast", device="cpu", ckpt=str(checkpoint))
            self.device = "cpu"
            result = self.remover.process(image.convert("RGB"), type="map")
        alpha = np.asarray(result.convert("L"))
        if alpha.shape != (image.height, image.width):
            alpha = cv2.resize(alpha, image.size, interpolation=cv2.INTER_LINEAR)
        return alpha

    def fallback(self, image: Image.Image, threshold: int = 128) -> tuple[list[DetectedInstance], np.ndarray]:
        alpha = self.map(image)
        binary = (alpha >= threshold).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        frame_area = binary.shape[0] * binary.shape[1]
        min_area = max(self.settings.min_mask_pixels, int(frame_area * self.settings.min_mask_fraction))
        instances = []
        for component in range(1, count):
            area = int(stats[component, cv2.CC_STAT_AREA])
            if not min_area <= area <= frame_area * self.settings.max_mask_fraction:
                continue
            x = int(stats[component, cv2.CC_STAT_LEFT])
            y = int(stats[component, cv2.CC_STAT_TOP])
            width = int(stats[component, cv2.CC_STAT_WIDTH])
            height = int(stats[component, cv2.CC_STAT_HEIGHT])
            if width > image.width * 0.75 or height > image.height * 0.75:
                continue
            mask = labels == component
            instances.append(DetectedInstance(mask=mask, confidence=0.45,
                                              source="inspyrenet_full_fallback"))
        return order_instances(instances), alpha

    def refine(self, image: Image.Image, candidate: DetectedInstance, padding: float = 0.12) -> DetectedInstance:
        x1, y1, x2, y2 = candidate.bbox
        pad = max(8, int(max(x2 - x1, y2 - y1) * padding))
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(image.width, x2 + pad), min(image.height, y2 + pad)
        crop = image.crop((x1, y1, x2, y2))
        alpha = self.map(crop)
        refined = np.zeros((image.height, image.width), dtype=bool)
        refined[y1:y2, x1:x2] = alpha >= 128
        if not refined.any():
            return candidate
        return DetectedInstance(refined, candidate.confidence, candidate.source,
                                refined_with_inspyrenet=True)
