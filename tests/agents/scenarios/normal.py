"""
Normal scenario — healthy governance baseline.

Tests PAAS paper claims:
  C1: Meritocracy — W_s reflects genuine contribution quality
  C2: Anti-capture — no single coalition can dominate decisions
  C3: Participation — broad engagement across domains
  C4: Audit integrity — aSTF operates independently
  C5: Anti-fragility — system learns from deliberation, doesn't degrade
  C6: Ledger integrity — tamper-evident record remains intact
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from ..config import CYCLE_INTERVAL, SPAWN_BATCH_SIZE, SPAWN_INTERVAL
from ..metrics import MetricsCollector, ScenarioMetrics

log = logging.getLogger(__name__)


@dataclass
class NormalMetrics(ScenarioMetrics):
    """Extended metrics tracking PAAS-specific claims."""
    # C1: Meritocracy
    top_contributors_ws_median: float = 0.0   # W_s of top 10% posters
    bottom_contributors_ws_median: float = 0.0  # W_s of bottom 50%
    ws_gini_coefficient: float = 0.0           # 0=equal, 1=maximally unequal

    # C2: Anti-capture
    max_coalition_vote_share: float = 0.0      # highest voting bloc fraction
    circle_composition_warnings: int = 0       # homogeneity flags

    # C3: Participation
    dormain_coverage: float = 0.0              # fraction of dormains with active contributors
    avg_contributions_per_member: float = 0.0

    # C4: Audit integrity
    astf_approve_rate: float = 0.0
    astf_revision_rate: float = 0.0
    astf_reject_rate: float = 0.0

    # C5: Anti-fragility
    ws_growth_trend: str = "unknown"           # growing | stable | declining

    def print_paas_claims(self) -> None:
        print("\n  PAAS paper claim validation:")
        print(f"    C1 Meritocracy:   top-10% W_s={self.top_contributors_ws_median:.0f} "
              f"vs bottom-50% W_s={self.bottom_contributors_ws_median:.0f}")
        print(f"    C2 Anti-capture:  max coalition vote share={self.max_coalition_vote_share:.1%} "
              f"| homogeneity warnings={self.circle_composition_warnings}")
        print(f"    C3 Participation: dormain coverage={self.dormain_coverage:.0%} "
              f"| avg contributions={self.avg_contributions_per_member:.1f}")
        print(f"    C4 Audit:         approve={self.astf_approve_rate:.0%} | "
              f"revision={self.astf_revision_rate:.0%} | reject={self.astf_reject_rate:.0%}")
        print(f"    C5 Anti-fragility: W_s trend={self.ws_growth_trend}")
        print(f"    C6 Ledger:        {'✓ intact' if self.ledger_chain_intact else '✗ broken'}")


async def run(pool, duration: int, metrics: ScenarioMetrics) -> None:
    """
    Healthy governance scenario.
    Population grows gradually, agents engage genuinely.
    """
    log.info(f"[normal] duration={duration}s, target_agents={metrics.total_agents}")
    start = time.time()

    # Phase 1 (0–20%): seed initial population
    initial = max(5, metrics.total_agents // 4)
    added = await pool.spawn_batch(initial, "normal")
    log.info(f"[normal] Phase 1: {added} agents seeded")

    cycle = 0
    while (elapsed := time.time() - start) < duration:
        await pool.run_cycle()
        cycle += 1
        log.debug(f"[normal] cycle {cycle}, elapsed={elapsed:.0f}s, agents={pool.count}")

        # Phase 2 (20–60%): gradual growth
        if duration * 0.2 < elapsed < duration * 0.6:
            if pool.count < metrics.total_agents and cycle % 3 == 0:
                batch = min(SPAWN_BATCH_SIZE, metrics.total_agents - pool.count)
                await pool.spawn_batch(batch, "normal")

        # Phase 3 (60–100%): full population, observe stability
        elif elapsed > duration * 0.6 and pool.count < metrics.total_agents:
            remaining = metrics.total_agents - pool.count
            if remaining > 0:
                await pool.spawn_batch(min(SPAWN_BATCH_SIZE * 2, remaining), "normal")

        await asyncio.sleep(CYCLE_INTERVAL)
