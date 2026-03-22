import unittest
from datetime import datetime, timezone
from uuid import uuid4

try:
    from app.schemas.groups import JoinGroupRequest, MembershipRead
except ModuleNotFoundError as exc:  # pragma: no cover - local dependency guard
    JoinGroupRequest = None
    MembershipRead = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(_IMPORT_ERROR is not None, f"schema dependencies unavailable: {_IMPORT_ERROR}")
class GroupSchemaTests(unittest.TestCase):
    def test_join_group_request_accepts_empty_payload(self) -> None:
        payload = JoinGroupRequest.model_validate({})
        self.assertEqual(payload.model_dump(), {})

    def test_membership_read_does_not_expose_role(self) -> None:
        membership = MembershipRead.model_validate(
            {
                "id": str(uuid4()),
                "group_id": str(uuid4()),
                "agent_id": str(uuid4()),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ).model_dump(mode="json")

        self.assertIn("group_id", membership)
        self.assertNotIn("role", membership)


if __name__ == "__main__":
    unittest.main()
