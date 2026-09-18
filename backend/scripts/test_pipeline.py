from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.pipeline import AnalysisPipeline  # noqa: E402
from app.db.models import AnalysisJob, utcnow  # noqa: E402
from app.services.images import sanitize_image  # noqa: E402
from app.services.storage import LocalStorageProvider  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mode", choices=["single", "group"], required=True)
    args = parser.parse_args()
    job_id = str(uuid4())
    store = LocalStorageProvider()
    mime = "image/png" if args.image.suffix.lower() == ".png" else "image/jpeg"
    original_name = "original.png" if mime == "image/png" else "original.jpg"
    store.write(job_id, original_name, sanitize_image(args.image.read_bytes(), mime))
    job = AnalysisJob(id=job_id, user_id=str(uuid4()), device_id=str(uuid4()), mode=args.mode,
                      status="processing", original_artifact=original_name,
                      created_at=utcnow(), captured_at=utcnow())
    result = AnalysisPipeline(storage=store)(job)
    output = store.root / job_id / "result.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"job_id": job_id, "physical_jewel_count": result["physical_jewel_count"],
                      "type_counts": result["type_counts"], "warnings": result["warnings"],
                      "timings_ms": result["timings_ms"], "result_json": str(output),
                      "annotated_image": str(store.root / job_id / "annotated.jpg")}, indent=2))


if __name__ == "__main__":
    main()
