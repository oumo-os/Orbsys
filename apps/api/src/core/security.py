from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(member_id: str, org_id: str, member_state: str) -> str:
    return jwt.encode(
        {
            "sub": member_id,
            "org": org_id,
            "state": member_state,
            "type": "access",
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(member_id: str, org_id: str) -> str:
    return jwt.encode(
        {
            "sub": member_id,
            "org": org_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_isolated_view_token(stf_instance_id: str, assignment_id: str) -> str:
    """
    Blind review token. Encodes STF context ONLY — not member identity.
    Structurally incompatible with session tokens (type='isolated_view').
    Wrong type on any endpoint returns 403, not 401.
    """
    return jwt.encode(
        {
            "stf_instance_id": stf_instance_id,
            "assignment_id": assignment_id,
            "type": "isolated_view",
            "exp": datetime.now(timezone.utc) + timedelta(days=14),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_isolated_view_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "isolated_view":
        raise JWTError("Not an isolated view token")
    return payload

# ── Platform-level tokens (federation layer) ──────────────────────────────────

def create_platform_token(account_id: str) -> str:
    """
    Platform token — proves you are a logged-in human, not org membership.
    Valid for: personal dashboard, credential wallet, org discovery,
    requesting an org session via /auth/enter-org/:org_id.
    Does NOT grant access to any org's governance endpoints.
    """
    return jwt.encode(
        {
            "sub": account_id,
            "type": "platform",
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_platform_refresh_token(account_id: str) -> str:
    return jwt.encode(
        {
            "sub": account_id,
            "type": "platform_refresh",
            "exp": datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_org_session_token(
    account_id: str, member_id: str, org_id: str, member_state: str
) -> str:
    """
    Org session token — issued after a platform-authenticated user
    "enters" a specific org. Carries both identities: the platform
    account (for unified notifications) and the org membership
    (for governance actions). This is what existing org endpoints
    expect as `member.org_id` / `member.member_id`.
    """
    return jwt.encode(
        {
            "sub": member_id,
            "account": account_id,
            "org": org_id,
            "state": member_state,
            "type": "access",   # unchanged — existing org endpoints check for this
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
