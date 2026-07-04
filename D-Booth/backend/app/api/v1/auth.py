from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.core.logging import logger
from app.core.security import create_access_token, create_refresh_token
from app.models.models import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter()
REFRESH_REVOCATION_UNAVAILABLE_DETAIL = "Refresh token revocation is unavailable"


def _refresh_revocation_key(payload: dict) -> str:
    return f"revoked_refresh:{payload.get('jti') or payload.get('sub')}"


def _decode_refresh_payload(refresh_token: str) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    return payload


def _refresh_token_ttl(payload: dict) -> int:
    return int(payload["exp"] - datetime.now(timezone.utc).timestamp())


async def _get_redis_client():
    import redis.asyncio as redis

    client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        await client.ping()
    except Exception as e:
        await client.aclose()
        logger.warning(f"Redis unavailable for refresh token revocation: {e}")
        return None
    return client


async def _is_refresh_token_revoked(payload: dict) -> bool:
    client = await _get_redis_client()
    if client is None:
        logger.warning("Redis unavailable while checking refresh token revocation")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REFRESH_REVOCATION_UNAVAILABLE_DETAIL,
        )
    try:
        return bool(await client.exists(_refresh_revocation_key(payload)))
    except Exception as e:
        logger.error(f"Failed to check refresh token revocation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REFRESH_REVOCATION_UNAVAILABLE_DETAIL,
        )
    finally:
        await client.aclose()


async def _revoke_refresh_payload(payload: dict, context: str, user_id: UUID) -> None:
    ttl = _refresh_token_ttl(payload)
    if ttl <= 0:
        return

    client = await _get_redis_client()
    if client is None:
        logger.warning(
            f"Redis unavailable during {context} for user {user_id}. "
            f"Token revocation cannot be confirmed ({ttl}s remaining)."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REFRESH_REVOCATION_UNAVAILABLE_DETAIL,
        )

    try:
        await client.setex(_refresh_revocation_key(payload), ttl, "1")
    except Exception as e:
        logger.error(f"Failed to revoke token during {context} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REFRESH_REVOCATION_UNAVAILABLE_DETAIL,
        )
    finally:
        await client.aclose()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    user_service = UserService(db)

    try:
        user = await user_service.create_user(user_in)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Login and get access token"""
    user_service = UserService(db)

    user = await user_service.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True), db: AsyncSession = Depends(get_db)
):
    """Refresh access token — refresh_token must be sent in the request body."""
    payload = _decode_refresh_payload(refresh_token)
    if await _is_refresh_token_revoked(payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    await _revoke_refresh_payload(payload, "refresh", user.id)

    return Token(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_token: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
):
    """
    Revoke a refresh token until it naturally expires.

    Logout must fail closed when token revocation cannot be confirmed; otherwise
    the refresh token would remain valid while the API reports success.
    """
    payload = _decode_refresh_payload(refresh_token)
    if payload["sub"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refresh token does not belong to current user",
        )

    ttl = _refresh_token_ttl(payload)
    if ttl <= 0:
        return None

    await _revoke_refresh_payload(payload, "logout", current_user.id)
    logger.info(f"User {current_user.id} logged out successfully, token revoked")
    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user
