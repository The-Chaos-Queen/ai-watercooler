"""Model-free/CPU tests for hardened Gemma G0b extraction helpers."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch
import torch.nn as nn

BRIDGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRIDGE_DIR))

from extract_oxytocin_gemma import (  # noqa: E402
    ACTUATOR_DECISION,
    DEFAULT_OUTPUT,
    EXPECTED_WIDTH,
    SURFACE_KIND,
    TARGET_LAYERS,
    _capture_one,
    _parser,
    atomic_torch_save_no_overwrite,
    build_artifact_payload,
    compute_method_a_directions,
    publish_digest_sidecar_no_overwrite,
    resolve_surface_bindings,
)
from sev_primary_holdout import (  # noqa: E402
    DEFAULT_CORPUS_PATH,
    DEFAULT_MANIFEST_PATH,
    load_primary_holdout_manifest,
)


class FakeValueNorm(nn.Module):
    with_scale = False

    def forward(self, value_states: torch.Tensor) -> torch.Tensor:
        return value_states


class FakeAttention(nn.Module):
    def __init__(self, width: int = EXPECTED_WIDTH):
        super().__init__()
        self.layer_type = "full_attention"
        self.use_alternative_attention = True
        self.v_proj = None
        self.is_kv_shared_layer = False
        self.head_dim = EXPECTED_WIDTH
        self.k_proj = nn.Linear(4, width, bias=False)
        self.v_norm = FakeValueNorm()


class FakeLayer(nn.Module):
    def __init__(self, width: int = EXPECTED_WIDTH):
        super().__init__()
        self.self_attn = FakeAttention(width)


class FakeLanguageModel(nn.Module):
    def __init__(self, width: int = EXPECTED_WIDTH):
        super().__init__()
        self.layers = nn.ModuleList([FakeLayer(width) for _ in range(42)])


class FakeContainer(nn.Module):
    def __init__(self, width: int = EXPECTED_WIDTH):
        super().__init__()
        self.language_model = FakeLanguageModel(width)


class FakeGemma(nn.Module):
    def __init__(self, width: int = EXPECTED_WIDTH):
        super().__init__()
        self.model = FakeContainer(width)
        layer_types = ["sliding_attention"] * 42
        for layer in TARGET_LAYERS:
            layer_types[layer] = "full_attention"
        self.config = SimpleNamespace(
            text_config=SimpleNamespace(
                attention_k_eq_v=True,
                num_global_key_value_heads=1,
                global_head_dim=EXPECTED_WIDTH,
                num_kv_shared_layers=0,
                layer_types=layer_types,
            )
        )

    def forward(self, input_ids: torch.Tensor, use_cache: bool = False):
        del use_cache
        batch, tokens = input_ids.shape
        for layer in TARGET_LAYERS:
            values = torch.full(
                (batch, tokens, 1, EXPECTED_WIDTH),
                float(layer),
                dtype=torch.float32,
            )
            self.model.language_model.layers[layer].self_attn.v_norm(values)
        return None


def test_option_a_binding_names_exact_value_norm_pre_surface():
    model = FakeGemma()
    bindings = resolve_surface_bindings(model)
    assert tuple(binding.layer for binding in bindings) == TARGET_LAYERS
    assert all(binding.module_path.endswith("self_attn.v_norm") for binding in bindings)
    assert all(binding.descriptor["surface_kind"] == SURFACE_KIND for binding in bindings)
    assert all(
        binding.descriptor["actuator_decision"] == ACTUATOR_DECISION
        for binding in bindings
    )
    assert "vproj" not in DEFAULT_OUTPUT.name.lower()


def test_option_a_binding_rejects_wrong_width():
    with pytest.raises(ValueError, match="width/module mismatch"):
        resolve_surface_bindings(FakeGemma(width=256))


def test_pre_hook_capture_reads_exact_value_norm_input():
    model = FakeGemma()
    bindings = resolve_surface_bindings(model)
    captured = _capture_one(
        model,
        lambda text: {"input_ids": torch.ones((1, len(text)), dtype=torch.long)},
        "abc",
        bindings,
        "cpu",
    )
    assert set(captured) == set(TARGET_LAYERS)
    for layer in TARGET_LAYERS:
        assert captured[layer].shape == (EXPECTED_WIDTH,)
        assert torch.all(captured[layer] == float(layer))


def _activation_maps() -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor]]:
    warm = {}
    neutral = {}
    for layer in TARGET_LAYERS:
        neutral[layer] = torch.zeros((3, EXPECTED_WIDTH))
        warm[layer] = torch.stack(
            [
                torch.ones(EXPECTED_WIDTH),
                torch.full((EXPECTED_WIDTH,), 2.0),
                torch.full((EXPECTED_WIDTH,), 3.0),
            ]
        )
    return warm, neutral


def test_method_a_is_fixed_paired_mean_delta_and_unit_norm():
    warm, neutral = _activation_maps()
    directions, statistics = compute_method_a_directions(warm, neutral)
    expected = torch.ones(EXPECTED_WIDTH)
    expected = expected / expected.norm()
    for layer in TARGET_LAYERS:
        assert torch.allclose(directions[layer], expected)
        assert float(directions[layer].norm()) == pytest.approx(1.0)
        assert statistics[layer]["pair_count"] == 3


def test_method_a_rejects_nonfinite_wrong_width_and_zero_delta():
    warm, neutral = _activation_maps()
    warm[29][0, 0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        compute_method_a_directions(warm, neutral)

    warm, neutral = _activation_maps()
    warm[35] = torch.zeros((3, 511))
    neutral[35] = torch.zeros((3, 511))
    with pytest.raises(ValueError, match="must be"):
        compute_method_a_directions(warm, neutral)

    zero = {layer: torch.zeros((3, EXPECTED_WIDTH)) for layer in TARGET_LAYERS}
    with pytest.raises(ValueError, match="zero"):
        compute_method_a_directions(zero, zero)


def test_atomic_publication_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "artifact.pt"
    digest = atomic_torch_save_no_overwrite({"value": torch.tensor([1.0])}, path)
    assert path.exists()
    assert len(digest) == 64
    with pytest.raises(FileExistsError, match="overwrite"):
        atomic_torch_save_no_overwrite({"value": torch.tensor([2.0])}, path)
    loaded = torch.load(path, map_location="cpu", weights_only=True)
    assert loaded["value"].item() == 1.0


def test_digest_sidecar_persists_artifact_identity_and_refuses_overwrite(tmp_path: Path):
    artifact = tmp_path / "artifact.pt"
    artifact.write_bytes(b"artifact")
    primary = SimpleNamespace(
        manifest_id="primary-holdout-test",
        frozen_split=SimpleNamespace(split_id="split-test"),
    )
    sidecar = publish_digest_sidecar_no_overwrite(
        artifact,
        artifact_sha256="a" * 64,
        code_revision="b" * 40,
        model_revision="c" * 40,
        primary_holdout=primary,
    )
    payload = __import__("json").loads(sidecar.read_text(encoding="utf-8"))
    assert payload["artifact_sha256"] == "a" * 64
    assert payload["split_id"] == "split-test"
    with pytest.raises(FileExistsError, match="overwrite"):
        publish_digest_sidecar_no_overwrite(
            artifact,
            artifact_sha256="a" * 64,
            code_revision="b" * 40,
            model_revision="c" * 40,
            primary_holdout=primary,
        )


def test_full_artifact_payload_remains_weights_only_safe(tmp_path: Path):
    warm, neutral = _activation_maps()
    directions, statistics = compute_method_a_directions(warm, neutral)
    primary = load_primary_holdout_manifest(DEFAULT_MANIFEST_PATH, DEFAULT_CORPUS_PATH)
    payload = build_artifact_payload(
        directions,
        statistics,
        model_id="google/gemma-4-12B",
        revision="a" * 40,
        model_provenance={"descriptor_sha256": "b" * 64},
        processor_provenance={"descriptor_sha256": "c" * 64},
        bindings=resolve_surface_bindings(FakeGemma()),
        primary_holdout=primary,
        split_manifest_path=DEFAULT_MANIFEST_PATH,
        corpus_path=DEFAULT_CORPUS_PATH,
        code_revision="d" * 40,
    )
    assert isinstance(payload["metadata"]["provenance"]["code"]["torch_version"], str)
    path = tmp_path / "full.pt"
    atomic_torch_save_no_overwrite(payload, path)
    restored = torch.load(path, map_location="cpu", weights_only=True)
    assert restored["schema_version"] == payload["schema_version"]


def test_cli_requires_split_manifest_and_exact_revision():
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--split-manifest",
                "split.json",
                "--revision",
                "main",
                "--code-revision",
                "a" * 40,
            ]
        )
