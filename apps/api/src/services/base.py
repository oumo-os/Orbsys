"""
Base service utilities.

All services take db: AsyncSession as constructor arg.
Query helpers return None on not-found rather than raising —
services decide whether to raise NotFound based on context.
"""
from __future__ import annotations

import uuid
from typing import TypeVar, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import Base

M = TypeVar("M", bound=Base)


class BaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, model: Type[M], id: uuid.UUID) -> M | None:
        result = await self.db.execute(select(model).where(model.id == id))
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, model: Type[M], id: uuid.UUID, org_id: uuid.UUID
    ) -> M | None:
        result = await self.db.execute(
            select(model).where(model.id == id, model.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def save(self, obj: M) -> M:
        self.db.add(obj)
        await self.db.flush()   # assigns PK + server defaults; does NOT commit
        await self.db.refresh(obj)
        return obj
