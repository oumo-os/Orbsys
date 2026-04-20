"""
Scenario runner — orchestrates agent spawning, concurrent activity loops,
and batch growth over time.

Usage:
    python runner.py --scenario normal   --agents 50  --duration 300
    python runner.py --scenario sybil    --agents 200 --duration 600 --report results.json
    python runner.py --scenario capture  --agents 100 --duration 600
    python runner.py --scenario collusion --agents 80 --duration 400
    python runner.py --scenario stress   --agents 500 --concurrent 100 --duration 300
    python runner.py --scenario mixed    --agents 200 --spawn-rate 15 --duration 600
    python runner.py --scenario all      --agents 80  --duration 240 --report all.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import time
from typing import Any

from agent import Agent
from config import (
    API_URL, TEST_ORG_SLUG, AGENT_CONCURRENCY,
    CYCLE_INTERVAL, SPAWN_BATCH_SIZE, MAX_AGENTS,
)
from factory import AgentFactory, AgentProfile
from metrics import MetricsCollector, ScenarioMetrics
from setup import auto_approve_applications, FOUNDER_HANDLE, FOUNDER_PASSWORD

log = logging.getLogger(__name__)



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
    Manages a growing pool of agents.
      - Concurrent activity (semaphore-limited)
      - Progressive spawning on demand
      - Dormancy baked into each agent's cycle
    """

    def __init__(self, concurrency: int, dormain_map: dict[str, str]):
        self._concurrency = concurrency
        self._dormain_map = dormain_map
        self._agents: list[Agent] = []
        self._setup_sem  = asyncio.Semaphore(20)
        self._active_sem = asyncio.Semaphore(concurrency)
        self._factory    = AgentFactory()

    @property
    def agents(self) -> list[Agent]:
        return self._agents

    @property
    def count(self) -> int:
        return len(self._agents)

    async def add_profiles(self, profiles: list[AgentProfile]) -> int:
        tasks   = [self._setup_one(p) for p in profiles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)

    async def _setup_one(self, profile: AgentProfile) -> bool:
        async with self._setup_sem:
            agent = Agent(profile)
            ok    = await agent.setup(self._dormain_map)
            if ok:
                self._agents.append(agent)
                log.info(f"  @{profile.handle} ready "
                         f"(intent={profile.intent}, activity={profile.activity_level:.2f})")
            else:
                log.debug(f"  @{profile.handle} setup failed")
            return ok

    async def run_cycle(self) -> None:
        tasks = [self._run_one(a) for a in self._agents]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_one(self, agent: Agent) -> None:
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
        if self.count >= MAX_AGENTS:
            log.warning(f"MAX_AGENTS ({MAX_AGENTS}) reached")
            return 0
        n = min(n, MAX_AGENTS - self.count)

        if scenario == "sybil":
            profiles = await self._factory.spawn_sybil_cluster(n, target_dormain)
        elif scenario == "capture":
            profiles = await self._factory.spawn_capture_cluster(n, target_dormain)
        elif scenario == "collusion":
            profiles = await self._factory.spawn_collusion_ring(n)
        elif scenario in ("stress", "normal"):
            profiles = await self._factory.spawn_genuine(n)
        else:  # mixed
            profiles = await self._factory.spawn_batch(n)

        return await self.add_profiles(profiles)


# ── Scenario dispatch ─────────────────────────────────────────────────────────

async def _run_scenario(
    name: str,
    pool: AgentPool,
    duration: int,
    metrics: ScenarioMetrics,
    spawn_rate: int,
) -> None:
    from scenarios.normal      import run     as run_normal
    from scenarios.adversarial import run_sybil, run_capture, run_collusion
    from scenarios.stress      import run_stress, run_mixed

    dispatch = {
        "normal":    lambda: run_normal(pool, duration, metrics),
        "sybil":     lambda: run_sybil(pool, duration, metrics),
        "capture":   lambda: run_capture(pool, duration, metrics),
        "collusion": lambda: run_collusion(pool, duration, metrics),
        "stress":    lambda: run_stress(pool, duration, metrics),
        "mixed":     lambda: run_mixed(pool, duration, metrics, spawn_rate),
    }
    fn = dispatch.get(name)
    if fn:
        await fn()
    else:
        log.error(f"Unknown scenario: {name}")


