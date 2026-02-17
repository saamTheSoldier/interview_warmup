"""User request/response schemas - API contract and validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    # bcrypt accepts max 72 bytes; longer passwords cause 500. Validate here for clear 422.
    password: str = Field(..., min_length=1, max_length=72)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
