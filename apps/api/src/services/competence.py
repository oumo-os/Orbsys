"""
Competence service.

W_s (Soft Competence) is written exclusively by the Integrity Engine
via the ΔC formula. The API here is read-only for W_s.

W_h (Hard Competence) claims are written here, then a vSTF is commissioned
(via event) to verify the credential. The claim is wh_preliminary until the
vSTF verdict upgrades it to wh_verified.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from .base import BaseService
from ..core.exceptions import NotFound, AlreadyExists
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..models.org import Member, Dormain
from ..models.competence import CompetenceScore, WhCredential, DeltaCEvent
from ..schemas.competence import (
    CompetenceScoreResponse, CompetenceScoresResponse,
    DormainLeaderboardResponse, LeaderboardEntryResponse,
    SubmitWhClaimRequest, WhClaimResponse,
    DormainListResponse, DeltaCEventResponse,
)
from ..schemas.common import MemberRef, DormainRef


class CompetenceService(BaseService):

    # ── Scores ────────────────────────────────────────────────────────────────

    async def my_scores(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> CompetenceScoresResponse:
        result = await self.db.execute(
            select(CompetenceScore, Dormain.name)
            .join(Dormain, CompetenceScore.dormain_id == Dormain.id)
            .where(
                CompetenceScore.member_id == member_id,
                Dormain.org_id == org_id,
            )
            .order_by(CompetenceScore.w_s.desc())
        )
        rows = result.all()

        return CompetenceScoresResponse(
            member_id=member_id,
            scores=[
                CompetenceScoreResponse(
                    dormain_id=score.dormain_id,
                    dormain_name=name,
                    w_s=float(score.w_s),
                    w_s_peak=float(score.w_s_peak),
                    w_h=float(score.w_h),
                    volatility_k=score.volatility_k,
                    proof_count=score.proof_count,
                    last_activity_at=score.last_activity_at,
                    mcmp_status=score.mcmp_status,
                    updated_at=score.updated_at,
                )
                for score, name in rows
            ],
        )

    async def dormain_leaderboard(
        self,
        dormain_id: uuid.UUID,
        org_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> DormainLeaderboardResponse:
        # Verify dormain exists in org
        dormain_result = await self.db.execute(
            select(Dormain).where(Dormain.id == dormain_id, Dormain.org_id == org_id)
        )
        dormain = dormain_result.scalar_one_or_none()
        if dormain is None:
            raise NotFound("Dormain", str(dormain_id))

        total_result = await self.db.execute(
            select(func.count(CompetenceScore.id)).where(
                CompetenceScore.dormain_id == dormain_id,
                CompetenceScore.w_s > 0,
            )
        )
        total = total_result.scalar_one()

        scores_result = await self.db.execute(
            select(CompetenceScore, Member)
            .join(Member, CompetenceScore.member_id == Member.id)
            .where(
                CompetenceScore.dormain_id == dormain_id,
                CompetenceScore.w_s > 0,
                Member.org_id == org_id,
            )
            .order_by(CompetenceScore.w_s.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = scores_result.all()

        entries = [
            LeaderboardEntryResponse(
                rank=(page - 1) * page_size + idx + 1,
                member=MemberRef(
                    id=member.id,
                    handle=member.handle,
                    display_name=member.display_name,
                ),
                w_s=float(score.w_s),
                w_s_peak=float(score.w_s_peak),
                last_activity_at=score.last_activity_at,
            )
            for idx, (score, member) in enumerate(rows)
        ]

        return DormainLeaderboardResponse(
            dormain=DormainRef(id=dormain.id, name=dormain.name),
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def list_dormains(self, org_id: uuid.UUID) -> list[DormainListResponse]:
        result = await self.db.execute(
            select(Dormain)
            .where(Dormain.org_id == org_id)
            .order_by(Dormain.name)
        )
        return [
            DormainListResponse(
                id=d.id,
                org_id=d.org_id,
                name=d.name,
                description=d.description,
                decay_fn=d.decay_fn.value,
                decay_half_life_months=float(d.decay_half_life_months),
                decay_floor_pct=float(d.decay_floor_pct),
                created_at=d.created_at,
            )
            for d in result.scalars().all()
        ]

    # ── W_h claims ────────────────────────────────────────────────────────────

    async def submit_wh_claim(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        body: SubmitWhClaimRequest,
    ) -> WhClaimResponse:
        """
        Submit a Hard Competence credential claim.
        Stored as wh_preliminary. Emits WH_CLAIM_SUBMITTED → Inferential Engine
        commissions a vSTF to verify the credential.
        """
        # Verify dormain is in this org
        dormain_result = await self.db.execute(
            select(Dormain).where(
                Dormain.id == body.dormain_id, Dormain.org_id == org_id
            )
        )
        dormain = dormain_result.scalar_one_or_none()
        if dormain is None:
            raise NotFound("Dormain", str(body.dormain_id))

        # One pending claim per (member, dormain, credential_type) at a time
        existing_result = await self.db.execute(
            select(WhCredential).where(
                WhCredential.member_id == member_id,
                WhCredential.dormain_id == body.dormain_id,
                WhCredential.credential_type == body.credential_type,
                WhCredential.status == "wh_preliminary",
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise AlreadyExists(
                "W_h claim",
                "member+dormain+credential_type",
                f"{member_id}+{body.dormain_id}+{body.credential_type.value}",
            )

        now = datetime.now(timezone.utc)
        credential = WhCredential(
            member_id=member_id,
            dormain_id=body.dormain_id,
            credential_type=body.credential_type,
            value_wh=body.claimed_value_wh,
            vdc_reference=body.vdc_reference,
            verified_at=now,  # preliminary — vSTF will update
            status="wh_preliminary",
        )
        await self.save(credential)

        await get_event_bus().emit(
            org_id,
            GovernanceEvent(
                event_type=EventType.WH_CLAIM_SUBMITTED,
                subject_id=credential.id,
                subject_type="wh_credential",
                payload={
                    "dormain_id": str(body.dormain_id),
                    "credential_type": body.credential_type.value,
                    "claimed_value_wh": body.claimed_value_wh,
                    "vdc_reference": body.vdc_reference,
                },
                triggered_by_member=member_id,
            ),
        )

        return WhClaimResponse(
            id=credential.id,
            dormain_id=credential.dormain_id,
            dormain_name=dormain.name,
            credential_type=credential.credential_type,
            claimed_value_wh=float(credential.value_wh),
            vdc_reference=credential.vdc_reference,
            status=credential.status,
            vstf_id=credential.vstf_id,
            verified_at=credential.verified_at,
            expires_at=credential.expires_at,
        )

    async def my_wh_claims(
        self, member_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[WhClaimResponse]:
        result = await self.db.execute(
            select(WhCredential, Dormain.name)
            .join(Dormain, WhCredential.dormain_id == Dormain.id)
            .where(
                WhCredential.member_id == member_id,
                Dormain.org_id == org_id,
            )
            .order_by(WhCredential.verified_at.desc())
        )
        return [
            WhClaimResponse(
                id=cred.id,
                dormain_id=cred.dormain_id,
                dormain_name=name,
                credential_type=cred.credential_type,
                claimed_value_wh=float(cred.value_wh),
                vdc_reference=cred.vdc_reference,
                status=cred.status,
                vstf_id=cred.vstf_id,
                verified_at=cred.verified_at,
                expires_at=cred.expires_at,
            )
            for cred, name in result.all()
        ]
