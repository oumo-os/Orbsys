import enum
import uuid
from sqlalchemy import DateTime, func
from sqlalchemy.orm import mapped_column, MappedColumn
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class MemberState(str, enum.Enum):
    PROBATIONARY = "probationary"
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    SUSPENDED = "suspended"
    EXITED = "exited"


class ExitReason(str, enum.Enum):
    RESIGNED = "resigned"
    FORFEITURE = "forfeiture"
    COMPETENCE_DRIFT = "competence_drift"
    CREDENTIAL_LAPSE = "credential_lapse"
    ROTATION_END = "rotation_end"
    AUDIT_REMOVAL = "audit_removal"
    TRANSFER = "transfer"
    CIRCLE_RESHUFFLE = "circle_reshuffle"
    CIRCLE_DISSOLUTION = "circle_dissolution"
    JUDICIAL_PENALTY = "judicial_penalty"
    ORG_EXPULSION = "org_expulsion"


class MandateType(str, enum.Enum):
    PRIMARY = "primary"      # M multiplier = 1.6
    SECONDARY = "secondary"  # M multiplier = 1.2


class DecayFn(str, enum.Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    STEP = "step"


class CellType(str, enum.Enum):
    DELIBERATION = "deliberation"
    CLOSED_CIRCLE = "closed_circle"
    MOTION_REVIEW = "motion_review"
    STF_WORKSPACE = "stf_workspace"
    PERIODIC_AUDIT = "periodic_audit"


class CellState(str, enum.Enum):
    ACTIVE = "active"
    TEMPORARILY_CLOSED = "temporarily_closed"
    REACTIVATED = "reactivated"
    ARCHIVED = "archived"
    DISSOLVED = "dissolved"
    FROZEN = "frozen"
    SUSPENDED = "suspended"


class CellVisibility(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class ContributionType(str, enum.Enum):
    DISCUSSION = "discussion"
    COMMONS_CONTEXT_IMPORT = "commons_context_import"
    REVISION_DIRECTIVE_RESPONSE = "revision_directive_response"
    EVIDENCE_ATTACHMENT = "evidence_attachment"


class TagSource(str, enum.Enum):
    AUTHOR = "author"
    INFERENTIAL_ENGINE = "inferential_engine"
    HUMAN_CORRECTION = "human_correction"


class FreezeReason(str, enum.Enum):
    CONDUCT = "conduct"
    JUDICIAL = "judicial"
    POLICY = "policy"


class MotionType(str, enum.Enum):
    SYS_BOUND = "sys_bound"
    NON_SYSTEM = "non_system"
    HYBRID = "hybrid"


class MotionState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    VOTED = "voted"
    GATE1_PENDING = "gate1_pending"
    GATE1_APPROVED = "gate1_approved"
    GATE1_REJECTED = "gate1_rejected"
    REVISION_REQUESTED = "revision_requested"
    PENDING_IMPLEMENTATION = "pending_implementation"
    GATE2_PENDING = "gate2_pending"
    ENACTED = "enacted"
    ENACTED_LOCKED = "enacted_locked"
    CONTESTED = "contested"
    DEVIATED_JUSTIFIED = "deviated_justified"
    ABANDONED = "abandoned"


class ResolutionState(str, enum.Enum):
    PENDING_IMPLEMENTATION = "pending_implementation"
    GATE2_PENDING = "gate2_pending"
    ENACTED = "enacted"
    ENACTED_LOCKED = "enacted_locked"
    CONTESTED = "contested"
    DEVIATED_JUSTIFIED = "deviated_justified"
    DEVIATED_UNJUSTIFIED = "deviated_unjustified"


class ImplementationType(str, enum.Enum):
    SYS_PARAMETER = "sys_parameter"
    IDENTITY_CHANGE = "identity_change"
    COMPETENCE_ADJUSTMENT = "competence_adjustment"
    DISCIPLINARY = "disciplinary"
    ORG_BOUND = "org_bound"


class Gate2Agent(str, enum.Enum):
    ASTF_DIFF = "astf_diff"
    ASTF_INTERPRETIVE = "astf_interpretive"
    VSTF = "vstf"
    JSTF = "jstf"


class STFType(str, enum.Enum):
    XSTF = "xstf"
    ASTF_MOTION = "astf_motion"
    ASTF_PERIODIC = "astf_periodic"
    VSTF = "vstf"
    JSTF = "jstf"
    META_ASTF = "meta_astf"


class STFState(str, enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    ALL_FILED = "all_filed"
    COMPLETED = "completed"
    DISSOLVED = "dissolved"


class VerdictType(str, enum.Enum):
    # aSTF motion
    APPROVE = "approve"
    REJECT = "reject"
    REVISION_REQUEST = "revision_request"
    # periodic aSTF
    CLEAR = "clear"
    CONCERNS = "concerns"
    VIOLATION = "violation"
    # vSTF
    ADEQUATE = "adequate"
    INSUFFICIENT = "insufficient"
    # jSTF / meta
    FINDING_CONFIRMED = "finding_confirmed"
    FINDING_REJECTED = "finding_rejected"


class UnsealingCondition(str, enum.Enum):
    MALPRACTICE_FINDING = "malpractice_finding"
    JUDICIAL_PENALTY = "judicial_penalty"


class ActivityType(str, enum.Enum):
    COMMONS_FORMAL_REVIEW = "commons_formal_review"           # G = 0.5
    CELL_CONTRIBUTION_REVIEW = "cell_contribution_review"     # G = 1.0
    MOTION_DELIBERATION_REVIEW = "motion_deliberation_review" # G = 1.0
    AUDIT_FORMAL_TEST = "audit_formal_test"                   # G = 1.2
    VSTF_CREDENTIAL_AUDIT = "vstf_credential_audit"           # G = 1.2
    ASTF_PERIOD_REVIEW = "astf_period_review"                 # G = 1.2
    BASELINE_RATIFICATION = "baseline_ratification"           # G = 1.0, bootstrap only


class McmpStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"


class CredentialType(str, enum.Enum):
    DEGREE = "degree"
    CERTIFICATION = "certification"
    PATENT = "patent"
    LICENSE = "license"
    VERIFIED_EXTERNAL_CONTRIBUTION = "verified_external_contribution"


class PreValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID_RANGE = "invalid_range"
    INVALID_PARAMETER = "invalid_parameter"
    MISSING_JUSTIFICATION = "missing_justification"


# ── Column helpers ────────────────────────────────────────────────────────────

def uuid_pk() -> MappedColumn:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_col() -> MappedColumn:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def updated_at_col() -> MappedColumn:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
