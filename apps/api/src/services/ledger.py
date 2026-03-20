"""
Ledger service.

The ledger is append-only and written exclusively by the Integrity Engine.
The API exposes read-only views to all active members — this is the
transparency guarantee of PAAS.

Hash chain verification:
  walk all events for the org in chronological order,
  recompute each hash, compare to stored event_hash.
  Returns ok if all match, broken + first_broken_event_id if any mismatch.

Hash computation (mirrors Integrity Engine):
  SHA-256(prev_hash + event_id + event_type + subject_id + payload_json)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func

from .base import BaseService
from ..core.exceptions import NotFound
from ..models.governance import LedgerEvent, STFInstance, STFVerdict, STFAssignment
from ..schemas.ledger import (
    LedgerEventResponse, LedgerVerifyResponse,
    AuditReportResponse, AuditRationale,
)
from ..schemas.common import Paginated


class LedgerService(BaseService):

    # ── Event reads ───────────────────────────────────────────────────────────

    async def list_events(
        self,
        org_id: uuid.UUID,
        event_type: str | None,
        subject_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> Paginated[LedgerEventResponse]:
        q = select(LedgerEvent).where(LedgerEvent.org_id == org_id)
        if event_type:
            q = q.where(LedgerEvent.event_type == event_type)
        if subject_id:
            q = q.where(LedgerEvent.subject_id == subject_id)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = await self.db.execute(
            q.order_by(LedgerEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        events = rows.scalars().all()

        return Paginated(
            items=[self._event_to_response(e) for e in events],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_event(
        self, event_id: uuid.UUID, org_id: uuid.UUID
    ) -> LedgerEventResponse:
        result = await self.db.execute(
            select(LedgerEvent).where(
                LedgerEvent.id == event_id,
                LedgerEvent.org_id == org_id,
            )
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise NotFound("Ledger event", str(event_id))
        return self._event_to_response(event)

    # ── Hash chain verification ───────────────────────────────────────────────

    async def verify_chain(self, org_id: uuid.UUID) -> LedgerVerifyResponse:
        """
        Walk the full hash chain for this org and recompute all hashes.
        O(n) in the number of ledger events. Suitable for on-demand verification;
        for large orgs, a background periodic verify is preferred.
        """
        result = await self.db.execute(
            select(LedgerEvent)
            .where(LedgerEvent.org_id == org_id)
            .order_by(LedgerEvent.created_at.asc())
        )
        events = result.scalars().all()

        first_broken: uuid.UUID | None = None
        verified = 0

        for event in events:
            computed = self._compute_hash(
                prev_hash=event.prev_hash,
                event_id=str(event.id),
                event_type=event.event_type,
                subject_id=str(event.subject_id) if event.subject_id else "",
                payload=event.payload,
            )
            if computed != event.event_hash:
                first_broken = event.id
                break
            verified += 1

        return LedgerVerifyResponse(
            status="ok" if first_broken is None else "broken",
            verified_events=verified,
            first_broken_event_id=first_broken,
            verified_at=datetime.now(timezone.utc),
        )

    # ── Audit archive ─────────────────────────────────────────────────────────

    async def audit_archive(
        self,
        org_id: uuid.UUID,
        stf_type: str | None,
        page: int,
        page_size: int,
    ) -> Paginated[AuditReportResponse]:
        """
        Completed STF reports with verdict rationales.
        Attributed to slot_type only — reviewer identity never included.
        """
        from ..models.types import STFState
        q = select(STFInstance).where(
            STFInstance.org_id == org_id,
            STFInstance.state == STFState.COMPLETED,
        )
        if stf_type:
            q = q.where(STFInstance.stf_type == stf_type)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = await self.db.execute(
            q.order_by(STFInstance.completed_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        instances = rows.scalars().all()

        reports = []
        for inst in instances:
            verdicts_result = await self.db.execute(
                select(STFVerdict, STFAssignment.slot_type)
                .join(STFAssignment, STFVerdict.assignment_id == STFAssignment.id)
                .where(STFVerdict.stf_instance_id == inst.id)
            )
            verdict_rows = verdicts_result.all()

            # Compute majority
            from collections import Counter
            verdict_counts = Counter(v.verdict for v, _ in verdict_rows)
            majority = verdict_counts.most_common(1)[0][0] if verdict_counts else "unknown"

            # Look up the ledger event for this STF completion
            ledger_result = await self.db.execute(
                select(LedgerEvent).where(
                    LedgerEvent.org_id == org_id,
                    LedgerEvent.event_type == "stf_completed",
                    LedgerEvent.subject_id == inst.id,
                ).limit(1)
            )
            ledger_event = ledger_result.scalar_one_or_none()

            reports.append(
                AuditReportResponse(
                    stf_instance_id=inst.id,
                    stf_type=inst.stf_type,
                    mandate=inst.mandate,
                    commissioned_by_circle_id=inst.commissioned_by_circle_id,
                    motion_id=inst.motion_id,
                    resolution_id=inst.resolution_id,
                    majority_verdict=majority,
                    rationales=[
                        AuditRationale(
                            slot_type=slot_type,
                            verdict=verdict.verdict,
                            rationale=verdict.rationale,
                            revision_directive=verdict.revision_directive,
                        )
                        for verdict, slot_type in verdict_rows
                    ],
                    completed_at=inst.completed_at,
                    ledger_event_id=ledger_event.id if ledger_event else uuid.uuid4(),
                )
            )

        return Paginated(
            items=reports, total=total, page=page, page_size=page_size,
            has_next=(page * page_size) < total,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _event_to_response(self, event: LedgerEvent) -> LedgerEventResponse:
        return LedgerEventResponse(
            id=event.id,
            org_id=event.org_id,
            event_type=event.event_type,
            subject_id=event.subject_id,
            subject_type=event.subject_type,
            payload=event.payload,
            supersedes=event.supersedes,
            triggered_by_member=event.triggered_by_member,
            triggered_by_resolution=event.triggered_by_resolution,
            created_at=event.created_at,
            prev_hash=event.prev_hash,
            event_hash=event.event_hash,
        )

    @staticmethod
    def _compute_hash(
        prev_hash: str,
        event_id: str,
        event_type: str,
        subject_id: str,
        payload: dict,
    ) -> str:
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        data = f"{prev_hash}|{event_id}|{event_type}|{subject_id}|{payload_str}"
        return hashlib.sha256(data.encode()).hexdigest()
