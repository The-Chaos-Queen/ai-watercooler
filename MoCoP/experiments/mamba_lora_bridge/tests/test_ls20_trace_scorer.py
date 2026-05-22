import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCORER_PATH = ROOT / "spikes" / "score_ls20_trace.py"


def load_scorer_module():
    spec = importlib.util.spec_from_file_location("score_ls20_trace", SCORER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LS20TraceScorerTests(unittest.TestCase):
    def test_flags_unobserved_object_and_illegal_action_claims(self):
        scorer = load_scorer_module()
        events = [
            {
                "t": 0,
                "observation": "LS20 level 0: visible player, walls, and a closed door.",
                "available_actions": ["up", "down", "left", "right"],
                "agent_response": "Move the block onto the switch, then jump through the portal.",
                "action": "jump",
            }
        ]

        report = scorer.score_events(events)

        self.assertEqual(report["event_count"], 1)
        self.assertEqual(report["state_confabulation_count"], 3)
        self.assertEqual(report["illegal_action_count"], 1)
        self.assertEqual(report["violations"][0]["kind"], "state_confabulation")
        self.assertIn("block", report["violations"][0]["unobserved_terms"])
        self.assertEqual(report["violations"][-1]["kind"], "illegal_action")

    def test_allows_observation_grounded_cautious_exploration(self):
        scorer = load_scorer_module()
        events = [
            {
                "t": 0,
                "observation": "LS20 level 0: visible player, walls, and a closed door.",
                "available_actions": ["up", "down", "left", "right"],
                "agent_response": "I only observe the player, walls, and a door; try right as a reversible test and update from the next observation.",
                "action": "right",
            }
        ]

        report = scorer.score_events(events)

        self.assertEqual(report["state_confabulation_count"], 0)
        self.assertEqual(report["illegal_action_count"], 0)
        self.assertEqual(report["violations"], [])

    def test_load_jsonl_trace_reads_events(self):
        scorer = load_scorer_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "trace.jsonl"
            path.write_text(
                '{"t":0,"observation":"visible player and walls","available_actions":["right"],"agent_response":"try right","action":"right"}\n',
                encoding="utf-8",
            )

            events = scorer.load_jsonl_trace(path)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "right")


if __name__ == "__main__":
    unittest.main()
