from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Event, Thread

from app.db.models import AnalysisJob, JewelInstance, utcnow
from app.db.session import get_session
from app.services.queue import SQLiteQueueProvider, heartbeat


log = logging.getLogger(__name__)
Processor = Callable[[AnalysisJob], dict]


def process_one(processor: Processor) -> bool:
    with get_session() as session:
        queue = SQLiteQueueProvider()
        queue.requeue_stale(session)
        job = queue.claim(session)
        if job is None:
            return False
        job_id = job.id
    stopped = Event()

    def pulse():
        while not stopped.wait(10):
            with get_session() as session:
                live = session.get(AnalysisJob, job_id)
                if not live or live.status != "processing":
                    return
                live.heartbeat_at = utcnow()
                heartbeat(session, models_ready=True)

    pulse_thread = Thread(target=pulse, daemon=True)
    pulse_thread.start()
    try:
        result = processor(job)
        with get_session() as session:
            live = session.get(AnalysisJob, job_id)
            live.result_json = result
            live.annotated_artifact = result.get("artifacts", {}).get("annotated")
            for item in result.get("instances", []):
                session.add(JewelInstance(
                    id=item["instance_id"], job_id=job_id,
                    instance_number=item["instance_number"], bbox=item["bbox"],
                    segmentation=item["segmentation"], classification=item["classification"],
                    crop_artifact=item["artifacts"].get("crop"),
                    mask_artifact=item["artifacts"].get("mask"),
                ))
            live.status = "completed"
            live.completed_at = utcnow()
            session.commit()
    except Exception as exc:
        log.exception("Job %s failed", job_id)
        with get_session() as session:
            live = session.get(AnalysisJob, job_id)
            live.status = "failed"
            live.error_message = str(exc)[:1000]
            live.completed_at = utcnow()
            session.commit()
    finally:
        stopped.set()
        pulse_thread.join(timeout=1)
    return True


def run_forever(processor: Processor, interval_seconds: float = 2.0):
    import time

    while True:
        with get_session() as session:
            heartbeat(session, models_ready=True)
        if not process_one(processor):
            time.sleep(interval_seconds)
