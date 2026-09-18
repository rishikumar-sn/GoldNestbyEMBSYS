from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.instances import DetectedInstance, deduplicate, draw_debug  # noqa: E402
from app.core.config import get_settings  # noqa: E402


def main():
    from ultralytics import YOLOE
    from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor

    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--reference", choices=["earring_and_bangle", "finger_ring"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.08)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    reference_root = settings.path(settings.yoloe_model).parent / "visual_prompts"
    manifest = json.loads((reference_root / "references.json").read_text())
    reference = next(item for item in manifest["references"] if item["name"] == args.reference)
    model = YOLOE(str(settings.path(settings.yoloe_model)))
    result = model.predict(str(args.image), refer_image=str(reference_root / reference["image"]),
                           visual_prompts={"bboxes": np.asarray(reference["bboxes"], dtype=np.float32),
                                           "cls": np.asarray(reference["cls"], dtype=np.int64)},
                           predictor=YOLOEVPSegPredictor, imgsz=settings.yoloe_image_size,
                           conf=args.confidence, retina_masks=True, verbose=False)[0]
    image = Image.open(args.image).convert("RGB")
    instances = []
    if result.masks is not None and result.boxes is not None:
        for raw_mask, confidence in zip(result.masks.data, result.boxes.conf, strict=False):
            mask = raw_mask.cpu().numpy() > 0.5
            if mask.shape != (image.height, image.width):
                mask = cv2.resize(mask.astype(np.uint8), image.size,
                                  interpolation=cv2.INTER_NEAREST).astype(bool)
            instances.append(DetectedInstance(mask, float(confidence), "yoloe_visual"))
    unique = deduplicate(instances, settings)
    cv2.imwrite(str(args.output / "annotated.jpg"),
                draw_debug(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR), unique))
    report = {"reference": args.reference, "raw_predictions": len(instances),
              "physical_jewel_count": len(unique),
              "instances": [{"number": i, "bbox": instance.bbox, "confidence": instance.confidence}
                            for i, instance in enumerate(unique, 1)]}
    (args.output / "result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
