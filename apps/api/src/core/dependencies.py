from typing import Annotated
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .security import decode_token, decode_isolated_view_token

bearer = HTTPBearer()

WRITE_BLOCKED = {"suspended", "under_review", "inactive", "exited"}
FULLY_BLOCKED = {"suspended", "exited"}


class CurrentMember:
    def __init__(self, member_id: str, org_id: str, state: str):
        self.member_id = member_id
        self.org_id = org_id
        self.state = state

    @property
    def can_govern(self) -> bool:
        return self.state not in WRITE_BLOCKED

    @property
    def is_active(self) -> bool:
        return self.state not in FULLY_BLOCKED


class IsolatedViewCtx:
    def __init__(self, stf_instance_id: str, assignment_id: str):
        self.stf_instance_id = stf_instance_id
        self.assignment_id = assignment_id


async def get_current_member(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentMember:
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise JWTError("Not a session token")
        return CurrentMember(payload["sub"], payload["org"], payload["state"])
    except (JWTError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session token")


async def require_active(
    member: Annotated[CurrentMember, Depends(get_current_member)],
) -> CurrentMember:
    if not member.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Member state '{member.state}' blocks access")
    return member


async def require_governance_write(
    member: Annotated[CurrentMember, Depends(get_current_member)],
) -> CurrentMember:
    if not member.can_govern:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Governance write blocked by member state")
    return member


async def get_isolated_view(
    x_isolated_view_token: Annotated[str | None, Header()] = None,
) -> IsolatedViewCtx:
    """Used exclusively by blind review endpoints. Rejects session tokens."""
    if not x_isolated_view_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "X-Isolated-View-Token required")
    try:
        payload = decode_isolated_view_token(x_isolated_view_token)
        return IsolatedViewCtx(payload["stf_instance_id"], payload["assignment_id"])
    except JWTError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid isolated view token")


# Type aliases used in route signatures
ActiveMember = Annotated[CurrentMember, Depends(require_active)]
GovWriter = Annotated[CurrentMember, Depends(require_governance_write)]
BlindCtx = Annotated[IsolatedViewCtx, Depends(get_isolated_view)]
DB = Annotated[AsyncSession, Depends(get_db)]
