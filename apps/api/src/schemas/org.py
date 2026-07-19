from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .common import OrmBase, DormainRef
from ..models.types import DecayFn, MandateType


# ── Org ───────────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(
        ..., min_length=2, max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe identifier. Immutable after creation.",
    )
    purpose: str | None = Field(None, max_length=2000)


class OrgResponse(OrmBase):
    id: uuid.UUID
    name: str
    slug: str
    purpose: str | None
    founding_tenets: str | None
    commons_visibility: str
    bootstrapped_at: datetime | None
    created_at: datetime


class OrgSummaryResponse(OrmBase):
    """Minimal org info — used in member session and public listings."""
    id: uuid.UUID
    name: str
    slug: str
    bootstrapped_at: datetime | None


# ── Dormains ──────────────────────────────────────────────────────────────────

class CreateDormainRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    parent_id: uuid.UUID | None = None
    decay_fn: DecayFn = DecayFn.EXPONENTIAL
    decay_half_life_months: float = Field(12.0, ge=1.0, le=120.0)
    decay_floor_pct: float = Field(0.300, ge=0.0, le=1.0)


class DormainResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    decay_fn: DecayFn
    decay_half_life_months: float
    decay_floor_pct: float
    decay_config_resolution_id: uuid.UUID | None
    created_at: datetime


# ── Org parameters ────────────────────────────────────────────────────────────

class OrgParameterResponse(OrmBase):
    id: uuid.UUID
    parameter: str
    value: dict
    resolution_id: uuid.UUID | None
    applied_at: datetime


# ── Circles (creation — detail is in circles schema) ─────────────────────────

class CreateCircleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    tenets: str | None = Field(None, max_length=5000)
    dormain_assignments: list[CircleDormainAssignment] = Field(
        ..., min_length=1,
        description="At least one Dormain required at creation.",
    )


class CircleDormainAssignment(BaseModel):
    dormain_id: uuid.UUID
    mandate_type: MandateType = MandateType.PRIMARY


# Resolve forward ref
CreateCircleRequest.model_rebuild()
