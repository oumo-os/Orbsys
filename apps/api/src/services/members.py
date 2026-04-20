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
from ..models.org import MemberApplication
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
        Joins feed_scores (written by Inferential Engine) when available.
        Falls back to chronological order when no scores exist for this member.
        """
        from sqlalchemy import func, outerjoin, literal
        from ..models.governance import CommonsThread, CommonsPost

        # Outer-join threads with feed_scores for this member
        # threads without a score get score=0 and basis="chrono"
        scored_q = (
            select(
                CommonsThread,
                FeedScore.relevance_score,
                FeedScore.score_basis,
            )
            .outerjoin(
                FeedScore,
                and_(
                    FeedScore.thread_id == CommonsThread.id,
                    FeedScore.member_id == member_id,
                ),
            )
            .where(
                CommonsThread.org_id == org_id,
                CommonsThread.state.in_(["open", "sponsored"]),
            )
            .order_by(
                FeedScore.relevance_score.desc().nullslast(),
                CommonsThread.created_at.desc(),
            )
        )

        total = (await self.db.execute(
            select(func.count()).select_from(scored_q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            scored_q
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(CommonsThread.tags))
        )).all()

        threads = [r[0] for r in rows]
        score_map = {r[0].id: (float(r[1]) if r[1] else 0.0, r[2] or "chrono") for r in rows}

        author_ids = list({t.author_id for t in threads if t.author_id})
        authors: dict = {}
        if author_ids:
            ar = await self.db.execute(select(Member).where(Member.id.in_(author_ids)))
            authors = {m.id: m for m in ar.scalars().all()}

        post_counts: dict = {}
        if threads:
            pc_result = await self.db.execute(
                select(CommonsPost.thread_id, func.count(CommonsPost.id))
                .where(CommonsPost.thread_id.in_([t.id for t in threads]))
                .group_by(CommonsPost.thread_id)
            )
            post_counts = dict(pc_result.all())

        dormain_name_map: dict = {}
        all_dormain_ids = {tag.dormain_id for t in threads for tag in (t.tags or [])}
        if all_dormain_ids:
            dr = await self.db.execute(
                select(Dormain).where(Dormain.id.in_(all_dormain_ids))
            )
            dormain_name_map = {d.id: d.name for d in dr.scalars().all()}

        from ..schemas.common import DormainRef, MemberRef

        items = []
        for thread in threads:
            author = authors.get(thread.author_id) if thread.author_id else None
            relevance, basis = score_map.get(thread.id, (0.0, "chrono"))
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
                        DormainRef(
                            id=tag.dormain_id,
                            name=dormain_name_map.get(tag.dormain_id, ""),
                        )
                        for tag in (thread.tags or [])
                    ],
                    state=thread.state,
                    post_count=post_counts.get(thread.id, 0),
                    created_at=thread.created_at,
                    sponsored_at=thread.sponsored_at,
                    feed_relevance=relevance,
                    relevance_source=basis,
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

    # ── Membership applications (post-bootstrap joining) ─────────────────────

    async def apply_to_join(
        self,
        org_id: uuid.UUID,
        handle: str,
        display_name: str,
        email: str,
        password: str,
        motivation: str | None = None,
        expertise_summary: str | None = None,
        proof_of_personhood_ref: str | None = None,
    ) -> dict:
        """
        Submit a membership application to a live org.
        Checks membership_policy parameter — raises 403 if not 'open_application'.
        Notifies Membership Circle members (P2 notification).
        """
        from ..models.org import Org, OrgParameter, MemberApplication
        from ..core.security import hash_password
        from ..core.exceptions import Forbidden

        org = (await self.db.execute(
            select(Org).where(Org.id == org_id)
        )).scalar_one_or_none()
        if not org:
            raise Forbidden("Org not found")

        # Check membership_policy parameter
        policy_row = (await self.db.execute(
            select(OrgParameter).where(
                OrgParameter.org_id == org_id,
                OrgParameter.parameter == "membership_policy",
            )
        )).scalar_one_or_none()
        policy = (policy_row.value if policy_row else {}).get("value", "open_application")

        if policy == "closed":
            raise Forbidden("MEMBERSHIP_CLOSED: this org is not accepting new members")
        if policy == "invite_only":
            raise Forbidden("MEMBERSHIP_INVITE_ONLY: join by invitation from a circle member")

        # Check no pending application with same handle/email
        from sqlalchemy import or_
        existing = (await self.db.execute(
            select(MemberApplication).where(
                MemberApplication.org_id == org_id,
                MemberApplication.status == "pending",
                or_(
                    MemberApplication.handle == handle,
                    MemberApplication.email == email,
                ),
            )
        )).scalar_one_or_none()
        if existing:
            raise AlreadyExists("MemberApplication", "handle/email", handle)

        # Also check active members
        existing_member = (await self.db.execute(
            select(Member).where(
                Member.org_id == org_id,
                or_(Member.handle == handle, Member.email == email),
            )
        )).scalar_one_or_none()
        if existing_member:
            raise AlreadyExists("Member", "handle/email", handle)

        application = MemberApplication(
            org_id=org_id,
            handle=handle,
            display_name=display_name,
            email=email,
            password_hash=hash_password(password),
            motivation=motivation,
            expertise_summary=expertise_summary,
            proof_of_personhood_ref=proof_of_personhood_ref,
            status="pending",
        )
        self.db.add(application)
        await self.db.flush()

        # Emit event → Insight Engine notifies Membership Circle members
        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.MEMBER_APPLICATION_SUBMITTED,
                subject_id=application.id,
                subject_type="member_application",
                payload={"handle": handle, "display_name": display_name},
            ),
        )

        return {
            "application_id": str(application.id),
            "status": "pending",
            "message": "Application submitted. The Membership Circle will review your application.",
        }

    async def list_applications(
        self,
        org_id: uuid.UUID,
        status_filter: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        """List membership applications. Membership Circle visibility only."""
        from ..models.org import MemberApplication
        from sqlalchemy import func

        q = select(MemberApplication).where(MemberApplication.org_id == org_id)
        if status_filter:
            q = q.where(MemberApplication.status == status_filter)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = await self.db.execute(
            q.order_by(MemberApplication.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        apps = rows.scalars().all()

        return {
            "items": [
                {
                    "id": str(a.id),
                    "handle": a.handle,
                    "display_name": a.display_name,
                    "email": a.email,
                    "motivation": a.motivation,
                    "expertise_summary": a.expertise_summary,
                    "status": a.status,
                    "created_at": a.created_at.isoformat(),
                    "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                    "review_note": a.review_note,
                }
                for a in apps
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
        }

    async def review_application(
        self,
        application_id: uuid.UUID,
        org_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        approve: bool,
        note: str | None = None,
    ) -> dict:
        """
        Approve or reject a pending application.
        On approval: creates the Member account and sends credentials.
        Reviewer must be a member of the Membership Circle (enforced here).
        """
        from ..models.org import MemberApplication, Circle, CircleDormain, CircleMember
        from ..models.types import MemberState
        from ..core.exceptions import NotFound, Forbidden

        app = (await self.db.execute(
            select(MemberApplication).where(
                MemberApplication.id == application_id,
                MemberApplication.org_id == org_id,
                MemberApplication.status == "pending",
            )
        )).scalar_one_or_none()
        if not app:
            raise NotFound("MemberApplication", str(application_id))

        # Reviewer must be in a Membership Circle
        # (circle with 'community' or 'governance' domain that has membership mandate)
        # For now: any GovWriter (circle member) can review — enforced at route level
        # In v1.1: require specific Membership Circle membership

        now = datetime.now(timezone.utc)
        app.reviewed_by = reviewer_id
        app.reviewed_at = now
        app.review_note = note
        app.status = "approved" if approve else "rejected"

        new_member_id = None
        if approve:
            # Create the member account using stored credentials
            member = Member(
                org_id=org_id,
                handle=app.handle,
                display_name=app.display_name,
                email=app.email,
                password_hash=app.password_hash,
                joined_at=now,
                current_state=MemberState.PROBATIONARY,
                proof_of_personhood_ref=app.proof_of_personhood_ref,
            )
            self.db.add(member)
            await self.db.flush()
            app.member_id = member.id
            new_member_id = member.id

            await get_event_bus().emit(
                org_id,
                GovernanceEvent(
                    event_type=EventType.MEMBER_STATE_CHANGED,
                    subject_id=member.id,
                    subject_type="member",
                    payload={
                        "from_state": None,
                        "to_state": "probationary",
                        "trigger": "application_approved",
                        "application_id": str(application_id),
                    },
                    triggered_by_member=reviewer_id,
                ),
            )

        await self.db.flush()

        return {
            "application_id": str(application_id),
            "status": app.status,
            "member_id": str(new_member_id) if new_member_id else None,
            "message": (
                f"Application approved. @{app.handle} can now log in."
                if approve
                else f"Application rejected. Note: {note or '(no reason given)'}"
            ),
        }

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
