# Phase 4 — model management

Status: PASS (17 September 2026)

Implemented a model manifest, official model setup script, checksum validation, deep load verification, explicit SigLIP2 processor cache, and CPU/provider inspection. `download_models.py` prepares YOLOE through the Ultralytics API in `backend/models/yoloe`, downloads the official InSPyReNet fast checkpoint with SHA-256 verification, optionally downloads the base checkpoint, and caches only the public SigLIP2 processor. It does not write into the supplied SigLIP2 directory.

Validation on Windows/Python 3.12: downloaded `yoloe-26s-seg.pt` (31,072,171 bytes), `mobileclip2_b.ts` (253,794,476 bytes), and `ckpt_fast.pth` (367,520,613 bytes). The fast checkpoint SHA-256 matched `e61ed7e85763dd83a796e1d650ea78604fff524121750858c54a6b560ac58c82`. `verify_models.py --deep` loaded YOLOE with text prompts, InSPyReNet fast on CPU, and the user's ONNX model with `CPUExecutionProvider`. The ONNX input is `onnx::Cast_0` float32 `[1,3,256,256]`; outputs are `[1,64,768]` and `[1,768]`.

Known limitations: this phase verifies loading but does not claim accurate inference on jewellery images. `torch.cuda.is_available()` is false and ONNX Runtime has no CUDA provider in the tested environment. The optional InSPyReNet base checkpoint was not downloaded. The `transformers` version used for setup must be checked against the existing classifier during phase 7.
