"""
User repository - encapsulates all user data access (SOLID: Single Responsibility).
Challenge: Keep queries in one place for optimization and reuse.
"""

from sqlalchemy import select

from app.db.models.user import User
from app.db.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """User-specific queries. Extends base CRUD with domain logic."""

    def __init__(self, session):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Find user by email - used for authentication."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
