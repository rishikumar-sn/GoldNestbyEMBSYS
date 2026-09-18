from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Device, RefreshToken, User, utcnow
from app.db.session import get_session


password_hasher = PasswordHasher()
bearer = HTTPBearer()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _secret() -> str:
    secret = get_settings().jwt_secret
    if len(secret) < 32 or secret == "REPLACE_WITH_A_RANDOM_64_CHARACTER_SECRET":
        raise RuntimeError("Set a random JWT_SECRET of at least 32 characters in backend/.env")
    return secret


def access_token(user_id: str, device_id: str) -> str:
    expires = utcnow() + timedelta(minutes=get_settings().access_token_minutes)
    return jwt.encode({"sub": user_id, "device_id": device_id, "exp": expires, "type": "access"}, _secret(), algorithm="HS256")


def new_refresh_token(session: Session, user_id: str, device_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    session.add(RefreshToken(
        user_id=user_id,
        device_id=device_id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days),
    ))
    return raw


def find_refresh(session: Session, raw: str) -> RefreshToken | None:
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record is None or record.revoked_at is not None:
        return None
    expires_at = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    return record if expires_at > utcnow() else None


def db_session():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(db_session),
) -> tuple[User, Device]:
    try:
        claims = jwt.decode(credentials.credentials, _secret(), algorithms=["HS256"])
        if claims.get("type") != "access":
            raise ValueError("Wrong token type")
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc
    if not claims.get("sub") or not claims.get("device_id"):
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = session.get(User, claims["sub"])
    device = session.get(Device, claims["device_id"])
    if not user or not user.is_active or not device or device.user_id != user.id or device.revoked_at:
        raise HTTPException(status_code=401, detail="Account or device is unavailable")
    return user, device
