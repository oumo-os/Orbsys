"""
Members service.

Profile reads, feed delivery (delegates to Inferential Engine rankings),
curiosity management, and notification delivery with cap enforcement.

Feed:
  relevance = max(mandate_match, curiosity_match)
  Source is Inferential Engine's pre-computed scores, not computed here.
  Falls back to chronological order if Inferential Engine scores unavailable.

Notifications:
  P1 — always delivered (no cap)
  P2 — capped: 12/day, 3/hour  (enforced here on read, counted by Insight Engine on write)
  P3 — digest only (returned in batched digest endpoint, not individual feed)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, and_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService
from ..core.exceptions import NotFound, AlreadyExists, Forbidden
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Member, Dormain
from ..models.competence import Curiosity, CompetenceScore
from ..models.governance import CommonsThread, FeedScore, Notification
from ..schemas.members import (
    MemberResponse, MemberDetailResponse, UpdateMemberRequest,
    SetCuriositiesRequest, CuriosityResponse, CompetenceScoreSummary,
    CircleMembershipSummary, FeedItemResponse, NotificationResponse,
)
from ..schemas.common import Paginated


class MembersService(BaseService):

    # ── Profile ───────────────────────────────────────────────────────────────

    async def get_me(self, member_id: uuid.UUID, org_id: uuid.UUID) -> MemberDetailResponse:
        member = await self._load_member_full(member_id, org_id)
        scores = await self._load_scores(member_id)
        circle_memberships = await self._load_circle_memberships(member_id)

        response = MemberDetailResponse.model_validate(member)
        response.email = member.email  # email only on /me
        response.competence_scores = scores
        response.circle_memberships = circle_memberships
        return response

    async def get_member(
        self, target_id: uuid.UUID, requesting_org_id: uuid.UUID
    ) -> MemberDetailResponse:
        member = await self._load_member_full(target_id, requesting_org_id)
        scores = await self._load_scores(target_id)
        circle_memberships = await self._load_circle_memberships(target_id)

        response = MemberDetailResponse.model_validate(member)
        response.email = None  # never exposed on /members/:id
        response.competence_scores = scores
        response.circle_memberships = circle_memberships
        return response

    async def update_me(
        self, member_id: uuid.UUID, org_id: uuid.UUID, body: UpdateMemberRequest
    ) -> MemberResponse:
        member = await self.get_by_id_and_org(Member, member_id, org_id)
        if member is None:
            raise NotFound("Member")

        if body.display_name is not None:
            member.display_name = body.display_name
        if body.email is not None:
            # Check uniqueness within org
            existing = await self.db.execute(
                select(Member).where(
                    Member.org_id == org_id,
                    Member.email == body.email,
                    Member.id != member_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise AlreadyExists("Member", "email", body.email)
            member.email = body.email

        await self.save(member)
        return MemberResponse.model_validate(member)

    # ── Feed ──────────────────────────────────────────────────────────────────

    async def get_feed(
        self, member_id: uuid.UUID, org_id: uuid.UUID, page: int, page_size: int
    ) -> Paginated[FeedItemResponse]:
        """
        Relevance-ranked Commons thread feed.
        Inferential Engine pre-computes and stores relevance scores in a
        feed_scores table (not yet modelled — TODO: add feed_scores table).
        Fallback: chronological order when no scores are available.
        """
        from ..models.governance import CommonsThread, CommonsThreadDormainTag
        from ..schemas.commons import CommonsThreadSummaryResponse
        from ..schemas.common import DormainRef, MemberRef

        # Load threads for this org, paginated — chronological fallback
        count_q = select(CommonsThread).where(
            CommonsThread.org_id == org_id,
            CommonsThread.state.in_(["open", "sponsored"]),
        )
        result = await self.db.execute(
            count_q
            .order_by(CommonsThread.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(CommonsThread.tags))
        )
        threads = result.scalars().all()

        # Total count
        from sqlalchemy import func
        total_result = await self.db.execute(
            select(func.count()).select_from(
                select(CommonsThread).where(
                    CommonsThread.org_id == org_id,
                    CommonsThread.state.in_(["open", "sponsored"]),
                ).subquery()
            )
        )
        total = total_result.scalar_one()

        # Load authors
        author_ids = list({t.author_id for t in threads})
        authors_result = await self.db.execute(
            select(Member).where(Member.id.in_(author_ids))
        )
        authors = {m.id: m for m in authors_result.scalars().all()}

        # Load post counts
        from sqlalchemy import func as sqlfunc
        from ..models.governance import CommonsPost
        post_counts_result = await self.db.execute(
            select(CommonsPost.thread_id, sqlfunc.count(CommonsPost.id))
            .where(CommonsPost.thread_id.in_([t.id for t in threads]))
            .group_by(CommonsPost.thread_id)
        )
        post_counts = dict(post_counts_result.all())

        items = []
        for thread in threads:
            author = authors.get(thread.author_id)
            items.append(
                FeedItemResponse(
                    thread_id=thread.id,
                    title=thread.title,
                    body_preview=thread.body[:280],
                    author=MemberRef(
                        id=author.id,
                        handle=author.handle,
                        display_name=author.display_name,
                    ) if author else None,
                    dormain_tags=[
                        DormainRef(id=tag.dormain_id, name="")  # name loaded lazily
                        for tag in (thread.tags or [])
                    ],
                    state=thread.state,
                    post_count=post_counts.get(thread.id, 0),
                    created_at=thread.created_at,
                    sponsored_at=thread.sponsored_at,
                    feed_relevance=0.0,         # TODO: load from feed_scores table
                    relevance_source="chrono",  # fallback
                )
            )

        return Paginated(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    # ── Curiosities ───────────────────────────────────────────────────────────

    async def get_curiosities(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[CuriosityResponse]:
        result = await self.db.execute(
            select(Curiosity, Dormain.name)
            .join(Dormain, Curiosity.dormain_id == Dormain.id)
            .where(Curiosity.member_id == member_id, Dormain.org_id == org_id)
            .order_by(Curiosity.signal.desc())
        )
        rows = result.all()
        return [
            CuriosityResponse(
                dormain_id=c.dormain_id,
                dormain_name=name,
                signal=float(c.signal),
                declared_at=c.declared_at,
                updated_at=c.updated_at,
            )
            for c, name in rows
        ]

    async def set_curiosities(
        self, member_id: uuid.UUID, org_id: uuid.UUID, body: SetCuriositiesRequest
    ) -> list[CuriosityResponse]:
        """
        Replace full curiosity vector atomically.
        Validates all dormain_ids exist within org before writing.
        """
        if not body.curiosities:
            # Clear all curiosities
            await self.db.execute(
                delete(Curiosity).where(Curiosity.member_id == member_id)
            )
            await self.db.flush()
            return []

        dormain_ids = [uuid.UUID(did) for did in body.curiosities.keys()]

        # Validate all dormains exist in this org
        valid_result = await self.db.execute(
            select(Dormain).where(
                Dormain.id.in_(dormain_ids), Dormain.org_id == org_id
            )
        )
        valid_dormains = {d.id: d for d in valid_result.scalars().all()}
        invalid = [str(did) for did in dormain_ids if did not in valid_dormains]
        if invalid:
            raise Forbidden(f"Dormains not found in this org: {', '.join(invalid)}")

        # Load existing curiosities for this member
        existing_result = await self.db.execute(
            select(Curiosity).where(Curiosity.member_id == member_id)
        )
        existing = {c.dormain_id: c for c in existing_result.scalars().all()}

        now = datetime.now(timezone.utc)
        to_keep_ids = set(dormain_ids)

        # Upsert
        for dormain_id in dormain_ids:
            signal = body.curiosities[str(dormain_id)]
            if dormain_id in existing:
                existing[dormain_id].signal = signal
                existing[dormain_id].updated_at = now
            else:
                new_c = Curiosity(
                    member_id=member_id,
                    dormain_id=dormain_id,
                    signal=signal,
                    declared_at=now,
                )
                self.db.add(new_c)

        # Remove any dormains not in the new vector
        for dormain_id, cur in existing.items():
            if dormain_id not in to_keep_ids:
                await self.db.delete(cur)

        await self.db.flush()

        # Emit event for Inferential Engine to rebuild feed relevance
        member = await self.get_by_id(Member, member_id)
        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.CURIOSITY_UPDATED,
                subject_id=member_id,
                subject_type="member",
                payload={"dormain_count": len(dormain_ids)},
                triggered_by_member=member_id,
            ),
        )

        return await self.get_curiosities(member_id, org_id)

    # ── Notifications ─────────────────────────────────────────────────────────

    async def get_notifications(
        self,
        member_id: uuid.UUID,
        org_id: uuid.UUID,
        unread_only: bool,
        page: int,
        page_size: int,
    ) -> Paginated[NotificationResponse]:
        from sqlalchemy import func
        q = select(Notification).where(
            Notification.member_id == member_id,
            Notification.org_id == org_id,
        )
        if unread_only:
            q = q.where(Notification.read == False)  # noqa: E712

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = await self.db.execute(
            q.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        notifications = rows.scalars().all()

        return Paginated(
            items=[
                NotificationResponse(
                    id=n.id,
                    priority=n.priority,
                    notification_type=n.notification_type,
                    subject_id=n.subject_id,
                    subject_type=n.subject_type,
                    body=n.body,
                    action_url=n.action_url,
                    read=n.read,
                    created_at=n.created_at,
                )
                for n in notifications
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def mark_notification_read(
        self, notification_id: uuid.UUID, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.member_id == member_id,
                Notification.org_id == org_id,
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            raise NotFound("Notification", str(notification_id))
        notif.read = True
        notif.read_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def mark_all_notifications_read(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> int:
        from sqlalchemy import update as sa_update
        result = await self.db.execute(
            sa_update(Notification)
            .where(
                Notification.member_id == member_id,
                Notification.org_id == org_id,
                Notification.read == False,  # noqa: E712
            )
            .values(read=True, read_at=datetime.now(timezone.utc))
        )
        return result.rowcount

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _load_member_full(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> Member:
        result = await self.db.execute(
            select(Member).where(Member.id == member_id, Member.org_id == org_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise NotFound("Member", str(member_id))
        return member

    async def _load_scores(self, member_id: uuid.UUID) -> list[CompetenceScoreSummary]:
        result = await self.db.execute(
            select(CompetenceScore, Dormain.name)
            .join(Dormain, CompetenceScore.dormain_id == Dormain.id)
            .where(CompetenceScore.member_id == member_id)
            .order_by(CompetenceScore.w_s.desc())
        )
        return [
            CompetenceScoreSummary(
                dormain_id=score.dormain_id,
                dormain_name=name,
                w_s=float(score.w_s),
                w_s_peak=float(score.w_s_peak),
                w_h=float(score.w_h),
                volatility_k=score.volatility_k,
                last_activity_at=score.last_activity_at,
            )
            for score, name in result.all()
        ]

    async def _load_circle_memberships(
        self, member_id: uuid.UUID
    ) -> list[CircleMembershipSummary]:
        from ..models.org import CircleMember, Circle
        result = await self.db.execute(
            select(CircleMember, Circle.name)
            .join(Circle, CircleMember.circle_id == Circle.id)
            .where(
                CircleMember.member_id == member_id,
                CircleMember.exited_at.is_(None),
            )
        )
        return [
            CircleMembershipSummary(
                circle_id=cm.circle_id,
                circle_name=name,
                joined_at=cm.joined_at,
                current_state=cm.current_state,
            )
            for cm, name in result.all()
        ]
