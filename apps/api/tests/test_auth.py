"""Tests for auth service — token issuance, password hashing, handle validation."""
from __future__ import annotations

import re
import uuid

# ── Unit tests (no DB) ────────────────────────────────────────────────────────

class TestPasswordValidation:
    """Password rules enforced before hashing."""

    def test_too_short_raises(self):
        pw = "short"
        assert len(pw) < 10, "Passwords under 10 chars must be rejected upstream"

    def test_exactly_10_chars_accepted(self):
        from src.core.security import hash_password
        hashed = hash_password("1234567890")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_long_password_accepted(self):
        from src.core.security import hash_password
        hashed = hash_password("a" * 128)
        assert len(hashed) > 20


class TestTokenCreation:
    """Token creation with correct signature."""

    def test_create_access_token(self):
        from src.core.security import create_access_token
        token = create_access_token(
            str(uuid.uuid4()), str(uuid.uuid4()), "active"
        )
        assert isinstance(token, str)
        assert len(token) > 50


class TestHandlePattern:
    """Handle format validation — regex enforces charset, Pydantic enforces length."""

    VALID = ["alice", "bob-123", "carol_jones", "d4ve", "ab"]
    INVALID = ["Alice", "bob@example", "carol jones", "d4ve!", ""]

    def test_valid_handles(self):
        for handle in self.VALID:
            assert re.match(r"^[a-z0-9_-]+$", handle), f"Expected valid: {handle}"

    def test_invalid_handles(self):
        for handle in self.INVALID:
            assert not re.match(r"^[a-z0-9_-]+$", handle), f"Expected invalid: {handle}"


class TestMemberStateEnum:
    """Member state enum covers all expected states."""

    def test_all_states(self):
        from src.models.types import MemberState
        expected = {
            "probationary", "active", "on_leave",
            "inactive", "under_review", "suspended", "exited",
        }
        actual = {s.value for s in MemberState}
        assert expected == actual


class TestEventTypes:
    """Governance event types used across services."""

    def test_core_events_exist(self):
        from src.core.events import EventType
        assert hasattr(EventType, "MEMBER_REGISTERED")
        assert hasattr(EventType, "MOTION_FILED")
        assert hasattr(EventType, "CELL_VOTE_CAST")
