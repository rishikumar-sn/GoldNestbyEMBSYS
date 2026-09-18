from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from download_models import INSPYRENET_FAST_SHA256, sha256  # noqa: E402


def verify(deep: bool = False) -> dict[str, str]:
    settings = get_settings()
    result: dict[str, str] = {}
    yoloe = settings.path(settings.yoloe_model)
    encoder = yoloe.parent / "mobileclip2_b.ts"
    result["YOLOE"] = "present" if yoloe.is_file() and encoder.is_file() else "missing checkpoint or text encoder"
    inspyrenet = settings.path(settings.inspyrenet_model)
    result["InSPyReNet"] = "present" if inspyrenet.is_file() and sha256(inspyrenet) == INSPYRENET_FAST_SHA256 else "missing or checksum mismatch"
    siglip = settings.path(settings.siglip_model_dir)
    required = ["siglip2-base-patch32-256_vision_encoder.sim.onnx", "jewelry_classifier.py",
                "jewelry_prompts.json", "jewelry_text_embeddings_cache.npz"]
    result["SigLIP2"] = "present" if all((siglip / name).is_file() for name in required) else "missing required user file"
    if deep:
        if result["YOLOE"] == "present":
            from ultralytics import YOLOE

            model = YOLOE(str(yoloe))
            previous = Path.cwd()
            try:
                os.chdir(yoloe.parent)
                model.set_classes([p.strip() for p in settings.yoloe_prompts.split(",") if p.strip()])
            finally:
                os.chdir(previous)
            result["YOLOE"] = "loaded"
        if result["SigLIP2"] == "present":
            import onnxruntime as ort

            session = ort.InferenceSession(str(siglip / required[0]), providers=["CPUExecutionProvider"])
            result["SigLIP2"] = f"loaded ({session.get_providers()})"
        if result["InSPyReNet"] == "present":
            from transparent_background import Remover

            Remover(mode="fast", device="cpu", ckpt=str(inspyrenet))
            result["InSPyReNet"] = "loaded"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args()
    status = verify(args.deep)
    for model, state in status.items():
        print(f"{model:15} {state}")
    if any(not value.startswith(("present", "loaded")) for value in status.values()):
        print("Run: python scripts/download_models.py")
        raise SystemExit(1)
