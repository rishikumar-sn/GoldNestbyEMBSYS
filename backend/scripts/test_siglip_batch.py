from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.siglip import SiglipJewelleryClassifier  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mask-dir", type=Path, required=True)
    args = parser.parse_args()
    image = Image.open(args.image).convert("RGB")
    classifier = SiglipJewelleryClassifier()
    results = []
    for number, mask_path in enumerate(sorted(args.mask_dir.glob("mask_*.png")), 1):
        mask = np.asarray(Image.open(mask_path).convert("L")) >= 128
        result = classifier.classify_instance(image, mask)
        results.append({"instance_number": number, **result})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
