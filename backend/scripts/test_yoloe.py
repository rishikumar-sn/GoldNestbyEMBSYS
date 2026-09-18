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

from app.ai.instances import draw_debug  # noqa: E402
from app.ai.yoloe import YoloeSegmenter  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "debug_yoloe")
    parser.add_argument("--with-visual", action="store_true")
    parser.add_argument("--mode", choices=["single", "group"], default="single")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    image = Image.open(args.image).convert("RGB")
    segmenter = YoloeSegmenter()
    if args.with_visual:
        instances, raw = segmenter.segment_with_visual(image, args.mode)
    else:
        instances, raw_count = segmenter.segment(image)
        raw = {"text_raw": raw_count, "visual_raw": 0}
    summary = {"image": str(args.image), "raw_predictions": raw,
               "physical_jewel_count": len(instances),
               "instances": [{"instance_number": n, "bbox": item.bbox, "confidence": item.confidence,
                              "source": item.source}
                             for n, item in enumerate(instances, 1)]}
    (args.output / "result.json").write_text(json.dumps(summary, indent=2))
    cv2.imwrite(str(args.output / "annotated.jpg"), draw_debug(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR), instances))
    for number, item in enumerate(instances, 1):
        cv2.imwrite(str(args.output / f"mask_{number}.png"), item.mask.astype(np.uint8) * 255)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
