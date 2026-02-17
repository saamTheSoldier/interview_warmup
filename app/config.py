"""
Configuration management using Pydantic Settings.
Challenge: Centralized config, env validation, type safety.
Design: Single source of truth for all environment variables.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment. Validates at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Interview API"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://app:secret@localhost:5432/appdb"

    # Redis (caching, rate limiting, Celery result backend)
    redis_url: str = "redis://localhost:6379/0"

    # Elasticsearch (search and analytics)
    # Use https:// and optional user:pass for ES 8 with security enabled, e.g. https://elastic:yourpassword@localhost:9200
    elasticsearch_url: str = "http://localhost:9200"
    # Set to false when using self-signed certs (e.g. local ES 8)
    elasticsearch_verify_certs: bool = True

    # Celery / RabbitMQ (queue management)
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Avoids re-reading env on every request (performance)."""
    return Settings()
