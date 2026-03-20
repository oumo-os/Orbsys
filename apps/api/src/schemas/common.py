"""
Shared base types used across all schema files.
Import from here, not from individual domain schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


# ── Base config ───────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    """All response models inherit from this. Enables from_attributes ORM mode."""
    model_config = ConfigDict(from_attributes=True)


# ── Pagination ────────────────────────────────────────────────────────────────

class Paginated(OrmBase, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 25

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ── Embedded refs — used inside other responses ───────────────────────────────

class MemberRef(OrmBase):
    """Minimal member identity. Used wherever authorship is shown."""
    id: uuid.UUID
    handle: str
    display_name: str


class DormainRef(OrmBase):
    """Minimal dormain reference."""
    id: uuid.UUID
    name: str


class CircleRef(OrmBase):
    """Minimal circle reference."""
    id: uuid.UUID
    name: str


# ── Standard action responses ─────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class IDResponse(BaseModel):
    id: uuid.UUID
