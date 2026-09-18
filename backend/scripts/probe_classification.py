from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.crops import context_crop, white_background_crop  # noqa: E402
from app.ai.siglip import SiglipJewelleryClassifier  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    args = parser.parse_args()
    image = Image.open(args.image).convert("RGB")
    mask = np.asarray(Image.open(args.mask).convert("L")) >= 128
    classifier = SiglipJewelleryClassifier()
    for kind, builder, ratios in (("white", white_background_crop, (0.05, 0.12, 0.3)),
                                   ("context", context_crop, (0.3, 0.7, 1.5))):
        for ratio in ratios:
            result = classifier.classify(builder(image, mask, ratio))
            top = [(item["label"], round(item["score"], 3)) for item in result["top_classes"]]
            print(kind, ratio, result["label"], round(result["classification_score"], 3),
                  "gallery", result["gallery_match"], round(result["gallery_similarity"], 3), top)


if __name__ == "__main__":
    main()
