from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "debug_siglip")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    image = Image.open(args.image).convert("RGB")
    mask = np.asarray(Image.open(args.mask).convert("L")) >= 128
    crop = white_background_crop(image, mask)
    crop.save(args.output / "white_crop.png")
    classifier = SiglipJewelleryClassifier()
    context = context_crop(image, mask)
    context.save(args.output / "context_crop.png")
    prediction = classifier.classify_with_context(crop, context)
    (args.output / "result.json").write_text(json.dumps(prediction, indent=2))
    print(json.dumps(prediction, indent=2))


if __name__ == "__main__":
    main()
