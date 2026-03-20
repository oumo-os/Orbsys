"""
STF service.

STF instances are the audit layer. The Inferential Engine matches candidates
to assignments; the Blind Review API accepts verdict submissions.
This service handles commissioning and read operations only.

Identity policy (enforced here):
  xSTF (non-blind): member identity returned in assignments
  All others (aSTF, vSTF, jSTF, meta-aSTF): member_id ABSENT from all responses

Enact resolution:
  Sys-bound only. Synchronous — this call blocks until the Integrity Engine
  commits the atomic parameter write and returns gate2 diffs.
  Timeout: 30 seconds → 503 SERVICE_UNAVAILABLE.

  The Integrity Engine is the single writer for sys-bound parameter changes.
  No partial writes: if gate2 diff fails, the transaction rolls back and
  state → CONTESTED.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func

from .base import BaseService
from ..core.exceptions import (
    NotFound, Forbidden, EngineTimeout
)
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Circle, Member
from ..models.governance import (
    STFInstance, STFAssignment, STFVerdict, Resolution, ResolutionGate2Diff
)
from ..models.types import STFType, STFState, ResolutionState
from ..schemas.stf import (
    CommissionSTFRequest, STFInstanceResponse, STFInstanceSummaryResponse,
    STFAssignmentResponse, VerdictAggregateResponse, VerdictRationaleResponse,
    EnactResolutionRequest, EnactResolutionResponse,
    BLIND_STF_TYPES,
)
from ..schemas.common import MemberRef, CircleRef, Paginated


class STFService(BaseService):

    # ── List / get ────────────────────────────────────────────────────────────

    async def list_stf_instances(
        self,
        org_id: uuid.UUID,
        stf_type: str | None,
        state: str | None,
        page: int,
        page_size: int,
    ) -> Paginated[STFInstanceSummaryResponse]:
        q = select(STFInstance).where(STFInstance.org_id == org_id)
        if stf_type:
            q = q.where(STFInstance.stf_type == stf_type)
        if state:
            q = q.where(STFInstance.state == state)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = await self.db.execute(
            q.order_by(STFInstance.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        instances = rows.scalars().all()

        # Assignment counts
        assignment_counts_result = await self.db.execute(
            select(STFAssignment.stf_instance_id, func.count(STFAssignment.id))
            .where(STFAssignment.stf_instance_id.in_([i.id for i in instances]))
            .group_by(STFAssignment.stf_instance_id)
        )
        assignment_counts = dict(assignment_counts_result.all())

        verdict_counts_result = await self.db.execute(
            select(STFVerdict.stf_instance_id, func.count(STFVerdict.id))
            .where(STFVerdict.stf_instance_id.in_([i.id for i in instances]))
            .group_by(STFVerdict.stf_instance_id)
        )
        verdict_counts = dict(verdict_counts_result.all())

        items = [
            STFInstanceSummaryResponse(
                id=inst.id,
                stf_type=inst.stf_type,
                state=inst.state,
                mandate_preview=inst.mandate[:200],
                deadline=inst.deadline,
                assignment_count=assignment_counts.get(inst.id, 0),
                verdicts_filed=verdict_counts.get(inst.id, 0),
                created_at=inst.created_at,
            )
            for inst in instances
        ]
        return Paginated(
            items=items, total=total, page=page, page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_stf(
        self, stf_id: uuid.UUID, org_id: uuid.UUID
    ) -> STFInstanceResponse:
        inst = await self._load_stf(stf_id, org_id)
        return await self._stf_to_response(inst)

    # ── Commission ────────────────────────────────────────────────────────────

    async def commission_stf(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: CommissionSTFRequest,
    ) -> STFInstanceResponse:
        # Verify commissioning circle
        circle = await self.get_by_id(Circle, body.commissioned_by_circle_id)
        if circle is None or circle.org_id != org_id:
            raise NotFound("Circle", str(body.commissioned_by_circle_id))

        inst = STFInstance(
            org_id=org_id,
            stf_type=body.stf_type,
            state=STFState.FORMING,
            mandate=body.mandate,
            commissioned_by_circle_id=body.commissioned_by_circle_id,
            motion_id=body.motion_id,
            resolution_id=body.resolution_id,
            subject_member_id=body.subject_member_id,
            deadline=body.deadline,
        )
        await self.save(inst)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.STF_COMMISSIONED,
                subject_id=inst.id,
                subject_type="stf_instance",
                payload={
                    "stf_type": body.stf_type.value,
                    "commissioned_by_circle_id": str(body.commissioned_by_circle_id),
                    "motion_id": str(body.motion_id) if body.motion_id else None,
                    "deadline": body.deadline.isoformat() if body.deadline else None,
                },
                triggered_by_member=member_id,
            ),
        )

        return await self._stf_to_response(inst)

    # ── Assignments ───────────────────────────────────────────────────────────

    async def get_assignments(
        self, stf_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[STFAssignmentResponse]:
        inst = await self._load_stf(stf_id, org_id)
        is_blind = STFType(inst.stf_type) in BLIND_STF_TYPES

        result = await self.db.execute(
            select(STFAssignment)
            .where(STFAssignment.stf_instance_id == stf_id)
            .order_by(STFAssignment.assigned_at.asc())
        )
        assignments = result.scalars().all()

        # Load members only for non-blind (xSTF)
        member_map: dict[uuid.UUID, Member] = {}
        if not is_blind:
            member_ids = [a.member_id for a in assignments]
            if member_ids:
                m_result = await self.db.execute(
                    select(Member).where(Member.id.in_(member_ids))
                )
                member_map = {m.id: m for m in m_result.scalars().all()}

        return [
            STFAssignmentResponse(
                id=a.id,
                stf_instance_id=a.stf_instance_id,
                stf_type=inst.stf_type,
                # member ABSENT for all blind types
                member=(
                    MemberRef(
                        id=member_map[a.member_id].id,
                        handle=member_map[a.member_id].handle,
                        display_name=member_map[a.member_id].display_name,
                    )
                    if not is_blind and a.member_id in member_map
                    else None
                ),
                slot_type=a.slot_type,
                assigned_at=a.assigned_at,
                rotation_end=a.rotation_end,
                verdict_filed_at=a.verdict_filed_at,
            )
            for a in assignments
        ]

    # ── Verdicts ──────────────────────────────────────────────────────────────

    async def get_verdicts(
        self, stf_id: uuid.UUID, org_id: uuid.UUID
    ) -> VerdictAggregateResponse:
        inst = await self._load_stf(stf_id, org_id)

        assignment_count = (await self.db.execute(
            select(func.count(STFAssignment.id)).where(
                STFAssignment.stf_instance_id == stf_id
            )
        )).scalar_one()

        verdict_agg_result = await self.db.execute(
            select(STFVerdict.verdict, func.count(STFVerdict.id))
            .where(STFVerdict.stf_instance_id == stf_id)
            .group_by(STFVerdict.verdict)
        )
        counts = {v: c for v, c in verdict_agg_result.all()}
        total_verdicts = sum(counts.values())

        majority = None
        if counts:
            majority_str = max(counts, key=lambda v: counts[v])
            from ..models.types import VerdictType
            try:
                majority = VerdictType(majority_str)
            except ValueError:
                pass

        return VerdictAggregateResponse(
            stf_instance_id=stf_id,
            stf_type=inst.stf_type,
            state=inst.state,
            total_assignments=assignment_count,
            verdicts_filed=total_verdicts,
            counts=counts,
            majority_verdict=majority,
            completed_at=inst.completed_at,
        )

    async def get_verdict_rationales(
        self, stf_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[VerdictRationaleResponse]:
        inst = await self._load_stf(stf_id, org_id)

        if inst.state != STFState.COMPLETED:
            raise Forbidden("RATIONALES_NOT_YET_AVAILABLE: STF must be completed")

        result = await self.db.execute(
            select(STFVerdict, STFAssignment.slot_type)
            .join(STFAssignment, STFVerdict.assignment_id == STFAssignment.id)
            .where(STFVerdict.stf_instance_id == stf_id)
        )
        rows = result.all()

        return [
            VerdictRationaleResponse(
                assignment_id=verdict.assignment_id,
                slot_type=slot_type,
                verdict=verdict.verdict,
                rationale=verdict.rationale,
                revision_directive=verdict.revision_directive,
                filed_at=verdict.filed_at,
            )
            for verdict, slot_type in rows
        ]

    # ── Enact resolution (synchronous) ────────────────────────────────────────

    async def enact_resolution(
        self,
        stf_id: uuid.UUID,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: EnactResolutionRequest,
    ) -> EnactResolutionResponse:
        """
        Synchronous Integrity Engine write via NATS request/reply.
        Timeout: 30 seconds → 503 if engine does not respond.

        The Integrity Engine receives the event, runs the atomic transaction,
        and publishes the result to the reply subject. We await that reply here.
        If NATS is unavailable or engine does not respond, returns CONTESTED
        with a clear reason — the resolution is NOT marked as enacted.
        """
        import json as _json
        from ..core.exceptions import EngineTimeout

        inst = await self._load_stf(stf_id, org_id)

        resolution = await self.db.execute(
            select(Resolution).where(Resolution.id == body.resolution_id)
        )
        res = resolution.scalar_one_or_none()
        if res is None:
            raise NotFound("Resolution", str(body.resolution_id))
        if res.org_id != org_id:
            raise Forbidden("RESOLUTION_ORG_MISMATCH")

        # Build event payload — org_id required by Integrity Engine
        event_payload = {
            "org_id": str(org_id),
            "stf_id": str(stf_id),
            "resolution_id": str(body.resolution_id),
        }

        bus = get_event_bus()
        engine_reply: dict | None = None

        if bus._connected and bus._nc is not None:
            # NATS request/reply — blocks until reply or timeout
            import json as json_mod
            try:
                msg = await bus._nc.request(
                    subject=f"ORG.{org_id}.events",
                    payload=json_mod.dumps({
                        "event_type": "resolution_enact_requested",
                        "org_id": str(org_id),
                        "resolution_id": str(body.resolution_id),
                        "stf_id": str(stf_id),
                        "triggered_by_member": str(member_id),
                        "payload": event_payload,
                    }, default=str).encode(),
                    timeout=30.0,
                )
                engine_reply = json_mod.loads(msg.data.decode())
            except Exception as e:
                # NATS unavailable or timeout
                return EnactResolutionResponse(
                    resolution_id=body.resolution_id,
                    resolution_ref=res.resolution_ref,
                    state="contested",
                    gate2_diffs=[],
                    enacted_at=None,
                    contested_reason=(
                        f"ENGINE_TIMEOUT: Integrity Engine did not respond within 30s. "
                        f"Error: {e}"
                    ),
                )
        else:
            # NATS not connected — emit fire-and-forget, return stub
            await get_event_bus().emit(
                org_id,
                GovernanceEvent(
                    event_type=EventType.RESOLUTION_ENACT_REQUESTED,
                    subject_id=body.resolution_id,
                    subject_type="resolution",
                    payload=event_payload,
                    triggered_by_member=member_id,
                ),
            )
            return EnactResolutionResponse(
                resolution_id=body.resolution_id,
                resolution_ref=res.resolution_ref,
                state="contested",
                gate2_diffs=[],
                enacted_at=None,
                contested_reason=(
                    "ENGINE_NOT_RUNNING: Integrity Engine is not connected. "
                    "Start the integrity service and retry."
                ),
            )

        # Parse engine reply
        status = engine_reply.get("status", "contested")
        if status == "enacted":
            import datetime as _dt
            return EnactResolutionResponse(
                resolution_id=body.resolution_id,
                resolution_ref=engine_reply.get("resolution_ref", res.resolution_ref),
                state=engine_reply.get("enacted_state", "enacted"),
                gate2_diffs=engine_reply.get("gate2_diffs", []),
                enacted_at=_dt.datetime.now(_dt.timezone.utc),
                contested_reason=None,
            )
        else:
            return EnactResolutionResponse(
                resolution_id=body.resolution_id,
                resolution_ref=engine_reply.get("resolution_ref", res.resolution_ref),
                state="contested",
                gate2_diffs=engine_reply.get("gate2_diffs", []),
                enacted_at=None,
                contested_reason=engine_reply.get("reason", "Engine returned contested"),
            )

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _load_stf(
        self, stf_id: uuid.UUID, org_id: uuid.UUID
    ) -> STFInstance:
        result = await self.db.execute(
            select(STFInstance).where(
                STFInstance.id == stf_id, STFInstance.org_id == org_id
            )
        )
        inst = result.scalar_one_or_none()
        if inst is None:
            raise NotFound("STF instance", str(stf_id))
        return inst

    async def _stf_to_response(self, inst: STFInstance) -> STFInstanceResponse:
        assignment_count = (await self.db.execute(
            select(func.count(STFAssignment.id)).where(
                STFAssignment.stf_instance_id == inst.id
            )
        )).scalar_one()

        verdict_count = (await self.db.execute(
            select(func.count(STFVerdict.id)).where(
                STFVerdict.stf_instance_id == inst.id
            )
        )).scalar_one()

        commissioned_by_circle = None
        if inst.commissioned_by_circle_id:
            circle = await self.get_by_id(Circle, inst.commissioned_by_circle_id)
            if circle:
                commissioned_by_circle = CircleRef(id=circle.id, name=circle.name)

        return STFInstanceResponse(
            id=inst.id,
            org_id=inst.org_id,
            stf_type=inst.stf_type,
            state=inst.state,
            mandate=inst.mandate,
            commissioned_by_circle=commissioned_by_circle,
            motion_id=inst.motion_id,
            resolution_id=inst.resolution_id,
            subject_member_id=inst.subject_member_id,
            deadline=inst.deadline,
            assignment_count=assignment_count,
            verdicts_filed=verdict_count,
            created_at=inst.created_at,
            completed_at=inst.completed_at,
        )
