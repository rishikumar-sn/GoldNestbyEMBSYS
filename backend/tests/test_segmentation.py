import numpy as np
from PIL import Image

from app.ai.instances import DetectedInstance
from app.ai.segmentation import JewellerySegmenter
from app.core.config import Settings


class EmptyYoloe:
    def segment_with_visual(self, _image, _mode):
        return [], {"text_raw": 0, "visual_raw": 0}


class FakeFallback:
    def fallback(self, image):
        mask = np.zeros((image.height, image.width), dtype=bool)
        mask[20:100, 20:100] = True
        return [DetectedInstance(mask, 0.45, "inspyrenet_full_fallback")], np.zeros_like(mask, dtype=np.uint8)


def test_full_fallback_metadata():
    provider = JewellerySegmenter(Settings(), yoloe=EmptyYoloe(), inspyrenet=FakeFallback())
    found, warnings, counts = provider.segment(Image.new("RGB", (120, 120), "white"), "single")
    assert len(found) == 1
    assert found[0].source == "inspyrenet_full_fallback"
    assert warnings and counts["text_raw"] == 0
