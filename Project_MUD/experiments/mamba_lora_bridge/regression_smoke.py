"""
regression_smoke.py - Lightweight checks for recent bridge regressions.

This script intentionally avoids model downloads and large checkpoints.
It validates local tensor wiring and shape/dtype guardrails only.

Run:
    python regression_smoke.py
"""

from __future__ import annotations

import sys
from typing import List, Tuple

import torch
import torch.nn as nn

from cognitive_bridge import BridgeConfig, CognitiveBridge
from models import MambaStateCompressor


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_compressor_explicit_geometry() -> None:
    """Compressor must use the configured feature width and reject mismatches."""
    comp = MambaStateCompressor(
        mamba_layers=2,
        mamba_d_model=4,
        mamba_d_state=4,
        output_dim=8,
        target_layer=1,
    )

    x1 = torch.randn(1, 2, 4, 4)
    y1 = comp(x1)
    _assert(tuple(y1.shape) == (1, 8), f"Unexpected output shape: {tuple(y1.shape)}")

    # Same shape should continue to work.
    _ = comp(torch.randn(1, 2, 4, 4))

    # Different flattened width should fail fast with clear error.
    try:
        _ = comp(torch.randn(1, 2, 4, 2))
        raise AssertionError("Expected compressor to reject changing feature width.")
    except RuntimeError as exc:
        _assert(
            "feature width changed" in str(exc),
            f"Unexpected error message: {exc}",
        )


def test_count_params_safe_initialized() -> None:
    """Explicitly-shaped modules should register all params immediately."""
    config = BridgeConfig(mamba_target_layer=1)
    bridge = CognitiveBridge(config)
    comp = MambaStateCompressor(2, 4, 4, 8, target_layer=config.mamba_target_layer)
    _assert(comp.target_layer == 1, f"Expected propagated target layer 1, got {comp.target_layer}")
    total, uninitialized = bridge._count_params_safe(comp)
    _assert(uninitialized == 0, f"Expected no uninitialized params, got {uninitialized}")
    _assert(total > 0, "Expected registered compressor params.")


def test_mixed_target_dims() -> None:
    """Per-layer hypernetwork must handle mixed GQA dimensions (q_proj != v_proj)."""
    from models import LoRAHypernetwork

    # GQA scenario: q_proj outputs 4096, v_proj outputs 512
    target_dims = [(2560, 4096), (2560, 512), (2560, 4096)]
    lora_rank = 4
    context_dim = 32

    hyper = LoRAHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        lora_rank=lora_rank,
        hidden_dim=64,
    )

    ctx = torch.randn(1, context_dim)
    pairs = hyper(ctx)

    _assert(len(pairs) == 3, f"Expected 3 pairs, got {len(pairs)}")
    # Check each pair has correct dimensions
    for i, ((A, B), (in_dim, out_dim)) in enumerate(zip(pairs, target_dims)):
        _assert(
            tuple(A.shape) == (1, in_dim, lora_rank),
            f"Pair {i} A shape: expected (1, {in_dim}, {lora_rank}), got {tuple(A.shape)}"
        )
        _assert(
            tuple(B.shape) == (1, lora_rank, out_dim),
            f"Pair {i} B shape: expected (1, {lora_rank}, {out_dim}), got {tuple(B.shape)}"
        )


def test_inject_lora_keeps_float() -> None:
    """_inject_lora must not cast LoRA tensors to quantized byte weight dtype."""

    class FakeDynamicLayer:
        def __init__(self):
            # Simulate 4-bit wrapper exposing uint8 weight storage dtype.
            self.weight = torch.zeros(1, dtype=torch.uint8)
            self.last_A = None
            self.last_B = None

        def set_lora(self, A: torch.Tensor, B: torch.Tensor):
            self.last_A = A
            self.last_B = B

        def clear_lora(self):
            self.last_A = None
            self.last_B = None

    class FakeHypernetwork(nn.Module):
        def __init__(self):
            super().__init__()
            self._dummy = nn.Parameter(torch.tensor(0.0, dtype=torch.float32))

        def forward(self, context_vector: torch.Tensor):
            A = torch.randn(1, 4, 2, dtype=torch.float32)
            B = torch.randn(1, 2, 6, dtype=torch.float32)
            return [(A, B)]

    bridge = CognitiveBridge(BridgeConfig())
    bridge.hypernetwork = FakeHypernetwork()
    bridge._hyper_device = torch.device("cpu")
    fake_layer = FakeDynamicLayer()
    bridge._patched_layers = [fake_layer]  # type: ignore[assignment]

    norms = bridge._inject_lora(torch.randn(1, 8))
    _assert(len(norms) == 1, f"Expected one norm, got {len(norms)}")
    _assert(fake_layer.last_A is not None and fake_layer.last_B is not None, "LoRA was not set.")
    _assert(
        fake_layer.last_A.dtype.is_floating_point and fake_layer.last_B.dtype.is_floating_point,
        f"Expected floating LoRA tensors, got {fake_layer.last_A.dtype}, {fake_layer.last_B.dtype}",
    )


def test_audit_schedule_detects_drift() -> None:
    """inject_every=6 with lags [3,12,24] must be flagged as drifting."""
    from mamba_linear_probe import audit_schedule
    result = audit_schedule(turns=60, inject_every=6, probe_lags=[3, 12, 24])
    _assert(result["drift_count"] > 0, f"Expected drift, got drift_count={result['drift_count']}")


def test_audit_schedule_zero_drift() -> None:
    """inject_every=5 with lags [3,12,24] should have zero drift."""
    from mamba_linear_probe import audit_schedule
    result = audit_schedule(turns=60, inject_every=5, probe_lags=[3, 12, 24])
    _assert(result["drift_count"] == 0, f"Expected zero drift, got drift_count={result['drift_count']}")
    _assert(result["probes_total"] >= 27, f"Expected >=27 probes, got {result['probes_total']}")


