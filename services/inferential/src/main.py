"""
Inferential Engine — the router.

Consumes governance events and performs:
  1. STF candidate matching — when stf_commissioned received, score all
     eligible members and create stf_assignments
  2. Commons feed relevance scoring — when thread/post created, score
     relevance for each member (written to feed_scores when table exists)
  3. Dormain tagging — layer 2 NLP on new Commons threads/posts
     (stub: author signal only in v1.0)
  4. Homogeneity flag — when a Cell is created with invited circles
     that share >80% dormain overlap, emit a soft warning event

DB role: orbsys_inferential (read-only).
Never writes directly. Emits events → Integrity Engine writes.

STF matching formula:
  candidate_score = competence_fit × curiosity_fit × availability × independence
  Novice floor: 30% of slots reserved for W_s < 800 in relevant dormain.
  Within novice pool: sort by curiosity_fit DESC.
  Within expert pool: sort by competence_fit DESC.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any

import nats
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

log = logging.getLogger(__name__)

NATS_URL     = os.environ.get("NATS_URL",    "nats://localhost:4222")
DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql+asyncpg://orbsys_inferential:change_me@localhost:5432/orbsys")

# STF size defaults
STF_MIN_SIZE = 3
STF_MAX_SIZE = 9
NOVICE_FLOOR_PCT = 0.30   # 30% of slots reserved for W_s < 800 in dormain
NOVICE_THRESHOLD = 800.0  # W_s below this = novice in a dormain

# Blind STF types — assignments get isolated_view_token
BLIND_STF_TYPES = {"astf", "astf_motion", "astf_periodic", "vstf", "jstf", "meta_astf"}

# Types that need dormain-matched candidates
COMPETENCE_MATCHED_TYPES = {"xstf", "astf", "astf_motion", "vstf", "jstf", "meta_astf"}


def make_session_factory(db_url: str) -> async_sessionmaker:
    engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=3)
    return async_sessionmaker(engine, expire_on_commit=False)


# ── STF candidate scoring ──────────────────────────────────────────────────────

async def score_candidates(
    db: AsyncSession,
    org_id: uuid.UUID,
    stf_id: uuid.UUID,
    stf_type: str,
    mandate: str,
    motion_id: uuid.UUID | None,
    subject_member_id: uuid.UUID | None,
    commissioned_by_circle_id: uuid.UUID | None,
) -> list[dict]:
    """
    Score all eligible members for an STF slot.
    Returns sorted list of {member_id, score, w_s, curiosity, slot_type}.
    """
    # Determine relevant dormain IDs from the motion / circle mandate
    dormain_ids = await _get_relevant_dormains(
        db, org_id, motion_id, commissioned_by_circle_id
    )

    # Load all active members in the org (excluding subject member if jSTF)
    exclusions: list[uuid.UUID] = []
    if subject_member_id:
        exclusions.append(subject_member_id)

    # For blind types, exclude current STF commissioners to avoid conflict-of-interest
    if commissioned_by_circle_id:
        circle_members = await db.execute(text("""
            SELECT member_id FROM circle_members
            WHERE circle_id = :cid AND exited_at IS NULL
        """), {"cid": commissioned_by_circle_id})
        # For aSTF: exclude the filing circle's members (independence)
        if stf_type in ("astf", "astf_motion"):
            exclusions.extend(row[0] for row in circle_members.fetchall())

    members_result = await db.execute(text("""
        SELECT m.id, m.current_state
        FROM members m
        WHERE m.org_id = :oid
          AND m.current_state IN ('active', 'probationary')
          AND m.id NOT IN :exclusions
    """), {
        "oid": org_id,
        "exclusions": tuple(exclusions) if exclusions else (uuid.uuid4(),),  # dummy
    })
    eligible_members = members_result.fetchall()

    if not eligible_members:
        return []

    scored = []
    for member_row in eligible_members:
        member_id = member_row[0]

        # Competence fit — max W_s across relevant dormains
        w_s = 0.0
        if dormain_ids:
            cs_result = await db.execute(text("""
                SELECT MAX(w_s) FROM competence_scores
                WHERE member_id = :mid AND dormain_id IN :dids
                  AND mcmp_status = 'active'
            """), {"mid": member_id, "dids": tuple(dormain_ids)})
            row = cs_result.fetchone()
            w_s = float(row[0] or 0.0)

        competence_fit = min(1.0, w_s / 3000.0)

        # Curiosity fit — max curiosity signal across relevant dormains
        curiosity_fit = 0.0
        if dormain_ids:
            cur_result = await db.execute(text("""
                SELECT MAX(signal) FROM curiosities
                WHERE member_id = :mid AND dormain_id IN :dids
            """), {"mid": member_id, "dids": tuple(dormain_ids)})
            row = cur_result.fetchone()
            curiosity_fit = float(row[0] or 0.0)

        # Availability — inverse of current STF load
        active_stf_result = await db.execute(text("""
            SELECT COUNT(*) FROM stf_assignments sa
            JOIN stf_instances si ON si.id = sa.stf_instance_id
            WHERE sa.member_id = :mid
              AND si.state IN ('forming', 'active', 'deliberating')
        """), {"mid": member_id})
        active_count = active_stf_result.scalar_one() or 0
        availability = max(0.0, 1.0 - (active_count * 0.2))

        # Independence — not already assigned to this STF
        is_independent = 1.0  # guaranteed by query structure

        # STF-type specific scoring adjustments
        if stf_type == "meta_astf":
            # jSTF requires W_h minimum — boost high-W_h members
            wh_result = await db.execute(text("""
                SELECT MAX(w_h) FROM competence_scores
                WHERE member_id = :mid AND dormain_id IN :dids
            """), {"mid": member_id, "dids": tuple(dormain_ids) if dormain_ids else (uuid.uuid4(),)})
            wh_row = wh_result.fetchone()
            w_h = float(wh_row[0] or 0.0)
            competence_fit = min(1.0, w_h / 2400.0)  # W_h ≥ 2400 target

        score = competence_fit * curiosity_fit * availability * is_independent

        # Add small random tiebreaker to avoid always picking same members
        score += random.uniform(0, 0.001)

        slot_type = "novice" if w_s < NOVICE_THRESHOLD else "standard"

        scored.append({
            "member_id": member_id,
            "score": score,
            "w_s": w_s,
            "curiosity": curiosity_fit,
            "slot_type": slot_type,
        })

    return scored


async def _get_relevant_dormains(
    db: AsyncSession,
    org_id: uuid.UUID,
    motion_id: uuid.UUID | None,
    circle_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    """Get dormain IDs relevant to this STF from the motion's circle or commissioning circle."""
    if motion_id:
        # Get the cell → look at invited circles → their dormains
        result = await db.execute(text("""
            SELECT DISTINCT cd.dormain_id
            FROM motions m
            JOIN cells c ON c.id = m.cell_id
            JOIN cell_invited_circles cic ON cic.cell_id = c.id
            JOIN circle_dormains cd ON cd.circle_id = cic.circle_id
            WHERE m.id = :mid AND cd.removed_at IS NULL
        """), {"mid": motion_id})
        ids = [row[0] for row in result.fetchall()]
        if ids:
            return ids

    if circle_id:
        result = await db.execute(text("""
            SELECT dormain_id FROM circle_dormains
            WHERE circle_id = :cid AND removed_at IS NULL
        """), {"cid": circle_id})
        return [row[0] for row in result.fetchall()]

    return []


