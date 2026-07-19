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

    async def bootstrap_complete(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        membership_policy: str = "open_application",
    ) -> OrgResponse:
        """
        Complete the founding bootstrap:
          1. Set org.bootstrapped_at = now()
          2. Dissolve all founding_circle=True circles
          3. Seed membership_policy org parameter
          4. Emit ORG_BOOTSTRAPPED ledger event

        Only permitted while bootstrapped_at is null.
        After this call:
          - POST /auth/register returns 403 (BootstrapOnly)
          - POST /members/apply accepts new members (if policy allows)
          - Circle invite requires a vote, not auto-confirm
        """
        from ..core.exceptions import Forbidden

        org = await self.get_by_id(Org, org_id)
        if org is None:
            raise NotFound("Org")
        if org.bootstrapped_at is not None:
            raise Forbidden("ALREADY_BOOTSTRAPPED: org is already live")

        if membership_policy not in ("open_application", "invite_only", "closed"):
            raise Forbidden(f"INVALID_POLICY: {membership_policy}")

        now = datetime.now(timezone.utc)

        # 1. Mark org live
        org.bootstrapped_at = now
        self.db.add(org)

        # 2. Dissolve all founding circles
        from sqlalchemy import update
        await self.db.execute(
            update(Circle)
            .where(Circle.org_id == org_id, Circle.founding_circle.is_(True))
            .values(dissolved_at=now)
        )

        # 3. Seed membership_policy parameter
        existing_policy = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "membership_policy",
            )
        )).scalar_one_or_none()

        if existing_policy is None:
            self.db.add(OrgParameter(
                org_id=org_id,
                parameter="membership_policy",
                value={"value": membership_policy},
                applied_at=now,
            ))
        else:
            existing_policy.value = {"value": membership_policy}
            existing_policy.applied_at = now
            self.db.add(existing_policy)

        # 4. Seed default novice_slot_floor_pct if missing
        existing_floor = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "novice_slot_floor_pct",
            )
        )).scalar_one_or_none()
        if existing_floor is None:
            self.db.add(OrgParameter(
                org_id=org_id,
                parameter="novice_slot_floor_pct",
                value={"value": 0.30},
                applied_at=now,
            ))

        await self.db.flush()

        # 5. Emit ledger event
        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.ORG_BOOTSTRAPPED,
                subject_id=org_id,
                subject_type="org",
                payload={
                    "bootstrapped_at": now.isoformat(),
                    "membership_policy": membership_policy,
                    "triggered_by_member": str(member_id),
                },
                triggered_by_member=member_id,
            ),
        )

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

    async def create_circle_bootstrap(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: object,  # BootstrapCircleRequest — avoid circular import
    ) -> "CircleResponse":
        """
        Direct circle creation during bootstrap (org.bootstrapped_at is null).
        In live operation circles are created via governance motions.
        """
        from ..core.exceptions import Forbidden, AlreadyExists, BootstrapOnly
        from ..models.org import Org, Circle, CircleDormain, CircleMember, Dormain
        from ..models.types import MandateType, MemberState
        from ..schemas.circles import CircleResponse, CircleDormainResponse
        from ..schemas.common import DormainRef

        org = await self.get_by_id(Org, org_id)
        if org is None:
            raise Forbidden("Org not found")
        if org.bootstrapped_at is not None:
            raise BootstrapOnly("circle creation via /org/circles")

        # Unique name within org
        existing = (await self.db.execute(
            select(Circle).where(Circle.org_id == org_id, Circle.name == body.name)
        )).scalar_one_or_none()
        if existing:
            raise AlreadyExists("Circle", "name", body.name)

        now = datetime.now(timezone.utc)
        circle = Circle(
            org_id=org_id,
            name=body.name,
            description=body.description,
            founding_circle=False,
        )
        await self.save(circle)

        # Attach dormains
        dormains: list = []
        for did in (body.dormain_ids or []):
            dormain = await self.get_by_id(Dormain, did)
            if dormain and dormain.org_id == org_id:
                da = CircleDormain(
                    circle_id=circle.id,
                    dormain_id=did,
                    mandate_type=MandateType.PRIMARY,
                    added_at=now,
                )
                self.db.add(da)
                dormains.append((da, dormain))

        # Auto-add creating member to circle
        self.db.add(CircleMember(
            circle_id=circle.id,
            member_id=member_id,
            joined_at=now,
            current_state=MemberState.ACTIVE,
        ))

        await self.db.flush()

        return CircleResponse(
            id=circle.id,
            org_id=circle.org_id,
            name=circle.name,
            description=circle.description,
            tenets=None,
            founding_circle=False,
            dormains=[
                CircleDormainResponse(
                    dormain=DormainRef(id=da.dormain_id, name=d.name),
                    mandate_type=da.mandate_type,
                    added_at=da.added_at,
                    removed_at=None,
                )
                for da, d in dormains
            ],
            member_count=1,
            created_at=circle.created_at,
            dissolved_at=None,
        )

    async def get_parameters(self, org_id: uuid.UUID) -> list[OrgParameterResponse]:
        result = await self.db.execute(
            select(OrgParameter)
            .where(OrgParameter.org_id == org_id)
            .order_by(OrgParameter.parameter)
        )
        return [OrgParameterResponse.model_validate(p) for p in result.scalars().all()]
