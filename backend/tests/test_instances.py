import numpy as np

from app.ai.instances import DetectedInstance, deduplicate
from app.core.config import Settings


def test_prompt_duplicates_do_not_double_count():
    one = np.zeros((200, 200), dtype=bool)
    two = np.zeros_like(one)
    one[20:80, 20:80] = True
    two[120:180, 120:180] = True
    found = [DetectedInstance(one, 0.9, "yoloe"), DetectedInstance(one.copy(), 0.8, "yoloe"),
             DetectedInstance(two, 0.7, "yoloe")]
    unique = deduplicate(found, Settings())
    assert len(unique) == 2
    assert [item.confidence for item in unique] == [0.9, 0.7]


def test_ring_hole_does_not_reject_mask():
    ring = np.zeros((200, 200), dtype=bool)
    ring[20:130, 20:130] = True
    ring[30:120, 30:120] = False
    assert len(deduplicate([DetectedInstance(ring, 0.9, "yoloe")], Settings())) == 1
