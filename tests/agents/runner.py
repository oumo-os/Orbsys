"""
Scenario runner — orchestrates agent spawning, concurrent activity loops,
and batch growth over time.

Usage:
    python runner.py --scenario normal --agents 50 --duration 300
    python runner.py --scenario sybil  --agents 200 --duration 600 --report
    python runner.py --scenario stress --agents 500 --concurrent 100
    python runner.py --scenario mixed  --agents 100 --spawn-rate 10 --duration 600
    python runner.py --scenario all    --agents 80  --report metrics.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import time
from typing import Sequence

from agent import Agent
from config import (
    API_URL, TEST_ORG_SLUG, AGENT_CONCURRENCY, CYCLE_INTERVAL,
    SPAWN_BATCH_SIZE, SPAWN_INTERVAL, MAX_AGENTS,
)
from factory import AgentFactory, AgentProfile
from metrics import MetricsCollector, ScenarioMetrics

log = logging.getLogger(__name__)

FOUNDER_HANDLE   = "sim-founder"
FOUNDER_PASSWORD = "sim-founder-2025"


# ── Dormain map loader ────────────────────────────────────────────────────────

def load_dormain_map() -> dict[str, str]:
    if os.path.exists("dormain_map.json"):
        with open("dormain_map.json") as f:
            return json.load(f)
    log.warning("dormain_map.json not found — run setup.py first")
    return {}


# ── Agent pool ────────────────────────────────────────────────────────────────

class AgentPool:
    """
    Manages a growing pool of agents. Handles:
    - Concurrent activity (semaphore-limited)
    - Progressive spawning over time
    - Dormancy (most agents inactive per cycle)
    """

    def __init__(self, concurrency: int, dormain_map: dict[str, str]):
        self._concurrency = concurrency
        self._dormain_map = dormain_map
        self._agents: list[Agent] = []
        self._setup_sem = asyncio.Semaphore(20)   # limit parallel registrations
        self._active_sem = asyncio.Semaphore(concurrency)
        self._factory = AgentFactory()

    @property
    def agents(self) -> list[Agent]:
        return self._agents

    @property
    def count(self) -> int:
        return len(self._agents)

    async def add_profiles(self, profiles: list[AgentProfile]) -> int:
        """Register and setup agents from profiles. Returns count added."""
        added = 0
        tasks = []
        for p in profiles:
            tasks.append(self._setup_one(p))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                added += 1
        return added

    async def _setup_one(self, profile: AgentProfile) -> bool:
        async with self._setup_sem:
            agent = Agent(profile)
            ok = await agent.setup(self._dormain_map)
            if ok:
                self._agents.append(agent)
                log.info(f"  Agent @{profile.handle} ready "
                         f"(intent={profile.intent}, activity={profile.activity_level:.2f})")
            return ok

    async def run_cycle(self) -> None:
        """Run one cycle for all agents concurrently (semaphore-limited)."""
        tasks = [self._run_one_cycle(a) for a in self._agents]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_one_cycle(self, agent: Agent) -> None:
        async with self._active_sem:
            try:
                await agent.run_cycle()
            except Exception as e:
                log.debug(f"[{agent.h}] cycle error: {e}")

    async def spawn_batch(
        self,
        n: int,
        scenario: str = "normal",
        target_dormain: str | None = None,
    ) -> int:
        """Spawn a new batch. scenario determines the population mix."""
        if self.count >= MAX_AGENTS:
            log.warning(f"MAX_AGENTS ({MAX_AGENTS}) reached — not spawning")
            return 0

        n = min(n, MAX_AGENTS - self.count)
        log.info(f"Spawning batch of {n} (scenario={scenario}, total will be {self.count+n})")

        if scenario == "sybil":
            profiles = await self._factory.spawn_sybil_cluster(n, target_dormain)
        elif scenario == "capture":
            profiles = await self._factory.spawn_capture_cluster(n, target_dormain)
        elif scenario == "collusion":
            profiles = await self._factory.spawn_collusion_ring(n)
        elif scenario == "stress":
            # Pure genuine load — no adversarial agents
            profiles = await self._factory.spawn_genuine(n)
        elif scenario == "mixed":
            profiles = await self._factory.spawn_batch(n)
        else:  # normal
            profiles = await self._factory.spawn_genuine(n)

        return await self.add_profiles(profiles)


# ── Scenario definitions ──────────────────────────────────────────────────────

async def run_normal(pool: AgentPool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Healthy governance: genuine agents, gradual population growth.
    Tests that meritocracy emerges, aSTF works, ledger stays intact.
    """
    log.info(f"[normal] Starting — duration={duration}s")
    start = time.time()

    # Initial batch
    initial = min(metrics.total_agents // 3, SPAWN_BATCH_SIZE)
    await pool.spawn_batch(initial, "normal")

    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

        # Progressively grow population
        if elapsed > duration * 0.2 and pool.count < metrics.total_agents:
            batch = min(SPAWN_BATCH_SIZE, metrics.total_agents - pool.count)
            added = await pool.spawn_batch(batch, "normal")
            if added:
                log.info(f"[normal] Pool grown to {pool.count} agents")

    metrics.active_agents = sum(1 for a in pool.agents if any(v > 0 for v in a.actions.values()))


async def run_sybil(pool: AgentPool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Sybil flood: large cluster of coordinated low-competence agents try to
    push one governance agenda. Tests Integrity Engine anomaly detection.
    """
    log.info(f"[sybil] Starting — duration={duration}s")
    start = time.time()

    n_genuine  = max(5, metrics.total_agents // 5)
    n_sybil    = metrics.total_agents - n_genuine
    target_d   = "Governance"

    log.info(f"[sybil] Seeding {n_genuine} genuine + {n_sybil} sybil agents targeting '{target_d}'")

    await pool.spawn_batch(n_genuine, "normal")
    await asyncio.sleep(5)  # let genuine agents establish first
    await pool.spawn_batch(n_sybil, "sybil", target_d)

    while time.time() - start < duration:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

    metrics.adversarial_agents = n_sybil
    metrics.genuine_agents     = n_genuine


async def run_capture(pool: AgentPool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Circle capture attempt: coordinated agents build W_s in one domain
    and try to stack a circle. Tests homogeneity detection and aSTF independence.
    """
    log.info(f"[capture] Starting — duration={duration}s")
    start = time.time()

    n_genuine = max(5, metrics.total_agents // 3)
    n_capture = metrics.total_agents - n_genuine
    target_d  = random.choice(["Governance", "Security", "Treasury"])

    log.info(f"[capture] {n_capture} capture agents targeting '{target_d}' circle")

    await pool.spawn_batch(n_genuine, "normal")
    await asyncio.sleep(10)
    await pool.spawn_batch(n_capture, "capture", target_d)

    while time.time() - start < duration:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

    metrics.adversarial_agents = n_capture
    metrics.genuine_agents     = n_genuine


async def run_collusion(pool: AgentPool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Endorsement ring: mutual high-scoring collusion. Tests rate limits,
    endorser meta-reputation tracking, and pattern detection.
    """
    log.info(f"[collusion] Starting — duration={duration}s")
    start = time.time()

    n_genuine   = max(10, int(metrics.total_agents * 0.6))
    n_collude   = metrics.total_agents - n_genuine

    await pool.spawn_batch(n_genuine, "normal")
    await asyncio.sleep(5)
    await pool.spawn_batch(n_collude, "collusion")

    while time.time() - start < duration:
        await pool.run_cycle()
        await asyncio.sleep(CYCLE_INTERVAL)

    metrics.adversarial_agents = n_collude
    metrics.genuine_agents     = n_genuine


async def run_mixed(
    pool: AgentPool, duration: int, metrics: ScenarioMetrics,
    spawn_rate: int = 10,
) -> None:
    """
    Mixed realistic population with continuous background spawning.
    New agents appear throughout the run — some genuine, some adversarial.
    Closest to real-world conditions.
    """
    log.info(f"[mixed] Starting — duration={duration}s, spawn_rate={spawn_rate}/interval")
    start = time.time()

    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()

        if elapsed % SPAWN_INTERVAL < CYCLE_INTERVAL and pool.count < metrics.total_agents:
            batch = min(spawn_rate, metrics.total_agents - pool.count)
            await pool.spawn_batch(batch, "mixed")

        await asyncio.sleep(CYCLE_INTERVAL)


async def run_stress(pool: AgentPool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    High-volume concurrent load — hundreds of active agents simultaneously.
    Tests API throughput, event bus backpressure, and engine scaling.
    """
    log.info(f"[stress] Starting — {metrics.total_agents} agents, duration={duration}s")
    start = time.time()

    # Spawn all genuine agents upfront in large batches
    for i in range(0, metrics.total_agents, 50):
        batch = min(50, metrics.total_agents - i)
        await pool.spawn_batch(batch, "stress")
        log.info(f"[stress] Spawned {pool.count} / {metrics.total_agents}")

    log.info(f"[stress] All agents spawned — running {duration}s under load")
    while time.time() - start < duration:
        await pool.run_cycle()
        await asyncio.sleep(max(1, CYCLE_INTERVAL / 4))  # faster cycles for stress


SCENARIOS = {
    "normal":    run_normal,
    "sybil":     run_sybil,
    "capture":   run_capture,
    "collusion": run_collusion,
    "mixed":     run_mixed,
    "stress":    run_stress,
}


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(
    scenario: str,
    num_agents: int,
    duration: int,
    concurrency: int,
    spawn_rate: int,
    report_path: str | None,
    run_all: bool,
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    dormain_map = load_dormain_map()
    if not dormain_map:
        print("ERROR: Run setup.py first to provision the test org.")
        return

    scenarios_to_run = list(SCENARIOS.keys()) if run_all else [scenario]
    all_metrics: list[ScenarioMetrics] = []

    for s in scenarios_to_run:
        print(f"\n{'='*60}")
        print(f"  Running scenario: {s.upper()}")
        print(f"  Agents: {num_agents}  Duration: {duration}s  Concurrency: {concurrency}")
        print(f"{'='*60}\n")

        metrics = ScenarioMetrics(scenario_name=s)
        metrics.total_agents = num_agents

        pool = AgentPool(concurrency=concurrency, dormain_map=dormain_map)

        fn = SCENARIOS[s]
        kwargs = {}
        if s == "mixed":
            kwargs["spawn_rate"] = spawn_rate

        try:
            await fn(pool, duration, metrics, **kwargs)
        except asyncio.CancelledError:
            log.info(f"Scenario '{s}' cancelled")

        # Aggregate agent-level metrics
        collector = MetricsCollector(FOUNDER_HANDLE, FOUNDER_PASSWORD)
        if await collector.setup():
            collector.aggregate_agent_actions(pool.agents, metrics)
            await collector.collect(metrics)
            await collector.close()
        else:
            log.warning("Metrics collector could not login — using agent-local data only")
            collector.aggregate_agent_actions(pool.agents, metrics)

        # Close all agent clients
        await asyncio.gather(
            *[a.client.close() for a in pool.agents],
            return_exceptions=True,
        )

        metrics.print_summary()
        all_metrics.append(metrics)

        if run_all and s != scenarios_to_run[-1]:
            print(f"\nPausing 10s before next scenario…")
            await asyncio.sleep(10)

    if report_path:
        report = [m.to_dict() for m in all_metrics]
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull metrics written to {report_path}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Orb Sys Agent Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  normal     Healthy governance — genuine agents, gradual growth
  sybil      Sybil flood — coordinated agents push one agenda
  capture    Circle capture — coordinated W_s building in one domain
  collusion  Endorsement ring — mutual high-scoring network
  mixed      Realistic mixed population with continuous spawning
  stress     Concurrent load — hundreds of agents simultaneously
  all        Run all scenarios in sequence
        """,
    )
    parser.add_argument("--scenario",    default="normal",    choices=list(SCENARIOS.keys()) + ["all"])
    parser.add_argument("--agents",      type=int, default=50,  help="Total agent population")
    parser.add_argument("--duration",    type=int, default=300, help="Duration in seconds")
    parser.add_argument("--concurrent",  type=int, default=AGENT_CONCURRENCY, help="Max concurrent agents")
    parser.add_argument("--spawn-rate",  type=int, default=SPAWN_BATCH_SIZE,  help="Agents spawned per batch (mixed)")
    parser.add_argument("--report",      default=None, metavar="FILE", help="Write JSON report to file")
    parser.add_argument("--api",         default=API_URL, help="API URL")
    args = parser.parse_args()

    # Override API_URL if provided
    if args.api != API_URL:
        os.environ["API_URL"] = args.api

    asyncio.run(main(
        scenario=args.scenario if args.scenario != "all" else "normal",
        num_agents=args.agents,
        duration=args.duration,
        concurrency=args.concurrent,
        spawn_rate=args.spawn_rate,
        report_path=args.report,
        run_all=args.scenario == "all",
    ))


if __name__ == "__main__":
    cli()
