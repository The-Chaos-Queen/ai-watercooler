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
import train_gemma_value_norm_bridge_microtrain as microtrain  # noqa: E402
import analyze_gemma_value_norm_bridge_refit_diagnostic as diagnostic  # noqa: E402


def _synthetic_payload() -> dict:
    """Construct a CPU-only captured artifact; no model capture or network access."""

    generator = torch.Generator().manual_seed(20260717)
    model = microtrain.ValueNormDeltaBridge(hidden_dim=4).cpu().eval()
    train_source = torch.randn(24, microtrain.SOURCE_WIDTH, generator=generator)
    eval_source = torch.randn(8, microtrain.SOURCE_WIDTH, generator=generator)
    with torch.no_grad():
        eval_predictions = model(eval_source)
    captured = {
        "train": {
            "source_deltas": train_source,
            "target_deltas": {
                str(tooth): torch.randn(24, microtrain.TARGET_WIDTH, generator=generator)
                for tooth in microtrain.APPROVED_TEETH
            },
        },
        "evaluation": {
            "source_deltas": eval_source,
            "target_deltas": {
                str(tooth): torch.randn(8, microtrain.TARGET_WIDTH, generator=generator)
                for tooth in microtrain.APPROVED_TEETH
            },
            "predicted_target_deltas": {
                str(tooth): eval_predictions[tooth].detach().clone()
                for tooth in microtrain.APPROVED_TEETH
            },
        },
    }
    return {
        "models": {
            "teeth": list(microtrain.APPROVED_TEETH),
            "source_width": microtrain.SOURCE_WIDTH,
            "target_width": microtrain.TARGET_WIDTH,
        },
        "training": {"hidden_dim": 4},
        "bridge_state_dict": model.state_dict(),
        "captured_deltas": captured,
        "captured_delta_sha256": refit.captured_delta_sha256(captured),
        "evaluation": {"shuffle_null": {"seed": 20260717, "count": 8}},
        "split_manifest": {"split_id": "synthetic-split"},
        "provenance": {"runner_code_sha256": "a" * 64},
    }


def test_train_only_norm_fits_recover_known_positive_scale_without_eval_inputs():
    prediction = torch.tensor([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    target = 2.0 * prediction

    vector_fit = diagnostic.fit_positive_vector_l2_scale(prediction, target)
    affine_fit = diagnostic.fit_affine_norm(prediction, target)

    assert vector_fit["alpha"] == pytest.approx(2.0)
    assert affine_fit["slope"] == pytest.approx(2.0)
    assert affine_fit["intercept"] == pytest.approx(0.0, abs=1e-6)
    assert diagnostic.apply_affine_norm(prediction, affine_fit) == pytest.approx(target)

    constrained = diagnostic.fit_positive_vector_l2_scale(prediction, -prediction)
    assert constrained["unconstrained_alpha"] == pytest.approx(-1.0)
    assert constrained["alpha"] == pytest.approx(0.0)
    assert constrained["nonnegative_constraint_active"] is True


def test_analyze_payload_verifies_receipts_and_rehydrates_cpu_bridge_without_model_capture():
    payload = _synthetic_payload()

    report = diagnostic.analyze_payload(
        payload,
        artifact_sha256="b" * 64,
        diagnostic_runner_sha256="c" * 64,
    )

    assert report["source_artifact"]["sha256"] == "b" * 64
    assert report["integrity"]["captured_delta_receipts_verified"] is True
    assert report["calibration_boundary"]["fit_rows"] == 24
    assert report["calibration_boundary"]["eval_rows"] == 8
    assert set(report["analysis"]["per_tooth"]) == {"29", "35", "41"}
    assert all(
        row["max_abs"] == pytest.approx(0.0)
        for row in report["integrity"]["saved_eval_reproduction"].values()
    )

    tampered = copy.deepcopy(payload)
    tampered["captured_delta_sha256"]["evaluation"]["source_deltas"] = "0" * 64
    with pytest.raises(ValueError, match="captured delta receipts"):
        diagnostic.analyze_payload(tampered, artifact_sha256="b" * 64, diagnostic_runner_sha256="c" * 64)


def test_json_publication_is_atomic_and_never_overwrites(tmp_path: Path):
    out = tmp_path / "diagnostic.json"

    digest = diagnostic.write_json_no_overwrite({"ok": True}, out)

    assert len(digest) == 64
    assert json.loads(out.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(FileExistsError, match="overwrite|artifact exists"):
        diagnostic.write_json_no_overwrite({"ok": False}, out)
