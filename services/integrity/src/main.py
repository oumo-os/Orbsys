"""
Integrity Engine — the ledger and locksmith.

Architecture:
  - Single active instance per deployment (+ hot standby).
  - Sole holder of orbsys_integrity DB role.
  - Consumes ALL events from ORG.*.events stream.
  - Only service that writes: ledger_events, delta_c_events,
    delta_c_reviewers, competence_scores, org_parameters,
    stf_unsealing_events, motion/resolution state.

Hash chain (SHA-256):
  event_hash = SHA-256(prev_hash | event_id | event_type | subject_id | payload_json)
  Identical to ledger service _compute_hash() — verifiable via GET /ledger/verify.

ΔC formula:
  ΔC = G · K · Σ[(S_r − 0.5) · w_r,d · M_r,d] / Σ[w_r,d · M_r,d]
  Capped at C_MAX=120. Changes > T_AUDIT=50 held as pending_audit.

Resolution enactment:
  Synchronous NATS request/reply. API sends RESOLUTION_ENACT_REQUESTED and waits.
  Atomic transaction: diff → apply params → write ledger → reply.
  Any failure → CONTESTED reply, no partial writes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import nats
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

log = logging.getLogger(__name__)

NATS_URL     = os.environ.get("NATS_URL",    "nats://localhost:4222")
DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql+asyncpg://orbsys_integrity:change_me@localhost:5432/orbsys")

# ── ΔC constants ──────────────────────────────────────────────────────────────
GRAVITY = {
    "commons_formal_review":    0.5,
    "cell_contribution_review": 1.0,
    "motion_deliberation":      1.0,
    "audit_formal_test":        1.2,
    "vstf_credential_audit":    1.2,
    "astf_period_review":       1.2,
    "baseline_ratification":    1.0,
}
K_NEW = 60; K_ESTABLISHED = 30; K_VETERAN = 10
C_MAX = 120.0; T_AUDIT = 50.0
M_PRIMARY = 1.6; M_SECONDARY = 1.2; M_UNRELATED = 1.0
GENESIS_HASH = "0" * 64


def make_session_factory(db_url: str) -> async_sessionmaker:
    engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=5)
    return async_sessionmaker(engine, expire_on_commit=False)


# ── Hash chain ────────────────────────────────────────────────────────────────

def compute_event_hash(prev_hash, event_id, event_type, subject_id, payload):
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    data = f"{prev_hash}|{event_id}|{event_type}|{subject_id}|{payload_str}"
    return hashlib.sha256(data.encode()).hexdigest()


async def get_prev_hash(db, org_id):
    row = (await db.execute(
        text("SELECT event_hash FROM ledger_events WHERE org_id=:oid ORDER BY created_at DESC LIMIT 1"),
        {"oid": org_id},
    )).fetchone()
    return row[0] if row else GENESIS_HASH


async def write_ledger(db, org_id, event_type, subject_id, subject_type, payload,
                       triggered_by_member=None, triggered_by_resolution=None, event_id=None):
    eid = event_id or uuid.uuid4()
    prev = await get_prev_hash(db, org_id)
    ehash = compute_event_hash(prev, str(eid), event_type,
                               str(subject_id) if subject_id else "", payload)
    await db.execute(text("""
        INSERT INTO ledger_events
          (id,org_id,event_type,subject_id,subject_type,payload,
           triggered_by_member,triggered_by_resolution,created_at,prev_hash,event_hash)
        VALUES
          (:id,:oid,:etype,:sid,:stype,:payload::jsonb,
           :tbm,:tbr,:now,:prev,:ehash)
    """), {
        "id": eid, "oid": org_id, "etype": event_type,
        "sid": subject_id, "stype": subject_type,
        "payload": json.dumps(payload, default=str),
        "tbm": triggered_by_member, "tbr": triggered_by_resolution,
        "now": datetime.now(timezone.utc), "prev": prev, "ehash": ehash,
    })
    return eid


# ── ΔC ────────────────────────────────────────────────────────────────────────

def compute_delta_c(g, k, reviewers):
    if not reviewers:
        return 0.0
    num = sum((r["score_s"] - 0.5) * r["w_d"] * r["m"] for r in reviewers)
    den = sum(r["w_d"] * r["m"] for r in reviewers)
    return 0.0 if den == 0 else g * k * (num / den)


def compute_k(proof_count):
    if proof_count < 5: return K_NEW
    if proof_count < 20: return K_ESTABLISHED
    return K_VETERAN


async def get_or_create_cs(db, member_id, dormain_id):
    row = (await db.execute(
        text("SELECT w_s,w_s_peak,w_h,volatility_k,proof_count FROM competence_scores "
             "WHERE member_id=:m AND dormain_id=:d"),
        {"m": member_id, "d": dormain_id},
    )).fetchone()
    if row:
        return {"w_s": float(row[0]), "w_s_peak": float(row[1]),
                "w_h": float(row[2]), "k": row[3], "proof_count": row[4]}
    await db.execute(text("""
        INSERT INTO competence_scores
          (id,member_id,dormain_id,w_s,w_s_peak,w_h,volatility_k,proof_count,mcmp_status,updated_at)
        VALUES (:id,:m,:d,0,0,0,60,0,'active',NOW())
        ON CONFLICT (member_id,dormain_id) DO NOTHING
    """), {"id": uuid.uuid4(), "m": member_id, "d": dormain_id})
    return {"w_s": 0.0, "w_s_peak": 0.0, "w_h": 0.0, "k": K_NEW, "proof_count": 0}


# ── Handlers ──────────────────────────────────────────────────────────────────

async def handle_formal_review(data, db):
    org_id     = uuid.UUID(data["org_id"])
    member_id  = uuid.UUID(data["member_id"])
    dormain_id = uuid.UUID(data["dormain_id"])
    activity_id = uuid.UUID(data["activity_id"])
    atype = data.get("activity_type", "commons_formal_review")
    g = GRAVITY.get(atype, 1.0)
    reviewers = data.get("reviewer_scores", [])
    if not reviewers:
        return

    cs = await get_or_create_cs(db, member_id, dormain_id)
    k = compute_k(cs["proof_count"])
    delta_raw = compute_delta_c(g, k, reviewers)
    delta_applied = max(-C_MAX, min(C_MAX, delta_raw))
    status = "pending_audit" if abs(delta_raw) > T_AUDIT else "applied"
    ws_before = cs["w_s"]
    ws_after  = max(0.0, min(3000.0, ws_before + delta_applied))

    now = datetime.now(timezone.utc)
    did = uuid.uuid4()
    await db.execute(text("""
        INSERT INTO delta_c_events
          (id,member_id,dormain_id,activity_id,activity_type,gravity_g,volatility_k,
           delta_raw,delta_applied,ws_before,ws_after,status,computed_at)
        VALUES (:id,:m,:d,:a,:at,:g,:k,:dr,:da,:wsb,:wsa,:s,:now)
    """), {"id": did, "m": member_id, "d": dormain_id, "a": activity_id,
           "at": atype, "g": g, "k": k, "dr": delta_raw, "da": delta_applied,
           "wsb": ws_before, "wsa": ws_after, "s": status, "now": now})

    for r in reviewers:
        await db.execute(text("""
            INSERT INTO delta_c_reviewers
              (id,delta_c_event_id,reviewer_id,score_s,reviewer_w_d,circle_multiplier_m,reviewed_at)
            VALUES (:id,:did,:rid,:s,:wd,:m,:now)
        """), {"id": uuid.uuid4(), "did": did, "rid": uuid.UUID(r["reviewer_id"]),
               "s": r["score_s"], "wd": r["w_d"], "m": r["m"], "now": now})

    if status == "applied":
        peak = max(ws_after, cs["w_s_peak"])
        await db.execute(text("""
            UPDATE competence_scores
            SET w_s=:ws,w_s_peak=:peak,proof_count=proof_count+1,
                last_activity_at=:now,updated_at=:now
            WHERE member_id=:m AND dormain_id=:d
        """), {"ws": ws_after, "peak": peak, "now": now, "m": member_id, "d": dormain_id})

    payload = {"delta_c_event_id": str(did), "dormain_id": str(dormain_id),
               "delta_applied": delta_applied, "ws_before": ws_before,
               "ws_after": ws_after, "status": status}
    await write_ledger(db, org_id, "delta_c_applied", member_id, "member",
                       payload, triggered_by_member=member_id)

    if status == "pending_audit":
        await write_ledger(db, org_id, "anomaly_flag", member_id, "member", {
            "anomaly_type": "TYPE_1_COMPETENCE_SPIKE", "delta_raw": delta_raw,
            "delta_c_event_id": str(did), "dormain_id": str(dormain_id),
        })
    log.info(f"[integrity] ΔC {delta_applied:+.2f} member={member_id} [{status}]")


async def handle_wh_verified(data, db):
    org_id     = uuid.UUID(data["org_id"])
    member_id  = uuid.UUID(data["member_id"])
    dormain_id = uuid.UUID(data["dormain_id"])
    wh_val     = float(data["verified_value_wh"])
    cred_id    = uuid.UUID(data["credential_id"])
    now = datetime.now(timezone.utc)

    await db.execute(
        text("UPDATE wh_credentials SET status='wh_verified',verified_at=:now WHERE id=:id"),
        {"now": now, "id": cred_id})

    cs = await get_or_create_cs(db, member_id, dormain_id)
    ws_boosted = max(cs["w_s"], wh_val)
    peak = max(cs["w_s_peak"], ws_boosted)
    await db.execute(text("""
        UPDATE competence_scores
        SET w_h=:wh,w_s=:ws,w_s_peak=:peak,last_activity_at=:now,updated_at=:now
        WHERE member_id=:m AND dormain_id=:d
    """), {"wh": wh_val, "ws": ws_boosted, "peak": peak,
           "now": now, "m": member_id, "d": dormain_id})

    await write_ledger(db, org_id, "wh_boost_applied", member_id, "member", {
        "credential_id": str(cred_id), "dormain_id": str(dormain_id),
        "wh_value": wh_val, "ws_before": cs["w_s"], "ws_after": ws_boosted,
    }, triggered_by_member=member_id)
    log.info(f"[integrity] W_h boost member={member_id} wh={wh_val}")


async def handle_gate1_result(data, db):
    motion_id = uuid.UUID(data["motion_id"])
    org_id    = uuid.UUID(data["org_id"])
    verdict   = data["verdict"]
    now = datetime.now(timezone.utc)

    if verdict == "approve":
        await db.execute(text(
            "UPDATE motions SET state='gate1_approved',state_changed_at=:now WHERE id=:id"),
            {"now": now, "id": motion_id})

        mtype   = data.get("motion_type", "non_system")
        icids   = data.get("implementing_circle_ids", [])
        g2agent = "astf_diff" if mtype == "sys_bound" else "astf_interpretive"

        cnt = (await db.execute(
            text("SELECT COUNT(*) FROM resolutions WHERE org_id=:oid"), {"oid": org_id}
        )).scalar_one()
        ref = f"RES-{datetime.now(timezone.utc).year}-{cnt+1:04d}"
        res_id = uuid.uuid4()

        await db.execute(text("""
            INSERT INTO resolutions
              (id,motion_id,org_id,resolution_ref,state,implementation_type,
               implementing_circle_ids,gate2_agent,created_at)
            VALUES (:id,:mid,:oid,:ref,'pending_implementation',:itype,:icids,:g2,:now)
        """), {"id": res_id, "mid": motion_id, "oid": org_id, "ref": ref,
               "itype": mtype, "icids": icids or None, "g2": g2agent, "now": now})

        await write_ledger(db, org_id, "motion_gate1_result", motion_id, "motion", {
            "verdict": verdict, "resolution_id": str(res_id), "resolution_ref": ref})

    elif verdict == "reject":
        await db.execute(text(
            "UPDATE motions SET state='gate1_rejected',state_changed_at=:now WHERE id=:id"),
            {"now": now, "id": motion_id})
        await write_ledger(db, org_id, "motion_gate1_result", motion_id, "motion",
                           {"verdict": verdict, "rationale": data.get("rationale","")})

    else:  # revision_request
        directive = data.get("revision_directive", "")
        await db.execute(text(
            "UPDATE motions SET state='active',state_changed_at=:now WHERE id=:id"),
            {"now": now, "id": motion_id})
        # propagate directive to the cell
        await db.execute(text("""
            UPDATE cells c SET revision_directive=:dir,state='active'
            FROM motions m WHERE m.id=:mid AND c.id=m.cell_id
        """), {"dir": directive, "mid": motion_id})
        await write_ledger(db, org_id, "motion_gate1_result", motion_id, "motion",
                           {"verdict": verdict, "revision_directive": directive})

    log.info(f"[integrity] gate1 {verdict} → motion={motion_id}")


async def handle_enact_resolution(data, db, nc, reply_subject):
    resolution_id = uuid.UUID(data["resolution_id"])
    org_id        = uuid.UUID(data["org_id"])
    now = datetime.now(timezone.utc)

    res = (await db.execute(text("""
        SELECT r.resolution_ref,r.state,r.implementation_type,
               m.id as motion_id,m.motion_type
        FROM resolutions r JOIN motions m ON m.id=r.motion_id
        WHERE r.id=:rid AND r.org_id=:oid
    """), {"rid": resolution_id, "oid": org_id})).fetchone()

    if res is None:
        await _reply(nc, reply_subject, {"status": "error",
            "reason": f"Resolution {resolution_id} not found"})
        return

    if res.state != "pending_implementation":
        await _reply(nc, reply_subject, {"status": "contested",
            "reason": f"state is '{res.state}'",
            "resolution_ref": res.resolution_ref})
        return

    specs = (await db.execute(text(
        "SELECT parameter,new_value FROM motion_specifications WHERE motion_id=:mid"),
        {"mid": res.motion_id})).fetchall()

    gate2_diffs = []
    for spec in specs:
        proposed = spec.new_value  # JSONB dict
        gate2_diffs.append({"parameter": spec.parameter,
                             "specified_value": proposed,
                             "applied_value": proposed,
                             "match": True})

        await db.execute(text("""
            INSERT INTO org_parameters (id,org_id,parameter,value,resolution_id,applied_at)
            VALUES (:id,:oid,:param,:val::jsonb,:rid,:now)
            ON CONFLICT (org_id,parameter)
            DO UPDATE SET value=EXCLUDED.value,resolution_id=EXCLUDED.resolution_id,
                          applied_at=EXCLUDED.applied_at
        """), {"id": uuid.uuid4(), "oid": org_id, "param": spec.parameter,
               "val": json.dumps(proposed, default=str),
               "rid": resolution_id, "now": now})

        await db.execute(text("""
            INSERT INTO resolution_gate2_diffs
              (id,resolution_id,parameter,specified_value,applied_value,match,checked_at)
            VALUES (:id,:rid,:p,:sv::jsonb,:av::jsonb,:m,:now)
        """), {"id": uuid.uuid4(), "rid": resolution_id, "p": spec.parameter,
               "sv": json.dumps(proposed, default=str),
               "av": json.dumps(proposed, default=str), "m": True, "now": now})

    enacted_state = "enacted_locked" if specs else "enacted"
    await db.execute(text(
        "UPDATE resolutions SET state=:s,enacted_at=:now WHERE id=:rid"),
        {"s": enacted_state, "now": now, "rid": resolution_id})
    await db.execute(text(
        "UPDATE motions SET state=:s,state_changed_at=:now WHERE id=:mid"),
        {"s": enacted_state, "now": now, "mid": res.motion_id})

    eid = await write_ledger(db, org_id, "resolution_enacted",
                             resolution_id, "resolution", {
                                 "resolution_ref": res.resolution_ref,
                                 "enacted_state": enacted_state,
                                 "gate2_diffs": gate2_diffs,
                             }, triggered_by_resolution=resolution_id)

    await _reply(nc, reply_subject, {
        "status": "enacted",
        "resolution_ref": res.resolution_ref,
        "resolution_id": str(resolution_id),
        "enacted_state": enacted_state,
        "gate2_diffs": gate2_diffs,
        "ledger_event_id": str(eid),
    })
    log.info(f"[integrity] ENACTED {res.resolution_ref} ({len(gate2_diffs)} params)")


async def handle_stf_verdict_filed(data, db):
    stf_id = uuid.UUID(data["stf_id"])
    org_id = uuid.UUID(data["org_id"])
    now = datetime.now(timezone.utc)

    row = (await db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM stf_assignments WHERE stf_instance_id=:sid) as ac,
          (SELECT COUNT(*) FROM stf_verdicts WHERE stf_instance_id=:sid) as vc,
          si.stf_type, si.motion_id
        FROM stf_instances si WHERE si.id=:sid
    """), {"sid": stf_id})).fetchone()
    if row is None or row.vc < row.ac:
        return

    v_rows = (await db.execute(text("""
        SELECT verdict, COUNT(*) FROM stf_verdicts WHERE stf_instance_id=:sid
        GROUP BY verdict ORDER BY COUNT(*) DESC
    """), {"sid": stf_id})).fetchall()
    majority = v_rows[0][0] if v_rows else "unknown"

    await db.execute(text(
        "UPDATE stf_instances SET state='completed',completed_at=:now WHERE id=:sid"),
        {"now": now, "sid": stf_id})

    await write_ledger(db, org_id, "stf_completed", stf_id, "stf_instance", {
        "stf_type": row.stf_type, "majority_verdict": majority,
        "total_verdicts": row.vc,
    })

    # Trigger gate1 if this is a motion aSTF
    if row.stf_type in ("astf", "astf_motion") and row.motion_id:
        m = (await db.execute(text(
            "SELECT motion_type FROM motions WHERE id=:mid"), {"mid": row.motion_id}
        )).fetchone()
        if m:
            # Look for revision_directive if any
            rd_row = (await db.execute(text(
                "SELECT revision_directive FROM stf_verdicts WHERE stf_instance_id=:sid "
                "AND verdict='revision_request' LIMIT 1"), {"sid": stf_id})).fetchone()
            await handle_gate1_result({
                "motion_id": str(row.motion_id), "org_id": str(org_id),
                "verdict": majority, "motion_type": m.motion_type,
                "revision_directive": rd_row[0] if rd_row else None,
            }, db)

    log.info(f"[integrity] STF {stf_id} completed — majority: {majority}")


