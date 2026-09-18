from __future__ import annotations

import numpy as np
from PIL import Image


def white_background_crop(image: Image.Image, mask: np.ndarray, padding_ratio: float = 0.12) -> Image.Image:
    if mask.shape != (image.height, image.width) or not mask.any():
        raise ValueError("Mask must match the source image and contain foreground")
    ys, xs = np.nonzero(mask)
    x1, x2 = int(xs.min()), int(xs.max() + 1)
    y1, y2 = int(ys.min()), int(ys.max() + 1)
    pad = max(8, int(max(x2 - x1, y2 - y1) * padding_ratio))
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(image.width, x2 + pad), min(image.height, y2 + pad)
    region = image.convert("RGB").crop((x1, y1, x2, y2))
    alpha = Image.fromarray((mask[y1:y2, x1:x2].astype(np.uint8) * 255), mode="L")
    white = Image.new("RGB", region.size, "white")
    white.paste(region, mask=alpha)
    side = max(white.size)
    square = Image.new("RGB", (side, side), "white")
    square.paste(white, ((side - white.width) // 2, (side - white.height) // 2))
    return square


def context_crop(image: Image.Image, mask: np.ndarray, padding_ratio: float = 1.5) -> Image.Image:
    if mask.shape != (image.height, image.width) or not mask.any():
        raise ValueError("Mask must match the source image and contain foreground")
    ys, xs = np.nonzero(mask)
    x1, x2 = int(xs.min()), int(xs.max() + 1)
    y1, y2 = int(ys.min()), int(ys.max() + 1)
    pad = int(max(x2 - x1, y2 - y1) * padding_ratio)
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(image.width, x2 + pad), min(image.height, y2 + pad)
    crop = image.convert("RGB").crop((x1, y1, x2, y2))
    side = max(crop.size)
    square = Image.new("RGB", (side, side), "white")
    square.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    return square
