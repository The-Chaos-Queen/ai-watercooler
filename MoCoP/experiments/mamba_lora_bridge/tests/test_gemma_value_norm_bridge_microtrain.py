from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))
import train_gemma_value_norm_bridge_microtrain as microtrain  # noqa: E402


def test_synthetic_microtrain_has_three_512_wide_outputs_and_learns():
    records = microtrain.synthetic_records(count=4, seed=41)
    model, summary = microtrain.train_records(
        records,
        steps=48,
        lr=1e-2,
        hidden_dim=32,
        seed=43,
    )
    source, targets = microtrain.validate_records(records)
    with torch.no_grad():
        outputs = model(source)
    assert set(outputs) == set(microtrain.APPROVED_TEETH)
    assert all(tuple(outputs[tooth].shape) == (4, microtrain.TARGET_WIDTH) for tooth in outputs)
    assert torch.isfinite(microtrain.directional_loss(outputs, targets))
    assert summary["final_directional_loss"] < summary["initial_directional_loss"]
    assert summary["trainable_parameters"] > 0


def test_record_validation_refuses_missing_current_tooth():
    record = microtrain.synthetic_records(count=2, seed=5)[0]
    broken = microtrain.TrainingRecord(
        scenario_id=record.scenario_id,
        neutral_id=record.neutral_id,
        source_delta=record.source_delta,
        target_deltas={29: record.target_deltas[29], 35: record.target_deltas[35]},
        source_norm=record.source_norm,
        target_norms={29: record.target_norms[29], 35: record.target_norms[35]},
    )
    with pytest.raises(ValueError, match="exactly"):
        microtrain.validate_records([broken, microtrain.synthetic_records(count=2, seed=6)[1]])


def test_checkpoint_publication_is_no_overwrite(tmp_path: Path):
    path = tmp_path / "microtrain.pt"
    digest = microtrain._atomic_torch_save_no_overwrite({"status": "ok"}, path)
    assert len(digest) == 64
    assert torch.load(path, weights_only=False)["status"] == "ok"
    with pytest.raises(FileExistsError):
        microtrain._atomic_torch_save_no_overwrite({"status": "nope"}, path)


def test_device_alias_targets_bridge_only():
    args = microtrain.build_parser().parse_args(
        [
            "--mode",
            "synthetic",
            "--out",
            "artifact.pt",
            "--device",
            "cuda",
            "--capture-progress-every",
            "1",
            "--train-progress-every",
            "3",
        ]
    )
    assert args.bridge_device == "cuda"
    assert args.capture_progress_every == 1
    assert args.train_progress_every == 3


def test_training_summary_records_loss_curve_and_per_tooth_cosines():
    records = microtrain.synthetic_records(count=4, seed=71)
    _, summary = microtrain.train_records(
        records,
        steps=12,
        lr=1e-2,
        hidden_dim=16,
        seed=73,
        device="cpu",
    )
    curve = summary["directional_loss_curve"]
    assert len(curve) == 13
    assert curve[0] == pytest.approx(summary["initial_directional_loss"])
    assert curve[-1] == pytest.approx(summary["final_directional_loss"])
    assert all(torch.isfinite(torch.tensor(curve)))
    assert set(summary["per_tooth_final_mean_cosine"]) == {"29", "35", "41"}
    assert all(
        -1.0 <= value <= 1.0 for value in summary["per_tooth_final_mean_cosine"].values()
    )


def test_train_progress_is_structured_and_rate_limited(capsys):
    records = microtrain.synthetic_records(count=4, seed=79)
    microtrain.train_records(
        records,
        steps=5,
        lr=1e-2,
        hidden_dim=16,
        seed=83,
        progress_every=2,
    )
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["step"] for event in events] == [2, 4, 5]
    assert all(event["event"] == "bridge_train_progress" for event in events)
    assert all(event["steps"] == 5 for event in events)


def test_selected_pair_manifest_binds_c1_exclusion_and_rejects_corruption(tmp_path: Path):
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "sev_disposition_v0"
    corpus = fixture_root / "sev_disposition_v0.jsonl"
    manifest = fixture_root / "primary_holdout_v2.json"
    _, source_manifest = microtrain.load_selected_pairs(
        corpus_path=corpus,
        holdout_path=manifest,
        scenario_ids=("craft_1_warm", "family_1_warm"),
    )
    assert source_manifest["c1_holdout_exclusion_checked"] is True
    assert "craft_5" in source_manifest["c1_held_out_skeletons"]
    assert source_manifest["selected_skeleton_ids"] == ["craft_1", "family_1"]

    corrupted = json.loads(manifest.read_text(encoding="utf-8"))
    corrupted["frozen_split"]["pairs"].append(
        {"scenario_id": "craft_5_warm", "neutral_id": "craft_5_neutral"}
    )
    corrupted_path = tmp_path / "corrupted_primary_holdout.json"
    corrupted_path.write_text(json.dumps(corrupted), encoding="utf-8")
    with pytest.raises(ValueError, match="C1-held-out"):
        microtrain.load_selected_pairs(
            corpus_path=corpus,
            holdout_path=corrupted_path,
            scenario_ids=("craft_5_warm",),
        )
