"""
Cells service.

A Cell is a bounded deliberation space. Key flows:

  Contribution → (vote rounds) → crystallise (draft) → file-motion (commit)
  ↓
  aSTF gate1 review → resolution → [gate2] → enacted

Vote model:
  One vote per (voter, dormain, motion). Weight = voter's w_s in that dormain
  at the moment of voting. Stored immutably.

file-motion:
  Pydantic schema validates implementing_circle_ids at request parse time.
  Service double-enforces (defence in depth) and persists Motion + children.
  Emits motion_filed → Inferential Engine commissions aSTF.

crystallise:
  Snapshot current Cell state, request mandate draft from Insight Engine.
  Returns draft — does NOT file. Sponsor edits and calls file-motion.
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
    NotFound, Forbidden, CellAccessDenied, VoteAlreadyCast,
    MotionAlreadyFiled, ValidationFailed, MissingExecutingCircles,
)
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Member, Circle, CircleMember, Dormain
from ..models.competence import CompetenceScore
from ..models.governance import (
    Cell, CellInvitedCircle, CellContribution, CellVote, CellCompositionProfile,
    Motion, MotionDirective, MotionSpecification, Resolution,
)
from ..models.types import (
    CellState, CellType, ContributionType, MotionType, MotionState,
    ResolutionState, ImplementationType, Gate2Agent,
)
from ..schemas.cells import (
    CellResponse, ContributionResponse, AddContributionRequest,
    ImportCommonsContextRequest, CellMinutesResponse,
    CastVoteRequest, CellVoteSummariesResponse, VoteSummaryResponse,
    CrystalliseDraftResponse, DirectiveDraft, SpecificationDraft,
    FileCrystallisedMotionRequest, FiledMotionResponse,
    CompositionProfileResponse, DissolveCellRequest,
)
from ..schemas.common import MemberRef, CircleRef, DormainRef, Paginated


class CellsService(BaseService):

    # ── Cell reads ────────────────────────────────────────────────────────────

    async def get_cell(
        self, cell_id: uuid.UUID, org_id: uuid.UUID, member_id: uuid.UUID
    ) -> CellResponse:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        return await self._cell_to_response(cell)

    # ── Contributions ─────────────────────────────────────────────────────────

    async def list_contributions(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> Paginated[ContributionResponse]:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)

        total_q = select(func.count(CellContribution.id)).where(
            CellContribution.cell_id == cell_id
        )
        total = (await self.db.execute(total_q)).scalar_one()

        rows = await self.db.execute(
            select(CellContribution)
            .where(CellContribution.cell_id == cell_id)
            .order_by(CellContribution.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        contributions = rows.scalars().all()

        author_ids = list({c.author_id for c in contributions})
        authors = await self._load_members(author_ids)

        items = [
            ContributionResponse(
                id=c.id,
                cell_id=c.cell_id,
                author=MemberRef(
                    id=authors[c.author_id].id,
                    handle=authors[c.author_id].handle,
                    display_name=authors[c.author_id].display_name,
                ) if c.author_id in authors else None,
                body=c.body,
                contribution_type=c.contribution_type,
                commons_post_ref=c.commons_post_ref,
                created_at=c.created_at,
            )
            for c in contributions
        ]
        return Paginated(
            items=items, total=total, page=page, page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def add_contribution(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: AddContributionRequest,
    ) -> ContributionResponse:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        await self._require_cell_active(cell)

        c = CellContribution(
            cell_id=cell_id,
            author_id=member_id,
            body=body.body,
            contribution_type=body.contribution_type,
        )
        await self.save(c)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.CELL_CONTRIBUTION_ADDED,
                subject_id=cell_id,
                subject_type="cell",
                payload={"contribution_id": str(c.id), "type": body.contribution_type.value},
                triggered_by_member=member_id,
            ),
        )

        author = await self.get_by_id(Member, member_id)
        return ContributionResponse(
            id=c.id,
            cell_id=cell_id,
            author=MemberRef(id=author.id, handle=author.handle,
                             display_name=author.display_name),
            body=c.body,
            contribution_type=c.contribution_type,
            commons_post_ref=None,
            created_at=c.created_at,
        )

    async def import_commons_context(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: ImportCommonsContextRequest,
    ) -> list[ContributionResponse]:
        from ..models.governance import CommonsPost, CommonsThread
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        await self._require_cell_active(cell)

        # Validate all post_ids belong to this org
        posts_result = await self.db.execute(
            select(CommonsPost)
            .join(CommonsThread, CommonsPost.thread_id == CommonsThread.id)
            .where(
                CommonsPost.id.in_(body.post_ids),
                CommonsThread.org_id == org_id,
            )
        )
        posts = {p.id: p for p in posts_result.scalars().all()}
        missing = [str(pid) for pid in body.post_ids if pid not in posts]
        if missing:
            raise NotFound("Commons post(s)", ", ".join(missing))

        author = await self.get_by_id(Member, member_id)
        created = []
        for pid in body.post_ids:
            post = posts[pid]
            c = CellContribution(
                cell_id=cell_id,
                author_id=member_id,
                body=post.body,
                contribution_type=ContributionType.COMMONS_CONTEXT_IMPORT,
                commons_post_ref=pid,
            )
            self.db.add(c)
            created.append(c)

        await self.db.flush()
        for c in created:
            await self.db.refresh(c)

        return [
            ContributionResponse(
                id=c.id,
                cell_id=cell_id,
                author=MemberRef(id=author.id, handle=author.handle,
                                 display_name=author.display_name),
                body=c.body,
                contribution_type=c.contribution_type,
                commons_post_ref=c.commons_post_ref,
                created_at=c.created_at,
            )
            for c in created
        ]

    # ── Votes ─────────────────────────────────────────────────────────────────

    async def get_votes(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> CellVoteSummariesResponse:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)

        # Get the active motion for this cell
        motion = await self._get_active_motion(cell_id)
        if motion is None:
            return CellVoteSummariesResponse(
                motion_id=None,
                tallies_by_dormain=[],
                overall_result=None,
            )

        # Aggregate votes by dormain
        agg_result = await self.db.execute(
            select(
                CellVote.dormain_id,
                CellVote.vote,
                func.sum(CellVote.weight).label("total_weight"),
                func.count(CellVote.id).label("count"),
            )
            .where(CellVote.motion_id == motion.id)
            .group_by(CellVote.dormain_id, CellVote.vote)
        )
        rows = agg_result.all()

        # Reshape: dormain_id → {vote → (weight, count)}
        by_dormain: dict[uuid.UUID, dict] = {}
        for dormain_id, vote, weight, count in rows:
            if dormain_id not in by_dormain:
                by_dormain[dormain_id] = {}
            by_dormain[dormain_id][vote] = {"weight": float(weight), "count": int(count)}

        dormain_ids = list(by_dormain.keys())
        dormains = {}
        if dormain_ids:
            d_res = await self.db.execute(
                select(Dormain).where(Dormain.id.in_(dormain_ids))
            )
            dormains = {d.id: d for d in d_res.scalars().all()}

        tallies = []
        for dormain_id, votes in by_dormain.items():
            yea_w = votes.get("yea", {}).get("weight", 0.0)
            nay_w = votes.get("nay", {}).get("weight", 0.0)
            abs_w = votes.get("abstain", {}).get("weight", 0.0)
            total_w = yea_w + nay_w + abs_w
            tallies.append(VoteSummaryResponse(
                motion_id=motion.id,
                dormain_id=dormain_id,
                dormain_name=dormains[dormain_id].name if dormain_id in dormains else "",
                yea_weight=yea_w,
                nay_weight=nay_w,
                abstain_weight=abs_w,
                total_weight=total_w,
                yea_count=votes.get("yea", {}).get("count", 0),
                nay_count=votes.get("nay", {}).get("count", 0),
                abstain_count=votes.get("abstain", {}).get("count", 0),
                quorum_met=total_w > 0,
                threshold_met=total_w > 0 and (yea_w / total_w) > 0.5,
                closed_at=None,
            ))

        return CellVoteSummariesResponse(
            motion_id=motion.id,
            tallies_by_dormain=tallies,
            overall_result=None,
        )

    async def cast_vote(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: CastVoteRequest,
    ) -> None:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        await self._require_cell_active(cell)

        motion = await self._get_active_motion(cell_id)
        if motion is None:
            raise Forbidden("VOTE_NO_ACTIVE_MOTION: no active motion in this cell")
        if motion.id != body.motion_id:
            raise Forbidden("VOTE_WRONG_MOTION: motion_id does not match the active motion")
        if motion.state != MotionState.ACTIVE:
            raise Forbidden(f"VOTE_CLOSED: motion state is {motion.state.value}")

        # Check for duplicate vote (UniqueConstraint on motion+voter+dormain)
        existing = await self.db.execute(
            select(CellVote).where(
                CellVote.motion_id == motion.id,
                CellVote.voter_id == member_id,
                CellVote.dormain_id == body.dormain_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise VoteAlreadyCast()

        # Load voter's w_s in this dormain — weight at time of vote
        score_result = await self.db.execute(
            select(CompetenceScore).where(
                CompetenceScore.member_id == member_id,
                CompetenceScore.dormain_id == body.dormain_id,
            )
        )
        score = score_result.scalar_one_or_none()
        w_s = float(score.w_s) if score else 0.0

        if w_s == 0.0:
            raise Forbidden(
                "VOTE_NO_COMPETENCE: w_s = 0 in this dormain — "
                "you have no weighted standing to vote"
            )

        vote = CellVote(
            cell_id=cell_id,
            motion_id=motion.id,
            voter_id=member_id,
            dormain_id=body.dormain_id,
            vote=body.vote,
            w_s_at_vote=w_s,
            weight=w_s,
            voted_at=datetime.now(timezone.utc),
        )
        await self.save(vote)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.CELL_VOTE_CAST,
                subject_id=motion.id,
                subject_type="motion",
                payload={
                    "vote": body.vote,
                    "dormain_id": str(body.dormain_id),
                    "weight": w_s,
                    # voter_id intentionally excluded from payload
                },
                triggered_by_member=member_id,
            ),
        )

    # ── Crystallise ───────────────────────────────────────────────────────────

    async def crystallise(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> CrystalliseDraftResponse:
        """
        Snapshot Cell state, request motion draft from Insight Engine.
        Returns ephemeral draft — does NOT file the motion.
        Sponsor edits and calls file-motion to commit.
        """
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        await self._require_cell_active(cell)
        await self._require_is_initiating_member(cell, member_id)

        # Check no motion already in flight
        existing_motion = await self._get_active_motion(cell_id)
        if existing_motion is not None:
            raise MotionAlreadyFiled(str(cell_id))

        # Snapshot contribution count
        contrib_count_result = await self.db.execute(
            select(func.count(CellContribution.id)).where(
                CellContribution.cell_id == cell_id
            )
        )
        contrib_count = contrib_count_result.scalar_one()

        # NATS request/reply to Insight Engine — 15s timeout.
        # Falls back to stub draft if engine unavailable.
        import json as _json
        bus = get_event_bus()
        engine_draft = None

        if bus._connected and bus._nc is not None:
            try:
                reply_msg = await bus._nc.request(
                    subject=f"ORG.{org_id}.events",
                    payload=_json.dumps({
                        "event_type": "cell_crystallise_requested",
                        "org_id": str(org_id),
                        "cell_id": str(cell_id),
                        "motion_type_hint": "non_system",
                    }, default=str).encode(),
                    timeout=15.0,
                )
                engine_draft = _json.loads(reply_msg.data.decode())
            except Exception:
                pass  # fall through to stub

        if engine_draft:
            directive = engine_draft.get("directive_draft", {})
            return CrystalliseDraftResponse(
                draft_id=engine_draft.get("draft_id", str(uuid.uuid4())),
                motion_type_suggested=MotionType(
                    engine_draft.get("motion_type_suggested", "non_system")
                ),
                directive_draft=DirectiveDraft(
                    body=directive.get("body", ""),
                    commitments=directive.get("commitments", []),
                    ambiguities_flagged=directive.get("ambiguities_flagged", []),
                    contributing_members=[],
                ),
                specification_drafts=None,
                accountability_circles_suggested=None,
                generated_at=datetime.now(timezone.utc),
            )

        # Fallback stub if Insight Engine unavailable
        author = await self.get_by_id(Member, member_id)
        return CrystalliseDraftResponse(
            draft_id=str(uuid.uuid4()),
            motion_type_suggested=MotionType.NON_SYSTEM,
            directive_draft=DirectiveDraft(
                body=(
                    f"[{contrib_count} contributions — Insight Engine not available. "
                    f"Write directive manually.]"
                ),
                commitments=[],
                ambiguities_flagged=[],
                contributing_members=[
                    MemberRef(id=author.id, handle=author.handle,
                              display_name=author.display_name)
                ],
            ),
            specification_drafts=None,
            accountability_circles_suggested=None,
            generated_at=datetime.now(timezone.utc),
        )

    # ── File motion ───────────────────────────────────────────────────────────

    async def file_motion(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: FileCrystallisedMotionRequest,
    ) -> FiledMotionResponse:
        """
        Persist a motion. Pydantic validator already checked implementing_circle_ids
        shape; service layer re-enforces as defence in depth, then creates:
          Motion + MotionDirective (if non_system/hybrid) +
          MotionSpecification[] (if sys_bound/hybrid) + emits motion_filed.
        """
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)
        await self._require_cell_active(cell)
        await self._require_is_initiating_member(cell, member_id)

        # Defence-in-depth: re-enforce implementing_circle_ids contract
        if body.motion_type in (MotionType.NON_SYSTEM, MotionType.HYBRID):
            if not body.implementing_circle_ids:
                raise MissingExecutingCircles(body.motion_type.value)

        # Prevent duplicate active motions per cell
        existing = await self._get_active_motion(cell_id)
        if existing is not None:
            raise MotionAlreadyFiled(str(cell_id))

        now = datetime.now(timezone.utc)

        motion = Motion(
            org_id=org_id,
            cell_id=cell_id,
            motion_type=body.motion_type,
            state=MotionState.ACTIVE,
            filed_by=member_id,
            crystallised_at=now,
            state_changed_at=now,
        )
        await self.save(motion)

        # Directive — non_system and hybrid
        if body.directive_body:
            directive = MotionDirective(
                motion_id=motion.id,
                body=body.directive_body,
                commitments=body.directive_commitments or [],
                ambiguities_flagged=body.directive_ambiguities_flagged or [],
            )
            self.db.add(directive)

        # Specifications — sys_bound and hybrid
        if body.specifications:
            for spec in body.specifications:
                s = MotionSpecification(
                    motion_id=motion.id,
                    parameter=spec.parameter,
                    new_value={"value": spec.new_value},
                    justification=spec.justification,
                )
                self.db.add(s)

        await self.db.flush()

        # Emit motion_filed → Inferential Engine commissions aSTF
        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.MOTION_FILED,
                subject_id=motion.id,
                subject_type="motion",
                payload={
                    "motion_type": body.motion_type.value,
                    "cell_id": str(cell_id),
                    "has_directive": body.directive_body is not None,
                    "spec_count": len(body.specifications or []),
                    "implementing_circle_ids": [
                        str(c) for c in (body.implementing_circle_ids or [])
                    ],
                },
                triggered_by_member=member_id,
            ),
        )

        author = await self.get_by_id(Member, member_id)
        return FiledMotionResponse(
            id=motion.id,
            motion_type=motion.motion_type,
            state=motion.state,
            cell_id=cell_id,
            filed_by=MemberRef(id=author.id, handle=author.handle,
                               display_name=author.display_name),
            implementing_circle_ids=body.implementing_circle_ids,
            created_at=motion.created_at,
        )

    # ── Minutes ───────────────────────────────────────────────────────────────

    async def get_minutes(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> CellMinutesResponse:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)

        contrib_count = (await self.db.execute(
            select(func.count(CellContribution.id)).where(
                CellContribution.cell_id == cell_id
            )
        )).scalar_one()

        # Real impl: read latest Insight Engine minutes snapshot.
        # Stub: return empty minutes until Insight Engine integration.
        return CellMinutesResponse(
            cell_id=cell_id,
            key_positions=[],
            open_questions=[],
            emerging_consensus=[],
            points_of_contention=[],
            contribution_count=contrib_count,
            generated_at=datetime.now(timezone.utc),
        )

    # ── Composition profile ───────────────────────────────────────────────────

    async def get_composition_profile(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> CompositionProfileResponse:
        cell = await self._load_cell(cell_id, org_id)
        await self._check_cell_access(cell, member_id, org_id)

        # Load latest profile snapshot
        result = await self.db.execute(
            select(CellCompositionProfile)
            .where(CellCompositionProfile.cell_id == cell_id)
            .order_by(CellCompositionProfile.computed_at.desc())
            .limit(1)
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            return CompositionProfileResponse(
                cell_id=cell_id,
                computed_at=datetime.now(timezone.utc),
                dormain_weights={},
                gap_dormains=[],
            )

        return CompositionProfileResponse(
            cell_id=cell_id,
            computed_at=profile.computed_at,
            dormain_weights=profile.profile.get("dormain_weights", {}),
            gap_dormains=[],
        )

    # ── Dissolve ──────────────────────────────────────────────────────────────

    async def dissolve_cell(
        self,
        cell_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: DissolveCellRequest,
    ) -> None:
        cell = await self._load_cell(cell_id, org_id)
        await self._require_is_initiating_member(cell, member_id)

        if cell.state in (CellState.DISSOLVED, CellState.ARCHIVED):
            raise Forbidden(f"Cell already {cell.state.value}")

        # Cannot dissolve if a motion is pending gate review
        active_motion = await self._get_active_motion(cell_id)
        if active_motion and active_motion.state in (
            MotionState.GATE1_PENDING, MotionState.PENDING_IMPLEMENTATION, MotionState.GATE2_PENDING
        ):
            raise Forbidden("DISSOLVE_BLOCKED: motion is in gate review — dissolve blocked")

        cell.state = CellState.DISSOLVED
        cell.state_changed_at = datetime.now(timezone.utc)
        await self.db.flush()

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.CELL_DISSOLVED,
                subject_id=cell_id,
                subject_type="cell",
                payload={"reason": body.reason},
                triggered_by_member=member_id,
            ),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _load_cell(self, cell_id: uuid.UUID, org_id: uuid.UUID) -> Cell:
        result = await self.db.execute(
            select(Cell)
            .where(Cell.id == cell_id, Cell.org_id == org_id)
            .options(selectinload(Cell.invited_circles))
        )
        cell = result.scalar_one_or_none()
        if cell is None:
            raise NotFound("Cell", str(cell_id))
        return cell

    async def _check_cell_access(
        self, cell: Cell, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        """
        Cell access: member must be in one of the invited Circles.
        The initiating member always has access regardless of Circle membership.
        """
        if cell.initiating_member_id == member_id:
            return

        invited_circle_ids = [ic.circle_id for ic in cell.invited_circles]
        if not invited_circle_ids:
            return  # open cell

        member_circles_result = await self.db.execute(
            select(CircleMember.circle_id)
            .where(
                CircleMember.member_id == member_id,
                CircleMember.circle_id.in_(invited_circle_ids),
                CircleMember.exited_at.is_(None),
            )
        )
        if member_circles_result.first() is None:
            raise CellAccessDenied(str(cell.id))

    async def _require_cell_active(self, cell: Cell) -> None:
        if cell.state != CellState.ACTIVE:
            raise Forbidden(f"CELL_{cell.state.value.upper()}: cell is not active")

    async def _require_is_initiating_member(
        self, cell: Cell, member_id: uuid.UUID
    ) -> None:
        if cell.initiating_member_id != member_id:
            raise Forbidden(
                "INITIATING_MEMBER_ONLY: only the sponsoring member can "
                "crystallise, file motions, or dissolve this cell"
            )

    async def _get_active_motion(self, cell_id: uuid.UUID) -> Motion | None:
        result = await self.db.execute(
            select(Motion)
            .where(
                Motion.cell_id == cell_id,
                Motion.state.not_in([
                    MotionState.ENACTED.value,
                    MotionState.ENACTED_LOCKED.value,
                    MotionState.ABANDONED.value,
                ]),
            )
            .order_by(Motion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_members(
        self, member_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Member]:
        if not member_ids:
            return {}
        result = await self.db.execute(
            select(Member).where(Member.id.in_(member_ids))
        )
        return {m.id: m for m in result.scalars().all()}

    async def _cell_to_response(self, cell: Cell) -> CellResponse:
        initiator = await self.get_by_id(Member, cell.initiating_member_id)

        # Load circle names for invited circles
        circle_ids = [ic.circle_id for ic in cell.invited_circles]
        circles: dict[uuid.UUID, Circle] = {}
        if circle_ids:
            c_result = await self.db.execute(
                select(Circle).where(Circle.id.in_(circle_ids))
            )
            circles = {c.id: c for c in c_result.scalars().all()}

        return CellResponse(
            id=cell.id,
            org_id=cell.org_id,
            cell_type=cell.cell_type,
            visibility=cell.visibility,
            state=cell.state,
            initiating_member=MemberRef(
                id=initiator.id,
                handle=initiator.handle,
                display_name=initiator.display_name,
            ) if initiator else None,
            founding_mandate=cell.founding_mandate,
            revision_directive=cell.revision_directive,
            invited_circles=[
                CircleRef(id=cid, name=circles[cid].name if cid in circles else "")
                for cid in circle_ids
            ],
            created_at=cell.created_at,
            state_changed_at=cell.state_changed_at,
        )
