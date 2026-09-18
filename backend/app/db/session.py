from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    if settings.resolved_database_url.startswith("sqlite"):
        url_path = settings.resolved_database_url.removeprefix("sqlite:///")
        from pathlib import Path

        Path(url_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.resolved_database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def sqlite_pragmas(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    return engine


def get_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()
