"""
Insight Engine — the scribe.

Responsibilities:
  1. Notifications — write to DB via Integrity Engine event, enforce priority caps
  2. Crystallise drafts — analyse Cell contributions, produce structured motion draft
  3. Rolling minutes — extract key positions, open questions, consensus from Cell record
  4. Deadline monitoring — emit P1 events for approaching STF deadlines and vote closings

LLM integration:
  The LLM sub-process receives content STRIPPED of org_id before any external call.
  Backend is configurable: LLM_BACKEND=openai|anthropic|local
  Falls back to rule-based extraction if LLM unavailable (LLM_API_KEY not set).

Does NOT:
  - Recommend votes
  - Generate proactive drafts
  - Access blind-type Cell content (orbsys_insight role is blocked by RLS)
  - Write to DB directly (emits events → Integrity Engine writes)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import nats
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

log = logging.getLogger(__name__)

NATS_URL     = os.environ.get("NATS_URL",    "nats://localhost:4222")
DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql+asyncpg://orbsys_insight:change_me@localhost:5432/orbsys")
LLM_BACKEND  = os.environ.get("LLM_BACKEND", "local")
LLM_API_KEY  = os.environ.get("LLM_API_KEY", "")
LLM_MODEL    = os.environ.get("LLM_MODEL",   "gpt-4o")

# Notification caps (Insight Engine writes, not enforces — cap counting in DB)
P1_TYPES = {"stf_deadline_24h", "vote_closing_2h", "judicial_flag", "stf_assigned"}
P2_TYPES = {"cell_sponsorship", "slot_available", "revision_requested", "motion_filed_in_circle"}
P3_TYPES = {"curiosity_match", "circle_health_update", "ledger_verify_ok"}

DAILY_CAP  = 12
HOURLY_CAP = 3


def make_session_factory(db_url: str) -> async_sessionmaker:
    engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=3)
    return async_sessionmaker(engine, expire_on_commit=False)


# ── LLM client ────────────────────────────────────────────────────────────────

async def call_llm(prompt: str, system: str = "") -> str | None:
    """
    Call the configured LLM backend. Strips org_id from content before call.
    Returns None if LLM is unavailable — callers fall back to rule-based.
    """
    if not LLM_API_KEY or LLM_BACKEND == "local":
        return None

    try:
        if LLM_BACKEND == "openai":
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500,
                    }
                )
                data = res.json()
                return data["choices"][0]["message"]["content"]
        elif LLM_BACKEND == "anthropic":
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": LLM_MODEL,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1500,
                    }
                )
                data = res.json()
                return data["content"][0]["text"]
    except Exception as e:
        log.warning(f"[insight] LLM call failed: {e}")
    return None


# ── Contribution analysis (rule-based fallback) ───────────────────────────────

def analyse_contributions_local(
    contributions: list[dict],
) -> dict:
    """
    Rule-based contribution analysis when LLM is unavailable.
    Extracts key positions and open questions heuristically.
    """
    if not contributions:
        return {
            "key_positions": [],
            "open_questions": [],
            "emerging_consensus": [],
            "points_of_contention": [],
            "mandate_suggestion": "No contributions to analyse.",
        }

    texts = [c["body"] for c in contributions]
    combined = " ".join(texts)
    word_count = len(combined.split())

    # Simple keyword detection for questions
    questions = [
        s.strip() + "?"
        for c in contributions
        for s in c["body"].split("?")
        if len(s.strip()) > 20 and s.strip()
    ][:5]

    # Detect positions: sentences with "should", "must", "propose", "suggest"
    position_keywords = ["should", "must", "propose", "suggest", "recommend",
                        "need to", "argue", "believe", "think we"]
    positions = []
    for c in contributions[:10]:
        for sentence in c["body"].split("."):
            s = sentence.strip()
            if any(kw in s.lower() for kw in position_keywords) and len(s) > 30:
                author = c.get("author_handle", "A contributor")
                positions.append(f"@{author}: {s[:150]}")
                break

    # Mandate suggestion from first substantive contribution
    first_long = next(
        (c["body"] for c in contributions if len(c["body"]) > 80), None
    )
    mandate = (
        first_long[:300].rsplit(".", 1)[0] + "."
        if first_long
        else f"Cell deliberation with {len(contributions)} contributions ({word_count} words)."
    )

    return {
        "key_positions": positions[:4],
        "open_questions": questions[:3],
        "emerging_consensus": [],
        "points_of_contention": [],
        "mandate_suggestion": mandate,
    }


async def analyse_contributions_llm(
    contributions: list[dict],
    motion_type_hint: str = "non_system",
) -> dict | None:
    """LLM-based contribution analysis. Strips identifiers before call."""
    if not contributions:
        return None

    # Strip org/member IDs — only sequence numbers and content
    stripped = [
        {"seq": i + 1, "body": c["body"], "type": c.get("contribution_type", "discussion")}
        for i, c in enumerate(contributions)
    ]

    system = (
        "You are a governance scribe. Analyse a deliberation record and extract structure. "
        "Be concise and neutral. Do not recommend how to vote. "
        "Return valid JSON only — no markdown fences."
    )

    prompt = f"""
