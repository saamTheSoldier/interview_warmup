"""
SQLAlchemy declarative base and metadata.
Challenge: Single place for table definitions and migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models. Enables Alembic migrations."""

    pass
