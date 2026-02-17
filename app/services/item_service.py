"""
Item service - business logic for items (SOLID: Single Responsibility).
Challenge: Orchestrate repository, cache, search, queue; keep controllers thin.
Design: Service depends on abstractions (repositories); easy to test with mocks.
"""

from app.db.repositories.item_repository import ItemRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas.item import ItemCreate, ItemUpdate, ItemWithOwnerResponse
from app.db.models.item import Item
from app.cache.redis_client import cache_get, cache_set, cache_delete
from app.search.elasticsearch_client import ensure_items_index
from app.queue.tasks import index_item_task

# Cache key prefix and TTL for item detail (performance optimization)
CACHE_PREFIX = "item:"
CACHE_TTL = 300


def _item_to_doc(item: Item) -> dict:
    """Convert ORM model to document for Elasticsearch and cache."""
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description or "",
        "price_cents": item.price_cents,
        "owner_id": item.owner_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _item_to_response(item: Item) -> ItemWithOwnerResponse:
    """Map model to API response with owner email."""
    data = {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "price_cents": item.price_cents,
        "owner_id": item.owner_id,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "owner_email": getattr(item.owner, "email", None) if hasattr(item, "owner") else None,
    }
    return ItemWithOwnerResponse(**data)


class ItemService:
    """Handles all item use cases: CRUD, cache, search indexing."""

    def __init__(self, item_repo: ItemRepository, user_repo: UserRepository):
        self.item_repo = item_repo
        self.user_repo = user_repo

    async def create(self, data: ItemCreate) -> ItemWithOwnerResponse:
        """Create item, enqueue indexing (event-driven), return response."""
        item = Item(
            title=data.title,
            description=data.description,
            price_cents=data.price_cents,
            owner_id=data.owner_id,
        )
        item = await self.item_repo.add(item)
        # Event-driven: send to queue instead of blocking on Elasticsearch
        index_item_task.delay(_item_to_doc(item))
        # Reload with owner loaded to avoid lazy load in async context (MissingGreenlet)
        item = await self.item_repo.get_by_id_with_owner(item.id)
        return _item_to_response(item)

    async def get_by_id(self, id: int, use_cache: bool = True) -> ItemWithOwnerResponse | None:
        """Get item by id. Uses Redis cache to reduce DB load (performance)."""
        if use_cache:
            cached = await cache_get(CACHE_PREFIX + str(id))
            if cached:
                import json
                data = json.loads(cached)
                return ItemWithOwnerResponse(**data)
        item = await self.item_repo.get_by_id_with_owner(id)
        if not item:
            return None
        resp = _item_to_response(item)
        if use_cache:
            await cache_set(CACHE_PREFIX + str(id), resp.model_dump(mode="json"), CACHE_TTL)
        return resp

    async def list_items(self, skip: int = 0, limit: int = 20) -> list[ItemWithOwnerResponse]:
        """Paginated list with owner (eager loading in repo)."""
        items = await self.item_repo.get_many_with_owner(skip=skip, limit=limit)
        return [_item_to_response(i) for i in items]

    async def update(self, id: int, data: ItemUpdate) -> ItemWithOwnerResponse | None:
        """Update item, invalidate cache, re-index in queue."""
        item = await self.item_repo.get_by_id_with_owner(id)
        if not item:
            return None
        if data.title is not None:
            item.title = data.title
        if data.description is not None:
            item.description = data.description
        if data.price_cents is not None:
            item.price_cents = data.price_cents
        await self.item_repo.session.flush()
        await self.item_repo.session.refresh(item)
        await cache_delete(CACHE_PREFIX + str(id))
        index_item_task.delay(_item_to_doc(item))
        return _item_to_response(item)

    async def delete(self, id: int) -> bool:
        """Delete item, invalidate cache, remove from search index."""
        item = await self.item_repo.get_by_id(id)
        if not item:
            return False
        await self.item_repo.delete(item)
        await cache_delete(CACHE_PREFIX + str(id))
        from app.search.elasticsearch_client import remove_item_from_index
        await remove_item_from_index(id)
        return True
