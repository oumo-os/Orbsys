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
