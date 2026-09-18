import numpy as np
from PIL import Image

from app.ai.crops import white_background_crop


def test_white_crop_preserves_jewellery_pixels_and_hole():
    image = Image.new("RGB", (100, 100), (70, 70, 70))
    pixels = np.asarray(image).copy()
    pixels[30:70, 30:70] = (200, 160, 30)
    image = Image.fromarray(pixels)
    mask = np.zeros((100, 100), dtype=bool)
    mask[30:70, 30:70] = True
    mask[40:60, 40:60] = False
    crop = white_background_crop(image, mask)
    values = np.asarray(crop)
    assert (values == (200, 160, 30)).all(axis=2).any()
    assert (values == (255, 255, 255)).all(axis=2).any()
    assert crop.width == crop.height
