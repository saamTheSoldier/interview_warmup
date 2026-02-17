"""
Item repository - item data access and query optimization (SOLID: Single Responsibility).
Challenge: Database query performance; avoid N+1, use indexes.
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.item import Item
from app.db.repositories.base_repository import BaseRepository


class ItemRepository(BaseRepository[Item]):
    """Item-specific queries. Uses selectinload to avoid N+1 when loading owner."""

    def __init__(self, session):
        super().__init__(session, Item)

    async def get_by_id_with_owner(self, id: int) -> Item | None:
        """Fetch item with owner in one query (solves N+1 problem)."""
        result = await self.session.execute(
            select(Item).where(Item.id == id).options(selectinload(Item.owner))
        )
        return result.scalar_one_or_none()

    async def get_many_with_owner(self, skip: int = 0, limit: int = 20) -> list[Item]:
        """Paginated items with owner loaded in one extra query (eager loading)."""
        result = await self.session.execute(
            select(Item)
            .options(selectinload(Item.owner))
            .offset(skip)
            .limit(limit)
            .order_by(Item.id)
        )
        return list(result.scalars().all())
