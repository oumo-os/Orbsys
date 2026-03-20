"""
Motions service.

Motion lifecycle is mostly driven by events from STF verdicts (handled
by the Integrity Engine) — the API surface here is read-heavy.

The one write path is validate-specification: a synchronous dry-run
that checks parameter ranges without persisting anything or emitting events.

Known sys-bound parameters and their validation rules are defined in
SYSTEM_PARAMETERS below. This list grows as org parameters are formalised.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseService
from ..core.exceptions import NotFound
from ..models.org import Member, Circle, Dormain
from ..models.governance import Motion, MotionDirective, MotionSpecification, Resolution
from ..models.types import MotionType, PreValidationStatus
from ..schemas.motions import (
    MotionResponse, MotionDirectiveResponse, MotionSpecificationResponse,
    ResolutionResponse, Gate2DiffEntry,
    ValidateSpecificationRequest, ValidateSpecificationResponse,
    SpecificationValidationResult,
)
from ..schemas.common import MemberRef, CircleRef


# ── Known sys-bound parameters ────────────────────────────────────────────────
# parameter → (type, min, max) — extend as org parameters are formalised.

SYSTEM_PARAMETERS: dict[str, dict] = {
    "decay_half_life_months":     {"type": float, "min": 1.0,  "max": 120.0},
    "decay_floor_pct":            {"type": float, "min": 0.0,  "max": 1.0},
    "c_max":                      {"type": float, "min": 10.0, "max": 500.0},
    "t_audit":                    {"type": float, "min": 10.0, "max": 200.0},
    "volatility_k_new":           {"type": int,   "min": 10,   "max": 120},
    "volatility_k_established":   {"type": int,   "min": 10,   "max": 120},
    "volatility_k_veteran":       {"type": int,   "min": 5,    "max": 60},
    "stf_min_size":               {"type": int,   "min": 3,    "max": 21},
    "stf_max_size":               {"type": int,   "min": 3,    "max": 21},
    "quorum_pct":                 {"type": float, "min": 0.1,  "max": 1.0},
    "pass_threshold_pct":         {"type": float, "min": 0.5,  "max": 1.0},
    "commons_visibility":         {"type": str,   "values": ["members_only", "public", "circle_only"]},
}


class MotionsService(BaseService):

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_motion(
        self, motion_id: uuid.UUID, org_id: uuid.UUID
    ) -> MotionResponse:
        result = await self.db.execute(
            select(Motion)
            .where(Motion.id == motion_id, Motion.org_id == org_id)
            .options(
                selectinload(Motion.directive),
                selectinload(Motion.specifications),
                selectinload(Motion.resolution).selectinload(Resolution.gate2_diffs),
            )
        )
        motion = result.scalar_one_or_none()
        if motion is None:
            raise NotFound("Motion", str(motion_id))

        return await self._motion_to_response(motion)

    # ── Specification dry-run validation ──────────────────────────────────────

    async def validate_specification(
        self,
        motion_id: uuid.UUID,
        org_id: uuid.UUID,
        body: ValidateSpecificationRequest,
    ) -> ValidateSpecificationResponse:
        """
        Synchronous dry-run. No event emitted. No state change.
        Looks up the motion to confirm org scope, then validates the parameter.
        """
        motion = await self.get_by_id(Motion, motion_id)
        if motion is None or motion.org_id != org_id:
            raise NotFound("Motion", str(motion_id))

        result = self._validate_one(body.parameter, body.new_value, body.justification)

        return ValidateSpecificationResponse(
            motion_id=motion_id,
            results=[result],
            all_valid=result.status == PreValidationStatus.VALID,
        )

    def _validate_one(
        self,
        parameter: str,
        new_value: object,
        justification: str,
    ) -> SpecificationValidationResult:
        # Load current org parameter value — stub (real: query OrgParameter table)
        current_value = None

        if parameter not in SYSTEM_PARAMETERS:
            return SpecificationValidationResult(
                parameter=parameter,
                status=PreValidationStatus.INVALID_PARAMETER,
                current_value=current_value,
                proposed_value=new_value,
                validation_message=f"Unknown system parameter '{parameter}'",
                valid_range=None,
            )

        rule = SYSTEM_PARAMETERS[parameter]
        msg: str | None = None
        status = PreValidationStatus.VALID

        try:
            if rule["type"] == float:
                v = float(new_value)  # type: ignore[arg-type]
                lo, hi = rule["min"], rule["max"]
                if not (lo <= v <= hi):
                    status = PreValidationStatus.INVALID_RANGE
                    msg = f"Must be between {lo} and {hi}; got {v}"
                valid_range = f"{lo}–{hi}"

            elif rule["type"] == int:
                v = int(new_value)  # type: ignore[arg-type]
                lo, hi = rule["min"], rule["max"]
                if not (lo <= v <= hi):
                    status = PreValidationStatus.INVALID_RANGE
                    msg = f"Must be between {lo} and {hi}; got {v}"
                valid_range = f"{lo}–{hi}"

            elif rule["type"] == str:
                v = str(new_value)
                allowed = rule["values"]
                if v not in allowed:
                    status = PreValidationStatus.INVALID_PARAMETER
                    msg = f"Must be one of: {', '.join(allowed)}"
                valid_range = ", ".join(allowed)

            else:
                valid_range = None

        except (TypeError, ValueError):
            status = PreValidationStatus.INVALID_PARAMETER
            msg = f"Cannot convert value to {rule['type'].__name__}"
            valid_range = None

        if status == PreValidationStatus.VALID and len(justification.strip()) < 20:
            status = PreValidationStatus.MISSING_JUSTIFICATION
            msg = "Justification must be at least 20 characters"

        return SpecificationValidationResult(
            parameter=parameter,
            status=status,
            current_value=current_value,
            proposed_value=new_value,
            validation_message=msg,
            valid_range=valid_range if "valid_range" in dir() else None,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _motion_to_response(self, motion: Motion) -> MotionResponse:
        filer = await self.get_by_id(Member, motion.filed_by)

        directive = None
        if motion.directive:
            directive = MotionDirectiveResponse(
                body=motion.directive.body,
                commitments=motion.directive.commitments,
                ambiguities_flagged=motion.directive.ambiguities_flagged,
            )

        specs = [
            MotionSpecificationResponse(
                id=s.id,
                parameter=s.parameter,
                new_value=s.new_value,
                justification=s.justification,
                pre_validation_status=s.pre_validation_status,
                pre_validated_at=s.pre_validated_at,
            )
            for s in (motion.specifications or [])
        ]

        resolution = None
        implementing_circles = None
        implementing_circle_ids = None

        if motion.resolution:
            res = motion.resolution
            implementing_circle_ids = res.implementing_circle_ids

            if implementing_circle_ids:
                c_result = await self.db.execute(
                    select(Circle).where(Circle.id.in_(implementing_circle_ids))
                )
                implementing_circles = [
                    CircleRef(id=c.id, name=c.name)
                    for c in c_result.scalars().all()
                ]

            diffs = [
                Gate2DiffEntry(
                    parameter=d.parameter,
                    specified_value=d.specified_value,
                    applied_value=d.applied_value,
                    match=d.match,
                    checked_at=d.checked_at,
                )
                for d in (res.gate2_diffs or [])
            ]

            resolution = ResolutionResponse(
                id=res.id,
                resolution_ref=res.resolution_ref,
                state=res.state,
                implementation_type=res.implementation_type,
                gate2_agent=res.gate2_agent,
                implementing_circles=implementing_circles,
                gate2_diffs=diffs,
                enacted_at=res.enacted_at,
                created_at=res.created_at,
            )

        return MotionResponse(
            id=motion.id,
            org_id=motion.org_id,
            cell_id=motion.cell_id,
            motion_type=motion.motion_type,
            state=motion.state,
            filed_by=MemberRef(
                id=filer.id, handle=filer.handle, display_name=filer.display_name
            ) if filer else None,
            directive=directive,
            specifications=specs,
            implementing_circle_ids=implementing_circle_ids,
            implementing_circles=implementing_circles,
            resolution=resolution,
            created_at=motion.created_at,
            crystallised_at=motion.crystallised_at,
            state_changed_at=motion.state_changed_at,
        )
