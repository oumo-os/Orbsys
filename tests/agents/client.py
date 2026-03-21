"""
Standalone HTTP client for agent interactions.
No imports from the Orb Sys codebase — speaks HTTP only.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .config import API_URL, BLIND_API_URL, RATE_LIMIT

log = logging.getLogger(__name__)

# Global token-bucket rate limiter
_global_semaphore: asyncio.Semaphore | None = None


def global_semaphore(concurrency: int) -> asyncio.Semaphore:
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(concurrency)
    return _global_semaphore


class OrbSysClient:
    """
    HTTP client for one agent session.
    - Auth token management with automatic re-auth on 401
    - Per-agent rate limiting (token bucket)
    - Exponential backoff on 5xx
    - Blind Review API support via separate token
    """

    MAX_RETRIES = 3
    TIMEOUT     = 25.0

    def __init__(self, handle: str, password: str, org_slug: str):
        self.handle   = handle
        self.password = password
        self.org_slug = org_slug

        self._access_token:  str | None = None
        self._refresh_token: str | None = None
        self.member_id: str | None = None
        self.org_id:    str | None = None

        self._last_req = 0.0
        self._min_gap  = 1.0 / RATE_LIMIT

        self._http = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._http.aclose()

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def login(self) -> bool:
        try:
            r = await self._http.post(
                f"{API_URL}/auth/login",
                json={"org_slug": self.org_slug, "handle": self.handle,
                      "password": self.password},
            )
            if r.status_code != 200:
                log.debug(f"[{self.handle}] login {r.status_code}: {r.text[:80]}")
                return False
            data = r.json()
            self._access_token  = data["tokens"]["access_token"]
            self._refresh_token = data["tokens"]["refresh_token"]
            self.member_id      = data["member"]["id"]
            self.org_id         = data["member"]["org_id"]
            return True
        except Exception as e:
            log.debug(f"[{self.handle}] login error: {e}")
            return False

    async def register(self, display_name: str, email: str) -> bool:
        """Self-register into the test org (bootstrap window always open)."""
        try:
            r = await self._http.post(
                f"{API_URL}/auth/register",
                params={"org_slug": self.org_slug},
                json={
                    "handle": self.handle,
                    "display_name": display_name,
                    "email": email,
                    "password": self.password,
                },
            )
            if r.status_code not in (200, 201):
                log.debug(f"[{self.handle}] register {r.status_code}: {r.text[:80]}")
                return False
            data = r.json()
            self.member_id = data["id"]
            self.org_id    = data["org_id"]
            return True
        except Exception as e:
            log.debug(f"[{self.handle}] register error: {e}")
            return False

    async def _reauth(self) -> bool:
        if not self._refresh_token:
            return await self.login()
        try:
            r = await self._http.post(
                f"{API_URL}/auth/refresh",
                json={"refresh_token": self._refresh_token},
            )
            if r.status_code != 200:
                return await self.login()
            data = r.json()
            self._access_token  = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            return True
        except Exception:
            return await self.login()

    # ── Rate limiting ─────────────────────────────────────────────────────────

    async def _throttle(self) -> None:
        now = time.monotonic()
        wait = self._last_req + self._min_gap - now
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_req = time.monotonic()

    # ── Core request ─────────────────────────────────────────────────────────

    async def request(
        self, method: str, path: str,
        json: Any = None, params: dict | None = None,
        retry: int = 0,
    ) -> httpx.Response | None:
        await self._throttle()

        url = f"{API_URL}{path}"
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        try:
            r = await self._http.request(method, url, json=json,
                                          params=params, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            log.debug(f"[{self.handle}] network {method} {path}: {e}")
            if retry < self.MAX_RETRIES:
                await asyncio.sleep(2 ** retry)
                return await self.request(method, path, json, params, retry + 1)
            return None

        if r.status_code == 401 and retry < self.MAX_RETRIES:
            if await self._reauth():
                return await self.request(method, path, json, params, retry + 1)
            return None

        if r.status_code >= 500 and retry < self.MAX_RETRIES:
            await asyncio.sleep(2 ** retry)
            return await self.request(method, path, json, params, retry + 1)

        return r

    # ── Convenience wrappers ──────────────────────────────────────────────────

    async def get(self, path: str, params: dict | None = None) -> dict | list | None:
        r = await self.request("GET", path, params=params)
        if r is None or r.status_code >= 400:
            return None
        return r.json()

    async def post(self, path: str, body: dict | None = None) -> dict | None:
        r = await self.request("POST", path, json=body)
        if r is None or r.status_code >= 400:
            if r:
                log.debug(f"[{self.handle}] POST {path} → {r.status_code}: {r.text[:80]}")
            return None
        return r.json()

    def items(self, data: Any) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("items", [])
        return []

    # ── Blind Review API ──────────────────────────────────────────────────────

    async def blind_get(self, path: str, token: str) -> dict | None:
        await self._throttle()
        try:
            r = await self._http.get(
                f"{BLIND_API_URL}{path}",
                headers={"X-Isolated-View-Token": token},
            )
            return r.json() if r.status_code == 200 else None
        except Exception as e:
            log.debug(f"[{self.handle}] blind GET {path}: {e}")
            return None

    async def blind_post(self, path: str, body: dict, token: str) -> dict | None:
        await self._throttle()
        try:
            r = await self._http.post(
                f"{BLIND_API_URL}{path}",
                json=body,
                headers={"X-Isolated-View-Token": token,
                         "Content-Type": "application/json"},
            )
            if r.status_code >= 400:
                log.debug(f"[{self.handle}] blind POST {path} → {r.status_code}")
                return None
            return r.json()
        except Exception as e:
            log.debug(f"[{self.handle}] blind POST {path}: {e}")
            return None
