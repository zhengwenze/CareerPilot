from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(subject: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "jti": str(uuid4()),
        "exp": expires_at,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
