"""
Security module for D-Booth backend.

Provides JWT token creation, verification, and refresh token rotation
with comprehensive security validations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when a token is invalid or malformed."""

    pass


class TokenTypeMismatchError(TokenError):
    """Raised when token type doesn't match expected type."""

    pass


def create_access_token(
    user_id: UUID,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token with optional additional claims.

    Args:
        user_id: User UUID to encode in the token
        expires_delta: Optional custom expiration time
        additional_claims: Optional dict of additional claims to include

    Returns:
        Encoded JWT access token string

    Example:
        token = create_access_token(
            user_id=user.id,
            additional_claims={"role": "admin", "team_id": "123"}
        )
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": str(uuid4()),
    }

    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)

    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug(f"Access token created for user {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise TokenError(f"Token creation failed: {e}") from e


def create_refresh_token(user_id: UUID, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a JWT refresh token with optional additional claims.

    Args:
        user_id: User UUID to encode in the token
        additional_claims: Optional dict of additional claims to include

    Returns:
        Encoded JWT refresh token string with longer expiration

    Example:
        refresh_token = create_refresh_token(user_id=user.id)
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": str(uuid4()),
    }

    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)

    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug(f"Refresh token created for user {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise TokenError(f"Token creation failed: {e}") from e


def verify_token(token: str, expected_type: str = "access") -> Optional[UUID]:
    """
    Verify JWT token and return user_id.

    Validates the token signature AND the ``type`` claim so that an access
    token cannot be used as a refresh token (and vice-versa). Callers must
    pass expected_type="refresh" when validating refresh tokens.

    Args:
        token: JWT token string to verify
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        User UUID if token is valid, None otherwise

    Example:
        user_id = verify_token(token, expected_type="access")
        if user_id:
            # Token is valid, proceed with user_id
            pass
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id_str: Optional[str] = payload.get("sub")
        token_type: str = payload.get("type", "")

        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            return None

        # Reject token-type mismatch (e.g. refresh token used as access token)
        if token_type != expected_type:
            logger.warning(f"Token type mismatch: expected '{expected_type}', got '{token_type}'")
            return None

        user_id = UUID(user_id_str)
        logger.debug(f"Token verified for user {user_id}")
        return user_id

    except ExpiredSignatureError:
        logger.debug(f"Token expired for type '{expected_type}'")
        return None
    except InvalidTokenError as e:
        logger.warning(f"JWT validation error: {e}")
        return None
    except ValueError as e:
        logger.warning(f"Invalid user_id format in token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def decode_token(token: str, verify: bool = True) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token and return full payload.

    Args:
        token: JWT token string to decode
        verify: Whether to verify signature (default True)

    Returns:
        Token payload dict if valid, None otherwise

    Example:
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            custom_claim = payload.get("custom_field")
    """
    try:
        if verify:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        else:
            payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except ExpiredSignatureError:
        logger.debug("Token expired during decode")
        return None
    except InvalidTokenError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


def get_token_jti(token: str) -> Optional[str]:
    """
    Extract JTI (JWT ID) from token without full verification.

    Useful for token revocation checks before expensive verification.

    Args:
        token: JWT token string

    Returns:
        JTI string if present, None otherwise
    """
    payload = decode_token(token, verify=False)
    if payload:
        return payload.get("jti")
    return None


def rotate_refresh_token(old_refresh_token: str, user_id: UUID) -> Optional[tuple[str, str]]:
    """
    Rotate refresh token: verify old token and issue new access + refresh tokens.

    This implements refresh token rotation for enhanced security. The old
    refresh token should be invalidated after successful rotation.

    Args:
        old_refresh_token: Current refresh token to rotate
        user_id: User UUID (for verification)

    Returns:
        Tuple of (new_access_token, new_refresh_token) if successful, None otherwise

    Example:
        tokens = rotate_refresh_token(old_token, user_id)
        if tokens:
            new_access, new_refresh = tokens
            # Store new_refresh JTI in database, invalidate old token
    """
    verified_user_id = verify_token(old_refresh_token, expected_type="refresh")

    if verified_user_id is None or verified_user_id != user_id:
        logger.warning(f"Refresh token rotation failed for user {user_id}")
        return None

    try:
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        logger.info(f"Refresh token rotated for user {user_id}")
        return (new_access_token, new_refresh_token)
    except Exception as e:
        logger.error(f"Error rotating refresh token: {e}")
        return None
