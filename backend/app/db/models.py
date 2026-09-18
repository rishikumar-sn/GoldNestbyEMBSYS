from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "installation_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    installation_id: Mapped[str] = mapped_column(String(36))
    platform: Mapped[str] = mapped_column(String(32))
    app_version: Mapped[str] = mapped_column(String(50), default="unknown")
    display_name: Mapped[str | None] = mapped_column(String(100))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="created", index=True)
    original_artifact: Mapped[str | None] = mapped_column(String(255))
    annotated_artifact: Mapped[str | None] = mapped_column(String(255))
    result_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    instances: Mapped[list[JewelInstance]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JewelInstance(Base):
    __tablename__ = "jewel_instances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), index=True)
    instance_number: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[dict] = mapped_column(JSON)
    segmentation: Mapped[dict] = mapped_column(JSON)
    classification: Mapped[dict] = mapped_column(JSON)
    crop_artifact: Mapped[str | None] = mapped_column(String(255))
    mask_artifact: Mapped[str | None] = mapped_column(String(255))
    job: Mapped[AnalysisJob] = relationship(back_populates="instances")


class JewelConfirmation(Base):
    __tablename__ = "jewel_confirmations"
    __table_args__ = (UniqueConstraint("job_id", "instance_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), index=True)
    instance_number: Mapped[int] = mapped_column(Integer)
    predicted_label: Mapped[str] = mapped_column(String(100))
    confirmed_label: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    confirmed_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerState(Base):
    __tablename__ = "worker_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    models_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[str | None] = mapped_column(Text)
