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
from app.ai.inspyrenet import InspyrenetSegmenter  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "debug_inspyrenet")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    image = Image.open(args.image).convert("RGB")
    instances, alpha = InspyrenetSegmenter().fallback(image)
    cv2.imwrite(str(args.output / "saliency.png"), alpha)
    cv2.imwrite(str(args.output / "annotated.jpg"), draw_debug(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR), instances))
    result = {"physical_component_count": len(instances),
              "instances": [{"instance_number": index, "bbox": item.bbox, "area": item.area}
                            for index, item in enumerate(instances, 1)]}
    (args.output / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

