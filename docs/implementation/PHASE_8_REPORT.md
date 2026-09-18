# Phase 8 — Complete backend pipeline

Status: **PASS for the integrated backend pipeline on the tested jewellery images.** Work stops at this phase as requested.

The worker now runs the uploaded image through YOLOE text and dataset visual prompts, InSPyReNet fallback or refinement, physical instance deduplication and counting, per-instance white-background crops, the supplied SigLIP2 classifier, annotated result rendering, database persistence, and the authenticated result and artifact API. The result includes captured date and time, type counts, per-piece details, warnings, model metadata, and timings for image load, segmentation, classification, annotation, and total processing. No weight field or weight display is produced.

PNG uploads are preserved as PNG after image sanitization. Re-encoding the supplied PNG as JPEG had changed one bangle classification on a held-out group sample. Client capture times are normalized to UTC before SQLite storage so the annotated image displays the correct local time in `Asia/Kolkata`.

## Validation

- `python -m pytest -q` — **13 passed**, with two third-party TestClient deprecation warnings.
- `scripts/test_pipeline.py` on `Jewel_count_20260825_161241_647_full.png` — **4 physical pieces: 2 Earrings / Nosepin and 2 Bangle**; total model pipeline time **6.21 s** on the tested CPU. The annotated image was visually inspected for four separate outlines, labels, count breakdown, date/time, and no weight.
- `scripts/test_pipeline.py` on `Rings_20260825_172738_888_full.png` — **1 Finger Ring**, no review warning; total model pipeline time **3.53 s**.
- `scripts/test_api_pipeline.py --image <group PNG> --expected-count 4` — passed login, job creation, PNG upload, submit, real worker execution, completed job polling, result retrieval, expected count, capture time normalization, no weight key, authenticated retrieval and image decoding of the annotated image plus four crops and four masks, and rejection of an unknown artifact. It uses an isolated temporary database and storage directory.

## Current limitations

The two bangle type scores in the group example were **0.32** and **0.35** and are explicitly flagged for review. These selected examples do not establish general detection or classification accuracy across the full dataset. The pipeline ran on CPU; GPU performance and a live Android client have not been validated in this phase. The Flutter application belongs to Phase 9 and has not been started.
