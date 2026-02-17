"""
Celery tasks - event-driven and async processing (job: queue management, event-driven).
Challenge: Offload indexing, notifications, heavy computation from request path.
"""

import asyncio

from app.queue.celery_app import celery_app
from app.search.elasticsearch_client import index_item, ensure_items_index


def _run_async(coro):
    """Run async function from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def index_item_task(self, item_doc: dict):
    """
    Index item in Elasticsearch asynchronously.
    Fired after item create/update (event-driven: API publishes, worker consumes).
    """
    try:
        _run_async(ensure_items_index())
        ok = _run_async(index_item(item_doc))
        if not ok:
            raise Exception("Index failed")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@celery_app.task
def dummy_health_task():
    """Simple task for queue health check (e.g. CI or monitoring)."""
    return "ok"
