"""
Commons service.

Threads are the public deliberative surface of the org.
Key flow: thread → formal review (ΔC signal) → sponsorship → Deliberation Cell.

Sponsorship is two-step:
  1. POST /threads/:id/sponsor
     — Snapshot thread state, ask Insight Engine for mandate draft.
       Returns ephemeral draft_id. Does NOT create a Cell yet.
  2. POST /threads/:id/sponsor/confirm
     — Sponsor edits/accepts draft, provides invited_circle_ids.
       Creates Cell atomically. Thread state → sponsored.

Formal review:
  — Circle members only.
  — Emits formal_review_filed event.
  — Integrity Engine computes ΔC asynchronously (G=0.5).
  — reviewer_id never returned in any response.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService
from ..core.exceptions import (
    NotFound, Forbidden, NotCircleMember, AlreadyExists
)
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Member, Circle, CircleMember, Dormain
from ..models.governance import (
    CommonsThread, CommonsThreadDormainTag, CommonsPost,
    CommonsFormalReview, Cell, CellInvitedCircle,
)
from ..models.types import (
    CellType, CellState, CellVisibility, TagSource, ContributionType
)
from ..schemas.commons import (
    CreateThreadRequest, CommonsThreadResponse, CommonsThreadSummaryResponse,
    CreatePostRequest, CommonsPostResponse,
    FormalReviewRequest, FormalReviewResponse,
    CorrectDormainTagRequest,
    ConfirmSponsorshipRequest, SponsorConfirmResponse, SponsorDraftResponse,
    DormainTagResponse,
)
from ..schemas.common import Paginated, MemberRef, DormainRef, CircleRef


class CommonsService(BaseService):

    # ── Threads ───────────────────────────────────────────────────────────────

    async def list_threads(
        self,
        org_id: uuid.UUID,
        dormain_id: uuid.UUID | None,
        state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> Paginated[CommonsThreadSummaryResponse]:
        q = select(CommonsThread).where(CommonsThread.org_id == org_id)

        if state:
            q = q.where(CommonsThread.state == state)
        else:
            q = q.where(CommonsThread.state != "dissolved")

        if search:
            q = q.where(CommonsThread.title.ilike(f"%{search}%"))

        if dormain_id:
            q = q.join(
                CommonsThreadDormainTag,
                CommonsThreadDormainTag.thread_id == CommonsThread.id,
            ).where(CommonsThreadDormainTag.dormain_id == dormain_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )
        total = total_result.scalar_one()

        threads_result = await self.db.execute(
            q.order_by(CommonsThread.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(CommonsThread.tags))
        )
        threads = threads_result.scalars().all()

        author_ids = list({t.author_id for t in threads})
        authors = await self._load_members_by_ids(author_ids)

        post_counts = await self._load_post_counts([t.id for t in threads])

        items = [
            await self._thread_to_summary(t, authors, post_counts)
            for t in threads
        ]

        return Paginated(
            items=items, total=total, page=page, page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_thread(
        self, thread_id: uuid.UUID, org_id: uuid.UUID
    ) -> CommonsThreadResponse:
        thread = await self._load_thread(thread_id, org_id)
        author = await self.get_by_id(Member, thread.author_id)
        post_counts = await self._load_post_counts([thread.id])
        return await self._thread_to_full(thread, author, post_counts)

    async def create_thread(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: CreateThreadRequest,
    ) -> CommonsThreadResponse:
        thread = CommonsThread(
            org_id=org_id,
            author_id=member_id,
            title=body.title,
            body=body.body,
            visibility="inherited",
            state="open",
        )
        await self.save(thread)

        # Apply author dormain signals
        now = datetime.now(timezone.utc)
        for dormain_id in body.dormain_ids:
            tag = CommonsThreadDormainTag(
                thread_id=thread.id,
                dormain_id=dormain_id,
                source=TagSource.AUTHOR,
                tagged_by=member_id,
                tagged_at=now,
            )
            self.db.add(tag)

        await self.db.flush()

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.COMMONS_THREAD_CREATED,
                subject_id=thread.id,
                subject_type="commons_thread",
                payload={
                    "title": thread.title,
                    "author_dormain_ids": [str(d) for d in body.dormain_ids],
                },
                triggered_by_member=member_id,
            ),
        )

        # Reload with tags for response
        await self.db.refresh(thread, ["tags"])
        author = await self.get_by_id(Member, member_id)
        post_counts = await self._load_post_counts([thread.id])
        return await self._thread_to_full(thread, author, post_counts)

    # ── Posts ─────────────────────────────────────────────────────────────────

    async def list_posts(
        self,
        thread_id: uuid.UUID,
        org_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> Paginated[CommonsPostResponse]:
        await self._load_thread(thread_id, org_id)  # access check

        total_result = await self.db.execute(
            select(func.count(CommonsPost.id)).where(
                CommonsPost.thread_id == thread_id
            )
        )
        total = total_result.scalar_one()

        posts_result = await self.db.execute(
            select(CommonsPost)
            .where(CommonsPost.thread_id == thread_id)
            .order_by(CommonsPost.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        posts = posts_result.scalars().all()

        author_ids = list({p.author_id for p in posts})
        authors = await self._load_members_by_ids(author_ids)

        # Formal review counts per post
        review_counts_result = await self.db.execute(
            select(CommonsFormalReview.post_id, func.count(CommonsFormalReview.id))
            .where(CommonsFormalReview.post_id.in_([p.id for p in posts]))
            .group_by(CommonsFormalReview.post_id)
        )
        review_counts = dict(review_counts_result.all())

        items = [
            CommonsPostResponse(
                id=p.id,
                thread_id=p.thread_id,
                author=MemberRef(
                    id=authors[p.author_id].id,
                    handle=authors[p.author_id].handle,
                    display_name=authors[p.author_id].display_name,
                ) if p.author_id in authors else None,
                body=p.body,
                parent_post_id=p.parent_post_id,
                formal_review_count=review_counts.get(p.id, 0),
                created_at=p.created_at,
                edited_at=p.edited_at,
            )
            for p in posts
        ]
        return Paginated(
            items=items, total=total, page=page, page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def create_post(
        self,
        thread_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: CreatePostRequest,
    ) -> CommonsPostResponse:
        thread = await self._load_thread(thread_id, org_id)

        if thread.state in ("frozen", "dissolved"):
            raise Forbidden(f"Thread is {thread.state} — no new posts permitted")

        if body.parent_post_id:
            parent_result = await self.db.execute(
                select(CommonsPost).where(
                    CommonsPost.id == body.parent_post_id,
                    CommonsPost.thread_id == thread_id,
                )
            )
            if parent_result.scalar_one_or_none() is None:
                raise NotFound("Parent post", str(body.parent_post_id))

        post = CommonsPost(
            thread_id=thread_id,
            author_id=member_id,
            body=body.body,
            parent_post_id=body.parent_post_id,
        )
        await self.save(post)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.COMMONS_POST_CREATED,
                subject_id=post.id,
                subject_type="commons_post",
                payload={"thread_id": str(thread_id)},
                triggered_by_member=member_id,
            ),
        )

        author = await self.get_by_id(Member, member_id)
        return CommonsPostResponse(
            id=post.id,
            thread_id=post.thread_id,
            author=MemberRef(
                id=author.id, handle=author.handle, display_name=author.display_name
            ),
            body=post.body,
            parent_post_id=post.parent_post_id,
            formal_review_count=0,
            created_at=post.created_at,
            edited_at=None,
        )

    # ── Sponsorship ───────────────────────────────────────────────────────────

    async def sponsor_thread(
        self,
        thread_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> SponsorDraftResponse:
        """
        Step 1: validate sponsorship eligibility, ask Insight Engine for draft.
        Thread state unchanged. Returns ephemeral draft.
        """
        thread = await self._load_thread(thread_id, org_id)

        if thread.state not in ("open",):
            raise Forbidden(f"Thread must be 'open' to sponsor; current state: {thread.state}")

        # Sponsor must be a Circle member
        await self._require_circle_member(member_id, org_id)

        # Snapshot post count for mandate generation context
        post_count_result = await self.db.execute(
            select(func.count(CommonsPost.id)).where(CommonsPost.thread_id == thread_id)
        )
        post_count = post_count_result.scalar_one()

        import json as _json

        draft_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Try NATS request/reply to Insight Engine (10s timeout)
        bus = get_event_bus()
        engine_draft = None
        if bus._connected and bus._nc is not None:
            try:
                reply_msg = await bus._nc.request(
                    subject=f"ORG.{org_id}.events",
                    payload=_json.dumps({
                        "event_type": "sponsor_draft_requested",
                        "org_id": str(org_id),
                        "thread_id": str(thread_id),
                        "draft_id": draft_id,
                        "title": thread.title,
                        "post_count": post_count,
                    }, default=str).encode(),
                    timeout=10.0,
                )
                engine_draft = _json.loads(reply_msg.data.decode())
            except Exception:
                pass

        author = await self.get_by_id(Member, member_id)

        if engine_draft:
            return SponsorDraftResponse(
                draft_id=engine_draft.get("draft_id", draft_id),
                founding_mandate=engine_draft.get("founding_mandate", ""),
                key_themes=engine_draft.get("key_themes", []),
                contributing_members=[
                    MemberRef(id=author.id, handle=author.handle,
                              display_name=author.display_name)
                ],
                generated_at=now,
            )

        # Fallback: load posts ourselves for a basic mandate
        posts_result = await self.db.execute(
            select(CommonsPost)
            .where(CommonsPost.thread_id == thread_id)
            .order_by(CommonsPost.created_at.asc())
            .limit(15)
        )
        posts = posts_result.scalars().all()
        combined = " ".join(p.body[:200] for p in posts)
        mandate_preview = (
            combined[:400].rsplit(".", 1)[0] + "."
            if combined
            else f"Deliberation cell for: {thread.title}"
        )

        return SponsorDraftResponse(
            draft_id=draft_id,
            founding_mandate=mandate_preview,
            key_themes=[],
            contributing_members=[
                MemberRef(id=author.id, handle=author.handle,
                          display_name=author.display_name)
            ],
            generated_at=now,
        )

    async def confirm_sponsorship(
        self,
        thread_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: ConfirmSponsorshipRequest,
    ) -> SponsorConfirmResponse:
        """
        Step 2: sponsor confirms mandate, provides invited circles.
        Creates Deliberation Cell atomically. Thread state → sponsored.
        """
        thread = await self._load_thread(thread_id, org_id)

        if thread.state not in ("open",):
            raise Forbidden(f"Thread state '{thread.state}' cannot be sponsored")

        await self._require_circle_member(member_id, org_id)

        # Validate all invited_circle_ids exist within org
        circles = await self._validate_circles(body.invited_circle_ids, org_id)

        now = datetime.now(timezone.utc)

        # Create the Deliberation Cell
        cell = Cell(
            org_id=org_id,
            cell_type=CellType.DELIBERATION,
            visibility=CellVisibility.CLOSED,
            state=CellState.ACTIVE,
            initiating_member_id=member_id,
            commons_thread_id=thread_id,
            commons_snapshot_at=now,
            founding_mandate=body.founding_mandate,
            state_changed_at=now,
        )
        await self.save(cell)

        # Attach invited circles
        for circle_id in body.invited_circle_ids:
            invitation = CellInvitedCircle(
                cell_id=cell.id,
                circle_id=circle_id,
                invited_because="sponsor_selection",
                invited_at=now,
            )
            self.db.add(invitation)

        # Mark thread as sponsored
        thread.state = "sponsored"
        thread.sponsored_at = now
        thread.sponsoring_cell_id = cell.id

        await self.db.flush()

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.CELL_CREATED,
                subject_id=cell.id,
                subject_type="cell",
                payload={
                    "thread_id": str(thread_id),
                    "invited_circle_ids": [str(c) for c in body.invited_circle_ids],
                    "cell_type": CellType.DELIBERATION.value,
                },
                triggered_by_member=member_id,
            ),
        )

        return SponsorConfirmResponse(
            cell_id=cell.id,
            thread_id=thread_id,
            founding_mandate=body.founding_mandate,
            invited_circles=[
                CircleRef(id=c.id, name=c.name) for c in circles
            ],
            created_at=now,
        )

    # ── Formal review ─────────────────────────────────────────────────────────

    async def formal_review(
        self,
        post_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: FormalReviewRequest,
    ) -> FormalReviewResponse:
        """
        Reviewer submits a formal score for a Commons post.
        Reviewer must be a Circle member with a mandate in the given dormain.
        Emits formal_review_filed → Integrity Engine computes ΔC (G=0.5).
        reviewer_id is NEVER returned in the response.
        """
        post = await self.db.execute(
            select(CommonsPost)
            .join(CommonsThread, CommonsPost.thread_id == CommonsThread.id)
            .where(CommonsPost.id == post_id, CommonsThread.org_id == org_id)
        )
        post_obj = post.scalar_one_or_none()
        if post_obj is None:
            raise NotFound("Post", str(post_id))

        # Cannot review your own post
        if post_obj.author_id == member_id:
            raise Forbidden("SELF_REVIEW_PROHIBITED: cannot formally review your own post")

        # Reviewer must be a Circle member with mandate in the specified dormain
        await self._require_circle_mandate(member_id, org_id, body.dormain_id)

        # One review per reviewer per dormain per post
        existing_review = await self.db.execute(
            select(CommonsFormalReview).where(
                CommonsFormalReview.post_id == post_id,
                CommonsFormalReview.reviewer_id == member_id,
                CommonsFormalReview.dormain_id == body.dormain_id,
            )
        )
        if existing_review.scalar_one_or_none() is not None:
            raise AlreadyExists("Formal review", "post_id+reviewer_id+dormain_id", str(post_id))

        review = CommonsFormalReview(
            post_id=post_id,
            reviewer_id=member_id,
            dormain_id=body.dormain_id,
            score_s=body.score_s,
            reviewed_at=datetime.now(timezone.utc),
        )
        await self.save(review)

        dormain = await self.get_by_id(Dormain, body.dormain_id)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.FORMAL_REVIEW_FILED,
                subject_id=post_id,
                subject_type="commons_post",
                payload={
                    "review_id": str(review.id),
                    "dormain_id": str(body.dormain_id),
                    "score_s": body.score_s,
                    "post_author_id": str(post_obj.author_id),
                    # reviewer_id intentionally excluded from event payload
                    # Integrity Engine reads it from delta_c_reviewers table only
                },
                triggered_by_member=member_id,
            ),
        )

        return FormalReviewResponse(
            id=review.id,
            post_id=post_id,
            dormain=DormainRef(id=dormain.id, name=dormain.name),
            score_s=float(review.score_s),
            delta_c_event_id=None,  # populated by Integrity Engine async
            reviewed_at=review.reviewed_at,
        )

    # ── Dormain tag correction ────────────────────────────────────────────────

    async def correct_dormain_tag(
        self,
        thread_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: CorrectDormainTagRequest,
    ) -> CommonsThreadResponse:
        thread = await self._load_thread(thread_id, org_id)
        now = datetime.now(timezone.utc)

        # Find the tag to remove
        old_tag_result = await self.db.execute(
            select(CommonsThreadDormainTag).where(
                CommonsThreadDormainTag.thread_id == thread_id,
                CommonsThreadDormainTag.dormain_id == body.remove_dormain_id,
            )
        )
        old_tag = old_tag_result.scalar_one_or_none()
        if old_tag is None:
            raise NotFound("Dormain tag", str(body.remove_dormain_id))

        # Validate new dormain exists in org
        new_dormain = await self.db.execute(
            select(Dormain).where(
                Dormain.id == body.add_dormain_id, Dormain.org_id == org_id
            )
        )
        if new_dormain.scalar_one_or_none() is None:
            raise NotFound("Dormain", str(body.add_dormain_id))

        # Remove old
        await self.db.delete(old_tag)

        # Add corrected tag
        new_tag = CommonsThreadDormainTag(
            thread_id=thread_id,
            dormain_id=body.add_dormain_id,
            source=TagSource.HUMAN_CORRECTION,
            tagged_by=member_id,
            tagged_at=now,
            corrected_from_dormain_id=body.remove_dormain_id,
        )
        self.db.add(new_tag)
        await self.db.flush()

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.DORMAIN_TAG_CORRECTED,
                subject_id=thread_id,
                subject_type="commons_thread",
                payload={
                    "removed_dormain_id": str(body.remove_dormain_id),
                    "added_dormain_id": str(body.add_dormain_id),
                },
                triggered_by_member=member_id,
            ),
        )

        await self.db.refresh(thread, ["tags"])
        author = await self.get_by_id(Member, thread.author_id)
        post_counts = await self._load_post_counts([thread.id])
        return await self._thread_to_full(thread, author, post_counts)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _load_thread(
        self, thread_id: uuid.UUID, org_id: uuid.UUID
    ) -> CommonsThread:
        result = await self.db.execute(
            select(CommonsThread)
            .where(CommonsThread.id == thread_id, CommonsThread.org_id == org_id)
            .options(selectinload(CommonsThread.tags))
        )
        thread = result.scalar_one_or_none()
        if thread is None:
            raise NotFound("Thread", str(thread_id))
        return thread

    async def _load_members_by_ids(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Member]:
        if not ids:
            return {}
        result = await self.db.execute(select(Member).where(Member.id.in_(ids)))
        return {m.id: m for m in result.scalars().all()}

    async def _load_post_counts(
        self, thread_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not thread_ids:
            return {}
        result = await self.db.execute(
            select(CommonsPost.thread_id, func.count(CommonsPost.id))
            .where(CommonsPost.thread_id.in_(thread_ids))
            .group_by(CommonsPost.thread_id)
        )
        return dict(result.all())

    async def _require_circle_member(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        result = await self.db.execute(
            select(CircleMember)
            .join(Circle, CircleMember.circle_id == Circle.id)
            .where(
                CircleMember.member_id == member_id,
                Circle.org_id == org_id,
                CircleMember.exited_at.is_(None),
                Circle.dissolved_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise NotCircleMember()

    async def _require_circle_mandate(
        self,
        member_id: uuid.UUID,
        org_id: uuid.UUID,
        dormain_id: uuid.UUID,
    ) -> None:
        """Member must be in a Circle with a mandate (primary or secondary) for dormain."""
        from ..models.org import CircleDormain
        result = await self.db.execute(
            select(CircleMember)
            .join(Circle, CircleMember.circle_id == Circle.id)
            .join(CircleDormain, CircleDormain.circle_id == Circle.id)
            .where(
                CircleMember.member_id == member_id,
                Circle.org_id == org_id,
                CircleDormain.dormain_id == dormain_id,
                CircleDormain.removed_at.is_(None),
                CircleMember.exited_at.is_(None),
                Circle.dissolved_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise Forbidden(
                "REVIEW_MANDATE_REQUIRED: you must be in a Circle with a mandate "
                "in this dormain to submit a formal review"
            )

    async def _validate_circles(
        self, circle_ids: list[uuid.UUID], org_id: uuid.UUID
    ) -> list[Circle]:
        result = await self.db.execute(
            select(Circle).where(
                Circle.id.in_(circle_ids),
                Circle.org_id == org_id,
                Circle.dissolved_at.is_(None),
            )
        )
        circles = result.scalars().all()
        found_ids = {c.id for c in circles}
        missing = [str(cid) for cid in circle_ids if cid not in found_ids]
        if missing:
            raise NotFound("Circle(s)", ", ".join(missing))
        return circles

    async def _thread_to_summary(
        self,
        thread: CommonsThread,
        authors: dict[uuid.UUID, Member],
        post_counts: dict[uuid.UUID, int],
    ) -> CommonsThreadSummaryResponse:
        author = authors.get(thread.author_id)
        return CommonsThreadSummaryResponse(
            id=thread.id,
            title=thread.title,
            body_preview=thread.body[:280],
            author=MemberRef(
                id=author.id, handle=author.handle, display_name=author.display_name
            ) if author else None,
            tags=[
                DormainRef(id=tag.dormain_id, name="")
                for tag in (thread.tags or [])
            ],
            state=thread.state,
            post_count=post_counts.get(thread.id, 0),
            created_at=thread.created_at,
            sponsored_at=thread.sponsored_at,
        )

    async def _thread_to_full(
        self,
        thread: CommonsThread,
        author: Member | None,
        post_counts: dict[uuid.UUID, int],
    ) -> CommonsThreadResponse:
        # Load dormain names for tags
        dormain_ids = [tag.dormain_id for tag in (thread.tags or [])]
        dormains: dict[uuid.UUID, Dormain] = {}
        if dormain_ids:
            d_result = await self.db.execute(
                select(Dormain).where(Dormain.id.in_(dormain_ids))
            )
            dormains = {d.id: d for d in d_result.scalars().all()}

        # Load tag authors
        tagger_ids = [
            tag.tagged_by for tag in (thread.tags or []) if tag.tagged_by
        ]
        taggers: dict[uuid.UUID, Member] = {}
        if tagger_ids:
            t_result = await self.db.execute(
                select(Member).where(Member.id.in_(tagger_ids))
            )
            taggers = {m.id: m for m in t_result.scalars().all()}

        tag_responses = []
        for tag in (thread.tags or []):
            d = dormains.get(tag.dormain_id)
            tagger = taggers.get(tag.tagged_by) if tag.tagged_by else None
            corrected_dormain = dormains.get(tag.corrected_from_dormain_id) if tag.corrected_from_dormain_id else None

            tag_responses.append(
                DormainTagResponse(
                    dormain=DormainRef(id=tag.dormain_id, name=d.name if d else ""),
                    source=tag.source,
                    tagged_by=MemberRef(
                        id=tagger.id, handle=tagger.handle, display_name=tagger.display_name
                    ) if tagger else None,
                    tagged_at=tag.tagged_at,
                    corrected_from=DormainRef(
                        id=tag.corrected_from_dormain_id,
                        name=corrected_dormain.name if corrected_dormain else "",
                    ) if tag.corrected_from_dormain_id else None,
                )
            )

        return CommonsThreadResponse(
            id=thread.id,
            title=thread.title,
            body=thread.body,
            author=MemberRef(
                id=author.id, handle=author.handle, display_name=author.display_name
            ) if author else None,
            tags=tag_responses,
            state=thread.state,
            visibility=thread.visibility,
            sponsored_at=thread.sponsored_at,
            sponsoring_cell_id=thread.sponsoring_cell_id,
            post_count=post_counts.get(thread.id, 0),
            created_at=thread.created_at,
        )
