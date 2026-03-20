"""
Event bus client — NATS JetStream.

Stream naming: ORG.<org_id>.events
All governance actions emit events here. Three engines consume everything.
The app API emits; engines consume and act.

Usage:
    bus = get_event_bus()
    await bus.emit(org_id, GovernanceEvent(
        event_type=EventType.FORMAL_REVIEW_FILED,
        subject_id=post_id,
        subject_type="commons_post",
        payload={...},
        triggered_by_member=member_id,
    ))
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Any

log = logging.getLogger(__name__)


# ── Event type catalogue ──────────────────────────────────────────────────────

class EventType(str, Enum):
    # ── Org lifecycle ─────────────────────────────────────────────────────────
    ORG_CREATED                = "org_created"
    ORG_BOOTSTRAPPED           = "org_bootstrapped"
    DORMAIN_CREATED            = "dormain_created"

    # ── Member lifecycle ──────────────────────────────────────────────────────
    MEMBER_REGISTERED          = "member_registered"
    MEMBER_STATE_CHANGED       = "member_state_changed"
    MEMBER_EXITED              = "member_exited"
    CURIOSITY_UPDATED          = "curiosity_updated"

    # ── Competence ────────────────────────────────────────────────────────────
    FORMAL_REVIEW_FILED        = "formal_review_filed"     # → Integrity Engine: ΔC
    WH_CLAIM_SUBMITTED         = "wh_claim_submitted"      # → Inferential: vSTF commission
    WH_CLAIM_VERIFIED          = "wh_claim_verified"       # → Integrity Engine: W_h boost

    # ── Commons ───────────────────────────────────────────────────────────────
    COMMONS_THREAD_CREATED     = "commons_thread_created"  # → Inferential: tag
    COMMONS_THREAD_SPONSORED   = "commons_thread_sponsored" # → Inferential: route
    COMMONS_POST_CREATED       = "commons_post_created"
    DORMAIN_TAG_CORRECTED      = "dormain_tag_corrected"   # → Inferential: retrain signal

    # ── Cells ─────────────────────────────────────────────────────────────────
    CELL_CREATED               = "cell_created"
    CELL_CONTRIBUTION_ADDED    = "cell_contribution_added" # → Insight: update minutes
    CELL_VOTE_CAST             = "cell_vote_cast"
    CELL_DISSOLVED             = "cell_dissolved"

    # ── Motions ───────────────────────────────────────────────────────────────
    MOTION_FILED               = "motion_filed"            # → Inferential: commission aSTF
    MOTION_GATE1_RESULT        = "motion_gate1_result"     # → API: state update
    MOTION_VOTE_CLOSED         = "motion_vote_closed"      # → Insight: P1 notif
    MOTION_REVISION_REQUESTED  = "motion_revision_requested"

    # ── Resolutions ───────────────────────────────────────────────────────────
    RESOLUTION_CREATED         = "resolution_created"
    RESOLUTION_ENACT_REQUESTED = "resolution_enact_requested"  # SYNC path
    RESOLUTION_ENACTED         = "resolution_enacted"          # → Integrity: write params
    RESOLUTION_CONTESTED       = "resolution_contested"

    # ── STF ───────────────────────────────────────────────────────────────────
    STF_COMMISSIONED           = "stf_commissioned"        # → Inferential: match candidates
    STF_FORMATION_REQUESTED    = "stf_formation_requested"
    STF_ASSIGNMENT_CREATED     = "stf_assignment_created"
    STF_DEADLINE_APPROACHING   = "stf_deadline_approaching" # → Insight: P1 notif
    STF_VERDICT_FILED          = "stf_verdict_filed"
    STF_COMPLETED              = "stf_completed"           # → Integrity: aggregate + write

    # ── Identity ──────────────────────────────────────────────────────────────
    STF_UNSEALING_TRIGGERED    = "stf_unsealing_triggered"

    # ── Anomalies ─────────────────────────────────────────────────────────────
    ANOMALY_FLAGGED            = "anomaly_flagged"         # → Integrity: review queue


class GovernanceEvent:
    """
    Single governance event. Emitted to ORG.<org_id>.events.
    ledger_event_id is null on emit — populated by Integrity Engine after commit.
    """
    def __init__(
        self,
        event_type: EventType,
        subject_id: uuid.UUID | None = None,
        subject_type: str | None = None,
        payload: dict[str, Any] | None = None,
        triggered_by_member: uuid.UUID | None = None,
        triggered_by_resolution: uuid.UUID | None = None,
    ):
        self.event_id = uuid.uuid4()
        self.event_type = event_type
        self.subject_id = subject_id
        self.subject_type = subject_type
        self.payload = payload or {}
        self.triggered_by_member = triggered_by_member
        self.triggered_by_resolution = triggered_by_resolution
        self.emitted_at = datetime.now(timezone.utc)
        self.ledger_event_id: uuid.UUID | None = None  # set by Integrity Engine

    def to_dict(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "subject_id": str(self.subject_id) if self.subject_id else None,
            "subject_type": self.subject_type,
            "payload": self.payload,
            "triggered_by_member": str(self.triggered_by_member) if self.triggered_by_member else None,
            "triggered_by_resolution": str(self.triggered_by_resolution) if self.triggered_by_resolution else None,
            "emitted_at": self.emitted_at.isoformat(),
            "ledger_event_id": None,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), default=str).encode()


# ── Client ────────────────────────────────────────────────────────────────────

class EventBus:
    """
    Thin wrapper around NATS JetStream.
    Manages one connection shared across all requests.
    """
    def __init__(self):
        self._nc = None
        self._js = None
        self._connected = False

    async def connect(self, nats_url: str) -> None:
        try:
            import nats
            self._nc = await nats.connect(nats_url)
            self._js = self._nc.jetstream()
            self._connected = True
            log.info(f"[event_bus] connected to {nats_url}")
        except Exception as e:
            log.warning(f"[event_bus] could not connect to NATS: {e}. Events will be dropped.")
            self._connected = False

    async def emit(self, org_id: uuid.UUID, event: GovernanceEvent) -> None:
        """
        Publish event to ORG.<org_id>.events stream.
        Fire-and-forget. If NATS is unavailable, logs the dropped event.
        The app API never blocks on event delivery.
        """
        if not self._connected or self._js is None:
            log.warning(
                f"[event_bus] NATS not connected — dropping event "
                f"{event.event_type.value} for org {org_id}"
            )
            return

        subject = f"ORG.{org_id}.events"
        try:
            await self._js.publish(subject, event.to_bytes())
            log.debug(f"[event_bus] emitted {event.event_type.value} → {subject}")
        except Exception as e:
            log.error(
                f"[event_bus] failed to emit {event.event_type.value} "
                f"for org {org_id}: {e}"
            )

    async def close(self) -> None:
        if self._nc:
            await self._nc.close()
            self._connected = False


# ── Singleton ─────────────────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
