from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import get_engine
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.services.queue import worker_is_ready
from app.db.models import WorkerState
from app.db.session import get_session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_engine()
    yield


app = FastAPI(title="GoldNest API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(jobs_router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/ready")
def ready():
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    with get_session() as session:
        worker = session.get(WorkerState, 1)
        is_ready = worker_is_ready(worker)
    return {"database": "ok", "status": "ready" if is_ready else "not_ready",
            "worker": "ready" if is_ready else "unavailable"}
