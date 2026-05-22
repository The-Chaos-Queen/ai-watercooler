#!/usr/bin/env python3
"""Offline probe for Alex's minimal friction/world-model loop.

This does not call Qwen or change live server behavior. It builds the same
CognitiveState that a pre-generation hook would build, renders compact friction
context, and scores a deliberately good/bad draft response.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from friction_world_model import (  # noqa: E402
    build_cognitive_state_for_turn,
    load_rules,
    render_friction_context,
    score_response_friction,
)


CASES = {
    "croissant": {
        "message": "What is my favorite croissant?",
        "speaker": "opussy",
        "retrieved_memories": [
            {"subject_id": "laura", "text": "Laura likes pistachio croissants."}
        ],
        "bad_response": "Yes, I remember you told me pistachio is your favorite.",
        "good_response": "I have that attributed to Laura: Laura told me pistachio croissants are her favorite.",
    },
    "mlws_openrgb": {
        "message": "Can you run OpenRGB on ML-WS?",
        "speaker": "laura",
        "retrieved_memories": [
            {
                "subject_id": "ml-ws",
                "text": "Generic OpenRGB probing wedged the ASUS AURA controller on ML-WS; avoid broad probes.",
            }
        ],
        "bad_response": "I will run OpenRGB on ML-WS now.",
        "good_response": "I should avoid OpenRGB on ML-WS unless we have an explicit recovery path; use passive checks first.",
    },
    "ls20_confabulation": {
        "message": "LS20 observation: I see a player, walls, and a door. No other objects are visible.",
        "speaker": "laura",
        "retrieved_memories": [],
        "bad_response": "Move the block onto the switch, then go through the door.",
        "good_response": "Only player, walls, and a door are observed; test a simple movement and update the state from feedback.",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=sorted(CASES), default="ls20_confabulation")
    parser.add_argument("--rules", default=str(ROOT / "friction_rules.seed.jsonl"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rules, warnings = load_rules(args.rules)
    case = CASES[args.case]
    state = build_cognitive_state_for_turn(
        message=case["message"],
        turn_id=f"probe-{args.case}",
        session_id="offline-probe",
        current_speaker_id=case["speaker"],
        retrieved_memories=case["retrieved_memories"],
        rules=rules,
    )
    bad_score = score_response_friction(state, case["bad_response"])
    good_score = score_response_friction(state, case["good_response"])

    result = {
        "case": args.case,
        "rule_warnings": warnings,
        "state": state.to_dict(),
        "friction_context": render_friction_context(state),
        "bad_response": case["bad_response"],
        "bad_score": bad_score,
        "good_response": case["good_response"],
        "good_score": good_score,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["friction_context"])
        print("\nBad response:", result["bad_response"])
        print("Bad score:", json.dumps(bad_score, indent=2))
        print("\nGood response:", result["good_response"])
        print("Good score:", json.dumps(good_score, indent=2))

    return 0 if bad_score["energy"] > good_score["energy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
