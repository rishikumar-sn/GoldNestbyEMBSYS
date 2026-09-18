from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import current_identity, db_session
from app.ai.feedback import LABELS, confirm_job
from app.db.models import AnalysisJob, Device, User, utcnow
from app.services.images import sanitize_image
from app.services.storage import LocalStorageProvider


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class CreateJob(BaseModel):
    mode: str = Field(pattern="^(single|group)$")
    captured_at: datetime | None = None


class ConfirmedPiece(BaseModel):
    instance_number: int = Field(ge=1)
    label: str


class ConfirmJob(BaseModel):
    items: list[ConfirmedPiece] = Field(min_length=1)


def _owned_job(job_id: str, user: User, session: Session) -> AnalysisJob:
    job = session.get(AnalysisJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _job_view(job: AnalysisJob) -> dict:
    return {"job_id": job.id, "mode": job.mode, "status": job.status,
            "created_at": job.created_at, "captured_at": job.captured_at,
            "completed_at": job.completed_at, "error_message": job.error_message,
            "physical_jewel_count": (job.result_json or {}).get("physical_jewel_count")}


@router.post("", status_code=201)
def create_job(body: CreateJob, identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    user, device = identity
    captured_at = body.captured_at or utcnow()
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    job = AnalysisJob(user_id=user.id, device_id=device.id, mode=body.mode,
                      captured_at=captured_at.astimezone(timezone.utc))
    session.add(job)
    session.commit()
    return _job_view(job)


@router.get("")
def list_jobs(identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    jobs = session.scalars(select(AnalysisJob).where(AnalysisJob.user_id == identity[0].id)
                           .order_by(AnalysisJob.created_at.desc()).limit(100)).all()
    return [_job_view(job) for job in jobs]


@router.post("/{job_id}/images")
async def upload_image(job_id: str, file: UploadFile = File(...),
                       identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    job = _owned_job(job_id, identity[0], session)
    if job.status != "created" or job.original_artifact:
        raise HTTPException(status_code=409, detail="Job already has an image or was submitted")
    data = await file.read(20 * 1024 * 1024 + 1)
    try:
        sanitized = sanitize_image(data, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    artifact = "original.png" if file.content_type == "image/png" else "original.jpg"
    LocalStorageProvider().write(job.id, artifact, sanitized)
    job.original_artifact = artifact
    session.commit()
    return {"job_id": job.id, "artifact": artifact}


@router.post("/{job_id}/submit")
def submit_job(job_id: str, identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    job = _owned_job(job_id, identity[0], session)
    if job.status != "created" or not job.original_artifact:
        raise HTTPException(status_code=409, detail="Upload one image before submitting")
    job.status = "queued"
    session.commit()
    return _job_view(job)


@router.get("/labels")
def jewellery_labels(identity: tuple[User, Device] = Depends(current_identity)):
    return {"labels": LABELS}


@router.get("/{job_id}")
def get_job(job_id: str, identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    return _job_view(_owned_job(job_id, identity[0], session))


@router.get("/{job_id}/result")
def get_result(job_id: str, identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    job = _owned_job(job_id, identity[0], session)
    if job.status != "completed" or job.result_json is None:
        raise HTTPException(status_code=409, detail="Result is not ready")
    return job.result_json


@router.post("/{job_id}/confirm")
def confirm_result(job_id: str, body: ConfirmJob,
                   identity: tuple[User, Device] = Depends(current_identity),
                   session: Session = Depends(db_session)):
    job = _owned_job(job_id, identity[0], session)
    numbers = [item.instance_number for item in body.items]
    if len(set(numbers)) != len(numbers):
        raise HTTPException(status_code=422, detail="Each piece must appear once")
    if any(item.label not in LABELS for item in body.items):
        raise HTTPException(status_code=422, detail="Unknown jewellery type")
    try:
        return confirm_job(session, job, identity[0].id,
                           {item.instance_number: item.label for item in body.items})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{job_id}/artifacts/{artifact_id}")
def get_artifact(job_id: str, artifact_id: str, identity: tuple[User, Device] = Depends(current_identity),
                 session: Session = Depends(db_session)):
    job = _owned_job(job_id, identity[0], session)
    allowed = {job.original_artifact, job.annotated_artifact}
    allowed.update(instance.crop_artifact for instance in job.instances)
    allowed.update(instance.mask_artifact for instance in job.instances)
    if artifact_id not in allowed or artifact_id is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        data = LocalStorageProvider().read(job.id, artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Artifact unavailable") from exc
    return Response(content=data, media_type="image/png" if artifact_id.endswith(".png") else "image/jpeg")