# ── Metrics enrichment ────────────────────────────────────────────────────────

async def _enrich_metrics(
    collector: MetricsCollector,
    pool: AgentPool,
    metrics: ScenarioMetrics,
) -> None:
    """
    Gather PAAS paper validation signals and security detection results.
    Reads from the live API via the probe client.
    """
    # Aggregate agent actions
    collector.aggregate_agent_actions(pool.agents, metrics)

    # Collect from API
    await collector.collect(metrics)

    # PAAS C1: meritocracy — check top vs bottom W_s spread
    try:
        top_dormain_data = await collector.probe.get(
            "/competence/leaderboard/dummy",  # will 404 but shows the pattern
        )
    except Exception:
        pass

    # PAAS C3: participation breadth
    dormain_data = await collector.probe.get("/competence/dormains")
    dormains = collector.probe.items(dormain_data)
    if dormains:
        active_dormains = 0
        for d in dormains:
            lb = await collector.probe.get(
                f"/competence/leaderboard/{d['id']}",
                params={"page": 1, "page_size": 1}
            )
            if isinstance(lb, dict) and lb.get("total", 0) > 0:
                active_dormains += 1
        metrics.__dict__["dormain_coverage"] = (
            active_dormains / len(dormains) if dormains else 0.0
        )

    # C4: aSTF rate breakdown
    gate1_data = await collector.probe.get(
        "/ledger", params={"event_type": "motion_gate1_result",
                            "page": 1, "page_size": 200}
    )
    if isinstance(gate1_data, dict):
        events = gate1_data.get("items", [])
        verdicts = [e.get("payload", {}).get("verdict", "") for e in events]
        total = len(verdicts)
        if total:
            metrics.__dict__["astf_approve_rate"]   = verdicts.count("approve") / total
            metrics.__dict__["astf_revision_rate"]  = verdicts.count("revision_request") / total
            metrics.__dict__["astf_reject_rate"]    = verdicts.count("reject") / total

    # C2: homogeneity warnings → circle_composition_warnings
    homogeneity_data = await collector.probe.get(
        "/ledger", params={"event_type": "anomaly_flagged", "page": 1, "page_size": 100}
    )
    if isinstance(homogeneity_data, dict):
        flags = homogeneity_data.get("items", [])
        metrics.__dict__["circle_composition_warnings"] = sum(
            1 for f in flags
            if "HOMOGENEITY" in f.get("payload", {}).get("anomaly_type", "").upper()
        )


# ── Main ──────────────────────────────────────────────────────────────────────

