"""
Circles service.

Circles are the membership layer — they hold mandate assignments across
Dormains and gate formal review eligibility.

Invitation flow:
  POST /circles/:id/members → creates a pending invitation
  A Circle vote is required to confirm it (driven by STF/Cell — v1.1)
  For bootstrap: invitation auto-confirms (no quorum yet).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from .base import BaseService
from ..core.exceptions import NotFound, AlreadyExists, Forbidden
from ..models.org import Circle, CircleDormain, CircleMember, Member, Dormain
from ..models.types import MemberState
from ..schemas.circles import (
    CircleResponse, CircleSummaryResponse, CircleDormainResponse,
    CircleMemberResponse, CircleHealthSnapshotResponse, InvitationResponse,
    InviteMemberRequest,
)
from ..schemas.common import MemberRef, DormainRef


class CirclesService(BaseService):

    async def list_circles(self, org_id: uuid.UUID) -> list[CircleSummaryResponse]:
        result = await self.db.execute(
            select(Circle)
            .where(Circle.org_id == org_id, Circle.dissolved_at.is_(None))
            .options(selectinload(Circle.dormain_assignments))
            .order_by(Circle.name)
        )
        circles = result.scalars().all()

        # Member counts per circle
        counts_result = await self.db.execute(
            select(CircleMember.circle_id, func.count(CircleMember.id))
            .where(
                CircleMember.circle_id.in_([c.id for c in circles]),
                CircleMember.exited_at.is_(None),
            )
            .group_by(CircleMember.circle_id)
        )
        counts = dict(counts_result.all())

        # Dormain names
        dormain_ids = {
            da.dormain_id
            for c in circles
            for da in (c.dormain_assignments or [])
        }
        dormains: dict[uuid.UUID, Dormain] = {}
        if dormain_ids:
            d_result = await self.db.execute(
                select(Dormain).where(Dormain.id.in_(dormain_ids))
            )
            dormains = {d.id: d for d in d_result.scalars().all()}

        return [
            CircleSummaryResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                dormains=[
                    DormainRef(id=da.dormain_id, name=dormains.get(da.dormain_id, Dormain()).name or "")
                    for da in (c.dormain_assignments or [])
                    if da.removed_at is None
                ],
                member_count=counts.get(c.id, 0),
                dissolved_at=c.dissolved_at,
            )
            for c in circles
        ]

    async def get_circle(
        self, circle_id: uuid.UUID, org_id: uuid.UUID
    ) -> CircleResponse:
        circle = await self._load_circle(circle_id, org_id)

        member_count_result = await self.db.execute(
            select(func.count(CircleMember.id)).where(
                CircleMember.circle_id == circle_id,
                CircleMember.exited_at.is_(None),
            )
        )
        member_count = member_count_result.scalar_one()

        dormain_ids = [da.dormain_id for da in (circle.dormain_assignments or [])]
        dormains: dict[uuid.UUID, Dormain] = {}
        if dormain_ids:
            d_result = await self.db.execute(
                select(Dormain).where(Dormain.id.in_(dormain_ids))
            )
            dormains = {d.id: d for d in d_result.scalars().all()}

        return CircleResponse(
            id=circle.id,
            org_id=circle.org_id,
            name=circle.name,
            description=circle.description,
            tenets=circle.tenets,
            founding_circle=circle.founding_circle,
            dormains=[
                CircleDormainResponse(
                    dormain=DormainRef(
                        id=da.dormain_id,
                        name=dormains.get(da.dormain_id, Dormain()).name or "",
                    ),
                    mandate_type=da.mandate_type,
                    added_at=da.added_at,
                    removed_at=da.removed_at,
                )
                for da in (circle.dormain_assignments or [])
            ],
            member_count=member_count,
            created_at=circle.created_at,
            dissolved_at=circle.dissolved_at,
        )

    async def list_circle_members(
        self, circle_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[CircleMemberResponse]:
        circle = await self._load_circle(circle_id, org_id)

        result = await self.db.execute(
            select(CircleMember, Member)
            .join(Member, CircleMember.member_id == Member.id)
            .where(
                CircleMember.circle_id == circle_id,
                CircleMember.exited_at.is_(None),
            )
            .order_by(CircleMember.joined_at.asc())
        )
        rows = result.all()

        return [
            CircleMemberResponse(
                member=MemberRef(
                    id=member.id,
                    handle=member.handle,
                    display_name=member.display_name,
                ),
                joined_at=cm.joined_at,
                current_state=cm.current_state,
                primary_dormain_ws=None,  # TODO: join competence_scores on primary dormain
            )
            for cm, member in rows
        ]

    async def invite_member(
        self,
        circle_id: uuid.UUID,
        org_id: uuid.UUID,
        inviting_member_id: uuid.UUID,
        body: InviteMemberRequest,
    ) -> InvitationResponse:
        """
        Creates a pending invitation. A Circle vote confirms it (v1.1).
        During bootstrap (org.bootstrapped_at is null): auto-confirms.
        """
        circle = await self._load_circle(circle_id, org_id)
        if circle.dissolved_at is not None:
            raise Forbidden(f"Circle '{circle.name}' is dissolved")

        # Inviting member must themselves be in the circle
        inviter_membership = await self.db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == circle_id,
                CircleMember.member_id == inviting_member_id,
                CircleMember.exited_at.is_(None),
            )
        )
        if inviter_membership.scalar_one_or_none() is None:
            raise Forbidden("INVITE_REQUIRES_MEMBERSHIP: you must be a circle member to invite")

        # Target member exists in org
        target = await self.db.execute(
            select(Member).where(
                Member.id == body.member_id, Member.org_id == org_id
            )
        )
        target_member = target.scalar_one_or_none()
        if target_member is None:
            raise NotFound("Member", str(body.member_id))

        # Not already a member
        existing_membership = await self.db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == circle_id,
                CircleMember.member_id == body.member_id,
                CircleMember.exited_at.is_(None),
            )
        )
        if existing_membership.scalar_one_or_none() is not None:
            raise AlreadyExists("Circle membership", "member_id", str(body.member_id))

        now = datetime.now(timezone.utc)

        # Bootstrap auto-confirm (org.bootstrapped_at is null)
        from ..models.org import Org
        org = await self.get_by_id(Org, org_id)
        auto_confirm = org is not None and org.bootstrapped_at is None

        invitation_id = uuid.uuid4()
        status = "pending_vote"

        if auto_confirm:
            # Create membership directly during bootstrap
            membership = CircleMember(
                circle_id=circle_id,
                member_id=body.member_id,
                joined_at=now,
                current_state=MemberState.PROBATIONARY,
            )
            self.db.add(membership)
            await self.db.flush()
            status = "accepted"

        return InvitationResponse(
            invitation_id=invitation_id,
            circle_id=circle_id,
            invited_member=MemberRef(
                id=target_member.id,
                handle=target_member.handle,
                display_name=target_member.display_name,
            ),
            status=status,
            created_at=now,
        )

    async def get_circle_health(
        self, circle_id: uuid.UUID, org_id: uuid.UUID
    ) -> CircleHealthSnapshotResponse:
        circle = await self._load_circle(circle_id, org_id)

        member_count = (await self.db.execute(
            select(func.count(CircleMember.id)).where(
                CircleMember.circle_id == circle_id,
                CircleMember.exited_at.is_(None),
            )
        )).scalar_one()

        # Health populated by periodic aSTF — null before first audit
        return CircleHealthSnapshotResponse(
            circle_id=circle_id,
            circle_name=circle.name,
            snapshot_at=None,
            overall_verdict=None,
            active_member_count=member_count,
            median_ws_primary_dormain=None,
            participation_rate_90d=None,
            open_concerns=[],
            stf_instance_id=None,
        )

    async def _load_circle(self, circle_id: uuid.UUID, org_id: uuid.UUID) -> Circle:
        result = await self.db.execute(
            select(Circle)
            .where(Circle.id == circle_id, Circle.org_id == org_id)
            .options(selectinload(Circle.dormain_assignments))
        )
        circle = result.scalar_one_or_none()
        if circle is None:
            raise NotFound("Circle", str(circle_id))
        return circle
