from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import AnalysisJob, WorkerState, utcnow


class QueueProvider(Protocol):
    def claim(self, session: Session) -> AnalysisJob | None: ...


class SQLiteQueueProvider:
    def requeue_stale(self, session: Session, max_age_seconds: int = 120) -> int:
        cutoff = utcnow() - timedelta(seconds=max_age_seconds)
        changed = session.execute(update(AnalysisJob)
            .where(AnalysisJob.status == "processing", AnalysisJob.heartbeat_at < cutoff)
            .values(status="queued", started_at=None, heartbeat_at=None))
        session.commit()
        return changed.rowcount

    def claim(self, session: Session) -> AnalysisJob | None:
        # SQLite serializes writers. The conditional UPDATE prevents a second
        # worker from claiming a job selected by the first.
        candidate = session.scalar(select(AnalysisJob.id).where(AnalysisJob.status == "queued")
                                   .order_by(AnalysisJob.created_at, AnalysisJob.id).limit(1))
        if candidate is None:
            return None
        claimed = session.execute(update(AnalysisJob)
            .where(AnalysisJob.id == candidate, AnalysisJob.status == "queued")
            .values(status="processing", started_at=utcnow(), heartbeat_at=utcnow(), attempts=AnalysisJob.attempts + 1))
        if claimed.rowcount != 1:
            session.rollback()
            return None
        session.commit()
        return session.get(AnalysisJob, candidate)


def heartbeat(session: Session, models_ready: bool, detail: str | None = None) -> None:
    state = session.get(WorkerState, 1)
    if state is None:
        state = WorkerState(id=1)
        session.add(state)
    state.heartbeat_at = utcnow()
    state.models_ready = models_ready
    state.detail = detail
    session.commit()


def worker_is_ready(state: WorkerState | None) -> bool:
    if not state or not state.heartbeat_at or not state.models_ready:
        return False
    at = state.heartbeat_at
    if at.tzinfo is None:
        from datetime import timezone

        at = at.replace(tzinfo=timezone.utc)
    return at >= utcnow() - timedelta(seconds=45)