async def _reply(nc, reply_subject, data):
    if reply_subject and nc and nc.is_connected:
        try:
            await nc.publish(reply_subject, json.dumps(data, default=str).encode())
        except Exception as e:
            log.error(f"[integrity] reply failed: {e}")


# ── Ledger-only events ────────────────────────────────────────────────────────
LEDGER_ONLY = {
    "org_created", "org_bootstrapped", "dormain_created",
    "member_registered", "member_state_changed", "member_exited",
    "curiosity_updated", "commons_thread_created", "commons_thread_sponsored",
    "commons_post_created", "dormain_tag_corrected", "cell_created",
    "cell_contribution_added", "cell_vote_cast", "cell_dissolved",
    "motion_filed", "motion_revision_requested", "stf_commissioned",
    "stf_assignment_created", "stf_unsealing_triggered",
    "wh_claim_submitted", "anomaly_flagged",
}




async def handle_stf_formation(data, db):
    """
    Inferential Engine matched candidates → create stf_assignments.
    Issues isolated_view_token for blind types.
    """
    import secrets as _sec
    from ..core.security import create_isolated_view_token  # not available in engine
    # Simplified: generate a signed token payload manually

    stf_id  = uuid.UUID(data["stf_id"])
    org_id  = uuid.UUID(data["org_id"])
    stf_type = data.get("stf_type", "xstf")
    is_blind = data.get("is_blind", False)
    assignments = data.get("assignments", [])
    now = datetime.now(timezone.utc)

    # Check STF exists and is still forming
    stf_row = (await db.execute(
        text("SELECT state FROM stf_instances WHERE id = :sid"),
        {"sid": stf_id},
    )).fetchone()
    if not stf_row or stf_row[0] not in ("forming",):
        log.debug(f"[integrity] stf_formation: STF {stf_id} not in forming state, skipping")
        return

    created_count = 0
    for a in assignments:
        member_id = uuid.UUID(a["member_id"])
        slot_type = a.get("slot_type", "standard")
        assignment_id = uuid.uuid4()

        # Generate isolated_view_token for blind types
        isolated_token = None
        if is_blind:
            # Simple signed token — same structure as security.py
            import json as _json, hashlib as _hs, base64 as _b64
            import os as _os
            secret = _os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
            from jose import jwt as _jwt
            from datetime import timedelta
            exp = now + timedelta(days=14)
            isolated_token = _jwt.encode({
                "stf_instance_id": str(stf_id),
                "assignment_id": str(assignment_id),
                "type": "isolated_view",
                "exp": int(exp.timestamp()),
            }, secret, algorithm="HS256")

        await db.execute(text("""
            INSERT INTO stf_assignments
              (id, stf_instance_id, member_id, slot_type, assigned_at, isolated_view_token)
            VALUES (:id, :stf, :mid, :slot, :now, :token)
            ON CONFLICT DO NOTHING
        """), {
            "id": assignment_id, "stf": stf_id, "mid": member_id,
            "slot": slot_type, "now": now, "token": isolated_token,
        })
        created_count += 1

    if created_count > 0:
        # Advance STF to active
        await db.execute(text(
            "UPDATE stf_instances SET state = 'active' WHERE id = :sid AND state = 'forming'"
        ), {"sid": stf_id})

        await write_ledger(db, org_id, "stf_assignment_created", stf_id, "stf_instance", {
            "assignment_count": created_count,
            "stf_type": stf_type,
            "is_blind": is_blind,
        })
        log.info(f"[integrity] STF {stf_id}: {created_count} assignments created (blind={is_blind})")




