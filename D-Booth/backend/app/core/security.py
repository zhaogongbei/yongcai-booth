from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from uuid import UUID, uuid4

from app.core.config import settings


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "jti": str(uuid4()),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(user_id: UUID) -> str:
    """Create JWT refresh token"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid4()),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Optional[UUID]:
    """Verify JWT token and return user_id.

    Validates the token signature AND the ``type`` claim so that an access
    token cannot be used as a refresh token (and vice-versa). Callers must
    pass expected_type="refresh" when validating refresh tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type", "")
        if user_id is None:
            return None
        # Reject token-type mismatch (e.g. refresh token used as access token)
        if token_type != expected_type:
            return None
        return UUID(user_id)
    except Exception:
        return None
