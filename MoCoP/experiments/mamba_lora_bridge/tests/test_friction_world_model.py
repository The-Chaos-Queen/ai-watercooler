import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from friction_world_model import (
    CognitiveState,
    FrictionRule,
    TensionEvent,
    build_cognitive_state_for_turn,
    classify_turn,
    load_rules,
    render_friction_context,
    score_response_friction,
    select_active_rules,
)


class FrictionWorldModelTests(unittest.TestCase):
    def test_cognitive_state_serializes_to_dict(self):
        state = CognitiveState(
            turn_id="t1",
            session_id="s1",
            current_speaker_id="opussy",
            identity_confidence=0.9,
            speech_act="personal_preference_statement",
            trigger_tags=["personal_fact", "preference"],
            topics=["croissant"],
            entities=[{"id": "pistachio_croissant", "type": "food"}],
            retrieved_memories=[{"subject_id": "laura", "text": "Laura likes pistachio croissants."}],
            active_rules=[],
            active_tensions=[],
        )

        data = state.to_dict()

        self.assertEqual(data["current_speaker_id"], "opussy")
        self.assertEqual(data["speech_act"], "personal_preference_statement")
        self.assertEqual(data["retrieved_memories"][0]["subject_id"], "laura")

    def test_friction_rule_defaults_counters_to_zero(self):
        rule = FrictionRule(
            id="preserve_attribution",
            title="Preserve attribution",
            status="active",
            trigger_tags=["attribution"],
            rule_text="Name the subject of cross-person memories.",
            failure_mode="provenance_collapse",
            energy_terms={"attribution": 1.0},
            evidence_ids=[],
            confidence=0.7,
        )

        self.assertEqual(rule.activation_count, 0)
        self.assertEqual(rule.success_count, 0)
        self.assertEqual(rule.failure_count, 0)

    def test_tension_event_records_prediction_and_observation(self):
        event = TensionEvent(
            id="e1",
            turn_id="t1",
            kind="prediction_error",
            severity=0.8,
            predicted="OpenRGB lists devices safely",
            observed="ML-WS became unreachable and fans ramped",
            prediction_error=1.0,
            evidence={"host": "ML-WS"},
        )

        self.assertTrue(event.observed.startswith("ML-WS"))
        self.assertFalse(event.resolved)

    def test_classify_turn_extracts_minimal_speech_acts(self):
        cases = [
            ("What is my favorite croissant?", "personal_recall_query", "personal_fact"),
            ("My favorite croissant is pistachio", "personal_preference_statement", "preference"),
            ("Do you remember who said pistachio?", "attribution_query", "attribution"),
            ("No, that's wrong, Laura said that", "correction", "correction"),
            ("Can you run OpenRGB on ML-WS?", "tool_action_request", "hardware_risk"),
        ]
        for message, expected_act, expected_tag in cases:
            with self.subTest(message=message):
                result = classify_turn(message)
                self.assertEqual(result["speech_act"], expected_act)
                self.assertIn(expected_tag, result["trigger_tags"])

    def test_load_rules_skips_malformed_lines_and_selects_matching_active_rules(self):
        with TemporaryDirectory() as td:
            rules_path = Path(td) / "rules.jsonl"
            rules_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "active_attr",
                                "title": "Attribution",
                                "status": "active",
                                "trigger_tags": ["attribution", "personal_fact"],
                                "rule_text": "Preserve subject attribution.",
                                "failure_mode": "provenance_collapse",
                                "energy_terms": {"attribution": 1.0},
                                "evidence_ids": [],
                                "confidence": 0.8,
                            }
                        ),
                        "not json",
                        json.dumps(
                            {
                                "id": "retired_rule",
                                "title": "Retired",
                                "status": "retired",
                                "trigger_tags": ["attribution"],
                                "rule_text": "Do not use.",
                                "failure_mode": "old",
                                "energy_terms": {},
                                "evidence_ids": [],
                                "confidence": 0.1,
                            }
                        ),
                    ]
                )
                + "\n"
            )

            rules, warnings = load_rules(rules_path)
            selected = select_active_rules(rules, ["personal_fact"], max_rules=5)

        self.assertEqual(warnings, 1)
        self.assertEqual([rule.id for rule in selected], ["active_attr"])

    def test_render_friction_context_is_compact_and_attributed(self):
        rule = FrictionRule(
            id="preserve_attribution",
            title="Preserve attribution",
            status="active",
            trigger_tags=["attribution"],
            rule_text="If mentioning memories about another person, name that person explicitly.",
            failure_mode="provenance_collapse",
            energy_terms={"attribution": 1.0},
            evidence_ids=[],
            confidence=0.9,
        )
        state = CognitiveState(
            turn_id="t1",
            session_id="s1",
            current_speaker_id="opussy",
            identity_confidence=0.95,
            speech_act="personal_preference_statement",
            trigger_tags=["preference", "personal_fact"],
            topics=["croissant"],
            entities=[],
            retrieved_memories=[{"subject_id": "laura", "text": "Laura likes pistachio croissants."}],
            active_rules=[rule],
            active_tensions=[],
        )

        rendered = render_friction_context(state, max_chars=500)

        self.assertIn("Current speaker: opussy", rendered)
        self.assertIn("Preserve attribution", rendered)
        self.assertIn("Laura likes pistachio", rendered)
        self.assertLessEqual(len(rendered), 500)

    def test_score_response_flags_cross_person_you_told_me_violation(self):
        state = CognitiveState(
            turn_id="t1",
            session_id="s1",
            current_speaker_id="opussy",
            identity_confidence=0.95,
            speech_act="personal_preference_statement",
            trigger_tags=["personal_fact", "attribution"],
            topics=["croissant"],
            entities=[],
            retrieved_memories=[{"subject_id": "laura", "text": "Laura likes pistachio croissants."}],
            active_rules=[],
            active_tensions=[],
        )

        score = score_response_friction(state, "Yes, I remember you told me pistachio is your favorite.")

        self.assertGreaterEqual(score["energy"], 1.0)
        self.assertEqual(score["violations"][0]["kind"], "provenance_collapse")

    def test_score_response_allows_explicit_cross_person_attribution(self):
        state = CognitiveState(
            turn_id="t1",
            session_id="s1",
            current_speaker_id="opussy",
            identity_confidence=0.95,
            speech_act="personal_preference_statement",
            trigger_tags=["personal_fact", "attribution"],
            topics=["croissant"],
            entities=[],
            retrieved_memories=[{"subject_id": "laura", "text": "Laura likes pistachio croissants."}],
            active_rules=[],
            active_tensions=[],
        )

        score = score_response_friction(state, "Laura told me pistachio is her favorite too.")

        self.assertEqual(score["energy"], 0.0)
        self.assertEqual(score["violations"], [])

    def test_build_cognitive_state_for_turn_selects_matching_rules(self):
        rules = [
            FrictionRule(
                id="state_tracking_required",
                title="State tracking required",
                status="active",
                trigger_tags=["game_state", "interactive_puzzle"],
                rule_text="Track only observed game state.",
                failure_mode="state_confabulation",
                energy_terms={"state_confabulation": 1.0},
                evidence_ids=[],
                confidence=0.9,
            )
        ]

        state = build_cognitive_state_for_turn(
            message="In LS20 I see a player, walls, and a door. What next?",
            turn_id="t-ls20",
            session_id="s1",
            current_speaker_id="laura",
            retrieved_memories=[],
            rules=rules,
        )

        self.assertEqual(state.speech_act, "interactive_game_observation")
        self.assertIn("game_state", state.trigger_tags)
        self.assertEqual([rule.id for rule in state.active_rules], ["state_tracking_required"])

    def test_score_response_flags_unobserved_game_object_confabulation(self):
        state = CognitiveState(
            turn_id="t-ls20",
            session_id="s1",
            current_speaker_id="laura",
            identity_confidence=0.95,
            speech_act="interactive_game_observation",
            trigger_tags=["game_state", "interactive_puzzle"],
            topics=["ls20"],
            entities=[
                {"id": "player", "type": "observed_game_object"},
                {"id": "wall", "type": "observed_game_object"},
                {"id": "door", "type": "observed_game_object"},
            ],
            retrieved_memories=[],
            active_rules=[],
            active_tensions=[],
        )

        score = score_response_friction(state, "Move the block onto the switch, then go through the door.")

        self.assertGreaterEqual(score["energy"], 1.0)
        self.assertEqual(score["violations"][0]["kind"], "state_confabulation")
        self.assertIn("block", score["violations"][0]["unobserved_terms"])

    def test_score_response_allows_observed_game_objects(self):
        state = CognitiveState(
            turn_id="t-ls20",
            session_id="s1",
            current_speaker_id="laura",
            identity_confidence=0.95,
            speech_act="interactive_game_observation",
            trigger_tags=["game_state", "interactive_puzzle"],
            topics=["ls20"],
            entities=[
                {"id": "player", "type": "observed_game_object"},
                {"id": "wall", "type": "observed_game_object"},
                {"id": "door", "type": "observed_game_object"},
            ],
            retrieved_memories=[],
            active_rules=[],
            active_tensions=[],
        )

        score = score_response_friction(state, "I observe only the player, walls, and a door; test moving right first.")

        self.assertEqual(score["energy"], 0.0)
        self.assertEqual(score["violations"], [])


if __name__ == "__main__":
    unittest.main()
