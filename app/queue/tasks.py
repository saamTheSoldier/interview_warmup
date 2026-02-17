"""
Celery tasks - event-driven and async processing (job: queue management, event-driven).
Challenge: Offload indexing, notifications, heavy computation from request path.
Use sync Elasticsearch in worker; async + event_loop in fork causes "Event loop is closed".
"""

from app.queue.celery_app import celery_app
from app.search.elasticsearch_client import ensure_items_index_sync, index_item_sync


@celery_app.task(bind=True, max_retries=3)
def index_item_task(self, item_doc: dict):
    """
    Index item in Elasticsearch.
    Fired after item create/update (event-driven: API publishes, worker consumes).
    """
    try:
        ensure_items_index_sync()
        ok = index_item_sync(item_doc)
        if not ok:
            raise Exception("Index failed")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@celery_app.task
def dummy_health_task():
    """Simple task for queue health check (e.g. CI or monitoring)."""
    return "ok"
