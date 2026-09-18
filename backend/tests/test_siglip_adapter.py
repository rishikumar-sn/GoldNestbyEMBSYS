from app.ai.siglip import SiglipJewelleryClassifier


def test_context_gallery_can_correct_white_crop_label():
    adapter = object.__new__(SiglipJewelleryClassifier)
    scores = [
        {"label": "one", "gallery_match": False, "gallery_similarity": 0.8},
        {"label": "two", "gallery_match": True, "gallery_similarity": 0.94},
    ]
    adapter.classify = lambda _image: scores.pop(0)
    result = adapter.classify_with_context(object(), object())
    assert result["label"] == "two"
    assert result["classification_source"] == "context_gallery"
    assert result["alternate_label"] == "one"
