from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")
SPIKES = Path(__file__).resolve().parents[1] / "spikes"
sys.path.insert(0, str(SPIKES))
import run_gemma_value_norm_bridge_refit_eval as refit  # noqa: E402


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "sev_disposition_v0"
CORPUS = FIXTURE_ROOT / "sev_disposition_v0.jsonl"
PRIMARY = FIXTURE_ROOT / "primary_holdout_v2.json"


EXPECTED_EVAL_SKELETONS = {
    "conflict_5",
    "craft_4",
    "discovery_4",
    "family_5",
    "food_1",
    "illness_2",
    "travel_2",
    "weather_3",
}


def test_bridge_refit_split_is_deterministic_topic_stratified_and_non_c1():
    manifest = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)
    rederived = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)

    assert manifest == rederived
    assert manifest["counts"] == {"eligible_non_c1_pairs": 32, "train_pairs": 24, "eval_pairs": 8}
    assert set(manifest["evaluation"]["skeleton_ids"]) == EXPECTED_EVAL_SKELETONS
    assert len(manifest["evaluation"]["topics"]) == 8
    assert len(set(manifest["evaluation"]["topics"])) == 8
    assert set(manifest["training"]["skeleton_ids"]).isdisjoint(EXPECTED_EVAL_SKELETONS)
    assert set(manifest["evaluation"]["skeleton_ids"]).isdisjoint(
        set(manifest["primary_c1_holdout"]["skeleton_ids"])
    )
    assert manifest["selection"]["domain"] == "mocop-bridge-refit-eval-v1"
    assert len(manifest["split_id"]) == 64


def test_refit_split_validation_rejects_tampered_membership():
    manifest = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)
    tampered = copy.deepcopy(manifest)
    tampered["evaluation"]["skeleton_ids"][0] = "craft_1"

    with pytest.raises(ValueError, match="split"):
        refit.validate_bridge_refit_split(
            tampered,
            corpus_path=CORPUS,
            primary_holdout_path=PRIMARY,
        )


def test_refit_split_publication_is_no_overwrite(tmp_path: Path):
    manifest = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)
    path = tmp_path / "refit_split.json"

    digest = refit.write_bridge_refit_split_no_overwrite(manifest, path)
    assert len(digest) == 64
    assert refit.load_and_validate_bridge_refit_split(
        path,
        corpus_path=CORPUS,
        primary_holdout_path=PRIMARY,
    ) == manifest
    with pytest.raises(FileExistsError):
        refit.write_bridge_refit_split_no_overwrite(manifest, path)


def test_captured_delta_hashes_bind_each_matrix_and_change_with_content():
    captured = {
        "train": {
            "source_deltas": torch.zeros(2, 2560),
            "target_deltas": {str(tooth): torch.zeros(2, 512) for tooth in (29, 35, 41)},
        },
        "evaluation": {
            "source_deltas": torch.ones(2, 2560),
            "target_deltas": {str(tooth): torch.ones(2, 512) for tooth in (29, 35, 41)},
            "predicted_target_deltas": {str(tooth): torch.full((2, 512), 2.0) for tooth in (29, 35, 41)},
        },
    }
    first = refit.captured_delta_sha256(captured)
    changed = copy.deepcopy(captured)
    changed["evaluation"]["predicted_target_deltas"]["29"][0, 0] = 3.0
    second = refit.captured_delta_sha256(changed)

    assert set(first) == {"train", "evaluation"}
    assert set(first["train"]) == {"source_deltas", "target_deltas"}
    assert set(first["evaluation"]) == {"source_deltas", "target_deltas", "predicted_target_deltas"}
    assert all(len(value) == 64 for section in first.values() for value in section.values())
    assert first != second


def test_main_refuses_existing_output_before_any_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)
    split_path = tmp_path / "valid.split.json"
    refit.write_bridge_refit_split_no_overwrite(manifest, split_path)
    protocol = tmp_path / "protocol.md"
    protocol.write_text("test protocol", encoding="utf-8")
    output = tmp_path / "already_exists.pt"
    output.write_bytes(b"existing artifact must survive")

    def capture_must_not_run(*args, **kwargs):
        raise AssertionError("capture must not start when output already exists")

    monkeypatch.setattr(refit.microtrain, "capture_training_records", capture_must_not_run)
    with pytest.raises(FileExistsError, match="overwrite"):
        refit.main(
            [
                "--mode",
                "capture_train_eval",
                "--split-manifest",
                str(split_path),
                "--out",
                str(output),
                "--protocol",
                str(protocol),
                "--corpus",
                str(CORPUS),
                "--primary-holdout",
                str(PRIMARY),
            ]
        )
    assert output.read_bytes() == b"existing artifact must survive"


def test_main_refuses_tampered_split_before_any_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest = refit.build_bridge_refit_split(corpus_path=CORPUS, primary_holdout_path=PRIMARY)
    manifest["training"]["pairs"][0]["scenario_id"] = "craft_1_warm"
    split_path = tmp_path / "tampered.split.json"
    split_path.write_text(json.dumps(manifest), encoding="utf-8")
    protocol = tmp_path / "protocol.md"
    protocol.write_text("test protocol", encoding="utf-8")

    def capture_must_not_run(*args, **kwargs):
        raise AssertionError("capture must not start for a tampered split")

    monkeypatch.setattr(refit.microtrain, "capture_training_records", capture_must_not_run)
    with pytest.raises(ValueError, match="split manifest"):
        refit.main(
            [
                "--mode",
                "capture_train_eval",
                "--split-manifest",
                str(split_path),
                "--out",
                str(tmp_path / "should_not_exist.pt"),
                "--protocol",
                str(protocol),
                "--corpus",
                str(CORPUS),
                "--primary-holdout",
                str(PRIMARY),
            ]
        )


def test_evaluation_beats_constant_and_deranged_pairing_for_oracle_predictions():
    generator = torch.Generator().manual_seed(20260716)
    eval_targets = {
        tooth: torch.randn(8, 512, generator=generator)
        for tooth in (29, 35, 41)
    }
    train_targets = {
        tooth: torch.full((24, 512), float(tooth))
        for tooth in (29, 35, 41)
    }
    predictions = {tooth: value.clone() for tooth, value in eval_targets.items()}

    report = refit.evaluate_predictions(
        predictions=predictions,
        eval_targets=eval_targets,
        train_targets=train_targets,
        shuffle_seed=20260717,
        shuffle_count=32,
    )

    assert report["sample_count"] == 8
    assert report["shuffle_null"]["count"] == 32
    for tooth in ("29", "35", "41"):
        row = report["per_tooth"][tooth]
        assert row["observed"]["mean_cosine"] == pytest.approx(1.0, abs=1e-6)
        assert row["observed_minus_constant_mean_cosine"] > 0.5
        assert row["observed_percentile_against_deranged_pairing"] == pytest.approx(1.0)
        assert row["observed"]["mean_relative_l2"] == pytest.approx(0.0, abs=1e-6)
        assert row["shuffle_null"]["p95_mean_cosine"] < 1.0
