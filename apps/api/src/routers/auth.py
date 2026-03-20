from fastapi import APIRouter, Query
from ..core.dependencies import DB
from ..services.auth import AuthService
from ..schemas import (
    LoginRequest, LoginResponse,
    RefreshRequest, TokenResponse,
    RegisterMemberRequest, MemberSessionResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DB):
    """Authenticate with org_slug + handle + password."""
    return await AuthService(db).login(body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DB):
    """Issue a new access token from a valid refresh token."""
    return await AuthService(db).refresh(body)


@router.post("/register", response_model=MemberSessionResponse, status_code=201)
async def register(
    body: RegisterMemberRequest,
    db: DB,
    org_slug: str = Query(..., description="Org to register into"),
):
    """
    Bootstrap step 3 — member self-registration.
    Only valid while org.bootstrapped_at is null.
    """
    return await AuthService(db).register(org_slug, body)


@router.post("/logout", status_code=204)
async def logout():
    """Stateless JWT — client discards token. Server-side revocation: v1.1."""
    return
