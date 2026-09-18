# Architecture

Android Flutter app → TLS-pinned FastAPI `/api/v1` → SQLite job queue → one model worker → local artifact storage. API and worker share SQLAlchemy repositories and a local storage provider. Authenticated clients can fetch only their own jobs and artifacts. The result JSON carries count, per-instance type/score, original and annotated image references, and UTC capture/processing times. The app converts timestamps to device local time.

The image pipeline uses YOLOE text-prompt instance segmentation, deduplicates physical masks, refines poor masks or falls back to InSPyReNet, prepares white-background crops, and calls the existing SigLIP2 classifier for each instance. Model versions and timings accompany each result. SQLite, storage, and queue implementations are replaceable behind service boundaries without changing mobile API calls.
