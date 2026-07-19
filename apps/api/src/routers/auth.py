"""
Org-scoped auth — bootstrap-only registration and logout.

Platform-level login, platform registration, token refresh, and the
enter-org exchange now live in routers/platform_auth.py:
  POST /auth/login              platform login (no org_slug)
  POST /auth/register-account   platform account creation
  POST /auth/refresh-platform   refresh a platform token
  POST /auth/enter-org/{org_id} exchange platform token -> org session token

This module retains only the bootstrap-window founding member path, which
now ALSO creates a linked PlatformAccount under the hood so founding
members immediately have a portable identity.
"""
from fastapi import APIRouter, Query
from ..core.dependencies import DB
from ..services.auth import AuthService
from ..schemas import RegisterMemberRequest, MemberSessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MemberSessionResponse, status_code=201)
async def register(
    body: RegisterMemberRequest,
    db: DB,
    org_slug: str = Query(..., description="Org to register into"),
):
    """
    Bootstrap step 3 — founding member self-registration.
    Only valid while org.bootstrapped_at is null.
    Returns BOOTSTRAP_ONLY (403) once the org is live; use
    POST /members/apply instead.

    Internally creates (or links, if email matches) a PlatformAccount,
    so the founding member can immediately use platform login and,
    later, join other orgs under the same identity.
    """
    return await AuthService(db).register(org_slug, body)


@router.post("/logout", status_code=204)
async def logout():
    """Stateless JWT — client discards token. Server-side revocation: v1.1."""
    return
