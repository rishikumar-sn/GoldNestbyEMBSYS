from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.core.config import Settings


@dataclass
class DetectedInstance:
    mask: np.ndarray
    confidence: float
    source: str
    refined_with_inspyrenet: bool = False

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        ys, xs = np.nonzero(self.mask)
        if not len(xs):
            return (0, 0, 0, 0)
        return (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))

    @property
    def area(self) -> int:
        return int(np.count_nonzero(self.mask))


def mask_quality(instance: DetectedInstance, settings: Settings) -> bool:
    mask = instance.mask
    if mask.ndim != 2 or not mask.any():
        return False
    frame_area = mask.shape[0] * mask.shape[1]
    if instance.area < max(settings.min_mask_pixels, int(frame_area * settings.min_mask_fraction)):
        return False
    if instance.area > frame_area * settings.max_mask_fraction:
        return False
    x1, y1, x2, y2 = instance.bbox
    return x2 > x1 and y2 > y1 and 0 <= x1 < x2 <= mask.shape[1] and 0 <= y1 < y2 <= mask.shape[0]


def deduplicate(instances: list[DetectedInstance], settings: Settings) -> list[DetectedInstance]:
    selected: list[DetectedInstance] = []
    for candidate in sorted(instances, key=lambda item: item.confidence, reverse=True):
        if not mask_quality(candidate, settings):
            continue
        duplicate = False
        for kept in selected:
            if kept.mask.shape != candidate.mask.shape:
                continue
            intersection = int(np.count_nonzero(candidate.mask & kept.mask))
            if not intersection:
                continue
            union = candidate.area + kept.area - intersection
            iou = intersection / union
            containment = intersection / min(candidate.area, kept.area)
            if iou >= settings.dedup_mask_iou or containment >= settings.dedup_containment:
                duplicate = True
                break
        if not duplicate:
            selected.append(candidate)
    return order_instances(selected)


def order_instances(instances: list[DetectedInstance]) -> list[DetectedInstance]:
    if not instances:
        return []
    height = instances[0].mask.shape[0]
    row_height = max(1, int(height * 0.15))
    return sorted(instances, key=lambda item: (((item.bbox[1] + item.bbox[3]) // 2) // row_height,
                                                (item.bbox[0] + item.bbox[2]) // 2))


def draw_debug(image: np.ndarray, instances: list[DetectedInstance]) -> np.ndarray:
    canvas = image.copy()
    for number, instance in enumerate(instances, 1):
        contours, _ = cv2.findContours(instance.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, (0, 180, 255), 3)
        x1, y1, _, _ = instance.bbox
        cv2.putText(canvas, str(number), (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(canvas, str(number), (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 220, 255), 2, cv2.LINE_AA)
    return canvas

