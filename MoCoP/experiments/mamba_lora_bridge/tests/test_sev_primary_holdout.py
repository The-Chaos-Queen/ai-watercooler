"""Model-free tests for the deterministic SEV primary holdout."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

BRIDGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRIDGE_DIR))

from matched_delta_recording import load_sev_corpus  # noqa: E402
from sev_primary_holdout import (  # noqa: E402
    DEFAULT_CORPUS_PATH,
    DEFAULT_MANIFEST_PATH,
    build_primary_holdout_manifest,
    derive_topic_selections,
    load_primary_holdout_manifest,
    training_warm_neutral_pairs,
    validate_primary_holdout_manifest,
    validate_requested_holdouts,
)


EXPECTED_HOLDOUTS = (
    "conflict_2",
    "craft_5",
    "discovery_3",
    "family_2",
    "food_4",
    "illness_3",
    "travel_5",
    "weather_1",
)


def test_current_corpus_selects_one_fixed_skeleton_per_topic():
    corpus = load_sev_corpus(DEFAULT_CORPUS_PATH)
    selections = derive_topic_selections(corpus)
    assert len(selections) == 8
    assert len({item["topic"] for item in selections}) == 8
    assert tuple(item["skeleton_id"] for item in selections) == EXPECTED_HOLDOUTS
    assert all(len(item["selection_digest"]) == 64 for item in selections)


def test_selection_is_independent_of_corpus_iteration_order():
    corpus = load_sev_corpus(DEFAULT_CORPUS_PATH)
    reversed_corpus = dict(reversed(list(corpus.items())))
    assert derive_topic_selections(reversed_corpus) == derive_topic_selections(corpus)


def test_manifest_binds_exact_holdout_and_training_split():
    manifest = build_primary_holdout_manifest(
        DEFAULT_CORPUS_PATH,
        corpus_label="fixtures/sev_disposition_v0/sev_disposition_v0.jsonl",
    )
    assert tuple(manifest["held_out_skeletons"]) == EXPECTED_HOLDOUTS
    assert manifest["frozen_split"]["n_pairs"] == 96
    assert len(manifest["frozen_split"]["pairs"]) == 96
    assert manifest["frozen_split"]["split_id"].startswith("split-")

    corpus = load_sev_corpus(DEFAULT_CORPUS_PATH)
    held = set(EXPECTED_HOLDOUTS)
    scenario_ids = {row["scenario_id"] for row in manifest["frozen_split"]["pairs"]}
    expected_ids = {
        record_id
        for record_id, record in corpus.items()
        if record["class"] != "neutral" and record["skeleton_id"] not in held
    }
    assert scenario_ids == expected_ids
    assert not {
        corpus[scenario_id]["skeleton_id"] for scenario_id in scenario_ids
    } & held


def test_checked_in_manifest_rederives_cleanly():
    primary = load_primary_holdout_manifest(DEFAULT_MANIFEST_PATH, DEFAULT_CORPUS_PATH)
    assert primary.held_out_skeletons == EXPECTED_HOLDOUTS
    assert primary.frozen_split.split_id == "split-5780c8ec67157703"


def test_g0_training_pairs_are_exactly_the_32_non_holdout_skeletons():
    primary = load_primary_holdout_manifest(DEFAULT_MANIFEST_PATH, DEFAULT_CORPUS_PATH)
    corpus = load_sev_corpus(DEFAULT_CORPUS_PATH)
    pairs = training_warm_neutral_pairs(corpus, primary)
    skeletons = {pair[0] for pair in pairs}
    assert len(pairs) == 32
    assert len(skeletons) == 32
    assert not skeletons & set(EXPECTED_HOLDOUTS)
    assert skeletons == {
        record["skeleton_id"]
        for record in corpus.values()
        if record["skeleton_id"] not in EXPECTED_HOLDOUTS
    }


def test_requested_holdouts_reject_unknown_duplicate_and_noncanonical_membership():
    corpus = load_sev_corpus(DEFAULT_CORPUS_PATH)
    with pytest.raises(ValueError, match="unknown"):
        validate_requested_holdouts(corpus, [*EXPECTED_HOLDOUTS[:-1], "bogus_99"])
    with pytest.raises(ValueError, match="duplicate"):
        validate_requested_holdouts(corpus, [*EXPECTED_HOLDOUTS, EXPECTED_HOLDOUTS[0]])
    with pytest.raises(ValueError, match="differs"):
        validate_requested_holdouts(
            corpus,
            [*EXPECTED_HOLDOUTS[:-1], "weather_2"],
            expected=EXPECTED_HOLDOUTS,
        )


def test_manifest_tamper_is_rejected_even_with_real_skeleton_ids():
    manifest = build_primary_holdout_manifest(DEFAULT_CORPUS_PATH)
    tampered = copy.deepcopy(manifest)
    tampered["held_out_skeletons"][-1] = "weather_2"
    with pytest.raises(ValueError, match="differs"):
        validate_primary_holdout_manifest(tampered, DEFAULT_CORPUS_PATH)

    reordered = copy.deepcopy(manifest)
    reordered["held_out_skeletons"] = list(reversed(reordered["held_out_skeletons"]))
    with pytest.raises(ValueError, match="canonical topic order"):
        validate_primary_holdout_manifest(reordered, DEFAULT_CORPUS_PATH)


def test_manifest_rejects_corpus_content_drift(tmp_path: Path):
    manifest = build_primary_holdout_manifest(DEFAULT_CORPUS_PATH)
    rows = DEFAULT_CORPUS_PATH.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["text"] += " changed"
    rows[0] = json.dumps(first, ensure_ascii=True)
    changed_path = tmp_path / "sev.jsonl"
    changed_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_primary_holdout_manifest(manifest, changed_path)
