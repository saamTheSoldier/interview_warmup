"""
Base repository - generic CRUD interface (SOLID: Interface Segregation, Dependency Inversion).
Challenge: Consistent data access, testability via mocks, query optimization in one place.
"""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository. Subclasses define model-specific methods."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> ModelType | None:
        """Fetch single entity by primary key. Used for detail endpoints."""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        """Paginated list. Avoids loading full table (performance)."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit).order_by(self.model.id)
        )
        return list(result.scalars().all())

    async def add(self, entity: ModelType) -> ModelType:
        """Persist new entity. Caller commits session."""
        self.session.add(entity)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Remove entity from DB."""
        await self.session.delete(entity)
