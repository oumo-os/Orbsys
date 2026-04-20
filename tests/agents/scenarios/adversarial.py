"""
Adversarial scenarios — Sybil, Circle capture, Collusion ring.

Each scenario seeds a mixed population where adversarial agents attempt
a specific attack on the governance system. The scenario tracks whether
the PAAS mechanisms detected and neutralised the attack.

Sybil attack theory:
  Many low-W_s agents flood deliberation and vote coordinated "yea".
  Defense: low W_s = low vote weight; Integrity Engine flags coordinated
  endorsement patterns; aSTF catches thin deliberation quality.

Circle capture theory:
  Coordinated agents build W_s in one dormain and try to stack a circle.
  Defense: Inferential Engine homogeneity warning; aSTF composition balancer;
  invitation requires existing member vote.

Collusion ring theory:
  Mutual high-scoring endorsement network inflates W_s artificially.
  Defense: Endorser meta-reputation tracking (failed audits reduce M);
  rate limits on same-target endorsements; pattern detection → jSTF.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time

from ..config import CYCLE_INTERVAL, SPAWN_BATCH_SIZE
from ..metrics import ScenarioMetrics

log = logging.getLogger(__name__)


async def run_sybil(pool, duration: int, metrics: ScenarioMetrics,
                    target_dormain: str | None = None) -> None:
    """
    Sybil flood: large cluster of coordinated agents push one agenda.
    Genuine agents are seeded first to establish baseline activity.
    Sybil cluster appears ~20% through the scenario.
    """
    log.info(f"[sybil] duration={duration}s, agents={metrics.total_agents}")
    start = time.time()

    n_genuine = max(5, metrics.total_agents // 5)
    n_sybil   = metrics.total_agents - n_genuine
    target    = target_dormain or random.choice(
        ["Governance", "Security", "Protocol Engineering"]
    )

    log.info(f"[sybil] {n_genuine} genuine + {n_sybil} Sybil agents | target: '{target}'")
    metrics.genuine_agents     = n_genuine
    metrics.adversarial_agents = n_sybil

    # Seed genuine agents first
    await pool.spawn_batch(n_genuine, "normal")
    log.info(f"[sybil] Genuine agents active. Waiting before Sybil flood…")

    # Run genuine agents for 20% of duration before attack
    setup_end = start + duration * 0.20
    while time.time() < setup_end:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

    # Sybil flood — all at once for maximum impact
    log.info(f"[sybil] ATTACK: flooding with {n_sybil} Sybil agents")
    await pool.spawn_batch(n_sybil, "sybil", target)
    log.info(f"[sybil] Pool size now {pool.count}. Monitoring…")

    while time.time() - start < duration:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

    log.info(f"[sybil] Scenario complete. Check anomaly_flags and sybil_detected in metrics.")


async def run_capture(pool, duration: int, metrics: ScenarioMetrics,
                      target_dormain: str | None = None) -> None:
    """
    Circle capture: coordinated agents methodically build W_s and push for circle membership.
    More patient than Sybil — agents don't all appear at once.
    """
    log.info(f"[capture] duration={duration}s, agents={metrics.total_agents}")
    start = time.time()

    n_genuine = max(10, metrics.total_agents // 3)
    n_capture = metrics.total_agents - n_genuine
    target    = target_dormain or "Governance"

    log.info(f"[capture] {n_genuine} genuine + {n_capture} capture agents | target: '{target}' circle")
    metrics.genuine_agents     = n_genuine
    metrics.adversarial_agents = n_capture

    # Genuine population first
    await pool.spawn_batch(n_genuine, "normal")

    # Capture agents appear gradually (they're patient)
    capture_batch = max(1, n_capture // 4)
    batches_deployed = 0

    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()

        # Deploy capture agents progressively over first 50% of scenario
        if elapsed < duration * 0.5 and batches_deployed * capture_batch < n_capture:
            if elapsed > batches_deployed * (duration * 0.1):
                remaining = n_capture - batches_deployed * capture_batch
                to_spawn  = min(capture_batch, remaining)
                if to_spawn > 0:
                    await pool.spawn_batch(to_spawn, "capture", target)
                    batches_deployed += 1
                    log.info(f"[capture] Deployed capture batch {batches_deployed}, "
                             f"pool={pool.count}")

        await asyncio.sleep(CYCLE_INTERVAL)


async def run_collusion(pool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Endorsement ring: mutual high-scoring network tries to inflate W_s.
    The ring is seeded alongside genuine agents — they blend in initially.
    """
    log.info(f"[collusion] duration={duration}s, agents={metrics.total_agents}")
    start = time.time()

    n_genuine  = max(10, int(metrics.total_agents * 0.65))
    n_collude  = metrics.total_agents - n_genuine

    log.info(f"[collusion] {n_genuine} genuine + {n_collude} collusion ring")
    metrics.genuine_agents     = n_genuine
    metrics.adversarial_agents = n_collude

    # Both populations appear together — ring blends in
    await pool.spawn_batch(n_genuine, "normal")
    await asyncio.sleep(5)
    await pool.spawn_batch(n_collude, "collusion")

    log.info(f"[collusion] Full population active ({pool.count}). Running…")

    cycle = 0
    while time.time() - start < duration:
        await pool.run_cycle()
        cycle += 1
        if cycle % 5 == 0:
            log.info(f"[collusion] cycle {cycle}, elapsed={time.time()-start:.0f}s")
        await asyncio.sleep(CYCLE_INTERVAL)
