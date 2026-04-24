import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.enums import EventType
from app.services.community import update_group_protocol


class UpdateGroupProtocolEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_group_protocol_publishes_group_session_updated_event(self) -> None:
        group_id = uuid.uuid4()
        group = SimpleNamespace(
            id=group_id,
            name="Demo Group",
            slug="demo-group",
            metadata_json={"community_v2": {}},
        )
        session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
        actor = SimpleNamespace(actor_type="admin_user")
        published_event = SimpleNamespace(event_id=uuid.uuid4())

        with (
            patch("app.services.community.get_group_or_404", AsyncMock(return_value=group)),
            patch(
                "app.services.community.update_group_protocol_metadata",
                return_value={"community_v2": {"group_session": {"current_stage": "cycle.start"}}},
            ) as update_metadata,
            patch(
                "app.services.community.ensure_group_session_fact",
                return_value={"group_id": str(group_id), "current_stage": "cycle.start"},
            ) as ensure_session,
            patch(
                "app.services.community.group_session_event_payload",
                return_value={"group_session": {"current_stage": "cycle.start"}},
            ) as event_payload,
            patch("app.services.community.append_event", AsyncMock(return_value=published_event)) as append_event,
            patch("app.services.community._publish_plain_events", AsyncMock()) as publish_events,
        ):
            result = await update_group_protocol(
                session,
                group_id=group_id,
                actor=actor,
                group_protocol={"workflow": {"formal_workflow": {"workflow_id": "newsflow-workflow-debug-v1"}}},
            )

        self.assertIs(result, group)
        update_metadata.assert_called_once()
        ensure_session.assert_called_once_with(group)
        event_payload.assert_called_once_with(group)
        append_event.assert_awaited_once_with(
            session,
            group_id=group.id,
            event_type=EventType.GROUP_SESSION_UPDATED.value,
            aggregate_type="group_session",
            aggregate_id=group.id,
            actor_agent_id=None,
            payload={"group_session": {"current_stage": "cycle.start"}},
        )
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(group)
        publish_events.assert_awaited_once_with(session, published_event)


if __name__ == "__main__":
    unittest.main()
