from __future__ import annotations

import logging
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from app.ai.instances import DetectedInstance, deduplicate
from app.ai.inspyrenet import InspyrenetSegmenter
from app.ai.yoloe import YoloeSegmenter
from app.core.config import Settings, get_settings


log = logging.getLogger(__name__)


class InstanceProvider(Protocol):
    def segment_with_visual(self, image: Image.Image, mode: str) -> tuple[list[DetectedInstance], dict[str, int]]: ...


class JewellerySegmenter:
    def __init__(self, settings: Settings | None = None, yoloe: InstanceProvider | None = None,
                 inspyrenet: InspyrenetSegmenter | None = None) -> None:
        self.settings = settings or get_settings()
        self.yoloe = yoloe or YoloeSegmenter(self.settings)
        self._inspyrenet = inspyrenet

    @property
    def inspyrenet(self) -> InspyrenetSegmenter:
        if self._inspyrenet is None:
            self._inspyrenet = InspyrenetSegmenter(self.settings)
        return self._inspyrenet

    def segment(self, image: Image.Image, mode: str) -> tuple[list[DetectedInstance], list[str], dict[str, int]]:
        instances, counts = self.yoloe.segment_with_visual(image, mode)
        warnings: list[str] = []
        if instances:
            if self.settings.inspyrenet_enabled:
                refined = []
                for instance in instances:
                    if self._needs_refinement(instance):
                        try:
                            refined.append(self.inspyrenet.refine(image, instance))
                        except Exception:
                            log.exception("InSPyReNet ROI refinement failed; keeping YOLOE mask")
                            refined.append(instance)
                            warnings.append("One mask could not be refined; the initial outline was retained.")
                    else:
                        refined.append(instance)
                instances = deduplicate(refined, self.settings)
            return instances, warnings, counts
        if not self.settings.inspyrenet_enabled:
            return [], ["No jewellery was detected."], counts
        fallback, _alpha = self.inspyrenet.fallback(image)
        warnings.append("Count uses foreground fallback and may need manual verification.")
        if not fallback:
            warnings.append("No jewellery was detected.")
        return fallback, warnings, counts

    @staticmethod
    def _needs_refinement(instance: DetectedInstance) -> bool:
        if not instance.mask.any():
            return False
        count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(instance.mask.astype(np.uint8))
        significant = sum(int(stats[index, cv2.CC_STAT_AREA]) >= max(12, instance.area * 0.02)
                          for index in range(1, count))
        return significant >= 7

