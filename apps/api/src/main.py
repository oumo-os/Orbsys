import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .core.config import get_settings
from .core.database import get_db
from .core.events import get_event_bus
from .core.exceptions import OrbSysError
from .routers import (
    auth,
    cells,
    circles,
    commons,
    competence,
    invitations,
    ledger,
    members,
    motions,
    org,
    platform_auth,
    setup,
    stf,
)

log = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("Orb Sys API starting…")
    bus = get_event_bus()
    await bus.connect(settings.nats_url)
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("Orb Sys API shutting down…")
    await bus.close()


app = FastAPI(
    title="Orb Sys API",
    version="0.1.0",
    description="PAAS governance platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Request-ID",
        "X-Isolated-View-Token",
    ],
)


# ── Request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Domain exception handler ──────────────────────────────────────────────────
@app.exception_handler(OrbSysError)
async def orbsys_exception_handler(request: Request, exc: OrbSysError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(members.router)
app.include_router(competence.router)
app.include_router(commons.router)
app.include_router(cells.router)
app.include_router(motions.router)
app.include_router(stf.router)
app.include_router(circles.router)
app.include_router(org.router)
app.include_router(ledger.router)
app.include_router(setup.router)
app.include_router(platform_auth.router)
app.include_router(invitations.router)


@app.post("/internal/events", include_in_schema=False)
async def internal_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal event callback — only from trusted services (blind API, engines).
    Authenticated by X-Internal-Token header, not a user session token.
    Publishes to the NATS event bus so the engines can process the event.
    """
    import os
    expected = os.environ.get("INTERNAL_TOKEN", "")
    token    = request.headers.get("X-Internal-Token", "")
    if not expected:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": "INTERNAL_TOKEN not configured"})
    if token != expected:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "FORBIDDEN"})

    data = await request.json()
    event_type = data.get("event_type", "")

    # Map back to EventType enum string and publish via event bus
    import uuid as _u

    from .core.events import EventType, GovernanceEvent, get_event_bus

    org_id_str = data.get("org_id")
    if not org_id_str:
        # Look up org_id from stf_instance_id if present
        stf_id_str = data.get("stf_instance_id")
        if stf_id_str:
            from sqlalchemy import text
            row = (await db.execute(
                text("SELECT org_id FROM stf_instances WHERE id=:sid"),
                {"sid": _u.UUID(stf_id_str)},
            )).fetchone()
            if row:
                org_id_str = str(row[0])

    if not org_id_str:
        return {"status": "dropped", "reason": "no org_id"}

    org_id = _u.UUID(org_id_str)
    subject_id = _u.UUID(data["stf_instance_id"]) if data.get("stf_instance_id") else org_id

    await get_event_bus().emit(
        org_id,
        GovernanceEvent(
            event_type=getattr(EventType, event_type.upper(), None) or event_type,
            subject_id=subject_id,
            subject_type="stf_instance",
            payload={k: v for k, v in data.items()
                     if k not in ("event_type", "org_id")},
        ),
    )
    return {"status": "published", "event_type": event_type}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Service health — includes org_count for first-run detection."""
    from fastapi.responses import JSONResponse
    try:
        from sqlalchemy import text as _text
        org_count = (await db.execute(_text("SELECT COUNT(*) FROM orgs"))).scalar_one() or 0
    except Exception as e:
        log.warning(f"[health] DB check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "service": "orbsys-api", "error": "database unreachable"},
        )
    return {"status": "ok", "service": "orbsys-api", "org_count": int(org_count)}
