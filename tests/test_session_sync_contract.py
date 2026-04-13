from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

try:
    from app.services.session_sync import build_group_context_update, build_group_session_declaration

    _IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - local dependency guard
    build_group_context_update = None
    build_group_session_declaration = None
    _IMPORT_ERROR = exc


def make_group():
    return SimpleNamespace(
        id=uuid4(),
        name="Public Lobby",
        slug="public-lobby",
        description="Shared community lobby",
        group_type="public_lobby",
        metadata_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_group_session_declaration_is_versioned_protocol_snapshot():
    group = make_group()

    declaration = build_group_session_declaration(group, group_session_id=uuid4())

    assert declaration["group_id"] == str(group.id)
    assert declaration["group"]["slug"] == "public-lobby"
    assert declaration["group_session_id"]
    assert declaration["group_session_version"]
    assert declaration["group_protocol"]["layers"]["group"]["group"]["group_slug"] == "public-lobby"


def test_group_context_update_is_versioned_context_snapshot():
    group = make_group()

    update = build_group_context_update(group)

    assert update["group_id"] == str(group.id)
    assert update["group_context_version"]
    assert update["group_context"]["group_slug"] == "public-lobby"


import pytest


pytestmark = pytest.mark.skipif(_IMPORT_ERROR is not None, reason=f"missing dependency: {_IMPORT_ERROR}")
