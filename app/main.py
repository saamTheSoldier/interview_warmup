"""
FastAPI application entry point.
Challenge: Mount routes, middleware (Prometheus), startup events (DB/ES init).
"""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.api.v1.router import api_router
from app.search.elasticsearch_client import ensure_items_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure Elasticsearch index when ES is available. Shutdown: cleanup if needed."""
    try:
        await ensure_items_index()
    except Exception:
        # Run without Docker: ES may be down; app still works (search returns empty)
        pass
    yield
    # Optional: close Redis/ES clients


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Interview project: scalable web services with FastAPI, PostgreSQL, Redis, Elasticsearch, Celery, Docker, CI/CD, monitoring.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS for frontend/API consumers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics at /metrics (monitoring & observability - job nice-to-have)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    app.include_router(api_router, prefix="/api")

    # Minimal UI (static)
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/")
        async def root():
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
