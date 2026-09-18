from __future__ import annotations

import logging

from app.ai.pipeline import AnalysisPipeline
from app.workers.jobs import run_forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    pipeline = AnalysisPipeline()
    logging.getLogger(__name__).info("Models loaded; worker ready")
    run_forever(pipeline)

