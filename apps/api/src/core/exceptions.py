"""
Domain exceptions. Services raise these; routers catch and convert.
Each exception carries the HTTP status it should produce.
"""
from fastapi import HTTPException, status


class OrbSysError(HTTPException):
    """Base for all domain errors."""
    pass


# ── 404 ───────────────────────────────────────────────────────────────────────

class NotFound(OrbSysError):
    def __init__(self, resource: str, identifier: str | None = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# ── 409 ───────────────────────────────────────────────────────────────────────

class AlreadyExists(OrbSysError):
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} with {field}='{value}' already exists",
        )


# ── 403 ───────────────────────────────────────────────────────────────────────

class Forbidden(OrbSysError):
    def __init__(self, reason: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=reason)


class BootstrapOnly(Forbidden):
    """Action only permitted while org.bootstrapped_at is null."""
    def __init__(self, action: str):
        super().__init__(f"BOOTSTRAP_ONLY: '{action}' is only permitted during bootstrap")


class PostBootstrapOnly(Forbidden):
    """Action only permitted after org.bootstrapped_at is set."""
    def __init__(self, action: str):
        super().__init__(f"POST_BOOTSTRAP_ONLY: '{action}' requires a fully bootstrapped org")


class MemberStateBlocked(Forbidden):
    def __init__(self, state: str, action: str):
        super().__init__(f"AUTH_STATE_{state.upper()}: member state blocks '{action}'")


class NotCircleMember(Forbidden):
    def __init__(self, circle_name: str | None = None):
        detail = "ACTION_REQUIRES_CIRCLE_MEMBERSHIP"
        if circle_name:
            detail = f"ACTION_REQUIRES_CIRCLE_MEMBERSHIP: not a member of '{circle_name}'"
        super().__init__(detail)


class CellAccessDenied(Forbidden):
    def __init__(self, cell_id: str):
        super().__init__(f"CELL_ACCESS_DENIED: your Circle was not invited to cell {cell_id}")


# ── 401 ───────────────────────────────────────────────────────────────────────

class InvalidCredentials(OrbSysError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS: handle or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── 422 ───────────────────────────────────────────────────────────────────────

class ValidationFailed(OrbSysError):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class MissingExecutingCircles(ValidationFailed):
    def __init__(self, motion_type: str):
        super().__init__(
            f"MOTION_MISSING_CIRCLES: implementing_circle_ids is required for {motion_type} motions"
        )


class InvalidSpecificationParameter(ValidationFailed):
    def __init__(self, parameter: str, reason: str):
        super().__init__(f"INVALID_SPECIFICATION: parameter '{parameter}' — {reason}")


# ── 409 governance conflicts ──────────────────────────────────────────────────

class MotionAlreadyFiled(OrbSysError):
    def __init__(self, cell_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MOTION_ALREADY_FILED: cell {cell_id} already has an active motion",
        )


class VerdictAlreadyFiled(OrbSysError):
    def __init__(self, assignment_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"VERDICT_ALREADY_FILED: assignment {assignment_id} already has a verdict",
        )


class VoteAlreadyCast(OrbSysError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="VOTE_ALREADY_CAST: you have already voted in this dormain for this motion",
        )


# ── 503 engine errors ─────────────────────────────────────────────────────────

class EngineTimeout(OrbSysError):
    def __init__(self, engine: str, operation: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ENGINE_TIMEOUT: {engine} did not respond to '{operation}' within timeout",
        )


class LedgerChainBroken(OrbSysError):
    def __init__(self, first_broken_event_id: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CHAIN_INTEGRITY_FAILURE: hash chain broken at event {first_broken_event_id}",
        )