ALL_SCENARIOS = ["normal", "sybil", "capture", "collusion", "mixed", "stress"]


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
        print("ERROR: Run setup.py first to provision the test org and save dormain_map.json")
        return

    scenarios_to_run = ALL_SCENARIOS if run_all else [scenario]
    all_metrics: list[ScenarioMetrics] = []

    for s in scenarios_to_run:
        print(f"\n{'='*62}")
        print(f"  Scenario: {s.upper()}")
        print(f"  Agents: {num_agents}  Duration: {duration}s  "
              f"Concurrency: {concurrency}")
        print(f"{'='*62}")

        metrics         = ScenarioMetrics(scenario_name=s)
        metrics.total_agents = num_agents

        pool = AgentPool(concurrency=concurrency, dormain_map=dormain_map)

        # Build founder auth headers for the auto-approver
        import httpx as _httpx
        _login_r = None
        _founder_headers: dict = {}
        try:
            async with _httpx.AsyncClient(timeout=10) as _c:
                _login_r = await _c.post(
                    f"{API_URL}/auth/login",
                    json={"org_slug": TEST_ORG_SLUG,
                          "handle": FOUNDER_HANDLE,
                          "password": FOUNDER_PASSWORD},
                )
            if _login_r and _login_r.status_code == 200:
                _tok = _login_r.json()["tokens"]["access_token"]
                _founder_headers = {"Authorization": f"Bearer {_tok}"}
        except Exception:
            pass

        # Run scenario + auto-approver concurrently
        async def _scenario_with_approver():
            approver = asyncio.create_task(
                auto_approve_applications(API_URL, _founder_headers, interval=5.0)
                if _founder_headers else asyncio.sleep(0)
            )
            try:
                await _run_scenario(s, pool, duration, metrics, spawn_rate)
            except asyncio.CancelledError:
                log.info(f"Scenario '{s}' cancelled")
            except Exception as e:
                log.error(f"Scenario '{s}' error: {e}", exc_info=True)
            finally:
                approver.cancel()

        try:
            await _scenario_with_approver()
        except Exception as e:
            log.error(f"Outer scenario error: {e}")

        # Collect and enrich metrics
        collector = MetricsCollector(FOUNDER_HANDLE, FOUNDER_PASSWORD)
        if await collector.setup():
            await _enrich_metrics(collector, pool, metrics)
            await collector.close()
        else:
            log.warning("Metrics collector could not login — using agent-local data only")
            collector.aggregate_agent_actions(pool.agents, metrics)

        # Close all agent clients
        await asyncio.gather(
            *[a.client.close() for a in pool.agents],
            return_exceptions=True,
        )

        # Print results
        metrics.print_summary()

        # Print PAAS-specific claims if available
        if hasattr(metrics, "print_paas_claims"):
            metrics.print_paas_claims()

        all_metrics.append(metrics)

        if run_all and s != scenarios_to_run[-1]:
            print(f"\n  Pausing 10s before next scenario…")
            await asyncio.sleep(10)

    # Write report
    if report_path:
        report = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "configuration": {
                "num_agents": num_agents,
                "duration_s": duration,
                "concurrency": concurrency,
                "llm_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "api_url": API_URL,
                "org_slug": TEST_ORG_SLUG,
            },
            "scenarios": [m.to_dict() for m in all_metrics],
            "summary": {
                "scenarios_run": len(all_metrics),
                "total_agents_across_scenarios": sum(m.total_agents for m in all_metrics),
                "any_ledger_broken": any(
                    m.ledger_chain_intact is False for m in all_metrics
                ),
                "any_anomaly_detected": any(m.anomaly_flags > 0 for m in all_metrics),
                "sybil_detected_in": [m.scenario_name for m in all_metrics if m.sybil_detected],
                "capture_detected_in": [m.scenario_name for m in all_metrics if m.capture_detected],
                "collusion_detected_in": [m.scenario_name for m in all_metrics if m.collusion_detected],
            },
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Full report written to {report_path}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Orb Sys Agent Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  normal     Healthy governance — genuine agents, gradual growth
             Tests PAAS claims: meritocracy, participation, audit integrity
  sybil      Sybil flood — coordinated agents push one agenda
             Expected: Integrity Engine flags correlation, W_s stays low
  capture    Circle capture — systematic W_s building + membership push
             Expected: homogeneity warning, aSTF composition balancer
  collusion  Endorsement ring — mutual high-scoring network
             Expected: endorser meta-reputation, rate limits, pattern detection
  mixed      Realistic mixed population with continuous spawning
             All attack types blended with genuine agents
  stress     Concurrent load — hundreds of agents simultaneously
             Tests API throughput and engine scaling
  all        Run all scenarios in sequence, write combined report
        """,
    )
    parser.add_argument("--scenario",   default="normal",
                        choices=ALL_SCENARIOS + ["all"])
    parser.add_argument("--agents",     type=int,   default=50,
                        help="Total agent population per scenario")
    parser.add_argument("--duration",   type=int,   default=300,
                        help="Scenario duration in seconds")
    parser.add_argument("--concurrent", type=int,   default=AGENT_CONCURRENCY,
                        help="Max concurrent active agents")
    parser.add_argument("--spawn-rate", type=int,   default=SPAWN_BATCH_SIZE,
                        help="Agents per spawn batch (mixed scenario)")
    parser.add_argument("--report",     default=None, metavar="FILE",
                        help="Write JSON report to file")
    parser.add_argument("--api",        default=API_URL,
                        help="API base URL override")
    args = parser.parse_args()

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
