"""
Agent engine configuration — all settings from environment variables.
No imports from the Orb Sys codebase.
"""
from __future__ import annotations
import os

# ── API endpoints ──────────────────────────────────────────────────────────────
API_URL       = os.environ.get("API_URL",       "http://localhost:8000")
BLIND_API_URL = os.environ.get("BLIND_API_URL", "http://localhost:8001")

# ── Test org ──────────────────────────────────────────────────────────────────
TEST_ORG_SLUG = os.environ.get("TEST_ORG_SLUG", "paas-sim")
TEST_ORG_NAME = os.environ.get("TEST_ORG_NAME", "PAAS Simulation Org")

# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.environ.get("ANTHROPIC_MODEL",   "claude-sonnet-4-20250514")
LLM_ENABLED       = bool(ANTHROPIC_API_KEY)

# ── Concurrency & pacing ─────────────────────────────────────────────────────
AGENT_CONCURRENCY = int(os.environ.get("AGENT_CONCURRENCY", "50"))
RATE_LIMIT        = float(os.environ.get("RATE_LIMIT", "2.0"))   # req/s per agent
GLOBAL_RATE_LIMIT = float(os.environ.get("GLOBAL_RATE_LIMIT", "100"))  # req/s total
CYCLE_INTERVAL    = float(os.environ.get("CYCLE_INTERVAL", "30"))      # seconds
JITTER            = float(os.environ.get("JITTER", "6"))               # ±seconds

# ── Spawn dynamics ────────────────────────────────────────────────────────────
SPAWN_BATCH_SIZE  = int(os.environ.get("SPAWN_BATCH_SIZE", "10"))
SPAWN_INTERVAL    = float(os.environ.get("SPAWN_INTERVAL", "60"))   # seconds between batches
MAX_AGENTS        = int(os.environ.get("MAX_AGENTS", "1000"))
DORMANCY_PROB     = float(os.environ.get("DORMANCY_PROB", "0.7"))   # fraction of agents inactive per cycle

# ── Scenario defaults ─────────────────────────────────────────────────────────
DEFAULT_SCENARIO  = os.environ.get("SCENARIO", "normal")
SCENARIO_DURATION = int(os.environ.get("SCENARIO_DURATION", "300"))  # seconds

# ── Domains seeded for the test org ──────────────────────────────────────────
# These match the PAAS paper's domain taxonomy.
TEST_ORG_DORMAINS = [
    {"name": "Governance",           "description": "Org governance, policy, and process."},
    {"name": "Protocol Engineering", "description": "Core protocol design and consensus."},
    {"name": "Community",            "description": "Member relations and community health."},
    {"name": "Security",             "description": "Security assurance and audit."},
    {"name": "Treasury",             "description": "Resource allocation and budget."},
    {"name": "Research",             "description": "Research methodology and evidence."},
]

TEST_ORG_CIRCLES = [
    {"name": "Governance Circle",       "dormains": ["Governance"]},
    {"name": "Protocol Circle",         "dormains": ["Protocol Engineering"]},
    {"name": "Community Circle",        "dormains": ["Community"]},
    {"name": "Security Circle",         "dormains": ["Security"]},
    {"name": "Treasury Circle",         "dormains": ["Treasury"]},
    {"name": "Research Circle",         "dormains": ["Research"]},
    {"name": "Org Integrity Circle",    "dormains": ["Governance", "Community"]},
    {"name": "Judicial Circle",         "dormains": ["Governance"]},
]