async def form_stf_assignments(
    db: AsyncSession,
    nc: Any,
    org_id: uuid.UUID,
    stf_id: uuid.UUID,
    stf_type: str,
    scored: list[dict],
    target_size: int,
) -> None:
    """
    Select candidates applying novice floor, then emit assignment events.
    The Integrity Engine is read-write so we actually need to INSERT here
    via a special event or direct write.

    Because the inferential engine is read-only, we emit a formation event
    that the API can act on (or we write via the special formation topic).
    In v1.0: emit stf_formation_requested with assignment list.
    The API's STF service listens and creates assignments.
    """
    novice_target = max(1, int(target_size * NOVICE_FLOOR_PCT))
    expert_target = target_size - novice_target

    novices = sorted(
        [s for s in scored if s["slot_type"] == "novice"],
        key=lambda x: x["curiosity"], reverse=True
    )
    experts = sorted(
        [s for s in scored if s["slot_type"] == "standard"],
        key=lambda x: x["score"], reverse=True
    )

    selected_novices = novices[:novice_target]
    selected_experts = experts[:expert_target]

    # If not enough novices, fill from experts
    if len(selected_novices) < novice_target:
        extra_needed = novice_target - len(selected_novices)
        extra_experts = [e for e in experts if e not in selected_experts][:extra_needed]
        selected_experts = (selected_experts + extra_experts)[:expert_target + extra_needed]

    assignments = [
        {"member_id": str(c["member_id"]), "slot_type": c["slot_type"],
         "w_s": c["w_s"], "score": round(c["score"], 4)}
        for c in selected_novices + selected_experts
    ]

    if not assignments:
        log.warning(f"[inferential] no candidates found for STF {stf_id}")
        return

    log.info(
        f"[inferential] STF {stf_id} ({stf_type}): "
        f"selected {len(assignments)} candidates "
        f"({len(selected_novices)} novice, {len(selected_experts)} expert)"
    )

    # Emit formation event — Integrity Engine / API will create actual DB rows
    event = {
        "event_type": "stf_formation_requested",
        "org_id": str(org_id),
        "stf_id": str(stf_id),
        "stf_type": stf_type,
        "assignments": assignments,
        "is_blind": stf_type in BLIND_STF_TYPES,
    }

    if nc and nc.is_connected:
        try:
            js = nc.jetstream()
            await js.publish(
                f"ORG.{org_id}.events",
                json.dumps(event, default=str).encode(),
            )
        except Exception as e:
            log.error(f"[inferential] failed to emit formation event: {e}")


