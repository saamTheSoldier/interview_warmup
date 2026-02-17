#!/usr/bin/env python3
"""
Create the Elasticsearch 'items' index with raw HTTP (no Python ES client).
Use this when the index keeps returning 503 no_shard_available even after --reset-index:
  python scripts/create_es_items_index.py

Then run reindex WITHOUT --reset-index so Celery only indexes into the new index:
  python scripts/reindex_elasticsearch.py

Reads ELASTICSEARCH_URL from .env (default http://localhost:9200).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.config import get_settings

ITEMS_INDEX = "items"

BODY = {
    "settings": {
        "index": {
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "standard"},
            "description": {"type": "text", "analyzer": "standard"},
            "price_cents": {"type": "integer"},
            "owner_id": {"type": "integer"},
            "created_at": {"type": "date"},
        }
    },
}


def main():
    settings = get_settings()
    base = settings.elasticsearch_url.rstrip("/")
    url = f"{base}/{ITEMS_INDEX}"

    with httpx.Client(timeout=30.0) as client:
        # Check if exists
        r = client.head(url)
        if r.status_code == 200:
            print(f"Index '{ITEMS_INDEX}' already exists. Delete it first if you want to recreate:")
            print(f"  curl -X DELETE '{base}/{ITEMS_INDEX}'")
            return
        r = client.put(url, json=BODY)
        if r.status_code not in (200, 201):
            print(f"Failed to create index: {r.status_code}")
            print(r.text[:500])
            sys.exit(1)
    print(f"Created index '{ITEMS_INDEX}' with number_of_replicas=0.")
    print("Run: python scripts/reindex_elasticsearch.py   (no --reset-index)")


if __name__ == "__main__":
    main()
