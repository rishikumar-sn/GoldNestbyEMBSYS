from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402


INSPYRENET_FAST_URL = "https://huggingface.co/plemeri/InSPyReNet/resolve/main/ckpt_fast.pth"
INSPYRENET_FAST_SHA256 = "e61ed7e85763dd83a796e1d650ea78604fff524121750858c54a6b560ac58c82"
INSPYRENET_BASE_URL = "https://huggingface.co/plemeri/InSPyReNet/resolve/main/ckpt_base.pth"
INSPYRENET_BASE_SHA256 = "0a6fe2a73ab0532d6d0b8d82849a9760a226df719e3063d09b4149ece6f80fcd"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_checked(url: str, destination: Path, expected: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and sha256(destination) == expected:
        print(f"Verified existing {destination}")
        return
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists():
        partial.unlink()
    print(f"Downloading {url} -> {destination}")
    try:
        with urllib.request.urlopen(url, timeout=45) as response, partial.open("wb") as target:
            for chunk in iter(lambda: response.read(4 * 1024 * 1024), b""):
                target.write(chunk)
        actual = sha256(partial)
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch for {destination}: {actual}")
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def prepare_yoloe() -> None:
    from ultralytics import YOLOE

    settings = get_settings()
    directory = settings.path(settings.yoloe_model).parent
    directory.mkdir(parents=True, exist_ok=True)
    original_dir = Path.cwd()
    try:
        os.chdir(directory)
        model = YOLOE(settings.yoloe_model.name)
        prompts = [prompt.strip() for prompt in settings.yoloe_prompts.split(",") if prompt.strip()]
        model.set_classes(prompts)
        encoder = directory / "mobileclip2_b.ts"
        if not encoder.is_file():
            raise RuntimeError("YOLOE text encoder was not prepared in the model directory")
        print(f"Prepared YOLOE checkpoint and text encoder in {directory}")
    finally:
        os.chdir(original_dir)


def prepare_siglip_processor() -> None:
    from transformers import AutoProcessor

    cache = ROOT / "models" / "_cache" / "huggingface" / "hub"
    cache.mkdir(parents=True, exist_ok=True)
    AutoProcessor.from_pretrained("google/siglip2-base-patch32-256", cache_dir=str(cache))
    print(f"Cached SigLIP2 processor in {cache}; user model files unchanged")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-yoloe", action="store_true")
    parser.add_argument("--skip-inspyrenet", action="store_true")
    parser.add_argument("--skip-siglip-processor", action="store_true")
    parser.add_argument("--include-inspyrenet-base", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not args.skip_yoloe:
        prepare_yoloe()
    if not args.skip_inspyrenet:
        download_checked(INSPYRENET_FAST_URL, settings.path(settings.inspyrenet_model), INSPYRENET_FAST_SHA256)
        if args.include_inspyrenet_base:
            download_checked(INSPYRENET_BASE_URL, settings.path(settings.inspyrenet_model).with_name("ckpt_base.pth"), INSPYRENET_BASE_SHA256)
    if not args.skip_siglip_processor:
        prepare_siglip_processor()
    print("User SigLIP2 files were not changed.")


if __name__ == "__main__":
    main()
