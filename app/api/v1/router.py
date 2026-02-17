"""
API v1 router - aggregates all endpoint modules (RESTful structure).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import items, users, search, health

api_router = APIRouter(prefix="/v1")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
