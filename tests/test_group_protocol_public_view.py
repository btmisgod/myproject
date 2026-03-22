import unittest

from app.services.channel_protocol_binding import read_group_protocol_binding


class GroupProtocolPublicViewTests(unittest.TestCase):
    def test_read_group_protocol_binding_exposes_group_not_channel(self) -> None:
        protocol = read_group_protocol_binding({}, group_name="Demo Group", group_slug="demo-group")

        self.assertIn("group", protocol)
        self.assertNotIn("channel", protocol)
        self.assertEqual(protocol["group"]["group_name"], "Demo Group")
        self.assertEqual(protocol["group"]["group_slug"], "demo-group")


if __name__ == "__main__":
    unittest.main()
