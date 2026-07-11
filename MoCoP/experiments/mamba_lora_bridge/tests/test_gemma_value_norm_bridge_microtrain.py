from __future__ import annotations

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
