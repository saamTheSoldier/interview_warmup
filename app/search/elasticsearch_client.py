"""
Elasticsearch client - search and analytics (job requirement).
Challenge: Index management, async operations, graceful degradation when ES is down.
Sync helpers used by Celery workers (no event loop in fork).
"""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, Elasticsearch

logger = logging.getLogger(__name__)

from app.config import get_settings

settings = get_settings()

# Index name for items (search use case)
ITEMS_INDEX = "items"

_es_client: AsyncElasticsearch | None = None


def _es_client_options() -> dict:
    """Build Elasticsearch client options from settings (supports HTTPS + basic auth in URL)."""
    url = settings.elasticsearch_url
    # Parse optional user:pass from URL (e.g. https://elastic:pass@localhost:9200)
    basic_auth = None
    if "@" in url and "://" in url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.username and parsed.password:
                basic_auth = (parsed.username, parsed.password)
            # Remove auth from URL for the client (it uses basic_auth separately)
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc += f":{parsed.port}"
            url = f"{parsed.scheme}://{netloc}"
        except Exception:
            pass
    opts = {
        "hosts": [url],
        "verify_certs": getattr(settings, "elasticsearch_verify_certs", True),
        "request_timeout": 30,  # PUT/index can be slow when ES busy; default 10s was too low
    }
    if basic_auth:
        opts["basic_auth"] = basic_auth
    return opts


async def get_elasticsearch() -> AsyncElasticsearch:
    """Get Elasticsearch client. Dependency injection for tests."""
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(**_es_client_options())
    return _es_client


def _items_index_mappings() -> dict:
    """Mapping for items index (shared by async and sync create)."""
    return {
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "standard"},
            "description": {"type": "text", "analyzer": "standard"},
            "price_cents": {"type": "integer"},
            "owner_id": {"type": "integer"},
            "created_at": {"type": "date"},
        }
    }


async def ensure_items_index() -> None:
    """Create items index with mapping if not exists. Single-node: 0 replicas to avoid unassigned shards."""
    es = await get_elasticsearch()
    if not await es.indices.exists(index=ITEMS_INDEX):
        await es.indices.create(
            index=ITEMS_INDEX,
            body={
                "settings": {"index": {"number_of_replicas": 0}},
                "mappings": _items_index_mappings(),
            },
        )


async def index_item(doc: dict[str, Any]) -> bool:
    """Index a single item for search. ES 8 expects id as str."""
    try:
        es = await get_elasticsearch()
        payload = {k: v for k, v in doc.items() if v is not None}
        if doc.get("created_at") is None and "created_at" not in payload:
            payload["created_at"] = "1970-01-01T00:00:00Z"
        await es.index(index=ITEMS_INDEX, id=str(doc["id"]), document=payload)
        return True
    except Exception:
        return False


async def search_items(query: str, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
    """Full-text search on title and description. Returns list of hits."""
    try:
        es = await get_elasticsearch()
        # Use explicit kwargs for ES 8 client (body merge can differ by version)
        response = await es.search(
            index=ITEMS_INDEX,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "description"],
                    "fuzziness": "AUTO",
                }
            },
            from_=skip,
            size=limit,
        )
        # Response may be ObjectApiResponse; support both .body and dict access
        body = getattr(response, "body", response)
        hits = body["hits"]["hits"]
        total = body["hits"].get("total")
        total_val = total.get("value", len(hits)) if isinstance(total, dict) else len(hits)
        if total_val == 0:
            logger.info("search_items: query=%r returned 0 hits (index may be empty or Celery not indexing)", query)
        return [hit["_source"] for hit in hits]
    except Exception as e:
        logger.warning("search_items failed: query=%r error=%s", query, e)
        return []


async def remove_item_from_index(item_id: int) -> bool:
    """Remove item from search index when deleted."""
    try:
        es = await get_elasticsearch()
        await es.delete(index=ITEMS_INDEX, id=str(item_id), ignore=404)
        return True
    except Exception:
        return False


# --- Sync API for Celery (workers run in sync context; async + new_event_loop fails after fork) ---

def _sync_es_client() -> Elasticsearch:
    """New sync client per call (safe in forked Celery worker)."""
    return Elasticsearch(**_es_client_options())


def ensure_items_index_sync() -> None:
    """Create items index if not exists. Single-node: 0 replicas. Call from Celery task."""
    try:
        es = _sync_es_client()
        if not es.indices.exists(index=ITEMS_INDEX):
            es.indices.create(
                index=ITEMS_INDEX,
                settings={"index": {"number_of_replicas": 0}},
                mappings=_items_index_mappings(),
            )
    except Exception as e:
        logger.warning("ensure_items_index_sync failed: %s", e)


def index_item_sync(doc: dict[str, Any]) -> bool:
    """Index a single item. Call from Celery task. ES 8 requires id to be str."""
    try:
        es = _sync_es_client()
        # ES 8 client expects document id as string
        doc_id = str(doc["id"])
        # Avoid sending null for date field (ES can reject)
        payload = {k: v for k, v in doc.items() if v is not None}
        if "created_at" not in payload and doc.get("created_at") is None:
            payload["created_at"] = "1970-01-01T00:00:00Z"
        es.index(index=ITEMS_INDEX, id=doc_id, document=payload)
        return True
    except Exception as e:
        logger.warning("index_item_sync failed for doc id=%s: %s", doc.get("id"), e)
        return False
