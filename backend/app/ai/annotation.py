from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.ai.instances import DetectedInstance


PALETTE = [(213, 166, 57), (52, 132, 127), (182, 103, 82), (111, 113, 185)]


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_result_image(image: Image.Image, instances: list[DetectedInstance], labels: list[str],
                        scores: list[float], captured_at: datetime, timezone_name: str,
                        type_counts: dict[str, int], confirmed: list[bool] | None = None) -> bytes:
    if len(instances) != len(labels) or len(labels) != len(scores):
        raise ValueError("Annotation labels must match instances")
    if confirmed is not None and len(confirmed) != len(labels):
        raise ValueError("Confirmation flags must match instances")
    original = image.convert("RGB")
    scale = min(1.0, 1200 / max(original.size))
    display = original.resize((max(1, round(original.width * scale)), max(1, round(original.height * scale))),
                              Image.Resampling.LANCZOS)
    array = np.asarray(display).copy()
    for number, instance in enumerate(instances, 1):
        mask = cv2.resize(instance.mask.astype(np.uint8), display.size, interpolation=cv2.INTER_NEAREST)
        color = PALETTE[(number - 1) % len(PALETTE)]
        tinted = array.astype(np.float32)
        tinted[mask > 0] = tinted[mask > 0] * 0.82 + np.array(color) * 0.18
        array = tinted.astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(array, contours, -1, color, 3)
    photo = Image.fromarray(array)
    draw = ImageDraw.Draw(photo)
    badge_font = _font(23, bold=True)
    badge_boxes: list[tuple[int, int, int, int]] = []
    for number, instance in enumerate(instances, 1):
        x1, y1, _, _ = instance.bbox
        px, py = int(x1 * scale), max(8, int(y1 * scale) - 42)
        title = f"{number}. {labels[number - 1]}"
        text_box = draw.textbbox((0, 0), title, font=badge_font)
        width = text_box[2] - text_box[0] + 24
        px = min(px, max(0, photo.width - width - 8))
        for offset in (0, -40, 40, -80, 80, -120, 120):
            candidate_y = py + offset
            candidate = (px, candidate_y, px + width, candidate_y + 36)
            if candidate_y < 8 or candidate_y + 36 > photo.height - 8:
                continue
            if all(candidate[2] <= other[0] or candidate[0] >= other[2] or
                   candidate[3] <= other[1] or candidate[1] >= other[3]
                   for other in badge_boxes):
                py = candidate_y
                break
        badge_boxes.append((px, py, px + width, py + 36))
        draw.rounded_rectangle((px, py, px + width, py + 36), radius=10, fill=(24, 35, 42))
        draw.text((px + 12, py + 3), title, font=badge_font, fill=(255, 255, 255))

    panel_width = 410
    panel_height = max(photo.height, 376 + len(type_counts) * 32 + 22 + 19 + len(labels) * 54 + 35)
    canvas = Image.new("RGB", (photo.width + panel_width, panel_height), (247, 248, 246))
    canvas.paste(photo, (0, 0))
    right = ImageDraw.Draw(canvas)
    x = photo.width + 28
    zone = ZoneInfo(timezone_name)
    when = captured_at.astimezone(zone)
    right.text((x, 30), "GOLDNEST", font=_font(18, True), fill=(153, 112, 41))
    right.text((x, 69), "Jewellery analysis", font=_font(29, True), fill=(26, 43, 48))
    right.line((x, 125, canvas.width - 28, 125), fill=(213, 218, 215), width=2)
    right.text((x, 150), "CAPTURED", font=_font(15, True), fill=(99, 115, 118))
    right.text((x, 177), when.strftime("%d %b %Y, %I:%M %p"), font=_font(21), fill=(29, 45, 49))
    right.text((x, 205), timezone_name, font=_font(14), fill=(99, 115, 118))
    right.text((x, 252), "TOTAL PIECES", font=_font(15, True), fill=(99, 115, 118))
    right.text((x, 277), str(len(instances)), font=_font(48, True), fill=(30, 111, 103))
    right.line((x, 353, canvas.width - 28, 353), fill=(213, 218, 215), width=2)
    y = 376
    for label, count in sorted(type_counts.items()):
        right.text((x, y), label, font=_font(17), fill=(33, 51, 55))
        right.text((canvas.width - 50, y), str(count), anchor="ra", font=_font(18, True), fill=(30, 111, 103))
        y += 32
    y += 22
    right.line((x, y, canvas.width - 28, y), fill=(213, 218, 215), width=2)
    y += 19
    for number, (label, score) in enumerate(zip(labels, scores, strict=True), 1):
        right.text((x, y), f"{number}. {label}", font=_font(18, True), fill=(33, 51, 55))
        detail = "Confirmed by reviewer" if confirmed and confirmed[number - 1] else f"Classification score {score:.2f}"
        right.text((x, y + 23), detail, font=_font(14), fill=(99, 115, 118))
        y += 54
    output = BytesIO()
    canvas.save(output, format="JPEG", quality=92, subsampling=0)
    return output.getvalue()
