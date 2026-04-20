"""
Stress scenario — concurrent load and progressive scale testing.

Tests:
  - API throughput under concurrent agent load
  - NATS JetStream backpressure handling
  - Integrity Engine write throughput (ΔC, ledger events)
  - Inferential Engine STF matching at scale
  - Database connection pool behaviour
  - Memory and CPU patterns under sustained load
"""
from __future__ import annotations

import asyncio
import logging
import time

from ..config import CYCLE_INTERVAL
from ..metrics import ScenarioMetrics

log = logging.getLogger(__name__)


async def run_stress(pool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Full concurrent stress: spawn all agents upfront, run at full concurrency.
    Most realistic test of the system's capacity ceiling.
    """
    log.info(f"[stress] target={metrics.total_agents}, duration={duration}s, "
             f"concurrency={pool._concurrency}")
    start = time.time()

    # Spawn all agents in rapid batches of 50
    log.info(f"[stress] Spawning {metrics.total_agents} agents…")
    for i in range(0, metrics.total_agents, 50):
        batch = min(50, metrics.total_agents - i)
        added = await pool.spawn_batch(batch, "stress")
        log.info(f"[stress] Pool: {pool.count} / {metrics.total_agents} (+{added})")
        await asyncio.sleep(1)  # brief pause between registration bursts

    log.info(f"[stress] All agents ready. Running sustained load for {duration}s…")

    # Fast cycles during stress — less sleep between rounds
    fast_interval = max(1.0, CYCLE_INTERVAL / 4)
    cycle = 0
    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()
        cycle += 1
        if cycle % 10 == 0:
            log.info(f"[stress] cycle {cycle}, elapsed={elapsed:.0f}s, agents={pool.count}")
        await asyncio.sleep(fast_interval)

    metrics.adversarial_agents = 0
    metrics.genuine_agents     = pool.count
    log.info(f"[stress] Complete. {cycle} cycles over {time.time()-start:.0f}s")


async def run_mixed(pool, duration: int, metrics: ScenarioMetrics,
                    spawn_rate: int = 10) -> None:
    """
    Progressive mixed population — closest to real-world conditions.
    New agents (genuine and adversarial) appear throughout the run.
    """
    log.info(f"[mixed] duration={duration}s, target={metrics.total_agents}, "
             f"spawn_rate={spawn_rate}/interval")
    start = time.time()
    last_spawn = start
    spawn_interval = 60.0  # seconds between spawn batches

    cycle = 0
    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()
        cycle += 1

        # Progressive spawning
        now = time.time()
        if now - last_spawn >= spawn_interval and pool.count < metrics.total_agents:
            batch = min(spawn_rate, metrics.total_agents - pool.count)
            await pool.spawn_batch(batch, "mixed")
            last_spawn = now
            log.info(f"[mixed] Batch spawned, pool now {pool.count}")

        await asyncio.sleep(CYCLE_INTERVAL)

    metrics.genuine_agents     = int(pool.count * 0.75)
    metrics.adversarial_agents = pool.count - metrics.genuine_agents
