"""
Item CRUD endpoints - RESTful resource (GET/POST/PUT/DELETE).
Challenge: Pagination, auth, validation, 404 handling.
Design: Thin controller; service layer holds business logic.
"""

from fastapi import APIRouter, HTTPException, status, Query

from app.db.session import DbSession
from app.db.repositories.item_repository import ItemRepository
from app.db.repositories.user_repository import UserRepository
from app.services.item_service import ItemService
from app.schemas.item import ItemCreate, ItemUpdate, ItemWithOwnerResponse
from app.core.dependencies import CurrentUserId
from app.config import get_settings

router = APIRouter()
settings = get_settings()


def _get_item_service(session: DbSession) -> ItemService:
    """Factory for service with repository injection (Dependency Inversion)."""
    return ItemService(ItemRepository(session), UserRepository(session))


@router.get("", response_model=list[ItemWithOwnerResponse])
async def list_items(
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=settings.max_page_size),
):
    """List items with pagination. REST: GET /items?skip=0&limit=20."""
    svc = _get_item_service(session)
    return await svc.list_items(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ItemWithOwnerResponse)
async def get_item(session: DbSession, item_id: int):
    """Get single item. Uses Redis cache for performance."""
    svc = _get_item_service(session)
    item = await svc.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.post("", response_model=ItemWithOwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_item(session: DbSession, data: ItemCreate, user_id: CurrentUserId):
    """Create item (authenticated). Owner set from token or body (here from body for demo)."""
    # In strict REST, owner_id might come from token only
    svc = _get_item_service(session)
    return await svc.create(data)


@router.put("/{item_id}", response_model=ItemWithOwnerResponse)
async def update_item(session: DbSession, item_id: int, data: ItemUpdate, user_id: CurrentUserId):
    """Update item. Invalidates cache and re-indexes in queue."""
    svc = _get_item_service(session)
    item = await svc.update(item_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(session: DbSession, item_id: int, user_id: CurrentUserId):
    """Delete item. Removes from DB, cache, and search index."""
    svc = _get_item_service(session)
    ok = await svc.delete(item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
