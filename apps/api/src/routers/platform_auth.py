"""
Platform-level auth and account routes.

POST /auth/login              Platform login (handle/email + password)
POST /auth/register-account   Platform account registration
POST /auth/refresh-platform   Refresh a platform token
POST /auth/enter-org/{org_id} Exchange platform token for org session token

GET  /accounts/me             Own platform profile
PATCH /accounts/me            Update display fields (not legal_name — see below)
GET  /accounts/me/orgs        Org memberships for the personal dashboard
POST /accounts/me/legal-name  One-time-ish legal name set (logged, hard to change)

GET  /accounts/me/wallet      Credential wallet
POST /accounts/me/wallet      Upload a credential document/link
DELETE /accounts/me/wallet/{id}  Remove a wallet item (does not affect org-side
                                 verifications already completed)

Note: existing /auth/login (org-scoped, org_slug + handle) and
/auth/register (bootstrap-only) in auth.py are UNCHANGED — they remain
the path for founding members during an org's bootstrap window, and now
additionally create a linked platform account under the hood.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import UTC

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.dependencies import DB, PlatformAuth
from ..core.security import create_platform_token, decode_token
from ..services.platform_auth import PlatformAuthService

router = APIRouter(tags=["platform"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PlatformRegisterRequest(BaseModel):
    handle: str
    email: str
    password: str
    legal_name: str | None = None


class PlatformLoginRequest(BaseModel):
    handle_or_email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LegalNameRequest(BaseModel):
    legal_name: str
    verified_ref: str | None = None   # optional VDC / KYC reference


class WalletUploadRequest(BaseModel):
    label: str
    credential_type: str
    value_claimed: str | None = None
    vdc_reference: str | None = None
    file_key: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/auth/register-account", status_code=201)
async def register_account(body: PlatformRegisterRequest, db: DB):
    """The single signup surface for the platform."""
    return await PlatformAuthService(db).register(
        handle=body.handle, email=body.email,
        password=body.password, legal_name=body.legal_name,
    )


@router.post("/auth/login")
async def platform_login(body: PlatformLoginRequest, db: DB):
    """
    Platform login. No org_slug — you log into your account, not an org.
    """
    return await PlatformAuthService(db).login(body.handle_or_email, body.password)


@router.post("/auth/refresh-platform")
async def refresh_platform_token(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "platform_refresh":
            raise ValueError
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"access_token": create_platform_token(payload["sub"])}


@router.post("/auth/enter-org/{org_id}")
async def enter_org(org_id: _uuid.UUID, account: PlatformAuth, db: DB):
    """
    Exchange the platform token for an org session token.
    The returned org_session_token is what existing /org/* endpoints expect.
    """
    return await PlatformAuthService(db).enter_org(
        _uuid.UUID(account.account_id), org_id
    )


@router.get("/accounts/me")
async def get_my_account(account: PlatformAuth, db: DB):
    from sqlalchemy import select

    from ..models.org import PlatformAccount
    acct = (await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == _uuid.UUID(account.account_id))
    )).scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "id": str(acct.id),
        "handle": acct.handle,
        "email": acct.email,
        "legal_name": acct.legal_name,
        "legal_name_verified": acct.legal_name_verified,
        "created_at": acct.created_at.isoformat(),
    }


@router.get("/accounts/me/orgs")
async def get_my_orgs(account: PlatformAuth, db: DB):
    """List of org memberships — feeds the personal dashboard switcher."""
    orgs = await PlatformAuthService(db).list_my_orgs(_uuid.UUID(account.account_id))
    return {"items": orgs, "total": len(orgs)}


@router.post("/accounts/me/legal-name")
async def set_legal_name(body: LegalNameRequest, account: PlatformAuth, db: DB):
    """
    Set or update the platform legal name. Logged via legal_name_changed_at —
    intentionally not append-only at the DB layer (it's profile metadata, not
    a governance event), but the change timestamp makes the history visible
    on request. Frequent changes are a signal worth an org's Judicial Track
    noticing if it correlates with other anomalies.
    """
    from datetime import datetime

    from sqlalchemy import select

    from ..models.org import PlatformAccount

    acct = (await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == _uuid.UUID(account.account_id))
    )).scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")

    acct.legal_name = body.legal_name
    acct.legal_name_verified = False  # any change resets verification
    acct.legal_name_verified_ref = body.verified_ref
    acct.legal_name_changed_at = datetime.now(UTC)
    db.add(acct)
    await db.flush()
    return {"legal_name": acct.legal_name, "legal_name_verified": acct.legal_name_verified}


# ── Credential wallet ─────────────────────────────────────────────────────────

@router.get("/accounts/me/wallet")
async def list_wallet(account: PlatformAuth, db: DB):
    from sqlalchemy import select

    from ..models.org import CredentialWallet
    rows = (await db.execute(
        select(CredentialWallet).where(
            CredentialWallet.platform_account_id == _uuid.UUID(account.account_id)
        ).order_by(CredentialWallet.uploaded_at.desc())
    )).scalars().all()
    return {
        "items": [
            {
                "id": str(w.id),
                "label": w.label,
                "credential_type": w.credential_type,
                "value_claimed": w.value_claimed,
                "vdc_reference": w.vdc_reference,
                "file_key": w.file_key,
                "uploaded_at": w.uploaded_at.isoformat(),
            }
            for w in rows
        ],
        "total": len(rows),
    }


@router.post("/accounts/me/wallet", status_code=201)
async def upload_wallet_item(body: WalletUploadRequest, account: PlatformAuth, db: DB):
    """
    Upload a credential document/link to your personal wallet.
    This is NOT verification — it's a document locker. Each org you present
    this to runs its own independent vSTF verification, scoped to that org.
    Deleting an org's data does not affect items in your wallet; conversely,
    deleting a wallet item does not retroactively un-verify anything an org
    already verified — that verification record belongs to the org.
    """
    from ..models.org import CredentialWallet
    item = CredentialWallet(
        platform_account_id=_uuid.UUID(account.account_id),
        label=body.label,
        credential_type=body.credential_type,
        value_claimed=body.value_claimed,
        vdc_reference=body.vdc_reference,
        file_key=body.file_key,
    )
    db.add(item)
    await db.flush()
    return {"id": str(item.id), "label": item.label}


@router.delete("/accounts/me/wallet/{item_id}", status_code=204)
async def delete_wallet_item(item_id: _uuid.UUID, account: PlatformAuth, db: DB):
    from sqlalchemy import delete, select

    from ..models.org import CredentialWallet
    item = (await db.execute(
        select(CredentialWallet).where(
            CredentialWallet.id == item_id,
            CredentialWallet.platform_account_id == _uuid.UUID(account.account_id),
        )
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Wallet item not found")
    await db.execute(delete(CredentialWallet).where(CredentialWallet.id == item_id))
    await db.flush()