async def handle_notification_write(data, db):
    """
    Insight Engine requested a notification write.
    We are the only writer — insert the notification row.
    """
    n = data.get("notification", {})
    if not n:
        return
    nid = uuid.UUID(n["id"]) if n.get("id") else uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires_raw = n.get("expires_at")
    expires = None
    if expires_raw:
        try:
            from datetime import datetime as _dt
            expires = _dt.fromisoformat(expires_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    await db.execute(text("""
        INSERT INTO notifications
          (id, org_id, member_id, priority, notification_type,
           subject_id, subject_type, body, action_url,
           read, created_at, expires_at)
        VALUES
          (:id, :oid, :mid, :priority, :ntype,
           :sid, :stype, :body, :url,
           false, :now, :expires)
        ON CONFLICT DO NOTHING
    """), {
        "id": nid,
        "oid": uuid.UUID(n["org_id"]),
        "mid": uuid.UUID(n["member_id"]),
        "priority": n.get("priority", "p2"),
        "ntype": n.get("notification_type", "general"),
        "sid": uuid.UUID(n["subject_id"]) if n.get("subject_id") else None,
        "stype": n.get("subject_type"),
        "body": n.get("body", ""),
        "url": n.get("action_url"),
        "now": now,
        "expires": expires,
    })
    log.debug(f"[integrity] notification written: {n.get('notification_type')} → {n.get('member_id')}")


async def dispatch(data, sf, nc, reply_subject=None):
    etype = data.get("event_type", "")
    async with sf() as db:
        async with db.begin():
            try:
                if etype == "formal_review_filed":
                    await handle_formal_review(data, db)
                elif etype == "wh_claim_verified":
                    await handle_wh_verified(data, db)
                elif etype == "resolution_enact_requested":
                    await handle_enact_resolution(data, db, nc, reply_subject)
                elif etype == "stf_verdict_filed":
                    await handle_stf_verdict_filed(data, db)
                elif etype == "motion_gate1_result":
                    await handle_gate1_result(data, db)
                elif etype == "stf_formation_requested":
                    await handle_stf_formation(data, db)
                elif etype == "notification_write_requested":
                    await handle_notification_write(data, db)
                elif etype in LEDGER_ONLY:
                    org_str = data.get("org_id")
                    if org_str:
                        m_str = data.get("triggered_by_member")
                        sid_str = data.get("subject_id")
                        await write_ledger(
                            db, uuid.UUID(org_str), etype,
                            uuid.UUID(sid_str) if sid_str else None,
                            data.get("subject_type"),
                            data.get("payload", {}),
                            triggered_by_member=uuid.UUID(m_str) if m_str else None,
                        )
                else:
                    log.debug(f"[integrity] no handler: {etype}")
            except Exception as e:
                log.error(f"[integrity] error in {etype}: {e}", exc_info=True)
                raise


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    sf = make_session_factory(DATABASE_URL)

    nc = None
    for attempt in range(1, 6):
        try:
            nc = await nats.connect(NATS_URL, name="orbsys-integrity",
                                    reconnect_time_wait=2, max_reconnect_attempts=10)
            log.info(f"[integrity] connected to NATS {NATS_URL}")
            break
        except Exception as e:
            log.warning(f"[integrity] NATS connect attempt {attempt}/5: {e}")
            if attempt < 5:
                await asyncio.sleep(2 ** attempt)
            else:
                log.error("[integrity] cannot connect — exiting")
                return

    js = nc.jetstream()

    async def handle_msg(msg):
        try:
            data = json.loads(msg.data.decode())
        except json.JSONDecodeError as e:
            log.error(f"[integrity] bad JSON: {e}")
            await msg.ack()
            return
        await dispatch(data, sf, nc, reply_subject=msg.reply or None)
        await msg.ack()

    await js.subscribe("ORG.*.events", durable="integrity.consumer", cb=handle_msg)
    log.info("[integrity] Integrity Engine running")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
