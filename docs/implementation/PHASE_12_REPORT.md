# Phase 12 — full-system verification

Status: PASS for the V1 verification gates exercised on 18 September 2026.

## Executed checks

- Backend test suite: `pytest -q` — 14 passed. This covers invalid credentials, token refresh rotation and replay rejection, logout, device revocation, guarded ownership, failed jobs, exclusive queue claiming, feedback confirmation, and duplicate-prompt instance deduplication.
- Flutter: `flutter analyze` — no issues; `flutter test` — 5 passed, with the two opt-in LAN tests skipped by default.
- Live backend: `https://192.168.29.121:8443/api/v1/health` returned `ok`; `/ready` returned database and worker `ready`.
- Real model API pipeline: a four-piece group image completed through authentication, upload, segmentation, classification, artifact retrieval, and result API. Result: 4 pieces, 2 Earrings / Nosepin and 2 Bangle.
- Real Android path on RMX3853: selected the image through Android Photo Picker, uploaded it through the certificate-pinned client, observed worker polling complete, and opened the result screen. The app displayed the annotated image, four individual crops, editable labels, and the matching type totals.
- Fallback and visual-prompt recovery, duplicate-detection handling, no-detection response, and single-ring classification were independently verified in Phases 5–8 and remain covered by their model and service tests.

## Limits of this verification

The model ran on CPU. The selected group image produced two low-confidence Bangle predictions, which the UI presents for reviewer correction. The checks demonstrate the implemented workflows; they do not establish accuracy for every lighting condition, jewellery style, or background.
