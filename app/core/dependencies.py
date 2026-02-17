"""
FastAPI dependencies - injection for DB, Redis, auth (SOLID: Dependency Inversion).
Challenge: Reusable auth, consistent error responses.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import DbSession
from app.db.repositories.user_repository import UserRepository
from app.core.security import decode_access_token

security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> int:
    """Resolve JWT to user id. Raises 401 if missing or invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    repo = UserRepository(session)
    user = await repo.get_by_id(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user.id


# Optional auth: for routes that behave differently when logged in
async def get_optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> int | None:
    """Return user id if valid token present, else None."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    return int(payload["sub"])


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