class FakeTokenizer:
    """Minimal tokenizer stub for dataset/masking tests.

    Deliberately does not implement decode(). Current tests run with
    include_text=False, so any decode call would signal an invalid test setup.
    """

    def __init__(self) -> None:
        self.pad_token = "<pad>"
        self.eos_token = "<eos>"
        self.pad_token_id = 0
        self.eos_token_id = 1
        self.all_special_tokens = ["<|im_start|>", "<|im_end|>", self.pad_token, self.eos_token]
        self._token_to_id = {
            self.pad_token: self.pad_token_id,
            self.eos_token: self.eos_token_id,
            "<|im_start|>": 2,
            "<|im_end|>": 3,
        }
        self._next_id = 4

    def encode(self, text: str, add_special_tokens: bool = False, return_tensors=None):
        del add_special_tokens
        ids = []
        cursor = 0
        while cursor < len(text):
            if text.startswith("<|im_start|>", cursor):
                ids.append(self._token_to_id["<|im_start|>"])
                cursor += len("<|im_start|>")
                continue
            if text.startswith("<|im_end|>", cursor):
                ids.append(self._token_to_id["<|im_end|>"])
                cursor += len("<|im_end|>")
                continue

            token = text[cursor]
            if token not in self._token_to_id:
                self._token_to_id[token] = self._next_id
                self._next_id += 1
            ids.append(self._token_to_id[token])
            cursor += 1

        if return_tensors == "pt":
            return torch.tensor([ids], dtype=torch.long)
        return ids

    def decode(self, token_ids, skip_special_tokens: bool = False) -> str:
        del token_ids, skip_special_tokens
        raise RuntimeError("FakeTokenizer.decode is unsupported; use include_text=False in tests.")


def test_bridge_dataset_answer_only_masking() -> None:
    """Fact mode must keep only answer tokens unmasked."""
    from bridge_dataset import BridgeDataset, BridgeDatasetConfig

    mamba_tokenizer = FakeTokenizer()
    qwen_tokenizer = FakeTokenizer()
    dataset = BridgeDataset(
        BridgeDatasetConfig(
            num_samples=2,
            mode="fact",
            mamba_context_tokens=128,
            max_qwen_tokens=256,
            min_post_target_tokens=16,
            max_post_target_tokens=32,
            seed=7,
            include_text=False,
        ),
        mamba_tokenizer=mamba_tokenizer,
        qwen_tokenizer=qwen_tokenizer,
    )

    sample = dataset[0]
    _assert(tuple(sample["mamba_history_ids"].shape) == (128,), "Mamba context must be exact-width.")

    answer_ids = torch.tensor(
        qwen_tokenizer.encode(sample["answer_text"], add_special_tokens=False),
        dtype=torch.long,
    )
    supervised = sample["qwen_labels"][sample["qwen_labels"] != -100]
    _assert(torch.equal(supervised, answer_ids), "Only exact answer tokens should remain unmasked.")

    answer_start, answer_end = sample["metadata"]["answer_span"]
    _assert(
        bool(torch.all(sample["qwen_labels"][:answer_start] == -100).item()),
        "Prompt tokens must be fully masked.",
    )
    _assert(
        bool(torch.all(sample["qwen_labels"][answer_end:] == -100).item()),
        "Tokens after the answer must remain masked.",
    )


def test_bridge_dataset_collator_shapes() -> None:
    """Collator must pad Qwen while preserving fixed Mamba windows."""
    from bridge_dataset import BridgeBatchCollator, BridgeDataset, BridgeDatasetConfig

    mamba_tokenizer = FakeTokenizer()
    qwen_tokenizer = FakeTokenizer()
    dataset = BridgeDataset(
        BridgeDatasetConfig(
            num_samples=3,
            mode="general",
            mamba_context_tokens=96,
            max_qwen_tokens=256,
            seed=11,
            include_text=False,
        ),
        mamba_tokenizer=mamba_tokenizer,
        qwen_tokenizer=qwen_tokenizer,
    )

    batch = BridgeBatchCollator(qwen_pad_token_id=qwen_tokenizer.pad_token_id)(
        [dataset[0], dataset[1]]
    )

    _assert(tuple(batch["mamba_history_ids"].shape) == (2, 96), "Unexpected Mamba batch shape.")
    _assert(batch["qwen_input_ids"].shape == batch["qwen_labels"].shape, "Qwen tensors must align.")
    _assert(
        batch["qwen_prompt_ids"].shape[1] < batch["qwen_input_ids"].shape[1],
        "Prompt tensor should exclude assistant answer tokens.",
    )
    _assert(
        batch["qwen_prompt_ids"].shape == batch["qwen_prompt_attention_mask"].shape,
        "Prompt ids and prompt mask must align.",
    )


def main() -> int:
    tests = [
        ("compressor_explicit_geometry", test_compressor_explicit_geometry),
        ("count_params_safe_initialized", test_count_params_safe_initialized),
        ("mixed_target_dims", test_mixed_target_dims),
        ("inject_lora_keeps_float", test_inject_lora_keeps_float),
        ("audit_schedule_detects_drift", test_audit_schedule_detects_drift),
        ("audit_schedule_zero_drift", test_audit_schedule_zero_drift),
        ("bridge_dataset_answer_only_masking", test_bridge_dataset_answer_only_masking),
        ("bridge_dataset_collator_shapes", test_bridge_dataset_collator_shapes),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("All regression smoke checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise
