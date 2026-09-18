# Phase 3 — queued jobs

Status: PASS (17 September 2026)

Implemented one-image job creation, MIME/decode/dimension/size validation, EXIF orientation correction with metadata stripping, queued submission, guarded polling/results/history/artifact retrieval, conditional SQLite job claiming, job heartbeat, stale-job requeue, and failure persistence. Processing runs through an injected worker callable; the phase test uses an explicit dummy callable and does not imply AI inference is ready.

Validation: `pytest -q tests/test_jobs.py` passed (3 tests) covering invalid upload, upload-before-submit, duplicate submit, authenticated ownership isolation, queued → processing → completed, exclusive claim, and failure visibility. Original artifacts were read through the protected API. The test fixture used a temporary SQLite database and storage root.

Known limitations: the production worker is not launched until model management and the real image pipeline pass their own gates. Result image rendering and per-instance classification are subsequent phases. The current worker loop updates readiness only when explicitly given a real, loaded processor.
