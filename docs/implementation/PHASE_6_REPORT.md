# Phase 6 — InSPyReNet and visual prompt recovery

Status: PASS for fallback integration and visual-prompt recovery, with full-frame saliency limits recorded.

Implemented lazy InSPyReNet fast loading, ROI refinement for severely fragmented masks, full-image saliency fallback, connected-component extraction, and a lower-confidence source/warning for fallback counts. CUDA out-of-memory retries once on CPU. After the user requested it, added YOLOE visual prompts from two copied dataset reference images, with manually verified boxes and an explicit source manifest. Visual predictions are deduplicated with text predictions; prompt group IDs are not treated as final type labels.

Validation: `pytest -q tests/test_instances.py tests/test_segmentation.py` passed (3 tests). InSPyReNet CPU inference on a held-out ring ROI yielded one component at the ring location. A full-scale ring image produced a broad saliency region and small artifacts; full-frame saliency alone is not a reliable count on that image. YOLOE visual prompting on a held-out four-piece group image found the bangle that the initial text-only test missed; combined text/visual inference yielded four outlined pieces. A distinct held-out full-frame ring photo had zero text predictions and one visual prediction at the ring. Reference images were not used as evaluation targets.

Known limitations: the group and ring examples share the same camera/tray style as the reference images. Full-frame InSPyReNet can mistake the scale/tray for foreground; results from this source are flagged for manual verification. Broader camera/background validation remains necessary before production accuracy claims.
