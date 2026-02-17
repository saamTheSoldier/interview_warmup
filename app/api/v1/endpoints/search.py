"""
Search endpoint - Elasticsearch full-text search (job requirement).
Challenge: Expose search API, pagination, graceful fallback if ES down.
"""

from fastapi import APIRouter, Query

from app.search.elasticsearch_client import search_items
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/items")
async def search_items_endpoint(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search on items (title, description) via Elasticsearch."""
    hits = await search_items(query=q, skip=skip, limit=limit)
    return {"query": q, "results": hits, "count": len(hits)}
