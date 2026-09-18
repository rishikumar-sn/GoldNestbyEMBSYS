# Phase 0 — repository and model audit

Status: PASS (17 September 2026)

## Existing tree

The project initially contained only `backend/models/siglip2/` with six files: the existing classifier implementation, prompt JSON, two correction galleries, text-embedding cache, and a 376 MB ONNX vision encoder. There was no API, database, mobile application, documentation, or Git repository. No model file was changed during this audit.

## SigLIP2 source of truth

- ONNX: `siglip2-base-patch32-256_vision_encoder.sim.onnx`; the existing classifier finds the 768-dimensional embedding output and passes the processor's float32 `pixel_values` under the session's first input name.
- The existing `JewelryZeroShotClassifier` loads the `google/siglip2-base-patch32-256` processor, uses the cached prompt embeddings when model ID and prompt hash match, and otherwise rebuilds them using the text model. It combines original and foreground-cropped image embeddings, scores the six classes, checks gold/negative prompts, and applies correction-gallery matching.
- Classes read from the current prompt JSON: Bracelet, Bangle, Chain / Necklace, Mattal, Earrings / Nosepin, Finger Ring. Groups: wrist, neck, ear, ear_hair, finger, gold_verification, non_gold_metal, negative. Other Gold Jewellery and Not Gold Jewelry may also be returned by existing rejection logic.
- Embedding cache: `labels (6,)`, `embeddings (6,768)`, `class_groups (6,)`, `group_labels (8,)`, `group_embeddings (8,768)`, `text_model_id (1,)`, `prompt_hash (1,)`.
- Correction gallery: `embeddings (801,768)`, `labels (801,)`. Pre-dataset calibration gallery: `(93,768)` and `(93,)`. Existing gallery match threshold is 0.90 with class-specific thresholds and exact-match handling; cosine similarity is not treated as probability.
- The white-background crop and existing processor must be used for classification. No NPZ regeneration or model replacement is warranted.

## Reference result UI

The Weight Integration App embeds `media.result_image` above individual item cards and has a result-image download action. Its weight and stone sections are outside this project's scope. Here the result image will show numbered masks, type labels, piece counts, and capture date/time; the mobile result screen will show the same image plus a per-piece breakdown, without weight.

## Environment and risks

- Windows host with Python 3.10/3.12/3.13; Python 3.12 has NumPy, Pillow, and Torch but lacked FastAPI, SQLAlchemy, Alembic, ONNX Runtime, and Ultralytics at audit time.
- Android SDK and a wireless ADB device (`RMX3853`) are available. Flutter was not on PATH at audit time.
- YOLOE and InSPyReNet checkpoints were absent. Actual model inference cannot be claimed until the official checkpoints and dependencies are installed and tested.

## Architecture

FastAPI `/api/v1` handles identity, devices, job creation, upload, polling, and authenticated artifact retrieval. SQLAlchemy and Alembic own the SQLite schema. A separate worker claims queued jobs, loads AI models once, stores original and annotated images through a storage provider, and writes a versioned result JSON. The Flutter client only depends on the API contract and obtains the annotated image as an authenticated artifact. Results use UTC timestamps in the API and local time in the UI. One uploaded image per job is supported in V1.

## Verification

Read the complete initial project file list, classifier constructor/scoring path, prompt classes/groups, NPZ keys/shapes, reference result component, and Android device listing. No code was modified before this report.
