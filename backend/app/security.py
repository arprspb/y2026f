from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.models import UserRole

settings = get_settings()


def _password_digest(password: str) -> bytes:
    """SHA256 перед bcrypt: без лимита 72 байта у bcrypt и без устаревшего passlib."""
    return hashlib.sha256(password.encode("utf-8")).digest()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_password_digest(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_digest(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, user_id: int, role: UserRole) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: dict[str, Any] = {
        "exp": expire,
        "sub": subject,
        "user_id": user_id,
        "role": role.value,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
