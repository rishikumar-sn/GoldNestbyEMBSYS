from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.security import access_token, current_identity, db_session, find_refresh, new_refresh_token, verify_password
from app.db.models import Device, RefreshToken, User, utcnow


router = APIRouter(prefix="/api/v1")


class LoginRequest(BaseModel):
    username: str
    password: str
    installation_id: UUID
    platform: str = Field(max_length=32)
    app_version: str = Field(default="unknown", max_length=50)
    display_name: str | None = Field(default=None, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    device_id: str


@router.post("/auth/login", response_model=Tokens)
def login(body: LoginRequest, session: Session = Depends(db_session)):
    user = session.scalar(select(User).where(User.username == body.username))
    if user is None or not user.is_active or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    device = session.scalar(select(Device).where(Device.user_id == user.id, Device.installation_id == str(body.installation_id)))
    if device and device.revoked_at:
        raise HTTPException(status_code=403, detail="Device has been revoked")
    if device is None:
        device = Device(user_id=user.id, installation_id=str(body.installation_id), platform=body.platform,
                        app_version=body.app_version, display_name=body.display_name)
        session.add(device)
        session.flush()
    else:
        device.platform = body.platform
        device.app_version = body.app_version
        device.display_name = body.display_name
    raw_refresh = new_refresh_token(session, user.id, device.id)
    session.commit()
    return Tokens(access_token=access_token(user.id, device.id), refresh_token=raw_refresh, device_id=device.id)


@router.post("/auth/refresh", response_model=Tokens)
def refresh(body: RefreshRequest, session: Session = Depends(db_session)):
    record = find_refresh(session, body.refresh_token)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = session.get(User, record.user_id)
    device = session.get(Device, record.device_id)
    if not user or not user.is_active or not device or device.revoked_at:
        raise HTTPException(status_code=401, detail="Account or device is unavailable")
    claimed = session.execute(update(RefreshToken).where(RefreshToken.id == record.id, RefreshToken.revoked_at.is_(None)).values(revoked_at=utcnow()))
    if claimed.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=401, detail="Refresh token already used")
    raw_refresh = new_refresh_token(session, user.id, device.id)
    session.commit()
    return Tokens(access_token=access_token(user.id, device.id), refresh_token=raw_refresh, device_id=device.id)


@router.post("/auth/logout")
def logout(body: RefreshRequest, identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    record = find_refresh(session, body.refresh_token)
    if record and record.user_id == identity[0].id and record.device_id == identity[1].id:
        record.revoked_at = utcnow()
        session.commit()
    return {"status": "ok"}


@router.get("/devices/me")
def device_me(identity: tuple[User, Device] = Depends(current_identity)):
    user, device = identity
    return {"user_id": user.id, "username": user.username, "device_id": device.id,
            "installation_id": device.installation_id, "platform": device.platform, "app_version": device.app_version}


@router.post("/devices/revoke")
def revoke_device(identity: tuple[User, Device] = Depends(current_identity), session: Session = Depends(db_session)):
    _, device = identity
    device = session.get(Device, device.id)
    device.revoked_at = utcnow()
    session.execute(update(RefreshToken).where(RefreshToken.device_id == device.id, RefreshToken.revoked_at.is_(None)).values(revoked_at=utcnow()))
    session.commit()
    return {"status": "revoked"}

