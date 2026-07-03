"""
Database module for D-Booth backend.

Provides async SQLAlchemy engine, session factory, and connection pool management
with comprehensive health checks and graceful shutdown support.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import Pool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Declarative base for ORM models
Base = declarative_base()

# Global engine instance
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None


def _configure_engine_kwargs() -> tuple[dict, dict]:
    """
    Configure engine connection arguments and kwargs based on database type.

    Returns:
        Tuple of (connect_args, engine_kwargs) for create_async_engine
    """
    database_url = settings.DATABASE_URL

    if database_url.startswith("sqlite"):
        # SQLite-specific configuration
        connect_args = {"check_same_thread": False}
        engine_kwargs = {
            "pool_pre_ping": False,  # Not needed for SQLite
        }
    else:
        # PostgreSQL/MySQL configuration with connection pooling
        connect_args = {
            "server_settings": {
                "application_name": settings.APP_NAME,
            },
            "command_timeout": 30,
        }
        engine_kwargs = {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_timeout": 30,  # Wait 30s for connection from pool
            "echo_pool": settings.DEBUG,  # Log pool checkouts/checkins
        }

    return connect_args, engine_kwargs


@event.listens_for(Pool, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record) -> None:
    """Set SQLite pragmas for better performance and reliability."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.close()


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine.

    Returns:
        AsyncEngine instance configured for the current database URL

    Raises:
        RuntimeError: If engine initialization fails
    """
    global _engine

    if _engine is None:
        connect_args, engine_kwargs = _configure_engine_kwargs()

        try:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                connect_args=connect_args,
                **engine_kwargs,
            )
            logger.info(
                f"Database engine initialized: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'SQLite'}"
            )
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise RuntimeError(f"Database engine initialization failed: {e}") from e

    return _engine


def get_session_maker() -> async_sessionmaker:
    """
    Get or create the global async session factory.

    Returns:
        async_sessionmaker configured with the global engine
    """
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        logger.info("Database session factory initialized")

    return _async_session_maker


class _AsyncSessionMakerProxy:
    """Backward-compatible callable for modules that import async_session_maker."""

    def __call__(self, *args, **kwargs):
        return get_session_maker()(*args, **kwargs)


class _AsyncEngineProxy:
    """Backward-compatible proxy for modules that import engine."""

    def begin(self):
        return get_engine().begin()

    def __getattr__(self, name: str):
        return getattr(get_engine(), name)


engine = _AsyncEngineProxy()
async_session_maker = _AsyncSessionMakerProxy()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database sessions.

    Yields:
        AsyncSession instance for database operations

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for manual database session management.

    Yields:
        AsyncSession instance with automatic rollback on exception

    Example:
        async with get_db_context() as db:
            user = await db.get(User, user_id)
            user.name = "New Name"
            await db.commit()
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database context error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """
    Check database connectivity and health.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.debug("Database health check passed")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def dispose_engine() -> None:
    """
    Gracefully dispose of the database engine and close all connections.

    Should be called during application shutdown.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        try:
            await _engine.dispose()
            logger.info("Database engine disposed successfully")
        except Exception as e:
            logger.error(f"Error disposing database engine: {e}")
        finally:
            _engine = None
            _async_session_maker = None
