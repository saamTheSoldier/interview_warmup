"""
User endpoints - registration and login (RESTful API).
Challenge: Secure auth, validation, clear status codes.
"""

from fastapi import APIRouter, HTTPException, status

from app.db.session import DbSession
from app.db.repositories.user_repository import UserRepository
from pydantic import BaseModel
from app.schemas.user import UserCreate, UserResponse
from app.core.security import hash_password, create_access_token, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", response_model=UserResponse)
async def register(session: DbSession, data: UserCreate):
    """Create new user. Returns user without password."""
    repo = UserRepository(session)
    existing = await repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    from app.db.models.user import User
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    user = await repo.add(user)
    return UserResponse.model_validate(user)


@router.post("/login")
async def login(session: DbSession, data: LoginRequest):
    """Authenticate and return JWT."""
    repo = UserRepository(session)
    user = await repo.get_by_email(data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}