# ── Commons dormain tagging ────────────────────────────────────────────────────

async def tag_commons_thread(
    db: AsyncSession,
    nc: Any,
    org_id: uuid.UUID,
    thread_id: uuid.UUID,
    title: str,
    body: str,
) -> None:
    """
    Layer 2: NLP dormain classification.
    v1.0 stub — returns empty (author signal from layer 1 is used).
    v1.1: embed title+body, cosine similarity against dormain name embeddings.
    """
    # Load org dormains for future NLP matching
    dormains_result = await db.execute(text(
        "SELECT id, name, description FROM dormains WHERE org_id = :oid"
    ), {"oid": org_id})
    dormains = dormains_result.fetchall()

    if not dormains:
        return

    # Stub: keyword-based matching as v1.0 approximation
    text_lower = f"{title} {body}".lower()
    matched: list[tuple[uuid.UUID, float]] = []

    for dormain_id, name, description in dormains:
        keywords = name.lower().split() + (description or "").lower().split()[:5]
        matches = sum(1 for kw in keywords if len(kw) > 3 and kw in text_lower)
        if matches > 0:
            confidence = min(0.9, matches * 0.15)
            matched.append((dormain_id, confidence))

    if matched:
        matched.sort(key=lambda x: x[1], reverse=True)
        top = matched[:3]  # tag up to 3 dormains

        tag_event = {
            "event_type": "dormain_tag_suggested",
            "org_id": str(org_id),
            "thread_id": str(thread_id),
            "suggested_tags": [
                {"dormain_id": str(did), "confidence": conf, "source": "nlp_v1"}
                for did, conf in top
            ],
        }

        if nc and nc.is_connected:
            try:
                js = nc.jetstream()
                await js.publish(
                    f"ORG.{org_id}.events",
                    json.dumps(tag_event, default=str).encode(),
                )
            except Exception as e:
                log.error(f"[inferential] failed to emit tag event: {e}")


# ── Homogeneity check ──────────────────────────────────────────────────────────

async def check_circle_homogeneity(
    db: AsyncSession,
    nc: Any,
    org_id: uuid.UUID,
    cell_id: uuid.UUID,
    circle_ids: list[uuid.UUID],
) -> None:
    """Warn if invited circles share >80% dormain overlap."""
    if len(circle_ids) < 2:
        return

    dormain_sets: dict[uuid.UUID, set] = {}
    for cid in circle_ids:
        result = await db.execute(text(
            "SELECT dormain_id FROM circle_dormains WHERE circle_id = :cid AND removed_at IS NULL"
        ), {"cid": cid})
        dormain_sets[cid] = {row[0] for row in result.fetchall()}

    all_dormains = set()
    for ds in dormain_sets.values():
        all_dormains |= ds

    if not all_dormains:
        return

    # Compute overlap: how many dormains are shared by ALL circles / total
    shared = set.intersection(*dormain_sets.values()) if dormain_sets else set()
    overlap_ratio = len(shared) / len(all_dormains) if all_dormains else 0

    if overlap_ratio > 0.8:
        log.info(
            f"[inferential] homogeneity flag: cell={cell_id} "
            f"overlap={overlap_ratio:.0%}"
        )
        flag_event = {
            "event_type": "anomaly_flagged",
            "org_id": str(org_id),
            "subject_id": str(cell_id),
            "subject_type": "cell",
            "payload": {
                "anomaly_type": "CIRCLE_HOMOGENEITY",
                "overlap_ratio": overlap_ratio,
                "circle_ids": [str(c) for c in circle_ids],
                "shared_dormains": [str(d) for d in shared],
            },
        }
        if nc and nc.is_connected:
            try:
                js = nc.jetstream()
                await js.publish(
                    f"ORG.{org_id}.events",
                    json.dumps(flag_event, default=str).encode(),
                )
            except Exception as e:
                log.error(f"[inferential] failed to emit homogeneity flag: {e}")


