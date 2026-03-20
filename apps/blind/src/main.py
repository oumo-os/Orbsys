"""
Blind Review API — completely isolated service on port 8001.

Design rules enforced here:
  1. ONLY accepts X-Isolated-View-Token — session JWTs are rejected with 403
  2. DB role orbsys_blind: SELECT on stf_assignments only, INSERT on stf_verdicts
  3. member_id is NEVER present in any response payload
  4. /docs and /redoc are disabled — this API is not browseable
  5. One verdict per assignment — 409 on duplicate

Token structure (isolated_view):
  { stf_instance_id, assignment_id, type: "isolated_view", exp }
  — issued by main API when a blind assignment is created
  — structurally incompatible with session tokens (type mismatch → 403)

Content returned:
  Only the Cell contributions and motion/directive text that the reviewer
  needs to form a judgment. No author names, no voter identities, no
  circle membership info.
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text

SECRET = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
DATABASE_URL = os.environ.get(
    "BLIND_DATABASE_URL",
    "postgresql+asyncpg://orbsys_blind:change_me@postgres:5432/orbsys",
)

# ── DB connection (blind role only) ───────────────────────────────────────────
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        async with session.begin():
            yield session


DB = Annotated[AsyncSession, Depends(get_db)]


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Orb Sys Blind Review API",
    version="0.1.0",
    docs_url=None,   # Never expose docs
    redoc_url=None,
    lifespan=lifespan,
)


# ── Token validation ──────────────────────────────────────────────────────────

class BlindCtx:
    def __init__(self, stf_instance_id: str, assignment_id: str):
        self.stf_instance_id = uuid.UUID(stf_instance_id)
        self.assignment_id = uuid.UUID(assignment_id)


def get_blind_ctx(
    x_isolated_view_token: Annotated[str | None, Header()] = None,
) -> BlindCtx:
    """
    Validates the isolated view token.
    Rejects session tokens (type != 'isolated_view') with 403.
    """
    if not x_isolated_view_token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "X-Isolated-View-Token required. Session tokens are not accepted here.",
        )
    try:
        payload = jwt.decode(x_isolated_view_token, SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "isolated_view":
            # Session token accidentally sent here — 403 not 401
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "TOKEN_TYPE_MISMATCH: session tokens are not valid for blind review endpoints",
            )
        return BlindCtx(payload["stf_instance_id"], payload["assignment_id"])
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired isolated view token")
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Malformed isolated view token")


BlindAuth = Annotated[BlindCtx, Depends(get_blind_ctx)]


# ── Schemas ───────────────────────────────────────────────────────────────────

class BlindContribution(BaseModel):
    """Contribution content stripped of all authorship."""
    id: uuid.UUID
    body: str
    contribution_type: str
    # author_id deliberately absent
    sequence: int
    created_at: datetime


class BlindMotionContent(BaseModel):
    """Motion/directive content for review. No filer identity."""
    motion_id: uuid.UUID
    motion_type: str
    directive_body: str | None
    commitments: list[str] | None
    ambiguities_flagged: list[str] | None
    specifications: list[dict] | None   # parameter + proposed_value + justification


class BlindReviewContent(BaseModel):
    """
    Everything the reviewer needs. Nothing that reveals identity.
    """
    stf_instance_id: uuid.UUID
    assignment_id: uuid.UUID
    stf_type: str
    mandate: str
    contributions: list[BlindContribution]
    motion: BlindMotionContent | None
    deadline: datetime | None
    # verdict_filed_at is present so reviewer knows if they already submitted
    verdict_filed_at: datetime | None


class FileVerdictRequest(BaseModel):
    verdict: str = Field(
        ...,
        pattern=r"^(approve|reject|revision_request|clear|concerns|violation|adequate|insufficient|finding_confirmed|finding_rejected)$",
    )
    rationale: str | None = Field(None, max_length=10000)
    revision_directive: str | None = Field(None, max_length=10000)
    checklist: dict | None = None


class VerdictConfirmation(BaseModel):
    verdict_id: uuid.UUID
    stf_instance_id: uuid.UUID
    assignment_id: uuid.UUID
    verdict: str
    filed_at: datetime


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/blind/{stf_id}/content", response_model=BlindReviewContent)
async def get_blind_content(stf_id: str, ctx: BlindAuth, db: DB):
    """
    Returns Cell contributions and motion content for this STF.
    All authorship information is stripped.
    Token must match the stf_instance_id in the path.
    """
    stf_uuid = _parse_uuid(stf_id)
    _assert_stf_match(ctx, stf_uuid)

    # Verify assignment exists and belongs to this STF
    assignment_row = await db.execute(
        text("""
            SELECT sa.id, sa.stf_instance_id, sa.member_id, sa.slot_type,
                   sa.assigned_at, sa.verdict_filed_at,
                   si.stf_type, si.mandate, si.deadline,
                   si.motion_id
            FROM stf_assignments sa
            JOIN stf_instances si ON si.id = sa.stf_instance_id
            WHERE sa.id = :assignment_id
              AND sa.stf_instance_id = :stf_id
        """),
        {"assignment_id": ctx.assignment_id, "stf_id": stf_uuid},
    )
    row = assignment_row.fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    # Verify stf_id in URL matches token
    if row.stf_instance_id != stf_uuid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token/URL mismatch")

    # Load contributions from the cell attached to the motion
    contributions = []
    motion_content = None

    if row.motion_id:
        motion_row = await db.execute(
            text("""
                SELECT m.id, m.motion_type, m.cell_id,
                       md.body as directive_body,
                       md.commitments, md.ambiguities_flagged
                FROM motions m
                LEFT JOIN motion_directives md ON md.motion_id = m.id
                WHERE m.id = :motion_id
            """),
            {"motion_id": row.motion_id},
        )
        motion = motion_row.fetchone()

        if motion:
            # Load specifications
            specs_result = await db.execute(
                text("""
                    SELECT parameter, new_value, justification
                    FROM motion_specifications
                    WHERE motion_id = :motion_id
                """),
                {"motion_id": row.motion_id},
            )
            specs = [
                {"parameter": s.parameter, "proposed_value": s.new_value,
                 "justification": s.justification}
                for s in specs_result.fetchall()
            ]

            motion_content = BlindMotionContent(
                motion_id=motion.id,
                motion_type=motion.motion_type,
                directive_body=motion.directive_body,
                commitments=motion.commitments,
                ambiguities_flagged=motion.ambiguities_flagged,
                specifications=specs if specs else None,
            )

            # Load contributions — stripped of all authorship
            contribs_result = await db.execute(
                text("""
                    SELECT id, body, contribution_type, created_at,
                           ROW_NUMBER() OVER (ORDER BY created_at ASC) as seq
                    FROM cell_contributions
                    WHERE cell_id = :cell_id
                    ORDER BY created_at ASC
                """),
                {"cell_id": motion.cell_id},
            )
            contributions = [
                BlindContribution(
                    id=c.id,
                    body=c.body,
                    contribution_type=c.contribution_type,
                    # author deliberately absent
                    sequence=c.seq,
                    created_at=c.created_at,
                )
                for c in contribs_result.fetchall()
            ]

    return BlindReviewContent(
        stf_instance_id=stf_uuid,
        assignment_id=ctx.assignment_id,
        stf_type=row.stf_type,
        mandate=row.mandate,
        contributions=contributions,
        motion=motion_content,
        deadline=row.deadline,
        verdict_filed_at=row.verdict_filed_at,
    )


@app.post("/blind/{stf_id}/verdicts", response_model=VerdictConfirmation, status_code=201)
async def file_verdict(
    stf_id: str, body: FileVerdictRequest, ctx: BlindAuth, db: DB
):
    """
    File verdict for this assignment.
    One verdict per assignment — 409 if already filed.
    reviewer_id is stored in stf_verdicts but NEVER returned.
    The DB role orbsys_blind has INSERT on stf_verdicts but no SELECT on members.
    """
    stf_uuid = _parse_uuid(stf_id)
    _assert_stf_match(ctx, stf_uuid)

    # Check assignment exists and hasn't already had verdict filed
    assignment_result = await db.execute(
        text("""
            SELECT id, member_id, verdict_filed_at
            FROM stf_assignments
            WHERE id = :assignment_id AND stf_instance_id = :stf_id
        """),
        {"assignment_id": ctx.assignment_id, "stf_id": stf_uuid},
    )
    assignment = assignment_result.fetchone()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    if assignment.verdict_filed_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "VERDICT_ALREADY_FILED: this assignment already has a verdict",
        )

    if body.verdict == "revision_request" and not body.revision_directive:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "revision_directive is required when verdict is revision_request",
        )

    now = datetime.now(timezone.utc)
    verdict_id = uuid.uuid4()

    # Insert verdict — orbsys_blind role has INSERT on stf_verdicts
    await db.execute(
        text("""
            INSERT INTO stf_verdicts
              (id, stf_instance_id, assignment_id, verdict, rationale,
               revision_directive, checklist, filed_at)
            VALUES
              (:id, :stf_id, :assignment_id, :verdict, :rationale,
               :revision_directive, :checklist::jsonb, :filed_at)
        """),
        {
            "id": verdict_id,
            "stf_id": stf_uuid,
            "assignment_id": ctx.assignment_id,
            "verdict": body.verdict,
            "rationale": body.rationale,
            "revision_directive": body.revision_directive,
            "checklist": __import__("json").dumps(body.checklist) if body.checklist else None,
            "filed_at": now,
        },
    )

    # Mark assignment as filed (UPDATE is permitted on stf_assignments for this field)
    await db.execute(
        text("""
            UPDATE stf_assignments
            SET verdict_filed_at = :filed_at
            WHERE id = :assignment_id
        """),
        {"filed_at": now, "assignment_id": ctx.assignment_id},
    )

    return VerdictConfirmation(
        verdict_id=verdict_id,
        stf_instance_id=stf_uuid,
        assignment_id=ctx.assignment_id,
        verdict=body.verdict,
        filed_at=now,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orbsys-blind"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid UUID: {value}")


def _assert_stf_match(ctx: BlindCtx, stf_uuid: uuid.UUID) -> None:
    if ctx.stf_instance_id != stf_uuid:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "TOKEN_STF_MISMATCH: token is not valid for this STF instance",
        )