Analyse these {len(stripped)} deliberation contributions and return a JSON object with:
- "key_positions": list of up to 5 strings summarising distinct positions (attribute to seq numbers)
- "open_questions": list of up to 4 unresolved questions
- "emerging_consensus": list of points where contributors appear to agree
- "points_of_contention": list of clear disagreements
- "mandate_suggestion": one-paragraph directive for a {motion_type_hint} motion based on the deliberation

Contributions:
{json.dumps(stripped, indent=2)[:4000]}
"""

    result = await call_llm(prompt, system)
    if not result:
        return None
    try:
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        log.warning("[insight] LLM returned non-JSON response")
        return None


# ── Crystallise ───────────────────────────────────────────────────────────────

async def handle_crystallise(data: dict, db: AsyncSession, nc: Any) -> None:
    """
    Cell crystallise request. Analyse contributions, produce motion draft.
    Emits crystallise_draft_ready event with structured payload.
    The API's cells service picks this up via NATS reply.
    """
    cell_id_str = data.get("cell_id")
    org_id_str  = data.get("org_id")
    reply_to    = data.get("reply_to")  # NATS reply subject

    if not cell_id_str:
        return

    # Load contributions (RLS blocks blind cells — safe)
    contribs_result = await db.execute(text("""
        SELECT cc.body, cc.contribution_type,
               m.handle as author_handle, m.display_name
        FROM cell_contributions cc
        LEFT JOIN members m ON m.id = cc.author_id
        WHERE cc.cell_id = :cid
        ORDER BY cc.created_at ASC
    """), {"cid": uuid.UUID(cell_id_str)})
    rows = contribs_result.fetchall()
    contributions = [
        {"body": r[0], "contribution_type": r[1], "author_handle": r[2] or "unknown"}
        for r in rows
    ]

    motion_type_hint = data.get("motion_type_hint", "non_system")

    # Try LLM first, fall back to rule-based
    analysis = await analyse_contributions_llm(contributions, motion_type_hint)
    if analysis is None:
        analysis = analyse_contributions_local(contributions)

    draft = {
        "draft_id": str(uuid.uuid4()),
        "motion_type_suggested": motion_type_hint,
        "directive_draft": {
            "body": analysis.get("mandate_suggestion", ""),
            "commitments": [],
            "ambiguities_flagged": analysis.get("open_questions", []),
            "contributing_members": [],
        },
        "specification_drafts": None,
        "accountability_circles_suggested": None,
        "key_positions": analysis.get("key_positions", []),
        "points_of_contention": analysis.get("points_of_contention", []),
        "emerging_consensus": analysis.get("emerging_consensus", []),
        "contribution_count": len(contributions),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if reply_to and nc and nc.is_connected:
        try:
            await nc.publish(reply_to, json.dumps(draft, default=str).encode())
            log.info(f"[insight] crystallise draft sent for cell {cell_id_str}")
        except Exception as e:
            log.error(f"[insight] failed to send crystallise reply: {e}")


# ── Rolling minutes ────────────────────────────────────────────────────────────

async def handle_contribution_added(data: dict, db: AsyncSession) -> None:
    """
    New contribution → update rolling minutes snapshot in cell_composition_profiles.
    Keeps the latest structured summary available for the Cell UI.
    """
    cell_id_str = data.get("subject_id") or data.get("cell_id")
    org_id_str  = data.get("org_id")
    if not cell_id_str or not org_id_str:
        return

    cell_id = uuid.UUID(cell_id_str)

    contribs_result = await db.execute(text("""
        SELECT cc.body, cc.contribution_type,
               m.handle as author_handle
        FROM cell_contributions cc
        LEFT JOIN members m ON m.id = cc.author_id
        WHERE cc.cell_id = :cid
        ORDER BY cc.created_at ASC
    """), {"cid": cell_id})
    rows = contribs_result.fetchall()
    contributions = [
        {"body": r[0], "contribution_type": r[1], "author_handle": r[2] or "unknown"}
        for r in rows
    ]

    if not contributions:
        return

    # Rule-based analysis for minutes (LLM too expensive on every contribution)
    analysis = analyse_contributions_local(contributions)

    minutes = {
        "contribution_count": len(contributions),
        "key_positions": analysis["key_positions"],
        "open_questions": analysis["open_questions"],
        "emerging_consensus": analysis["emerging_consensus"],
        "points_of_contention": analysis["points_of_contention"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert into cell_composition_profiles (reusing for minutes storage)
    # In v1.1 a dedicated cell_minutes table would be cleaner
    await db.execute(text("""
        INSERT INTO cell_composition_profiles (id, cell_id, computed_at, profile)
        VALUES (:id, :cid, :now, :profile::jsonb)
        ON CONFLICT DO NOTHING
    """), {
        "id": uuid.uuid4(), "cid": cell_id,
        "now": datetime.now(timezone.utc),
        "profile": json.dumps({"minutes": minutes, "dormain_weights": {}}, default=str),
    })

    log.debug(f"[insight] minutes updated for cell {cell_id}")




async def handle_sponsor_draft(data: dict, db: AsyncSession, nc: Any) -> None:
    """
    Circle member clicked Sponsor — generate Cell founding mandate draft.
    Reads thread posts AT THIS MOMENT. Replies via NATS reply subject.
    """
    thread_id_str = data.get("thread_id")
    org_id_str    = data.get("org_id")
    reply_to      = data.get("reply_to")
    title         = data.get("title", "")

    if not thread_id_str:
        return

    # Load posts (strip member IDs for LLM)
    posts_result = await db.execute(text("""
        SELECT body, created_at FROM commons_posts
        WHERE thread_id = :tid
        ORDER BY created_at ASC
        LIMIT 25
    """), {"tid": uuid.UUID(thread_id_str)})
    posts = [{"body": r[0]} for r in posts_result.fetchall()]

    analysis = await analyse_contributions_llm(posts, "non_system")
    if analysis is None:
        analysis = analyse_contributions_local(posts)

    mandate = analysis.get("mandate_suggestion", "")
    if not mandate and title:
        mandate = f"Deliberation cell for: {title}"

    draft = {
        "draft_id": data.get("draft_id", str(uuid.uuid4())),
        "founding_mandate": mandate,
        "key_themes": analysis.get("key_positions", [])[:3],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if reply_to and nc and nc.is_connected:
        try:
            await nc.publish(reply_to, json.dumps(draft, default=str).encode())
        except Exception as e:
            log.error(f"[insight] failed to send sponsor draft reply: {e}")


# ── Notifications ─────────────────────────────────────────────────────────────

async def emit_notification(
    db: AsyncSession,
    nc: Any,
    org_id: uuid.UUID,
    member_id: uuid.UUID,
    priority: str,
    notification_type: str,
    body: str,
    subject_id: uuid.UUID | None = None,
    subject_type: str | None = None,
    action_url: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    """
    Enforce caps for P2/P3, then write notification via event.
    P1 always delivered. P2: 12/day, 3/hour cap.
    """
    now = datetime.now(timezone.utc)

    if priority == "p2":
        # Count P2 notifications in last hour and last day
        hour_ago = now - timedelta(hours=1)
        day_ago  = now - timedelta(days=1)

        hour_count = (await db.execute(text("""
            SELECT COUNT(*) FROM notifications
            WHERE member_id = :mid AND priority = 'p2'
              AND created_at > :since
        """), {"mid": member_id, "since": hour_ago})).scalar_one()

        if hour_count >= HOURLY_CAP:
            log.debug(f"[insight] P2 hourly cap hit for member {member_id}")
            return

        day_count = (await db.execute(text("""
            SELECT COUNT(*) FROM notifications
            WHERE member_id = :mid AND priority IN ('p1', 'p2')
              AND created_at > :since
        """), {"mid": member_id, "since": day_ago})).scalar_one()

        if day_count >= DAILY_CAP:
            log.debug(f"[insight] daily cap hit for member {member_id}")
            return

    elif priority == "p3":
        # P3: write to a digest bucket, not individual notifications
        # v1.0: skip P3 — they'll be added via a daily digest endpoint
        return

    # Write notification via event → Integrity Engine creates the DB row
    event = {
        "event_type": "notification_write_requested",
        "org_id": str(org_id),
        "member_id": str(member_id),
        "notification": {
            "id": str(uuid.uuid4()),
            "org_id": str(org_id),
            "member_id": str(member_id),
            "priority": priority,
            "notification_type": notification_type,
            "subject_id": str(subject_id) if subject_id else None,
            "subject_type": subject_type,
            "body": body,
            "action_url": action_url,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
    }

    if nc and nc.is_connected:
        try:
            js = nc.jetstream()
            await js.publish(
                f"ORG.{org_id}.events",
                json.dumps(event, default=str).encode(),
            )
        except Exception as e:
            log.error(f"[insight] failed to emit notification event: {e}")


async def handle_stf_formation(data: dict, db: AsyncSession, nc: Any) -> None:
    """
    STF assignments created → notify each assigned member (P1).
    """
    payload = data.get("payload", data)
    org_id_str = data.get("org_id")
    if not org_id_str:
        return

    org_id = uuid.UUID(org_id_str)
    stf_id_str = payload.get("stf_id") or data.get("subject_id")
    if not stf_id_str:
        return

    stf_id = uuid.UUID(stf_id_str)
    stf_type = payload.get("stf_type", "stf")

    # Load all assignments for this STF
    assignments = (await db.execute(text("""
        SELECT sa.member_id, si.stf_type, si.mandate
        FROM stf_assignments sa
        JOIN stf_instances si ON si.id = sa.stf_instance_id
        WHERE sa.stf_instance_id = :sid
    """), {"sid": stf_id})).fetchall()

    for member_id, assigned_type, mandate in assignments:
        body = (
            f"You have been assigned to a {assigned_type.upper()} panel. "
            f"Mandate: {mandate[:120]}{'…' if len(mandate) > 120 else ''}"
        )
        await emit_notification(
            db, nc, org_id, member_id,
            priority="p1",
            notification_type="stf_assigned",
            subject_id=stf_id,
            subject_type="stf_instance",
            body=body,
            action_url=f"/org/stf/{stf_id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        )


async def handle_motion_filed(data: dict, db: AsyncSession, nc: Any) -> None:
    """
    Motion filed → notify Circle members of the involved circles (P2).
    """
    org_id_str = data.get("org_id")
    motion_id_str = data.get("subject_id")
    if not org_id_str or not motion_id_str:
        return

    org_id   = uuid.UUID(org_id_str)
    motion_id = uuid.UUID(motion_id_str)
    payload  = data.get("payload", {})

    # Get invited circles from the cell
    cell_id = payload.get("cell_id")
    if not cell_id:
        return

    # Load circle members for invited circles
    members_result = await db.execute(text("""
        SELECT DISTINCT cm.member_id
        FROM cell_invited_circles cic
        JOIN circle_members cm ON cm.circle_id = cic.circle_id
        WHERE cic.cell_id = :cid AND cm.exited_at IS NULL
    """), {"cid": uuid.UUID(cell_id)})

    for (member_id,) in members_result.fetchall():
        await emit_notification(
            db, nc, org_id, member_id,
            priority="p2",
            notification_type="motion_filed_in_circle",
            subject_id=motion_id,
            subject_type="motion",
            body="A motion has been filed in a Circle you belong to — your vote carries weight.",
            action_url=f"/org/motions/{motion_id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


async def handle_stf_deadline(data: dict, db: AsyncSession, nc: Any) -> None:
    """P1 notification — STF deadline approaching <24h."""
    org_id_str = data.get("org_id")
    stf_id_str = data.get("stf_id") or data.get("subject_id")
    if not org_id_str or not stf_id_str:
        return

    org_id = uuid.UUID(org_id_str)
    stf_id = uuid.UUID(stf_id_str)

    members_result = await db.execute(text("""
        SELECT sa.member_id
        FROM stf_assignments sa
        WHERE sa.stf_instance_id = :sid AND sa.verdict_filed_at IS NULL
    """), {"sid": stf_id})

    for (member_id,) in members_result.fetchall():
        await emit_notification(
            db, nc, org_id, member_id,
            priority="p1",
            notification_type="stf_deadline_24h",
            subject_id=stf_id,
            subject_type="stf_instance",
            body="STF deadline in <24 hours — file your verdict.",
            action_url=f"/org/stf/{stf_id}",
        )


async def handle_revision_requested(data: dict, db: AsyncSession, nc: Any) -> None:
    """
    Gate 1 aSTF returned a revision_request → notify Cell initiating member (P2).
    """
    org_id_str  = data.get("org_id")
    motion_id_str = data.get("subject_id")
    if not org_id_str or not motion_id_str:
        return

    org_id    = uuid.UUID(org_id_str)
    motion_id = uuid.UUID(motion_id_str)

    motion_row = (await db.execute(text("""
        SELECT m.filed_by, c.initiating_member_id
        FROM motions m
        JOIN cells c ON c.id = m.cell_id
        WHERE m.id = :mid
    """), {"mid": motion_id})).fetchone()

    if not motion_row:
        return

    member_id = motion_row[1] or motion_row[0]  # initiator or filer
    directive = data.get("payload", {}).get("revision_directive", "")[:200]

    await emit_notification(
        db, nc, org_id, member_id,
        priority="p2",
        notification_type="revision_requested",
        subject_id=motion_id,
        subject_type="motion",
        body=f"Gate 1 review returned a revision request. {directive}",
        action_url=f"/org/cells/{motion_id}",  # link to cell
    )


# ── Deadline monitoring ───────────────────────────────────────────────────────

async def check_stf_deadlines(sf: async_sessionmaker, nc: Any) -> None:
    """
    Periodic task: find STFs with deadlines in <24h and emit deadline events.
    Runs every 30 minutes.
    """
    cutoff = datetime.now(timezone.utc) + timedelta(hours=24)
    now = datetime.now(timezone.utc)

    async with sf() as db:
        result = await db.execute(text("""
            SELECT si.id, si.org_id
            FROM stf_instances si
            WHERE si.state IN ('active', 'deliberating')
              AND si.deadline IS NOT NULL
              AND si.deadline <= :cutoff
              AND si.deadline > :now
        """), {"cutoff": cutoff, "now": now})

        for stf_id, org_id in result.fetchall():
            data = {"org_id": str(org_id), "stf_id": str(stf_id)}
            await handle_stf_deadline(data, db, nc)


# ── Notification write handler (for Integrity Engine) ────────────────────────
# This event is emitted by Insight Engine and consumed by Integrity Engine.
# Integrity Engine needs to handle "notification_write_requested" to INSERT the row.
# We add a handler note here — the actual DB write is in integrity/src/main.py.


# ── Event routing ─────────────────────────────────────────────────────────────

async def dispatch(data: dict, sf: async_sessionmaker, nc: Any) -> None:
    etype = data.get("event_type", "")

    async with sf() as db:
        try:
            if etype == "sponsor_draft_requested":
                await handle_sponsor_draft(data, db, nc)

            elif etype == "cell_crystallise_requested":
                await handle_crystallise(data, db, nc)

            elif etype == "cell_contribution_added":
                await handle_contribution_added(data, db)

            elif etype == "stf_assignment_created":
                await handle_stf_formation(data, db, nc)

            elif etype == "motion_filed":
                await handle_motion_filed(data, db, nc)

            elif etype == "motion_revision_requested":
                await handle_revision_requested(data, db, nc)

            elif etype == "stf_deadline_approaching":
                await handle_stf_deadline(data, db, nc)

        except Exception as e:
            log.error(f"[insight] error handling {etype}: {e}", exc_info=True)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    sf = make_session_factory(DATABASE_URL)

    nc = None
    for attempt in range(1, 6):
        try:
            nc = await nats.connect(
                NATS_URL, name="orbsys-insight",
                reconnect_time_wait=2, max_reconnect_attempts=10,
            )
            log.info(f"[insight] connected to NATS {NATS_URL}")
            break
        except Exception as e:
            log.warning(f"[insight] NATS connect attempt {attempt}/5: {e}")
            if attempt < 5:
                await asyncio.sleep(2 ** attempt)
            else:
                log.error("[insight] cannot connect — exiting")
                return

    js = nc.jetstream()

    HANDLED_EVENTS = {
        "sponsor_draft_requested",
        "cell_crystallise_requested", "cell_contribution_added",
        "stf_assignment_created", "motion_filed",
        "motion_revision_requested", "stf_deadline_approaching",
    }

    async def handle_msg(msg):
        try:
            data = json.loads(msg.data.decode())
        except json.JSONDecodeError as e:
            log.error(f"[insight] bad JSON: {e}")
            await msg.ack()
            return

        if data.get("event_type") in HANDLED_EVENTS:
            await dispatch(data, sf, nc)
        await msg.ack()

    await js.subscribe("ORG.*.events", durable="insight.consumer", cb=handle_msg)
    log.info("[insight] Insight Engine running")

    # Background deadline monitor
    async def deadline_monitor():
        while True:
            await asyncio.sleep(1800)  # every 30 minutes
            try:
                await check_stf_deadlines(sf, nc)
            except Exception as e:
                log.error(f"[insight] deadline monitor error: {e}")

    asyncio.create_task(deadline_monitor())

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