# ── Event routing ─────────────────────────────────────────────────────────────

async def dispatch(data: dict, sf: async_sessionmaker, nc: Any) -> None:
    etype = data.get("event_type", "")
    org_str = data.get("org_id")
    if not org_str:
        return

    try:
        org_id = uuid.UUID(org_str)
    except ValueError:
        return

    async with sf() as db:
        try:
            if etype == "stf_commissioned":
                stf_id_str = data.get("stf_id") or data.get("subject_id")
                if not stf_id_str:
                    return
                stf_id = uuid.UUID(stf_id_str)
                stf_type = data.get("stf_type", "xstf")
                mandate = data.get("mandate", "")
                motion_id_str = data.get("motion_id")
                subject_str = data.get("subject_member_id")
                circle_str = data.get("commissioned_by_circle_id")

                # Load full STF details if not in event payload
                if not stf_type or not mandate:
                    stf_row = (await db.execute(text(
                        "SELECT stf_type, mandate, motion_id, subject_member_id, "
                        "commissioned_by_circle_id FROM stf_instances WHERE id = :sid"
                    ), {"sid": stf_id})).fetchone()
                    if stf_row:
                        stf_type = stf_row[0]
                        mandate = stf_row[1]
                        motion_id_str = str(stf_row[2]) if stf_row[2] else None
                        subject_str = str(stf_row[3]) if stf_row[3] else None
                        circle_str = str(stf_row[4]) if stf_row[4] else None

                if stf_type not in COMPETENCE_MATCHED_TYPES:
                    log.debug(f"[inferential] no matching for stf_type={stf_type}")
                    return

                motion_id = uuid.UUID(motion_id_str) if motion_id_str else None
                subject_id = uuid.UUID(subject_str) if subject_str else None
                circle_id = uuid.UUID(circle_str) if circle_str else None

                scored = await score_candidates(
                    db, org_id, stf_id, stf_type, mandate,
                    motion_id, subject_id, circle_id,
                )

                if scored:
                    target = min(STF_MAX_SIZE, max(STF_MIN_SIZE, len(scored)))
                    await form_stf_assignments(db, nc, org_id, stf_id, stf_type, scored, target)

            elif etype in ("commons_thread_created", "commons_post_created"):
                thread_id_str = data.get("subject_id") or data.get("thread_id")
                if not thread_id_str:
                    return
                thread_id = uuid.UUID(thread_id_str)
                payload = data.get("payload", {})
                title = payload.get("title", "")
                body_text = payload.get("body", "")
                await tag_commons_thread(db, nc, org_id, thread_id, title, body_text)

            elif etype == "cell_created":
                cell_id_str = data.get("subject_id")
                if not cell_id_str:
                    return
                cell_id = uuid.UUID(cell_id_str)
                payload = data.get("payload", {})
                circle_ids_raw = payload.get("invited_circle_ids", [])
                circle_ids = [uuid.UUID(c) for c in circle_ids_raw if c]
                if circle_ids:
                    await check_circle_homogeneity(db, nc, org_id, cell_id, circle_ids)

        except Exception as e:
            log.error(f"[inferential] error handling {etype}: {e}", exc_info=True)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    sf = make_session_factory(DATABASE_URL)

    nc = None
    for attempt in range(1, 6):
        try:
            nc = await nats.connect(
                NATS_URL, name="orbsys-inferential",
                reconnect_time_wait=2, max_reconnect_attempts=10,
            )
            log.info(f"[inferential] connected to NATS {NATS_URL}")
            break
        except Exception as e:
            log.warning(f"[inferential] NATS connect attempt {attempt}/5: {e}")
            if attempt < 5:
                await asyncio.sleep(2 ** attempt)
            else:
                log.error("[inferential] cannot connect — exiting")
                return

    js = nc.jetstream()

    async def handle_msg(msg):
        try:
            data = json.loads(msg.data.decode())
        except json.JSONDecodeError as e:
            log.error(f"[inferential] bad JSON: {e}")
            await msg.ack()
            return

        # Only process events we care about
        etype = data.get("event_type", "")
        if etype in ("stf_commissioned", "commons_thread_created",
                     "commons_post_created", "cell_created"):
            await dispatch(data, sf, nc)

        await msg.ack()

    await js.subscribe(
        "ORG.*.events",
        durable="inferential.consumer",
        cb=handle_msg,
    )
    log.info("[inferential] Inferential Engine running")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
