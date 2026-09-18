# Phase 5 — YOLOE instance segmentation

Status: PASS for YOLOE provider and deduplication; full counting accuracy remains a pipeline acceptance item.

Implemented a preloaded YOLOE text-prompt adapter, full-resolution masks, configurable confidence/image size, mask quality checks that preserve hollow bangles, prompt-agnostic mask-overlap deduplication, stable geometric ordering, annotated debug output, and a standalone CLI that writes count JSON, masks, and an image.

Validation: `pytest -q tests/test_instances.py` passed (2 tests) for duplicate predictions and a ring-shaped mask. The real dataset `Jewel_count_20260825_150537_210_full.png` contains two earrings and two bangles; with tuned prompts and 0.15 threshold, YOLOE produced five raw predictions and four deduplicated physical instances, and the annotated image visually matches the four pieces. This exercised CPU inference with the downloaded checkpoint.

Known limitations: an early test passed RGB arrays to the Ultralytics NumPy input path, which expects BGR; that test missed one bangle in `Jewel_count_20260825_161241_647_full.png`. After correcting the channel order, text prompting found four pieces in that photo. A small ring on a full-scale photo still yielded zero with text prompting; visual prompting recovered it in subsequent tests. These samples do not establish general count accuracy. YOLOE output is not used as the final type label.
