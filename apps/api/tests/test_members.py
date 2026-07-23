"""Tests for members service — schemas, pagination, request validation."""
from __future__ import annotations

import uuid

import pytest

# ── Schema tests ──────────────────────────────────────────────────────────────

class TestUpdateMemberRequest:
    """UpdateMemberRequest field constraints."""

    def test_display_name_max_length(self):
        from src.schemas.members import UpdateMemberRequest
        req = UpdateMemberRequest(display_name="a" * 255)
        assert len(req.display_name) == 255

    def test_display_name_empty_string_rejected(self):
        from pydantic import ValidationError

        from src.schemas.members import UpdateMemberRequest
        with pytest.raises(ValidationError):
            UpdateMemberRequest(display_name="")

    def test_all_optional(self):
        from src.schemas.members import UpdateMemberRequest
        req = UpdateMemberRequest()
        assert req.display_name is None
        assert req.email is None


class TestSetCuriositiesRequest:
    """Curiosity vector validation."""

    def test_valid_curiosities(self):
        from src.schemas.members import SetCuriositiesRequest
        req = SetCuriositiesRequest(curiosities={
            str(uuid.uuid4()): 0.5,
            str(uuid.uuid4()): 1.0,
        })
        assert len(req.curiosities) == 2

    def test_out_of_range_rejected(self):
        from pydantic import ValidationError

        from src.schemas.members import SetCuriositiesRequest
        with pytest.raises(ValidationError):
            SetCuriositiesRequest(curiosities={str(uuid.uuid4()): 1.5})

    def test_negative_rejected(self):
        from pydantic import ValidationError

        from src.schemas.members import SetCuriositiesRequest
        with pytest.raises(ValidationError):
            SetCuriositiesRequest(curiosities={str(uuid.uuid4()): -0.1})


class TestMemberResponse:
    """MemberResponse schema shape."""

    def test_has_required_fields(self):
        from src.schemas.members import MemberResponse
        fields = MemberResponse.model_fields
        required = {"id", "handle", "display_name", "org_id", "current_state", "joined_at"}
        assert required.issubset(set(fields.keys()))


class TestPagination:
    """Paginated response shape."""

    def test_paginated_structure(self):
        from src.schemas.common import Paginated
        p = Paginated(items=[], total=0, page=1, page_size=25, has_next=False)
        assert p.items == []
        assert p.total == 0
        assert p.has_next is False

    def test_paginated_has_next_true(self):
        from src.schemas.common import Paginated
        p = Paginated(items=["x"], total=50, page=2, page_size=25, has_next=True)
        assert p.has_next is True
