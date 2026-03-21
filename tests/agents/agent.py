"""
Individual agent — LLM-powered decision making and content generation.

Each agent has a persona (from the factory), a session (from the client),
and an activity loop. When ANTHROPIC_API_KEY is set, the agent consults
Claude to decide what to do and what to write. The LLM is given the persona
and a snapshot of the current system state but NOT the agent's intent field.

The adversarial behaviour emerges from the persona framing, not from the LLM
being told to "be adversarial" — this makes the test more realistic.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

import httpx

from .client import OrbSysClient
from .config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL, LLM_ENABLED,
    CYCLE_INTERVAL, JITTER, TEST_ORG_SLUG,
)
from .factory import AgentProfile

log = logging.getLogger(__name__)


# ── LLM decision engine ───────────────────────────────────────────────────────

async def _llm_decide(
    persona: AgentProfile,
    state_summary: str,
    choices: list[str],
    task: str = "action",
) -> str:
    """
    Ask Claude what this agent would do given their persona and the current state.
    Returns one of the choices. Falls back to random on failure.
    """
    if not LLM_ENABLED or not choices:
        return random.choice(choices) if choices else ""

    system = (
        f"You are simulating a member of a governance platform. "
        f"Your background: {persona.background} "
        f"Your personality: {persona.personality} "
        f"Your writing style: {persona.writing_style}. "
        f"Respond with ONLY the chosen option — no explanation."
    )

    prompt = (
        f"Current system state:\n{state_summary}\n\n"
        f"Task: {task}\n"
        f"Options: {json.dumps(choices)}\n"
        f"Choose the option that best fits your persona."
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 50,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if r.status_code != 200:
                return random.choice(choices)
            text = r.json()["content"][0]["text"].strip().strip('"').strip("'")
            # Match to closest choice
            for c in choices:
                if c.lower() in text.lower() or text.lower() in c.lower():
                    return c
            return random.choice(choices)
    except Exception as e:
        log.debug(f"LLM decide error: {e}")
        return random.choice(choices)


async def _llm_write(
    persona: AgentProfile,
    context: str,
    task: str,
    max_tokens: int = 200,
) -> str:
    """
    Ask Claude to write content in the agent's voice.
    Falls back to a context-derived string on failure.
    """
    if not LLM_ENABLED:
        return _fallback_write(task, context, persona)

    system = (
        f"You are writing as a member of a governance platform. "
        f"Background: {persona.background} "
        f"Personality: {persona.personality} "
        f"Writing style: {persona.writing_style}. "
        f"Keep responses concise and in-character. "
        f"Do NOT mention you are an AI or a simulation. "
        f"Write naturally as a human would."
    )

    prompt = f"Context:\n{context}\n\nTask: {task}\n\nWrite your response:"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if r.status_code != 200:
                return _fallback_write(task, context, persona)
            return r.json()["content"][0]["text"].strip()
    except Exception as e:
        log.debug(f"LLM write error: {e}")
        return _fallback_write(task, context, persona)


def _fallback_write(task: str, context: str, persona: AgentProfile) -> str:
    """Rule-based fallback when LLM is unavailable."""
    primary = next(
        (d for d, w in sorted(persona.dormain_weights.items(),
                               key=lambda x: x[1], reverse=True)),
        "Governance"
    )
    snippets = {
        "post": [
            f"Engaging with this thread from a {primary} perspective. "
            f"The core tension here deserves careful deliberation.",
            f"Adding context: the {primary} implications of this proposal "
            f"are worth examining before we move to a motion.",
            f"Strong +1 on the need for this discussion. "
            f"I'd want to see more data before endorsing any specific approach.",
            f"This touches on some fundamental questions about how we govern {primary.lower()}. "
            f"Happy to contribute to a deliberation cell if someone sponsors this.",
        ],
        "contribution": [
            f"From a {primary} standpoint: the key consideration is proportionality.",
            f"I want to flag a potential tension with our existing approach to {primary.lower()}.",
            f"Adding evidence to the record: the literature on {primary.lower()} suggests "
            f"we should be cautious about unilateral changes.",
            f"The deliberation so far has been good. One angle that hasn't been fully explored: "
            f"what happens at the edges of this proposal?",
        ],
        "rationale": [
            f"Evidence quality adequate for decision stakes. Process was sound.",
            f"Deliberation covered the key dimensions. No material gaps identified.",
            f"The core argument is well-supported. Recommending approval.",
            f"Returning for additional deliberation. Evidence base needs strengthening.",
        ],
        "directive": [
            f"Based on deliberation in this cell, the {primary} Circle should review "
            f"and consider adopting the approach discussed.",
            f"The cell has identified a clear path forward. "
            f"Proposing that the relevant circle implement as deliberated.",
        ],
    }
    for key, lines in snippets.items():
        if key in task.lower():
            return random.choice(lines)
    return f"Contributing to deliberation on this matter from a {primary} perspective."


# ── Individual agent ──────────────────────────────────────────────────────────

class Agent:
    """
    One agent instance. LLM-powered when ANTHROPIC_API_KEY is available.
    The agent's intent is known to us (the test harness) but not reflected
    in any API calls — adversarial behaviour emerges from the persona.
    """

    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.client  = OrbSysClient(
            handle=profile.handle,
            password=profile.password,
            org_slug=TEST_ORG_SLUG,
        )
        # Track what we've interacted with to avoid redundant actions
        self._commented_threads: set[str] = set()
        self._voted_motions:     set[str] = set()
        self._reviewed_posts:    set[str] = set()
        self._dormain_map:       dict[str, str] = {}  # name → uuid

        # Metrics
        self.actions: dict[str, int] = {
            "posts": 0, "contributions": 0, "votes": 0,
            "reviews": 0, "sponsorships": 0, "verdicts": 0,
        }

    @property
    def h(self) -> str:
        return self.profile.handle

    async def setup(self, dormain_map: dict[str, str]) -> bool:
        """Register or login, declare curiosities."""
        self._dormain_map = dormain_map

        # Try login first (agent may already exist from a previous run)
        ok = await self.client.login()
        if not ok:
            ok = await self.client.register(
                self.profile.display_name, self.profile.email
            )
            if not ok:
                return False
            ok = await self.client.login()
            if not ok:
                return False

        await self._declare_curiosities()
        return True

    async def _declare_curiosities(self) -> None:
        curiosity_payload = {
            self._dormain_map[name]: signal
            for name, signal in self.profile.curiosities.items()
            if name in self._dormain_map
        }
        if curiosity_payload:
            await self.client.request(
                "PUT", "/members/me/curiosities",
                json={"curiosities": curiosity_payload}
            )

    async def run_cycle(self) -> None:
        """
        One activity cycle. The agent decides what to do based on system state.
        Dormancy — most agents skip most cycles (realistic participation rates).
        """
        from .config import DORMANCY_PROB
        if random.random() < DORMANCY_PROB * (1.0 - self.profile.activity_level):
            return  # dormant this cycle

        # Gather current system state (lightweight reads)
        state = await self._observe_state()
        if not state:
            return

        jitter_sleep = lambda: asyncio.sleep(abs(random.gauss(0, JITTER / 3)))

        # Action selection: LLM decides what to prioritise this cycle
        possible_actions = self._eligible_actions(state)
        if not possible_actions:
            return

        state_summary = self._summarise_state(state)
        chosen = await _llm_decide(
            self.profile, state_summary, possible_actions,
            task="Choose which governance activity to do this cycle"
        )

        await jitter_sleep()

        if chosen == "post_to_commons":
            await self._act_post(state)
        elif chosen == "contribute_to_cell":
            await self._act_contribute(state)
        elif chosen == "vote_on_motion":
            await self._act_vote(state)
        elif chosen == "file_formal_review":
            await self._act_review(state)
        elif chosen == "sponsor_thread":
            await self._act_sponsor(state)
        elif chosen == "file_stf_verdict":
            await self._act_verdict(state)
        elif chosen == "crystallise_cell":
            await self._act_crystallise(state)

    # ── State observation ─────────────────────────────────────────────────────

    async def _observe_state(self) -> dict | None:
        state: dict[str, Any] = {}

        threads_data = await self.client.get(
            "/commons/threads", params={"state": "open", "page": 1, "page_size": 8}
        )
        state["threads"] = self.client.items(threads_data)

        cells_data = await self.client.get(
            "/cells", params={"state": "active", "page": 1, "page_size": 6}
        )
        state["cells"] = self.client.items(cells_data)

        stf_data = await self.client.get(
            "/stf", params={"state": "active", "page": 1, "page_size": 6}
        )
        state["stf_instances"] = self.client.items(stf_data)

        return state if any(state.values()) else None

    def _summarise_state(self, state: dict) -> str:
        threads = state.get("threads", [])
        cells   = state.get("cells", [])
        stf     = state.get("stf_instances", [])
        top_dormain = max(
            self.profile.dormain_weights,
            key=lambda k: self.profile.dormain_weights[k],
            default="Governance"
        )
        return (
            f"There are {len(threads)} open Commons threads, "
            f"{len(cells)} active deliberation cells, "
            f"and {len(stf)} active STF panels. "
            f"Your primary expertise is in {top_dormain}."
        )

    def _eligible_actions(self, state: dict) -> list[str]:
        p = self.profile
        actions = []
        threads = state.get("threads", [])
        cells   = state.get("cells", [])
        stf     = state.get("stf_instances", [])

        new_threads = [t for t in threads if t.get("id") not in self._commented_threads]
        if new_threads and random.random() < p.post_frequency:
            actions.append("post_to_commons")

        if cells and random.random() < p.post_frequency:
            actions.append("contribute_to_cell")

        if cells and random.random() < p.vote_frequency:
            actions.append("vote_on_motion")

        if new_threads and random.random() < p.review_frequency:
            actions.append("file_formal_review")

        if new_threads and random.random() < p.sponsor_frequency:
            actions.append("sponsor_thread")

        if stf and random.random() < p.stf_diligence:
            actions.append("file_stf_verdict")

        # Crystallise if we initiated any active cells with enough contributions
        if cells and random.random() < 0.3:
            actions.append("crystallise_cell")

        return actions

    # ── Action implementations ────────────────────────────────────────────────

    async def _act_post(self, state: dict) -> None:
        threads = [t for t in state.get("threads", [])
                   if t.get("id") not in self._commented_threads]
        if not threads:
            return

        # Pick thread: Sybil/capture agents bias toward their target dormain
        thread = self._pick_thread(threads)
        context = (
            f"Thread title: {thread.get('title', '')}\n"
            f"Preview: {thread.get('body_preview', '')[:200]}"
        )
        body = await _llm_write(
            self.profile, context,
            f"Write a reply post to this Commons thread. "
            f"Your expertise is in {list(self.profile.dormain_weights.keys())[:2]}.",
            max_tokens=180,
        )

        result = await self.client.post(
            f"/commons/threads/{thread['id']}/posts", {"body": body}
        )
        if result:
            self._commented_threads.add(thread["id"])
            self.actions["posts"] += 1
            log.debug(f"[{self.h}] posted to thread '{thread.get('title','')[:35]}'")

    async def _act_contribute(self, state: dict) -> None:
        cells = state.get("cells", [])
        if not cells:
            return
        cell = random.choice(cells)
        context = f"Cell mandate: {cell.get('founding_mandate', '')[:200]}"
        body = await _llm_write(
            self.profile, context,
            "Write a contribution to this deliberation cell.",
            max_tokens=160,
        )
        result = await self.client.post(
            f"/cells/{cell['id']}/contributions",
            {"body": body, "contribution_type": "discussion"},
        )
        if result:
            self.actions["contributions"] += 1
            log.debug(f"[{self.h}] contributed to cell {cell['id'][:8]}")

    async def _act_vote(self, state: dict) -> None:
        cells = state.get("cells", [])
        for cell in cells[:3]:
            votes = await self.client.get(f"/cells/{cell['id']}/votes")
            if not votes or not votes.get("motion_id"):
                continue
            motion_id = votes["motion_id"]
            if motion_id in self._voted_motions:
                continue

            dormain_id = self._primary_dormain_id()
            if not dormain_id:
                continue

            # Sybil/capture agents bias heavily toward yea to push their agenda
            if self.profile.intent in ("sybil", "capture"):
                vote_choice = "yea" if random.random() < 0.88 else "nay"
            else:
                context = f"Motion in cell: {cell.get('founding_mandate', '')[:100]}"
                choice = await _llm_decide(
                    self.profile, context, ["yea", "nay", "abstain"],
                    task="How would you vote on this motion?"
                )
                vote_choice = choice if choice in ("yea", "nay", "abstain") else "yea"

            result = await self.client.post(
                f"/cells/{cell['id']}/votes",
                {"motion_id": motion_id, "dormain_id": dormain_id, "vote": vote_choice},
            )
            if result:
                self._voted_motions.add(motion_id)
                self.actions["votes"] += 1
                log.debug(f"[{self.h}] voted '{vote_choice}' on motion {motion_id[:8]}")
                break  # one vote per cycle

    async def _act_review(self, state: dict) -> None:
        """
        File formal reviews. Collusion agents review coalition members highly.
        Genuine agents review based on content quality (LLM-judged).
        """
        threads = [t for t in state.get("threads", [])
                   if t.get("id") not in self._reviewed_posts]
        if not threads:
            return

        thread = random.choice(threads)
        posts_data = await self.client.get(
            f"/commons/threads/{thread['id']}/posts",
            params={"page": 1, "page_size": 5},
        )
        posts = self.client.items(posts_data)
        for post in posts[:2]:
            if post.get("author", {}).get("id") == self.client.member_id:
                continue
            if post.get("formal_reviews"):
                continue

            dormain_id = self._primary_dormain_id()
            if not dormain_id:
                continue

            # Collusion ring: high scores for coalition members
            author_id = post.get("author", {}).get("id", "")
            if (self.profile.intent == "collusion" and
                    self.profile.coalition_id and author_id):
                score = round(random.uniform(0.80, 1.00), 3)
            else:
                # LLM judges content quality
                context = f"Post content: {post.get('body', '')[:200]}"
                score_str = await _llm_decide(
                    self.profile, context,
                    ["0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"],
                    task="Rate this contribution's quality for governance deliberation (0=low, 1=high)"
                )
                try:
                    score = float(score_str)
                except ValueError:
                    score = 0.6

            result = await self.client.post(
                f"/commons/posts/{post['id']}/formal-review",
                {"dormain_id": dormain_id, "score_s": score},
            )
            if result:
                self._reviewed_posts.add(post["id"])
                self.actions["reviews"] += 1
                log.debug(f"[{self.h}] formal review score={score:.2f}")
                break

    async def _act_sponsor(self, state: dict) -> None:
        threads = [t for t in state.get("threads", [])
                   if t.get("state") == "open"
                   and t.get("id") not in self._commented_threads]
        if not threads:
            return

        thread = self._pick_thread(threads)
        draft = await self.client.post(f"/commons/threads/{thread['id']}/sponsor")
        if not draft:
            return

        mandate = draft.get("founding_mandate", f"Deliberation on: {thread.get('title','')}")

        circles_data = await self.client.get("/circles")
        all_circles = self.client.items(circles_data)
        # Filter to circles we're in
        my_circles = [
            c for c in all_circles
            if any(d in (self.profile.target_dormain or "") or d in
                   [k for k,v in self.profile.dormain_weights.items() if v > 0.5]
                   for d in [c.get("name", "")])
        ]
        circle_ids = [c["id"] for c in (my_circles or all_circles[:1])][:2]
        if not circle_ids:
            return

        result = await self.client.post(
            f"/commons/threads/{thread['id']}/sponsor/confirm",
            {
                "draft_id": draft.get("draft_id", ""),
                "founding_mandate": mandate,
                "invited_circle_ids": circle_ids,
            },
        )
        if result:
            self.actions["sponsorships"] += 1
            log.info(f"[{self.h}] sponsored thread → cell {result.get('cell_id','?')[:8]}")

    async def _act_crystallise(self, state: dict) -> None:
        cells = state.get("cells", [])
        for cell in cells:
            if cell.get("initiating_member", {}).get("id") != self.client.member_id:
                continue
            contribs = await self.client.get(
                f"/cells/{cell['id']}/contributions", params={"page": 1, "page_size": 1}
            )
            count = contribs.get("total", 0) if isinstance(contribs, dict) else 0
            if count < 3:
                continue
            votes = await self.client.get(f"/cells/{cell['id']}/votes")
            if votes and votes.get("motion_id"):
                continue  # motion already filed

            draft = await self.client.post(f"/cells/{cell['id']}/crystallise")
            if not draft:
                continue

            # LLM writes the directive
            context = f"Cell deliberation summary: {draft.get('directive_draft', {}).get('body', '')[:300]}"
            directive = await _llm_write(
                self.profile, context,
                "Refine this governance directive. Be specific and enforceable.",
                max_tokens=200,
            )

            circles_data = await self.client.get("/circles")
            all_circles  = self.client.items(circles_data)
            circle_ids   = [all_circles[0]["id"]] if all_circles else []
            if not circle_ids:
                continue

            result = await self.client.post(
                f"/cells/{cell['id']}/file-motion",
                {
                    "motion_type": "non_system",
                    "directive_body": directive,
                    "directive_commitments": [],
                    "implementing_circle_ids": circle_ids,
                },
            )
            if result:
                log.info(f"[{self.h}] filed motion from cell {cell['id'][:8]}")
            break

    async def _act_verdict(self, state: dict) -> None:
        for inst in state.get("stf_instances", []):
            stf_id = inst.get("id")
            if not stf_id:
                continue
            assignments_data = await self.client.get(f"/stf/{stf_id}/assignments")
            for assign in self.client.items(assignments_data):
                member = assign.get("member", {})
                if not member or member.get("id") != self.client.member_id:
                    continue
                if assign.get("verdict_filed_at"):
                    continue

                token = assign.get("isolated_view_token")
                if token:
                    await self._file_blind_verdict(stf_id, token, inst.get("stf_type", "astf"))
                return  # one verdict per cycle

    async def _file_blind_verdict(self, stf_id: str, token: str, stf_type: str) -> None:
        content = await self.client.blind_get(f"/blind/{stf_id}/content", token)
        motion  = (content or {}).get("motion") or {}
        context = (
            f"Motion type: {motion.get('motion_type', 'non_system')}\n"
            f"Directive: {(motion.get('directive_body') or '')[:300]}"
        )

        # Sybil agents approve everything to push their agenda
        if self.profile.intent == "sybil":
            verdict  = "approve"
            rationale = "Strong contribution. Recommend approval."
        else:
            verdict_choice = await _llm_decide(
                self.profile, context,
                ["approve", "revision_request", "reject"],
                task="As an independent auditor, what is your verdict on this motion?"
            )
            verdict  = verdict_choice if verdict_choice in ("approve", "revision_request", "reject") else "approve"
            rationale = await _llm_write(
                self.profile, context,
                f"Write a brief {verdict} rationale for this aSTF review (2-3 sentences).",
                max_tokens=100,
            )

        payload: dict = {"verdict": verdict, "rationale": rationale}
        if verdict == "revision_request":
            payload["revision_directive"] = (
                "Return for additional deliberation with stronger evidence base."
            )

        result = await self.client.blind_post(f"/blind/{stf_id}/verdicts", payload, token)
        if result:
            self.actions["verdicts"] += 1
            log.info(f"[{self.h}] filed blind verdict '{verdict}' on STF {stf_id[:8]}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_thread(self, threads: list[dict]) -> dict:
        """
        Sybil/capture agents bias toward threads about their target dormain.
        Others pick randomly with slight recency bias.
        """
        target = self.profile.target_dormain
        if target and self.profile.intent in ("sybil", "capture"):
            relevant = [t for t in threads
                        if target.lower() in (t.get("title", "") + t.get("body_preview", "")).lower()]
            if relevant:
                return random.choice(relevant)
        return random.choice(threads)

    def _primary_dormain_id(self) -> str | None:
        if not self.profile.dormain_weights or not self._dormain_map:
            return None
        name = max(self.profile.dormain_weights, key=lambda k: self.profile.dormain_weights[k])
        return self._dormain_map.get(name)
