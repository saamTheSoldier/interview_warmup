"""
Async database session management.
Challenge: Connection pooling, scoped sessions, proper cleanup.
Design: Dependency injection for request-scoped sessions (no connection leaks).
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import Base

settings = get_settings()

# Async engine with connection pool (scalability)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=10,
    max_overflow=20,
)

# Session factory: one session per request
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session per request. Ensures rollback on error, close on exit."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for FastAPI dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
