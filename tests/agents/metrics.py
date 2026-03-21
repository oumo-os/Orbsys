"""
Metrics collector for scenario runs.

Tracks governance outcomes that validate the PAAS paper claims and
surface security test results (capture detection, Sybil patterns, etc.).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .client import OrbSysClient
from .config import TEST_ORG_SLUG

log = logging.getLogger(__name__)


@dataclass
class ScenarioMetrics:
    scenario_name: str
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    # Agent population
    total_agents:       int = 0
    genuine_agents:     int = 0
    adversarial_agents: int = 0
    active_agents:      int = 0   # at least one action this run

    # Governance lifecycle
    threads_created:    int = 0
    cells_created:      int = 0
    motions_filed:      int = 0
    resolutions_enacted:int = 0
    stf_panels:         int = 0
    verdicts_filed:     int = 0

    # Agent actions
    total_posts:          int = 0
    total_contributions:  int = 0
    total_votes:          int = 0
    total_reviews:        int = 0
    total_verdicts_filed: int = 0

    # PAAS paper validation signals
    ledger_chain_intact: bool | None = None
    anomaly_flags:       int = 0     # Integrity Engine flags
    rejection_rate:      float = 0.0  # aSTF Gate 1 rejection rate

    # Security test results
    sybil_detected:      bool = False
    capture_detected:    bool = False
    collusion_detected:  bool = False

    # Raw ledger events for analysis
    ledger_event_count: int = 0

    @property
    def duration_s(self) -> float:
        return (self.finished_at or time.time()) - self.started_at

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario_name,
            "duration_seconds": round(self.duration_s, 1),
            "population": {
                "total": self.total_agents,
                "genuine": self.genuine_agents,
                "adversarial": self.adversarial_agents,
                "active_fraction": (
                    round(self.active_agents / self.total_agents, 3)
                    if self.total_agents else 0
                ),
            },
            "governance": {
                "threads": self.threads_created,
                "cells": self.cells_created,
                "motions": self.motions_filed,
                "resolutions": self.resolutions_enacted,
                "stf_panels": self.stf_panels,
                "verdicts": self.verdicts_filed,
                "rejection_rate": round(self.rejection_rate, 3),
            },
            "agent_actions": {
                "posts": self.total_posts,
                "contributions": self.total_contributions,
                "votes": self.total_votes,
                "reviews": self.total_reviews,
                "verdicts": self.total_verdicts_filed,
            },
            "paas_validation": {
                "ledger_chain_intact": self.ledger_chain_intact,
                "anomaly_flags": self.anomaly_flags,
            },
            "security": {
                "sybil_detected": self.sybil_detected,
                "capture_detected": self.capture_detected,
                "collusion_detected": self.collusion_detected,
            },
            "ledger_events_total": self.ledger_event_count,
        }

    def print_summary(self) -> None:
        d = self.to_dict()
        print("\n" + "=" * 60)
        print(f"  Scenario: {d['scenario']}")
        print(f"  Duration: {d['duration_seconds']}s")
        print("=" * 60)
        print(f"  Population:    {d['population']['total']} agents "
              f"({d['population']['genuine']} genuine, "
              f"{d['population']['adversarial']} adversarial)")
        print(f"  Active agents: {d['population']['active_fraction']*100:.0f}% participated")
        print()
        g = d["governance"]
        print(f"  Governance lifecycle:")
        print(f"    Commons threads:    {g['threads']}")
        print(f"    Deliberation cells: {g['cells']}")
        print(f"    Motions filed:      {g['motions']}")
        print(f"    Resolutions:        {g['resolutions']}")
        print(f"    STF panels:         {g['stf_panels']}")
        print(f"    Gate 1 rejection:   {g['rejection_rate']*100:.1f}%")
        print()
        a = d["agent_actions"]
        print(f"  Agent actions: {a['posts']} posts | "
              f"{a['contributions']} contributions | {a['votes']} votes | "
              f"{a['reviews']} reviews | {a['verdicts']} verdicts")
        print()
        pv = d["paas_validation"]
        chain_status = "✓ intact" if pv["ledger_chain_intact"] else \
                       "✗ broken" if pv["ledger_chain_intact"] is False else "? unchecked"
        print(f"  PAAS validation:")
        print(f"    Ledger chain: {chain_status}")
        print(f"    Anomaly flags: {pv['anomaly_flags']}")
        print()
        s = d["security"]
        print(f"  Security detections:")
        print(f"    Sybil:     {'DETECTED' if s['sybil_detected'] else 'clean'}")
        print(f"    Capture:   {'DETECTED' if s['capture_detected'] else 'clean'}")
        print(f"    Collusion: {'DETECTED' if s['collusion_detected'] else 'clean'}")
        print(f"  Ledger events: {d['ledger_events_total']}")
        print("=" * 60)


class MetricsCollector:
    """
    Reads back from the live API to compute scenario metrics.
    Uses a probe client (login as one of the agents or the founder).
    """

    def __init__(self, probe_handle: str, probe_password: str):
        self.probe = OrbSysClient(probe_handle, probe_password, TEST_ORG_SLUG)

    async def setup(self) -> bool:
        return await self.probe.login()

    async def close(self) -> None:
        await self.probe.close()

    async def collect(self, m: ScenarioMetrics) -> None:
        """Read current state from the API and populate metrics."""
        await asyncio.gather(
            self._collect_governance(m),
            self._collect_ledger(m),
            self._collect_anomalies(m),
            return_exceptions=True,
        )
        m.finished_at = time.time()

    async def _collect_governance(self, m: ScenarioMetrics) -> None:
        # Threads
        threads_data = await self.probe.get(
            "/commons/threads", params={"page": 1, "page_size": 1}
        )
        if isinstance(threads_data, dict):
            m.threads_created = threads_data.get("total", 0)

        # Cells
        cells_data = await self.probe.get("/cells", params={"page": 1, "page_size": 1})
        if isinstance(cells_data, dict):
            m.cells_created = cells_data.get("total", 0)

        # Motions and resolutions
        motions_data = await self.probe.get("/motions", params={"page": 1, "page_size": 1})
        if isinstance(motions_data, dict):
            m.motions_filed = motions_data.get("total", 0)

        enacted_data = await self.probe.get(
            "/motions", params={"state": "enacted", "page": 1, "page_size": 1}
        )
        if isinstance(enacted_data, dict):
            m.resolutions_enacted = enacted_data.get("total", 0)

        # STF panels
        stf_data = await self.probe.get("/stf", params={"page": 1, "page_size": 1})
        if isinstance(stf_data, dict):
            m.stf_panels = stf_data.get("total", 0)

        # Rejection rate from ledger
        gate1_approved = 0
        gate1_rejected = 0
        approved_data = await self.probe.get(
            "/ledger", params={"event_type": "motion_gate1_result",
                                "page": 1, "page_size": 100}
        )
        if isinstance(approved_data, dict):
            for ev in (approved_data.get("items") or []):
                payload = ev.get("payload", {})
                if payload.get("verdict") == "approve":
                    gate1_approved += 1
                elif payload.get("verdict") == "reject":
                    gate1_rejected += 1
        total = gate1_approved + gate1_rejected
        m.rejection_rate = gate1_rejected / total if total else 0.0

    async def _collect_ledger(self, m: ScenarioMetrics) -> None:
        # Chain verify
        verify_data = await self.probe.get("/ledger/verify")
        if isinstance(verify_data, dict):
            m.ledger_chain_intact = verify_data.get("status") == "ok"
            m.ledger_event_count  = verify_data.get("verified_events", 0)

    async def _collect_anomalies(self, m: ScenarioMetrics) -> None:
        # Read anomaly flags from the ledger
        anomaly_data = await self.probe.get(
            "/ledger", params={"event_type": "anomaly_flagged", "page": 1, "page_size": 100}
        )
        if isinstance(anomaly_data, dict):
            flags = anomaly_data.get("items", [])
            m.anomaly_flags = len(flags)
            for flag in flags:
                payload = flag.get("payload", {})
                atype   = payload.get("anomaly_type", "").upper()
                if "SYBIL" in atype or "COORDINATED" in atype:
                    m.sybil_detected = True
                if "CAPTURE" in atype or "HOMOGENEITY" in atype:
                    m.capture_detected = True
                if "COLLUSION" in atype or "ENDORSEMENT" in atype:
                    m.collusion_detected = True

    def aggregate_agent_actions(self, agents: list[Any], m: ScenarioMetrics) -> None:
        for a in agents:
            m.total_posts          += a.actions.get("posts", 0)
            m.total_contributions  += a.actions.get("contributions", 0)
            m.total_votes          += a.actions.get("votes", 0)
            m.total_reviews        += a.actions.get("reviews", 0)
            m.total_verdicts_filed += a.actions.get("verdicts", 0)
            if any(v > 0 for v in a.actions.values()):
                m.active_agents += 1
