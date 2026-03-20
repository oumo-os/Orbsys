"""
Org service.

Handles org and dormain creation during bootstrap, and parameter reads
for live operations. Circle creation is here too — circles are org-level
constructs even though their members are managed separately.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService
from ..core.exceptions import (
    NotFound, AlreadyExists, BootstrapOnly, PostBootstrapOnly
)
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Org, Dormain, OrgParameter, Circle, CircleDormain
from ..models.types import DecayFn, MandateType
from ..schemas.org import (
    CreateOrgRequest, OrgResponse, DormainResponse,
    CreateDormainRequest, OrgParameterResponse, CreateCircleRequest,
)


class OrgService(BaseService):

    # ── Org creation (bootstrap step 1) ───────────────────────────────────────

    async def create_org(self, body: CreateOrgRequest) -> OrgResponse:
        # Slug must be globally unique
        existing = await self.db.execute(select(Org).where(Org.slug == body.slug))
        if existing.scalar_one_or_none() is not None:
            raise AlreadyExists("Org", "slug", body.slug)

        org = Org(
            name=body.name,
            slug=body.slug,
            purpose=body.purpose,
            bootstrapped_at=None,  # explicit — null means bootstrap in progress
        )
        await self.save(org)

        await get_event_bus().emit(
            org.id,
            GovernanceEvent(
                event_type=EventType.ORG_CREATED,
                subject_id=org.id,
                subject_type="org",
                payload={"slug": org.slug, "name": org.name},
            ),
        )

        return OrgResponse.model_validate(org)

    async def get_org(self, org_id: uuid.UUID) -> OrgResponse:
        org = await self.get_by_id(Org, org_id)
        if org is None:
            raise NotFound("Org")
        return OrgResponse.model_validate(org)

    # ── Dormains (bootstrap step 2) ───────────────────────────────────────────

    async def create_dormain(
        self, org_id: uuid.UUID, body: CreateDormainRequest, member_id: uuid.UUID
    ) -> DormainResponse:
        # Unique name within org
        existing = await self.db.execute(
            select(Dormain).where(Dormain.org_id == org_id, Dormain.name == body.name)
        )
        if existing.scalar_one_or_none() is not None:
            raise AlreadyExists("Dormain", "name", body.name)

        # Validate parent exists within same org
        if body.parent_id:
            parent = await self.db.execute(
                select(Dormain).where(
                    Dormain.id == body.parent_id, Dormain.org_id == org_id
                )
            )
            if parent.scalar_one_or_none() is None:
                raise NotFound("Parent Dormain", str(body.parent_id))

        dormain = Dormain(
            org_id=org_id,
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
            decay_fn=body.decay_fn,
            decay_half_life_months=body.decay_half_life_months,
            decay_floor_pct=body.decay_floor_pct,
        )
        await self.save(dormain)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.DORMAIN_CREATED,
                subject_id=dormain.id,
                subject_type="dormain",
                payload={"name": dormain.name},
                triggered_by_member=member_id,
            ),
        )

        return DormainResponse.model_validate(dormain)

    async def list_dormains(self, org_id: uuid.UUID) -> list[DormainResponse]:
        result = await self.db.execute(
            select(Dormain).where(Dormain.org_id == org_id).order_by(Dormain.name)
        )
        return [DormainResponse.model_validate(d) for d in result.scalars().all()]

    # ── Org parameters ────────────────────────────────────────────────────────

    async def get_parameters(self, org_id: uuid.UUID) -> list[OrgParameterResponse]:
        result = await self.db.execute(
            select(OrgParameter)
            .where(OrgParameter.org_id == org_id)
            .order_by(OrgParameter.parameter)
        )
        return [OrgParameterResponse.model_validate(p) for p in result.scalars().all()]
