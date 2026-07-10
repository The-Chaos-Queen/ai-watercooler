"""Training-side matched-delta target selection + SEV-mirror parity (Codex #806).

Exercises the minimal seam added to ``train_cheese_bridge`` that makes
DirectionalLoss' ``target_dict[layer]`` the recorded DELTA (scenario - neutral)
rather than the absolute v_proj output, plus a parity guard (N5) that the
torch-free SEV pairing mirror in ``matched_delta_recording`` stays in lockstep
with ``disposition_runner`` over real SEV ids. No model load; torch (and, for the
parity test, transformers via disposition_runner) is imported, so the repo ``gpu``
marker applies and the suite is skipped by bare ``pytest``.

    python -m pytest tests/test_matched_delta_train_target.py -m gpu -q
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gpu

torch = pytest.importorskip("torch")
# The bare-pytest env can expose a partial/namespace ``torch`` (no torch.optim);
# require a real submodule so collection skips cleanly instead of erroring when
# train_cheese_bridge does ``from torch.optim import AdamW``.
pytest.importorskip("torch.optim")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from train_cheese_bridge import (  # noqa: E402
    DirectionalLoss,
    extract_matched_delta_target,
    is_matched_delta_payload,
)


def _delta_payload():
    """A record shaped like matched_delta_recording._write_records_torch output."""
    return {
        "recipe": "matched_delta_v1",
        "scenario_id": "craft_1_warm",
        "neutral_control_id": "craft_1_neutral",
        "split_id": "split-deadbeef",
        "layers": {
            "12": {
                "v_proj_out_scenario": torch.tensor([3.0, 4.0]),
                "v_proj_out_neutral": torch.tensor([1.0, 1.0]),
                "v_proj_out_delta": torch.tensor([2.0, 3.0]),
                "v_proj_out": torch.tensor([3.0, 4.0]),   # back-compat absolute
            }
        },
    }


def test_is_matched_delta_payload_discriminates():
    assert is_matched_delta_payload(_delta_payload()) is True
    # legacy per-layer dict is NOT a matched-delta payload.
    assert is_matched_delta_payload({12: {"v_proj_out": torch.tensor([1.0])}}) is False
    assert is_matched_delta_payload({"recipe": "something_else", "layers": {}}) is False


def test_extract_selects_delta_not_absolute():
    payload = _delta_payload()
    got = extract_matched_delta_target(payload, 12, "craft_1_warm")
    assert torch.equal(got, torch.tensor([2.0, 3.0]))       # the DELTA, not [3,4]


def test_extract_missing_delta_is_hard_error():
    payload = _delta_payload()
    del payload["layers"]["12"]["v_proj_out_delta"]
    with pytest.raises(KeyError):
        extract_matched_delta_target(payload, 12, "craft_1_warm")


def test_directional_loss_consumes_delta_target_dict():
    """The load-bearing contract: target_dict[layer] = the delta flows straight
    into DirectionalLoss. A prediction equal to the delta gives ~0 loss."""
    payload = _delta_payload()
    # single-layer probe against DirectionalLoss over that one target spec.
    from train_cheese_bridge import TARGET_SPECS

    layer0 = TARGET_SPECS[0][0]
    delta = extract_matched_delta_target(
        {**payload, "layers": {str(layer0): payload["layers"]["12"]}},
        layer0, "craft_1_warm")
    target_dict = {layer: delta for layer, _ in TARGET_SPECS}
    pred = [delta.clone().unsqueeze(0) for _ in TARGET_SPECS]   # perfect prediction
    loss = DirectionalLoss(alpha=0.9)(pred, target_dict)
    assert float(loss) < 1e-4


# --------------------------------------------------------------------------- #
# N5: the torch-free SEV mirror must stay in lockstep with disposition_runner. #
#     Imports disposition_runner (torch/transformers transitive) so it lives   #
#     here in the gpu-marked suite, not the model-free one.                    #
# --------------------------------------------------------------------------- #
def test_sev_mirror_matches_disposition_runner():
    pytest.importorskip("transformers")
    import disposition_runner as dr
    import matched_delta_recording as mdr

    corpus = mdr.load_sev_corpus()
    if not corpus:
        pytest.skip("SEV corpus not present")

    # load_sev_corpus parity: same ids + same records.
    dr_corpus = dr.load_sev_corpus()
    assert set(dr_corpus) == set(corpus)
    assert all(dr_corpus[i] == corpus[i] for i in corpus)

    # neutral_control_id parity over every real SEV id (+ the edge inputs).
    for cid in list(corpus) + ["DRIFT_CASES", "not_a_sev_id"]:
        assert mdr.neutral_control_id(cid) == dr.neutral_control_id(cid)
