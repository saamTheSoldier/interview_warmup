#!/usr/bin/env python3
"""
Reindex all existing items from DB into Elasticsearch via Celery.
Use this after fixing the worker or when the index was empty; no new data is created.
Requires: API running (to fetch items). Celery worker must be running to process the queue.

If you get 503 / no_shard_available from Elasticsearch, delete the broken index and reindex:
  python scripts/reindex_elasticsearch.py --reset-index

  python scripts/reindex_elasticsearch.py
  python scripts/reindex_elasticsearch.py --base-url http://localhost:8000/api/v1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.queue.tasks import index_item_task

API_BASE = "http://localhost:8000/api/v1"
PAGE_SIZE = 100  # API max_page_size


def delete_items_index():
    """Delete the items index so Celery will recreate it with number_of_replicas=0 (single-node safe)."""
    from app.search.elasticsearch_client import ITEMS_INDEX, _sync_es_client
    es = _sync_es_client()
    if es.indices.exists(index=ITEMS_INDEX):
        es.indices.delete(index=ITEMS_INDEX)
        print(f"Deleted index '{ITEMS_INDEX}'. Celery will recreate it when processing the first task.")
    else:
        print(f"Index '{ITEMS_INDEX}' does not exist (already deleted or never created).")


def main():
    ap = argparse.ArgumentParser(description="Enqueue all items for Elasticsearch reindex")
    ap.add_argument("--base-url", default=API_BASE, help="API base URL")
    ap.add_argument("--reset-index", action="store_true", help="Delete the items index first (fixes 503 / no_shard_available), then enqueue")
    args = ap.parse_args()

    if args.reset_index:
        delete_items_index()
        print()

    all_items = []
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        skip = 0
        while True:
            r = client.get(f"/items?skip={skip}&limit={PAGE_SIZE}")
            if r.status_code != 200:
                print(f"Failed to fetch items: {r.status_code} {r.text[:200]}")
                sys.exit(1)
            page = r.json()
            if not page:
                break
            all_items.extend(page)
            if len(page) < PAGE_SIZE:
                break
            skip += PAGE_SIZE

    items = all_items
    if not items:
        print("No items in DB. Run seed_data.py first or create items via the UI.")
        return

    for it in items:
        doc = {
            "id": it["id"],
            "title": it["title"],
            "description": it.get("description") or "",
            "price_cents": it.get("price_cents", 0),
            "owner_id": it["owner_id"],
            "created_at": it.get("created_at"),  # keep as-is (string from API)
        }
        index_item_task.delay(doc)

    print(f"Enqueued {len(items)} items for Elasticsearch reindex. Ensure Celery worker is running.")
    print("Wait a few seconds, then try Search in the UI or: curl -s 'http://localhost:9200/items/_count?pretty'")


if __name__ == "__main__":
    main()
