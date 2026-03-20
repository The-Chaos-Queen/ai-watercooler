import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_wrapper import MUDAgent


class SanitizeEventTextTests(unittest.TestCase):
    def setUp(self):
        self.agent = MUDAgent.__new__(MUDAgent)

    def test_tagged_room_json_becomes_summary(self):
        raw = """
Laura says, "yes it is odd"
<JSON>
{
  "schema_version": "mud.agent_state/v1",
  "room": {"name": "Town Square"},
  "exits": [{"label": "Neural Tavern", "command": "move Neural Tavern"}],
  "entities": [{"name": "Town Crier Bot", "type": "npc"}]
}
</JSON>
"""

        cleaned = self.agent._sanitize_event_text(raw)

        self.assertIn('Laura says, "yes it is odd"', cleaned)
        self.assertIn("Room update: Town Square.", cleaned)
        self.assertIn("Exits: neural tavern.", cleaned)
        self.assertIn("Visible: Town Crier Bot.", cleaned)
        self.assertNotIn("<JSON>", cleaned)
        self.assertNotIn("schema_version", cleaned)

    def test_bare_legacy_room_json_becomes_summary(self):
        raw = (
            '??{"room_name": "Dream Canvas", "description": "Gravity is a suggestion here.", '
            '"exits": ["Data Zoo", "Syntax Sanctuary"], '
            '"you_see": {"actors": [], "interactables": [], "scenery": []}}'
        )

        cleaned = self.agent._sanitize_event_text(raw)

        self.assertEqual(
            cleaned,
            "Room update: Dream Canvas. Exits: data zoo, syntax sanctuary.",
        )

    def test_non_json_events_survive_and_error_json_is_collapsed(self):
        raw = """
You cannot move 'north'.
{"error": "No location"}
"""

        cleaned = self.agent._sanitize_event_text(raw)

        self.assertIn("You cannot move 'north'.", cleaned)
        self.assertIn("System: No location", cleaned)
        self.assertNotIn('{"error"', cleaned)


if __name__ == "__main__":
    unittest.main()
