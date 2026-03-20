from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.events import get_event_bus
from .core.exceptions import OrbSysError
from .routers import auth, members, competence, commons, cells, motions, stf, circles, org, ledger

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
    allow_headers=["*"],
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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orbsys-api"}
