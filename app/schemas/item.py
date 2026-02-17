"""Item request/response schemas - REST API contract."""

from datetime import datetime

from pydantic import BaseModel


class ItemBase(BaseModel):
    title: str
    description: str | None = None
    price_cents: int = 0


class ItemCreate(ItemBase):
    owner_id: int


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price_cents: int | None = None


class ItemResponse(ItemBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ItemWithOwnerResponse(ItemResponse):
    owner_email: str | None = None  # Populated by service layer
