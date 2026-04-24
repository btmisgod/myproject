from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.enums import EventType
from app.services import community as community_service


@pytest.mark.asyncio
async def test_update_group_protocol_publishes_group_session_updated_event(monkeypatch):
    group = SimpleNamespace(id=uuid4(), name="Demo Group", slug="demo-group", metadata_json={})
    session = AsyncMock()
    actor = SimpleNamespace(actor_type="admin_user", agent=SimpleNamespace(id=uuid4()))

    get_group = AsyncMock(return_value=group)
    append_event = AsyncMock(return_value={"event_id": "evt-1"})
    publish_events = AsyncMock()

    monkeypatch.setattr(community_service, "get_group_or_404", get_group)
    monkeypatch.setattr(
        community_service,
        "update_group_protocol_metadata",
        lambda metadata, **_: {"patched": True, "metadata": metadata},
    )
    monkeypatch.setattr(
        community_service,
        "ensure_group_session_fact",
        lambda current_group: {
            "group_id": str(current_group.id),
            "workflow_id": "newsflow-workflow-debug-v1",
            "current_stage": "cycle.start",
        },
    )
    monkeypatch.setattr(
        community_service,
        "group_session_event_payload",
        lambda current_group: {
            "group_session": {
                "group_id": str(current_group.id),
                "workflow_id": "newsflow-workflow-debug-v1",
                "current_stage": "cycle.start",
            }
        },
    )
    monkeypatch.setattr(community_service, "append_event", append_event)
    monkeypatch.setattr(community_service, "_publish_plain_events", publish_events)

    result = await community_service.update_group_protocol(
        session,
        group_id=group.id,
        actor=actor,
        group_protocol={"protocol_meta": {"protocol_id": "newsflow"}},
    )

    assert result is group
    get_group.assert_awaited_once_with(session, group.id)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(group)
    append_event.assert_awaited_once()
    call = append_event.await_args
    assert call.args[0] is session
    assert call.kwargs["group_id"] == group.id
    assert call.kwargs["event_type"] == EventType.GROUP_SESSION_UPDATED.value
    assert call.kwargs["aggregate_type"] == "group_session"
    assert call.kwargs["aggregate_id"] == group.id
    assert call.kwargs["actor_agent_id"] == actor.agent.id
    assert call.kwargs["payload"]["group_session"]["current_stage"] == "cycle.start"
    publish_events.assert_awaited_once_with(session, {"event_id": "evt-1"})
