"""
Elasticsearch client - search and analytics (job requirement).
Challenge: Index management, async operations, graceful degradation when ES is down.
"""

from typing import Any

from elasticsearch import AsyncElasticsearch

from app.config import get_settings

settings = get_settings()

# Index name for items (search use case)
ITEMS_INDEX = "items"

_es_client: AsyncElasticsearch | None = None


async def get_elasticsearch() -> AsyncElasticsearch:
    """Get Elasticsearch client. Dependency injection for tests."""
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(settings.elasticsearch_url)
    return _es_client


async def ensure_items_index() -> None:
    """Create items index with mapping if not exists (analytics-friendly fields)."""
    es = await get_elasticsearch()
    if not await es.indices.exists(index=ITEMS_INDEX):
        await es.indices.create(
            index=ITEMS_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "price_cents": {"type": "integer"},
                        "owner_id": {"type": "integer"},
                        "created_at": {"type": "date"},
                    }
                }
            },
        )


async def index_item(doc: dict[str, Any]) -> bool:
    """Index a single item for search."""
    try:
        es = await get_elasticsearch()
        await es.index(index=ITEMS_INDEX, id=doc["id"], document=doc)
        return True
    except Exception:
        return False


async def search_items(query: str, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
    """Full-text search on title and description. Returns list of hits."""
    try:
        es = await get_elasticsearch()
        response = await es.search(
            index=ITEMS_INDEX,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "description"],
                        "fuzziness": "AUTO",
                    }
                },
                "from": skip,
                "size": limit,
            },
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
    except Exception:
        return []


async def remove_item_from_index(item_id: int) -> bool:
    """Remove item from search index when deleted."""
    try:
        es = await get_elasticsearch()
        await es.delete(index=ITEMS_INDEX, id=item_id, ignore=404)
        return True
    except Exception:
        return False
