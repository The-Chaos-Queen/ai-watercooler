"""
train_bridge.py - Phase 2 trainer for the Mamba -> Qwen cognitive bridge.

This script trains only the context encoder (compressor or raw-state bypass)
and bridge hypernetwork. Mamba and Qwen stay frozen. Training uses teacher
forcing on prompts from bridge_dataset.py, and evaluation uses strict
exact-match recall on held-out fact prompts.

Dry-run mode uses tiny local stub models and tokenizer stubs so the full
training/evaluation loop can be exercised without model downloads.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence, Tuple

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset, Subset

try:
    from transformers.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
except Exception:
    pass

from transformers import AutoModelForCausalLM, AutoTokenizer

from bridge_dataset import (
    BridgeBatchCollator,
    BridgeDataset,
    BridgeDatasetConfig,
    MAMBA_MODEL_ID,
    QWEN_MODEL_ID,
    build_splits,
    compute_split_counts,
)
from cognitive_bridge import BridgeConfig
from models import (
    ActivationBiasHypernetwork,
    ConstantBiasBridge,
    DynamicLoRALinear,
    LoRAHypernetwork,
    MambaStateCompressor,
    RawStateProjector,
    ZeroContextEncoder,
)

LOGGER = logging.getLogger("TrainBridge")
SUPPORTED_BRIDGE_MODES = ("lora", "activation_bias", "constant_bias")


@dataclass
class TrainingRuntime:
    bridge_config: BridgeConfig
    qwen_model: nn.Module
    mamba_model: nn.Module
    compressor: nn.Module
    hypernetwork: nn.Module
    patched_layers: List[DynamicLoRALinear]
    target_specs: List[Tuple[int, str]]
    qwen_device: torch.device
    mamba_device: torch.device
    hyper_device: torch.device
    qwen_tokenizer: Any
    mamba_tokenizer: Any
    bridge_mode: str
    context_mode: str = "compressed"
    requires_mamba: bool = True
    skip_compressor: bool = False
    dry_run: bool = False


@dataclass
class AccuracySummary:
    accuracy: float
    correct: int
    total: int
    wilson_low: float
    wilson_high: float
    bootstrap_low: float
    bootstrap_high: float


@dataclass
class EvalResults:
    bridge: AccuracySummary
    baseline: AccuracySummary
    random_control: AccuracySummary
    bridge_lora_norm_mean: float
    random_lora_norm_mean: float
    bridge_lora_clamp_fraction: float
    p_value_bridge_vs_baseline: float
    context_vectors_path: Optional[str] = None
    predictions_path: Optional[str] = None
    reconstruction_path: Optional[str] = None
    general_ppl: Optional[Dict[str, float]] = None
    compressed_state_stats: Optional[Dict[str, float]] = None
    reconstruction_stats: Optional[Dict[str, float]] = None


class FakeTokenizer:
    """Tokenizer stub for --dry-run. It supports plain text plus ChatML markers."""

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
        self._id_to_token = {value: key for key, value in self._token_to_id.items()}
        self._next_id = 4

    def encode(self, text: str, add_special_tokens: bool = False, return_tensors=None):
        del add_special_tokens
        ids: List[int] = []
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
                self._id_to_token[self._next_id] = token
                self._next_id += 1
            ids.append(self._token_to_id[token])
            cursor += 1

        if return_tensors == "pt":
            return torch.tensor([ids], dtype=torch.long)
        return ids

    def decode(self, token_ids, skip_special_tokens: bool = False) -> str:
        if isinstance(token_ids, torch.Tensor):
            token_ids = token_ids.tolist()
        pieces: List[str] = []
        for token_id in token_ids:
            token = self._id_to_token.get(int(token_id), "")
            if skip_special_tokens and token in {
                "<|im_start|>",
                "<|im_end|>",
                self.pad_token,
                self.eos_token,
            }:
                continue
            pieces.append(token)
        return "".join(pieces)


class ToySelfAttention(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mixed = torch.tanh(self.q_proj(x) + self.k_proj(x) + self.v_proj(x))
        return self.o_proj(mixed)


class ToyDecoderLayer(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.self_attn = ToySelfAttention(hidden_size)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 2),
            nn.GELU(),
            nn.Linear(hidden_size * 2, hidden_size),
        )
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.self_attn(x)
        x = x + self.mlp(x)
        return self.norm(x)


class ToyBackbone(nn.Module):
    def __init__(self, vocab_size: int, hidden_size: int, num_layers: int):
        super().__init__()
        self.embed_tokens = nn.Embedding(vocab_size, hidden_size)
        self.layers = nn.ModuleList([ToyDecoderLayer(hidden_size) for _ in range(num_layers)])

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        hidden = self.embed_tokens(input_ids)
        for layer in self.layers:
            hidden = layer(hidden)
        return hidden


class ToyCausalLM(nn.Module):
    def __init__(self, vocab_size: int, hidden_size: int, num_layers: int):
        super().__init__()
        self.model = ToyBackbone(vocab_size=vocab_size, hidden_size=hidden_size, num_layers=num_layers)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False)

    def forward(self, input_ids: torch.Tensor, attention_mask: Optional[torch.Tensor] = None):
        del attention_mask
        hidden = self.model(input_ids)
        logits = self.lm_head(hidden)
        return SimpleNamespace(logits=logits)

    def generate(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        max_new_tokens: int = 1,
        min_new_tokens: int = 0,
        do_sample: bool = False,
        use_cache: bool = True,
        return_dict_in_generate: bool = False,
        **_: Any,
    ) -> torch.Tensor:
        del attention_mask, do_sample, use_cache, return_dict_in_generate
        generated = input_ids.clone()
        total_new_tokens = max(max_new_tokens, min_new_tokens)
        for _ in range(total_new_tokens):
            logits = self.forward(generated).logits
            next_token = logits[:, -1, :].argmax(dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=1)
        return generated


class ToyMamba(nn.Module):
    def __init__(self, vocab_size: int, num_layers: int, d_model: int, d_state: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.projections = nn.ModuleList([nn.Linear(d_model, d_model * d_state) for _ in range(num_layers)])
        self.d_model = d_model
        self.d_state = d_state

    def forward(self, input_ids: torch.Tensor, use_cache: bool = True):
        del use_cache
        pooled = self.embedding(input_ids).mean(dim=1)
        ssm_states = [
            proj(pooled).view(pooled.shape[0], self.d_model, self.d_state)
            for proj in self.projections
        ]
        cache = SimpleNamespace(ssm_states=ssm_states)
        return SimpleNamespace(cache_params=cache)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(requested)


def get_cuda_memory_gib(device: torch.device) -> float:
    if device.type != "cuda":
        return 0.0
    index = device.index if device.index is not None else torch.cuda.current_device()
    total_bytes = torch.cuda.get_device_properties(index).total_memory
    return total_bytes / float(1024 ** 3)


def get_cuda_memory_stats_gib(device: torch.device) -> Tuple[float, float]:
    if device.type != "cuda":
        return 0.0, 0.0

    index = device.index if device.index is not None else torch.cuda.current_device()
    total_gib = get_cuda_memory_gib(device)
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(index)
        return free_bytes / float(1024 ** 3), total_bytes / float(1024 ** 3)
    except TypeError:
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        return free_bytes / float(1024 ** 3), total_bytes / float(1024 ** 3)
    except Exception:
        return 0.0, total_gib


def resolve_mamba_device(requested: str, qwen_device: torch.device) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if qwen_device.type != "cuda":
        return qwen_device

    gpu_memory_gib = get_cuda_memory_gib(qwen_device)
    if gpu_memory_gib <= 10.0:
        LOGGER.info(
            "Detected %.1f GiB GPU VRAM; defaulting Mamba to CPU/system RAM offload.",
            gpu_memory_gib,
        )
        return torch.device("cpu")
    return qwen_device


def resolve_mamba_state_geometry(
    mamba_model: nn.Module,
    fallback_config: BridgeConfig,
) -> Tuple[int, int, int]:
    model_config = getattr(mamba_model, "config", None)
    if model_config is None:
        return (
            fallback_config.mamba_layers,
            fallback_config.mamba_d_model,
            fallback_config.mamba_d_state,
        )

    layer_count = int(
        getattr(
            model_config,
            "num_hidden_layers",
            getattr(model_config, "n_layer", fallback_config.mamba_layers),
        )
    )
    state_width = int(
        getattr(
            model_config,
            "intermediate_size",
            getattr(model_config, "hidden_size", fallback_config.mamba_d_model),
        )
    )
    state_depth = int(getattr(model_config, "state_size", fallback_config.mamba_d_state))
    return layer_count, state_width, state_depth


def parse_target_layers(raw: Optional[str]) -> Optional[List[Tuple[int, str]]]:
    if raw is None or not raw.strip():
        return None
    specs: List[Tuple[int, str]] = []
    for piece in raw.split(","):
        part = piece.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Invalid target layer spec: {part!r}. Use layer:projection.")
        layer_text, proj_name = part.split(":", 1)
        specs.append((int(layer_text), proj_name.strip()))
    return specs


def extract_ssm_state(outputs) -> torch.Tensor:
    cache = getattr(outputs, "cache_params", None)
    if cache is None:
        cache = getattr(outputs, "past_key_values", None)
    if cache is None or not hasattr(cache, "ssm_states"):
        attrs = [attr for attr in dir(outputs) if not attr.startswith("_")]
        raise RuntimeError(
            "Mamba output did not expose cache with ssm_states. "
            f"Available attrs: {attrs}"
        )
    return torch.stack(cache.ssm_states, dim=1)


def resolve_target_specs(
    qwen_model: nn.Module,
    explicit_specs: Optional[List[Tuple[int, str]]] = None,
) -> List[Tuple[int, str]]:
    if explicit_specs is not None:
        return explicit_specs

    num_decoder_layers = len(qwen_model.model.layers)
    specs: List[Tuple[int, str]] = []
    for layer_idx in range(0, num_decoder_layers, 4):
        specs.append((layer_idx, "q_proj"))
        specs.append((layer_idx, "v_proj"))
    if not specs:
        raise ValueError("No target layers resolved for Qwen patching.")
    return specs


def validate_target_specs(qwen_model: nn.Module, specs: List[Tuple[int, str]]) -> None:
    if not specs:
        raise ValueError("target_layers is empty.")
    valid_projections = {"q_proj", "k_proj", "v_proj", "o_proj"}
    num_layers = len(qwen_model.model.layers)
    for idx, (layer_idx, proj_name) in enumerate(specs):
        if layer_idx < 0 or layer_idx >= num_layers:
            raise ValueError(f"Target spec {idx} has invalid layer index {layer_idx}.")
        if proj_name not in valid_projections:
            raise ValueError(f"Target spec {idx} has invalid projection {proj_name!r}.")


def get_layer_module(qwen_model: nn.Module, spec: Tuple[int, str]) -> nn.Linear:
    layer_idx, proj_name = spec
    decoder_layer = qwen_model.model.layers[layer_idx]
    return getattr(decoder_layer.self_attn, proj_name)


def set_layer_module(qwen_model: nn.Module, spec: Tuple[int, str], module: nn.Module) -> None:
    layer_idx, proj_name = spec
    decoder_layer = qwen_model.model.layers[layer_idx]
    setattr(decoder_layer.self_attn, proj_name, module)


def patch_qwen_model(
    qwen_model: nn.Module,
    target_specs: List[Tuple[int, str]],
    scaling: float,
) -> List[DynamicLoRALinear]:
    patched_layers: List[DynamicLoRALinear] = []
    for spec in target_specs:
        original = get_layer_module(qwen_model, spec)
        dynamic = DynamicLoRALinear(original, scaling=scaling)
        set_layer_module(qwen_model, spec, dynamic)
        patched_layers.append(dynamic)
    return patched_layers


def clear_lora(patched_layers: Sequence[DynamicLoRALinear]) -> None:
    for layer in patched_layers:
        layer.clear_lora()


def set_lora(
    patched_layers: Sequence[DynamicLoRALinear],
    lora_pairs: Sequence[Tuple[torch.Tensor, torch.Tensor]],
) -> None:
    if len(patched_layers) != len(lora_pairs):
        raise RuntimeError(
            f"LoRA pair count mismatch: got {len(lora_pairs)}, expected {len(patched_layers)}"
        )
    for layer, (A, B) in zip(patched_layers, lora_pairs):
        layer.set_lora(A, B)


def set_activation_bias(
    patched_layers: Sequence[DynamicLoRALinear],
    bias_vectors: Sequence[torch.Tensor],
) -> None:
    if len(patched_layers) != len(bias_vectors):
        raise RuntimeError(
            f"Activation-bias count mismatch: got {len(bias_vectors)}, expected {len(patched_layers)}"
        )
    for layer, bias in zip(patched_layers, bias_vectors):
        layer.set_activation_bias(bias)


def compute_lora_norm_stats(
    lora_pairs: Sequence[Tuple[torch.Tensor, torch.Tensor]],
) -> Tuple[float, float, torch.Tensor]:
    sample_norms: List[torch.Tensor] = []
    for A, B in lora_pairs:
        delta = torch.matmul(A.float(), B.float())
        flat = delta.reshape(delta.shape[0], -1)
        sample_norms.append(torch.linalg.vector_norm(flat, dim=-1))

    if not sample_norms:
        zero = torch.zeros(1)
        return 0.0, 0.0, zero

    stacked = torch.stack(sample_norms, dim=1)
    sample_means = stacked.mean(dim=1)
    mean_norm = float(stacked.mean().item())
    variance = float(sample_means.var(unbiased=False).item()) if sample_means.numel() > 1 else 0.0
    return mean_norm, variance, sample_means


def compute_bias_norm_stats(
    bias_vectors: Sequence[torch.Tensor],
) -> Tuple[float, float, torch.Tensor]:
    sample_norms: List[torch.Tensor] = []
    for bias in bias_vectors:
        flat = bias.float().reshape(bias.shape[0], -1)
        sample_norms.append(torch.linalg.vector_norm(flat, dim=-1))

    if not sample_norms:
        zero = torch.zeros(1)
        return 0.0, 0.0, zero

    stacked = torch.stack(sample_norms, dim=1)
    sample_means = stacked.mean(dim=1)
    mean_norm = float(stacked.mean().item())
    variance = float(sample_means.var(unbiased=False).item()) if sample_means.numel() > 1 else 0.0
    return mean_norm, variance, sample_means


def clamp_lora_pairs_by_delta_norm(
    lora_pairs: Sequence[Tuple[torch.Tensor, torch.Tensor]],
    max_delta_norm: float,
) -> Tuple[List[Tuple[torch.Tensor, torch.Tensor]], int, int]:
    clamped_pairs: List[Tuple[torch.Tensor, torch.Tensor]] = []
    clamped_count = 0
    total_count = 0
    eps = 1e-8

    for A, B in lora_pairs:
        batch_size = int(A.shape[0])
        total_count += batch_size
        if max_delta_norm <= 0.0:
            clamped_pairs.append((A, B))
            continue

        delta = torch.matmul(A.float(), B.float())
        flat = delta.reshape(batch_size, -1)
        delta_norms = torch.linalg.vector_norm(flat, dim=-1)
        over_limit = delta_norms > max_delta_norm
        clamped_count += int(over_limit.sum().item())

        if not torch.any(over_limit):
            clamped_pairs.append((A, B))
            continue

        scale = torch.ones_like(delta_norms)
        scale = torch.where(
            over_limit,
            max_delta_norm / delta_norms.clamp_min(eps),
            scale,
        )
        sqrt_scale = torch.sqrt(scale).to(dtype=A.dtype).view(-1, 1, 1)
        clamped_pairs.append((A * sqrt_scale, B * sqrt_scale))

    return clamped_pairs, clamped_count, total_count


def sample_norm_matched_random_lora(
    lora_pairs: Sequence[Tuple[torch.Tensor, torch.Tensor]],
    generator: Optional[torch.Generator] = None,
) -> List[Tuple[torch.Tensor, torch.Tensor]]:
    random_pairs: List[Tuple[torch.Tensor, torch.Tensor]] = []
    eps = 1e-8
    for A, B in lora_pairs:
        rand_A = torch.randn(A.shape, device=A.device, dtype=A.dtype, generator=generator)
        rand_B = torch.randn(B.shape, device=B.device, dtype=B.dtype, generator=generator)
        target_delta = torch.matmul(A.float(), B.float())
        rand_delta = torch.matmul(rand_A.float(), rand_B.float())
        target_norm = torch.linalg.vector_norm(target_delta.reshape(target_delta.shape[0], -1), dim=-1)
        rand_norm = torch.linalg.vector_norm(rand_delta.reshape(rand_delta.shape[0], -1), dim=-1).clamp_min(eps)
        scale = torch.sqrt((target_norm / rand_norm).to(dtype=A.dtype)).view(-1, 1, 1)
        random_pairs.append((rand_A * scale, rand_B * scale))
    return random_pairs


def sample_norm_matched_random_bias(
    bias_vectors: Sequence[torch.Tensor],
    generator: Optional[torch.Generator] = None,
) -> List[torch.Tensor]:
    random_vectors: List[torch.Tensor] = []
    eps = 1e-8
    for bias in bias_vectors:
        rand_bias = torch.randn(bias.shape, device=bias.device, dtype=bias.dtype, generator=generator)
        target_norm = torch.linalg.vector_norm(bias.float().reshape(bias.shape[0], -1), dim=-1)
        rand_norm = torch.linalg.vector_norm(
            rand_bias.float().reshape(rand_bias.shape[0], -1),
            dim=-1,
        ).clamp_min(eps)
        scale = (target_norm / rand_norm).to(dtype=bias.dtype).view(-1, 1)
        random_vectors.append(rand_bias * scale)
    return random_vectors


def build_bridge_hypernetwork(
    bridge_mode: str,
    config: BridgeConfig,
    target_dims: List[Tuple[int, int]],
) -> nn.Module:
    if bridge_mode == "constant_bias":
        return ConstantBiasBridge(target_dims=target_dims)
    if bridge_mode == "activation_bias":
        return ActivationBiasHypernetwork(
            context_dim=config.context_dim,
            target_dims=target_dims,
            hidden_dim=config.hyper_hidden_dim,
        )
    if bridge_mode == "lora":
        return LoRAHypernetwork(
            context_dim=config.context_dim,
            target_dims=target_dims,
            lora_rank=config.lora_rank,
            hidden_dim=config.hyper_hidden_dim,
        )
    raise ValueError(f"Unsupported bridge_mode: {bridge_mode!r}")


def build_context_encoder(
    skip_compressor: bool,
    mamba_layers: int,
    mamba_d_model: int,
    mamba_d_state: int,
    context_dim: int,
    target_layer: int,
) -> Tuple[nn.Module, int, str]:
    if skip_compressor:
        encoder = RawStateProjector(
            mamba_layers=mamba_layers,
            mamba_d_model=mamba_d_model,
            mamba_d_state=mamba_d_state,
            target_layer=target_layer,
        )
        return encoder, encoder.output_dim, "raw_state"

    encoder = MambaStateCompressor(
        mamba_layers=mamba_layers,
        mamba_d_model=mamba_d_model,
        mamba_d_state=mamba_d_state,
        output_dim=context_dim,
        target_layer=target_layer,
    )
    return encoder, context_dim, "compressed"


def module_dtype(module: nn.Module) -> torch.dtype:
    parameter = next(module.parameters(), None)
    if parameter is not None:
        return parameter.dtype
    buffer = next(module.buffers(), None)
    if buffer is not None:
        return buffer.dtype
    return torch.float32


def encode_context(runtime: TrainingRuntime, mamba_state: torch.Tensor) -> torch.Tensor:
    encoder_dtype = module_dtype(runtime.compressor)
    state_for_encoder = mamba_state.to(runtime.hyper_device, dtype=encoder_dtype)
    return runtime.compressor(state_for_encoder)


def flatten_target_mamba_state(runtime: TrainingRuntime, mamba_state: torch.Tensor) -> Optional[torch.Tensor]:
    target_layer = getattr(runtime.compressor, "target_layer", None)
    if target_layer is None:
        return None
    if mamba_state.size(1) <= target_layer:
        raise ValueError(
            f"Mamba state only has {mamba_state.size(1)} layers, cannot extract layer {target_layer}."
        )

    targeted_state = mamba_state[:, int(target_layer)]
    flat = targeted_state.reshape(targeted_state.shape[0], -1)
    expected_width = getattr(runtime.compressor, "input_flat_size", None)
    if expected_width is not None and flat.shape[1] != int(expected_width):
        raise RuntimeError(
            "Target Mamba state width changed after encoder initialization: "
            f"got {flat.shape[1]}, expected {expected_width}."
        )
    return flat


def build_batch_context_and_target_state(
    runtime: TrainingRuntime,
    batch: Dict[str, Any],
) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
    if runtime.bridge_mode == "constant_bias":
        batch_size = int(batch["qwen_input_ids"].shape[0])
        return runtime.compressor(batch_size), None
    if not runtime.requires_mamba:
        raise RuntimeError("This runtime has no live Mamba path for per-sample context construction.")

    mamba_state = run_mamba_state(runtime, batch["mamba_history_ids"])
    context = encode_context(runtime, mamba_state)
    return context, flatten_target_mamba_state(runtime, mamba_state)


def build_batch_context(runtime: TrainingRuntime, batch: Dict[str, Any]) -> torch.Tensor:
    context, _ = build_batch_context_and_target_state(runtime, batch)
    return context


def collect_reconstruction_probe_tensors(
    runtime: TrainingRuntime,
    loader: Optional[DataLoader],
) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
    if loader is None or not runtime.requires_mamba:
        return None, None

    context_rows: List[torch.Tensor] = []
    target_rows: List[torch.Tensor] = []
    with torch.no_grad():
        for batch in loader:
            context, flat_target = build_batch_context_and_target_state(runtime, batch)
            if flat_target is None:
                return None, None
            context_rows.append(context.detach().cpu().float())
            target_rows.append(flat_target.detach().cpu().float())

    if not context_rows or not target_rows:
        return None, None
    return torch.cat(context_rows, dim=0), torch.cat(target_rows, dim=0)


def compute_reconstruction_probe_errors(
    train_contexts: Optional[torch.Tensor],
    train_targets: Optional[torch.Tensor],
    eval_contexts: Optional[torch.Tensor],
    eval_targets: Optional[torch.Tensor],
) -> Optional[torch.Tensor]:
    if (
        train_contexts is None
        or train_targets is None
        or eval_contexts is None
        or eval_targets is None
        or train_contexts.numel() == 0
        or train_targets.numel() == 0
        or eval_contexts.numel() == 0
        or eval_targets.numel() == 0
    ):
        return None

    # Logging-only probe: fit the best affine linear decoder on the train split,
    # then score held-out eval contexts against the original flattened Mamba state.
    train_contexts_f = train_contexts.float()
    train_targets_f = train_targets.float()
    eval_contexts_f = eval_contexts.float()
    eval_targets_f = eval_targets.float()

    train_design = torch.cat(
        [
            train_contexts_f,
            torch.ones(train_contexts_f.shape[0], 1, dtype=train_contexts_f.dtype),
        ],
        dim=1,
    )
    eval_design = torch.cat(
        [
            eval_contexts_f,
            torch.ones(eval_contexts_f.shape[0], 1, dtype=eval_contexts_f.dtype),
        ],
        dim=1,
    )

    decoder_projection = eval_design @ torch.linalg.pinv(train_design)
    reconstructed = decoder_projection @ train_targets_f
    squared_error = (reconstructed - eval_targets_f).pow(2.0)
    return squared_error.reshape(squared_error.shape[0], -1).mean(dim=1)


def clamp_bridge_adjustments(
    bridge_mode: str,
    adjustments: Sequence[Any],
    max_lora_delta_norm: float,
) -> Tuple[List[Any], int, int]:
    if bridge_mode in {"activation_bias", "constant_bias"}:
        return list(adjustments), 0, 0
    return clamp_lora_pairs_by_delta_norm(adjustments, max_lora_delta_norm)


def sample_norm_matched_random_adjustments(
    bridge_mode: str,
    adjustments: Sequence[Any],
    generator: Optional[torch.Generator] = None,
) -> List[Any]:
    if bridge_mode in {"activation_bias", "constant_bias"}:
        return sample_norm_matched_random_bias(adjustments, generator=generator)
    return sample_norm_matched_random_lora(adjustments, generator=generator)


def compute_bridge_norm_stats(
    bridge_mode: str,
    adjustments: Sequence[Any],
) -> Tuple[float, float, torch.Tensor]:
    if bridge_mode in {"activation_bias", "constant_bias"}:
        return compute_bias_norm_stats(adjustments)
    return compute_lora_norm_stats(adjustments)


def set_bridge_adjustments(runtime: TrainingRuntime, adjustments: Sequence[Any]) -> None:
    if runtime.bridge_mode in {"activation_bias", "constant_bias"}:
        set_activation_bias(runtime.patched_layers, adjustments)
        return
    set_lora(runtime.patched_layers, adjustments)


def slice_bridge_adjustments(
    bridge_mode: str,
    adjustments: Sequence[Any],
    row: int,
) -> List[Any]:
    if bridge_mode in {"activation_bias", "constant_bias"}:
        return [bias[row : row + 1] for bias in adjustments]
    return [(A[row : row + 1], B[row : row + 1]) for A, B in adjustments]


def bridge_norm_label(bridge_mode: str) -> str:
    return "bias" if bridge_mode in {"activation_bias", "constant_bias"} else "lora"


def expand_fixed_adjustments(
    bridge_mode: str,
    adjustments: Sequence[Any],
    batch_size: int,
) -> List[Any]:
    if bridge_mode in {"activation_bias", "constant_bias"}:
        return [bias.expand(batch_size, -1) for bias in adjustments]
    return [
        (A.expand(batch_size, -1, -1), B.expand(batch_size, -1, -1))
        for A, B in adjustments
    ]


def compute_fixed_mean_adjustments(
    runtime: TrainingRuntime,
    loader: DataLoader,
) -> List[Any]:
    if runtime.bridge_mode != "activation_bias":
        raise ValueError("Fixed-mean adjustments are only defined for activation_bias checkpoints.")

    runtime.compressor.eval()
    runtime.hypernetwork.eval()
    runtime.mamba_model.eval()

    totals: Optional[List[torch.Tensor]] = None
    sample_count = 0
    with torch.no_grad():
        for batch in loader:
            context = build_batch_context(runtime, batch)
            adjustments = runtime.hypernetwork(context)
            if totals is None:
                totals = [
                    bias.sum(dim=0, keepdim=True).detach().clone()
                    for bias in adjustments
                ]
            else:
                for index, bias in enumerate(adjustments):
                    totals[index] += bias.sum(dim=0, keepdim=True)
            sample_count += int(context.shape[0])

    if totals is None or sample_count <= 0:
        raise RuntimeError("Could not compute fixed-mean adjustments from an empty loader.")

    return [bias_sum / float(sample_count) for bias_sum in totals]


def compute_fixed_mean_adjustments_from_saved_contexts(
    runtime: TrainingRuntime,
    contexts_path: str,
) -> List[Any]:
    if runtime.bridge_mode != "activation_bias":
        raise ValueError("Saved-context fixed-mean controls are only defined for activation_bias checkpoints.")

    rows = torch.load(contexts_path, map_location="cpu", weights_only=False)
    if not rows:
        raise RuntimeError(f"No saved context rows found in {contexts_path!r}.")

    context_vectors = torch.stack([row["context_vector"] for row in rows], dim=0).to(runtime.hyper_device)
    runtime.hypernetwork.eval()
    with torch.no_grad():
        adjustments = runtime.hypernetwork(context_vectors)
    return [bias.mean(dim=0, keepdim=True) for bias in adjustments]


def compute_teacher_forcing_loss(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    shifted_logits = logits[:, :-1, :].contiguous()
    shifted_labels = labels[:, 1:].to(device=shifted_logits.device).contiguous()
    vocab_size = shifted_logits.shape[-1]
    return F.cross_entropy(
        shifted_logits.view(-1, vocab_size),
        shifted_labels.view(-1),
        ignore_index=-100,
    )


def build_lr_scheduler(optimizer: AdamW, warmup_steps: int, total_steps: int) -> LambdaLR:
    safe_total_steps = max(1, total_steps)
    safe_warmup = max(0, min(warmup_steps, safe_total_steps - 1))

    def lr_lambda(step: int) -> float:
        if safe_warmup > 0 and step < safe_warmup:
            return float(step + 1) / float(safe_warmup)
        if safe_total_steps <= safe_warmup:
            return 1.0
        progress = float(step - safe_warmup) / float(max(1, safe_total_steps - safe_warmup))
        progress = min(max(progress, 0.0), 1.0)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    return LambdaLR(optimizer, lr_lambda=lr_lambda)


def wilson_interval(correct: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    phat = correct / total
    denom = 1.0 + (z * z) / total
    center = (phat + (z * z) / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((phat * (1.0 - phat) / total) + ((z * z) / (4.0 * total * total)))
    return max(0.0, center - margin), min(1.0, center + margin)


def bootstrap_accuracy_ci(values: Sequence[int], resamples: int, seed: int) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    draws: List[float] = []
    for _ in range(max(1, resamples)):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        draws.append(sum(sample) / n)
    draws.sort()
    low_idx = max(0, int(0.025 * (len(draws) - 1)))
    high_idx = min(len(draws) - 1, int(0.975 * (len(draws) - 1)))
    return draws[low_idx], draws[high_idx]


def paired_t_test_p_value(xs: Sequence[int], ys: Sequence[int]) -> float:
    if len(xs) != len(ys):
        raise ValueError("Paired t-test requires equal-length samples.")
    if len(xs) < 2:
        return 1.0

    diffs = [float(x) - float(y) for x, y in zip(xs, ys)]
    mean_diff = statistics.fmean(diffs)
    if all(abs(diff - mean_diff) < 1e-12 for diff in diffs):
        return 0.0 if abs(mean_diff) > 1e-12 else 1.0

    variance = statistics.variance(diffs)
    if variance <= 0.0:
        return 0.0 if abs(mean_diff) > 1e-12 else 1.0

    t_stat = mean_diff / math.sqrt(variance / len(diffs))
    try:
        from scipy import stats  # type: ignore

        p_value = float(2.0 * stats.t.sf(abs(t_stat), df=len(diffs) - 1))
    except Exception:
        normal = statistics.NormalDist()
        p_value = float(2.0 * (1.0 - normal.cdf(abs(t_stat))))
    return max(0.0, min(1.0, p_value))


def summarize_accuracy(values: Sequence[int], bootstrap_resamples: int, seed: int) -> AccuracySummary:
    total = len(values)
    correct = int(sum(values))
    accuracy = (correct / total) if total else 0.0
    wilson_low, wilson_high = wilson_interval(correct=correct, total=total)
    bootstrap_low, bootstrap_high = bootstrap_accuracy_ci(values, bootstrap_resamples, seed)
    return AccuracySummary(
        accuracy=accuracy,
        correct=correct,
        total=total,
        wilson_low=wilson_low,
        wilson_high=wilson_high,
        bootstrap_low=bootstrap_low,
        bootstrap_high=bootstrap_high,
    )


def format_accuracy_summary(name: str, summary: AccuracySummary) -> str:
    return (
        f"{name}: {summary.accuracy:.3f} "
        f"[{summary.wilson_low:.3f}, {summary.wilson_high:.3f}] "
        f"boot[{summary.bootstrap_low:.3f}, {summary.bootstrap_high:.3f}]"
    )


def truncate_padded(ids: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    length = int(mask.sum().item())
    return ids[:length]


def decode_tokens(tokenizer: Any, token_ids: torch.Tensor) -> str:
    return tokenizer.decode(token_ids.detach().cpu(), skip_special_tokens=True)


def manual_greedy_generate_answer(
    qwen_model: nn.Module,
    prompt_ids: torch.Tensor,
    answer_len: int,
    qwen_device: torch.device,
) -> torch.Tensor:
    generated_ids = prompt_ids.unsqueeze(0).to(qwen_device)
    attention_mask = torch.ones_like(generated_ids, dtype=torch.long)
    produced: List[torch.Tensor] = []
    for _ in range(answer_len):
        outputs = qwen_model(input_ids=generated_ids, attention_mask=attention_mask)
        next_token = outputs.logits[:, -1, :].argmax(dim=-1, keepdim=True)
        produced.append(next_token.squeeze(0))
        generated_ids = torch.cat([generated_ids, next_token], dim=1)
        attention_mask = torch.ones_like(generated_ids, dtype=torch.long)
    if not produced:
        return torch.empty(0, dtype=torch.long, device=qwen_device)
    return torch.cat(produced, dim=0)


def greedy_generate_answer(
    qwen_model: nn.Module,
    prompt_ids: torch.Tensor,
    answer_len: int,
    qwen_device: torch.device,
) -> torch.Tensor:
    if answer_len <= 0:
        return torch.empty(0, dtype=torch.long, device=qwen_device)

    if not hasattr(qwen_model, "generate"):
        return manual_greedy_generate_answer(qwen_model, prompt_ids, answer_len, qwen_device)

    prompt_batch = prompt_ids.unsqueeze(0).to(qwen_device)
    attention_mask = torch.ones_like(prompt_batch, dtype=torch.long)
    generation_kwargs: Dict[str, Any] = {
        "input_ids": prompt_batch,
        "attention_mask": attention_mask,
        "max_new_tokens": answer_len,
        "min_new_tokens": answer_len,
        "do_sample": False,
        "use_cache": True,
        "return_dict_in_generate": False,
    }
    generation_config = getattr(qwen_model, "generation_config", None)
    model_config = getattr(qwen_model, "config", None)
    pad_token_id = getattr(generation_config, "pad_token_id", None)
    if pad_token_id is None:
        pad_token_id = getattr(model_config, "pad_token_id", None)
    if pad_token_id is not None:
        generation_kwargs["pad_token_id"] = int(pad_token_id)
    if getattr(generation_config, "forced_eos_token_id", None) is not None:
        generation_kwargs["forced_eos_token_id"] = None

    try:
        generated = qwen_model.generate(**generation_kwargs)
    except Exception as exc:
        LOGGER.debug("model.generate() unavailable in this runtime, falling back to manual loop: %s", exc)
        return manual_greedy_generate_answer(qwen_model, prompt_ids, answer_len, qwen_device)

    new_tokens = generated[0, prompt_batch.shape[1] :]
    return new_tokens[:answer_len]


def compute_context_unusualness_metrics(context: torch.Tensor) -> Dict[str, torch.Tensor]:
    context_f = context.float()
    if context_f.ndim != 2:
        raise ValueError(f"Expected (batch, dim) compressed state tensor, got shape={tuple(context.shape)}")

    centroid = context_f.mean(dim=0, keepdim=True)
    centroid_expanded = centroid.expand_as(context_f)
    centroid_l2 = torch.linalg.vector_norm(context_f - centroid_expanded, dim=-1)
    context_norm = torch.linalg.vector_norm(context_f, dim=-1)
    centroid_cosine_distance = 1.0 - F.cosine_similarity(context_f, centroid_expanded, dim=-1, eps=1e-8)
    return {
        "context_norm": context_norm,
        "context_centroid_l2": centroid_l2,
        "context_centroid_cosine_distance": centroid_cosine_distance,
    }


def summarize_metric_values(values: Sequence[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = statistics.fmean(values)
    variance = statistics.pvariance(values) if len(values) > 1 else 0.0
    return mean, variance


def summarize_named_metric_values(values_by_name: Dict[str, Sequence[float]]) -> Dict[str, float]:
    summary: Dict[str, float] = {}
    for name, values in values_by_name.items():
        mean, variance = summarize_metric_values(values)
        summary[f"{name}_mean"] = mean
        summary[f"{name}_var"] = variance
    return summary


def build_eval_comparison_record(
    runtime: TrainingRuntime,
    epoch_index: int,
    eval_split: str,
    eval_adjustment_source: str,
    train_stats: Dict[str, Any],
    eval_results: EvalResults,
) -> Dict[str, Any]:
    general_ppl = eval_results.general_ppl or {}
    reconstruction_stats = eval_results.reconstruction_stats or {}
    bridge_ppl = general_ppl.get("bridge_ppl")
    baseline_ppl = general_ppl.get("baseline_ppl")
    random_ppl = general_ppl.get("random_ppl")
    norm_label = bridge_norm_label(runtime.bridge_mode)

    bridge_vs_baseline_delta = None
    random_vs_baseline_delta = None
    if bridge_ppl is not None and baseline_ppl is not None:
        bridge_vs_baseline_delta = float(bridge_ppl) - float(baseline_ppl)
    if random_ppl is not None and baseline_ppl is not None:
        random_vs_baseline_delta = float(random_ppl) - float(baseline_ppl)

    return {
        "epoch": epoch_index,
        "bridge_mode": runtime.bridge_mode,
        "context_mode": runtime.context_mode,
        "eval_adjustment_source": eval_adjustment_source,
        "eval_split": eval_split,
        "qwen_model_id": runtime.bridge_config.qwen_model_id,
        "mamba_model_id": runtime.bridge_config.mamba_model_id,
        "target_specs": list(runtime.target_specs),
        "train": {
            "loss": float(train_stats["loss"]),
            "norm_label": norm_label,
            "norm_mean": float(train_stats["lora_norm_mean"]),
            "norm_var": float(train_stats["lora_norm_var"]),
            "clamp_fraction": float(train_stats["lora_clamp_fraction"]),
        },
        "eval": {
            "bridge_accuracy": float(eval_results.bridge.accuracy),
            "baseline_accuracy": float(eval_results.baseline.accuracy),
            "random_accuracy": float(eval_results.random_control.accuracy),
            "p_value": float(eval_results.p_value_bridge_vs_baseline),
            "norm_label": norm_label,
            "bridge_norm_mean": float(eval_results.bridge_lora_norm_mean),
            "random_norm_mean": float(eval_results.random_lora_norm_mean),
            "bridge_clamp_fraction": float(eval_results.bridge_lora_clamp_fraction),
            "baseline_ppl": (float(baseline_ppl) if baseline_ppl is not None else None),
            "random_ppl": (float(random_ppl) if random_ppl is not None else None),
            "bridge_ppl": (float(bridge_ppl) if bridge_ppl is not None else None),
            "bridge_vs_baseline_ppl_delta": bridge_vs_baseline_delta,
            "random_vs_baseline_ppl_delta": random_vs_baseline_delta,
            "reconstruction_mse_mean": reconstruction_stats.get("reconstruction_mse_mean"),
            "reconstruction_mse_var": reconstruction_stats.get("reconstruction_mse_var"),
        },
    }


def write_eval_comparison_artifacts(
    output_dir: Path,
    runtime: TrainingRuntime,
    epoch_index: int,
    eval_split: str,
    eval_adjustment_source: str,
    train_stats: Dict[str, Any],
    eval_results: EvalResults,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    record = build_eval_comparison_record(
        runtime=runtime,
        epoch_index=epoch_index,
        eval_split=eval_split,
        eval_adjustment_source=eval_adjustment_source,
        train_stats=train_stats,
        eval_results=eval_results,
    )

    comparison_path = output_dir / f"eval_epoch_{epoch_index:03d}_comparison.json"
    with open(comparison_path, "w", encoding="utf-8") as fp:
        json.dump(record, fp, ensure_ascii=False, indent=2)

    history_path = output_dir / "eval_comparison_history.jsonl"
    with open(history_path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    latest_path = output_dir / "eval_comparison_latest.json"
    with open(latest_path, "w", encoding="utf-8") as fp:
        json.dump(record, fp, ensure_ascii=False, indent=2)

    return str(comparison_path)


def run_mamba_state(runtime: TrainingRuntime, mamba_history_ids: torch.Tensor) -> torch.Tensor:
    with torch.no_grad():
        outputs = runtime.mamba_model(mamba_history_ids.to(runtime.mamba_device), use_cache=True)
        state = extract_ssm_state(outputs)
    return state


def move_batch_tensor(batch: Dict[str, Any], key: str, device: torch.device) -> torch.Tensor:
    return batch[key].to(device)


def evaluate_language_model(
    runtime: TrainingRuntime,
    loader: Optional[DataLoader],
    seed: int,
    max_lora_delta_norm: float,
    eval_adjustment_source: str = "learned",
    fixed_mean_adjustments: Optional[List[Any]] = None,
) -> Optional[Dict[str, float]]:
    if loader is None:
        return None

    runtime.compressor.eval()
    runtime.hypernetwork.eval()
    runtime.qwen_model.eval()
    runtime.mamba_model.eval()

    generator = torch.Generator(device=str(runtime.hyper_device))
    generator.manual_seed(seed)
    totals = {"baseline_loss": 0.0, "bridge_loss": 0.0, "random_loss": 0.0, "tokens": 0}

    with torch.no_grad():
        for batch in loader:
            labels = move_batch_tensor(batch, "qwen_labels", runtime.qwen_device)
            token_count = int((labels[:, 1:] != -100).sum().item())
            if token_count == 0:
                continue

            batch_size = int(labels.shape[0])
            if eval_adjustment_source == "fixed_mean":
                if fixed_mean_adjustments is None:
                    raise ValueError("fixed_mean evaluation requested without precomputed fixed_mean_adjustments.")
                bridge_adjustments = expand_fixed_adjustments(
                    runtime.bridge_mode,
                    fixed_mean_adjustments,
                    batch_size,
                )
            else:
                context = build_batch_context(runtime, batch)
                bridge_adjustments = runtime.hypernetwork(context)
            bridge_adjustments, _, _ = clamp_bridge_adjustments(
                runtime.bridge_mode,
                bridge_adjustments,
                max_lora_delta_norm,
            )
            random_adjustments = sample_norm_matched_random_adjustments(
                runtime.bridge_mode,
                bridge_adjustments,
                generator=generator,
            )

            qwen_input_ids = move_batch_tensor(batch, "qwen_input_ids", runtime.qwen_device)
            qwen_attention_mask = move_batch_tensor(batch, "qwen_attention_mask", runtime.qwen_device)

            clear_lora(runtime.patched_layers)
            baseline_logits = runtime.qwen_model(
                input_ids=qwen_input_ids,
                attention_mask=qwen_attention_mask,
            ).logits
            baseline_loss = compute_teacher_forcing_loss(baseline_logits, labels)

            set_bridge_adjustments(runtime, random_adjustments)
            try:
                random_logits = runtime.qwen_model(
                    input_ids=qwen_input_ids,
                    attention_mask=qwen_attention_mask,
                ).logits
            finally:
                clear_lora(runtime.patched_layers)
            random_loss = compute_teacher_forcing_loss(random_logits, labels)

            set_bridge_adjustments(runtime, bridge_adjustments)
            try:
                bridge_logits = runtime.qwen_model(
                    input_ids=qwen_input_ids,
                    attention_mask=qwen_attention_mask,
                ).logits
            finally:
                clear_lora(runtime.patched_layers)
            bridge_loss = compute_teacher_forcing_loss(bridge_logits, labels)

            totals["baseline_loss"] += float(baseline_loss.item()) * token_count
            totals["random_loss"] += float(random_loss.item()) * token_count
            totals["bridge_loss"] += float(bridge_loss.item()) * token_count
            totals["tokens"] += token_count

    if totals["tokens"] == 0:
        return None

    token_total = float(totals["tokens"])
    baseline_ce = totals["baseline_loss"] / token_total
    random_ce = totals["random_loss"] / token_total
    bridge_ce = totals["bridge_loss"] / token_total
    return {
        "baseline_ce": baseline_ce,
        "random_ce": random_ce,
        "bridge_ce": bridge_ce,
        "baseline_ppl": math.exp(min(20.0, baseline_ce)),
        "random_ppl": math.exp(min(20.0, random_ce)),
        "bridge_ppl": math.exp(min(20.0, bridge_ce)),
    }


def evaluate_fact_accuracy(
    runtime: TrainingRuntime,
    loader: DataLoader,
    reconstruction_probe_loader: Optional[DataLoader],
    bootstrap_resamples: int,
    seed: int,
    epoch_index: int,
    output_dir: Optional[Path],
    save_eval_contexts: bool,
    save_eval_predictions: bool,
    eval_prediction_samples: int,
    general_loader: Optional[DataLoader],
    max_lora_delta_norm: float,
    eval_adjustment_source: str = "learned",
    fixed_mean_adjustments: Optional[List[Any]] = None,
) -> EvalResults:
    runtime.compressor.eval()
    runtime.hypernetwork.eval()
    runtime.qwen_model.eval()
    runtime.mamba_model.eval()

    generator = torch.Generator(device=str(runtime.hyper_device))
    generator.manual_seed(seed)
    train_reconstruction_contexts, train_reconstruction_targets = collect_reconstruction_probe_tensors(
        runtime,
        reconstruction_probe_loader,
    )

    baseline_correct: List[int] = []
    random_correct: List[int] = []
    bridge_correct: List[int] = []
    bridge_norm_values: List[float] = []
    random_norm_values: List[float] = []
    bridge_lora_clamped = 0
    bridge_lora_total = 0
    compressed_state_metric_values: Dict[str, List[float]] = {
        "context_norm": [],
        "context_centroid_l2": [],
        "context_centroid_cosine_distance": [],
    }
    context_rows: List[Dict[str, Any]] = []
    prediction_rows: List[Dict[str, Any]] = []
    reconstruction_rows: List[Dict[str, Any]] = []
    eval_reconstruction_contexts: List[torch.Tensor] = []
    eval_reconstruction_targets: List[torch.Tensor] = []
    sample_index = 0

    with torch.no_grad():
        for batch in loader:
            context: Optional[torch.Tensor] = None
            flat_target_state: Optional[torch.Tensor] = None
            context_metrics: Dict[str, torch.Tensor] = {}
            if runtime.requires_mamba:
                context, flat_target_state = build_batch_context_and_target_state(runtime, batch)
                context_metrics = compute_context_unusualness_metrics(context)
                for metric_name, metric_tensor in context_metrics.items():
                    compressed_state_metric_values[metric_name].extend(
                        float(value) for value in metric_tensor.detach().cpu().tolist()
                    )
                if flat_target_state is not None:
                    eval_reconstruction_contexts.append(context.detach().cpu().float())
                    eval_reconstruction_targets.append(flat_target_state.detach().cpu().float())

            batch_size = int(batch["qwen_prompt_ids"].shape[0])
            if eval_adjustment_source == "fixed_mean":
                if fixed_mean_adjustments is None:
                    raise ValueError("fixed_mean evaluation requested without precomputed fixed_mean_adjustments.")
                bridge_adjustments = expand_fixed_adjustments(
                    runtime.bridge_mode,
                    fixed_mean_adjustments,
                    batch_size,
                )
            else:
                if context is None:
                    context = build_batch_context(runtime, batch)
                bridge_adjustments = runtime.hypernetwork(context)
            bridge_adjustments, batch_clamped, batch_total = clamp_bridge_adjustments(
                runtime.bridge_mode,
                bridge_adjustments,
                max_lora_delta_norm,
            )
            bridge_lora_clamped += batch_clamped
            bridge_lora_total += batch_total
            random_adjustments = sample_norm_matched_random_adjustments(
                runtime.bridge_mode,
                bridge_adjustments,
                generator=generator,
            )

            _, _, bridge_sample_norms = compute_bridge_norm_stats(runtime.bridge_mode, bridge_adjustments)
            _, _, random_sample_norms = compute_bridge_norm_stats(runtime.bridge_mode, random_adjustments)

            for row in range(batch_size):
                prompt_ids = truncate_padded(
                    batch["qwen_prompt_ids"][row],
                    batch["qwen_prompt_attention_mask"][row],
                )
                answer_ids = batch["qwen_labels"][row][batch["qwen_labels"][row] != -100]
                answer_len = int(answer_ids.shape[0])

                clear_lora(runtime.patched_layers)
                baseline_pred = greedy_generate_answer(
                    runtime.qwen_model,
                    prompt_ids=prompt_ids,
                    answer_len=answer_len,
                    qwen_device=runtime.qwen_device,
                )
                baseline_is_correct = int(torch.equal(baseline_pred.cpu(), answer_ids.cpu()))
                baseline_correct.append(baseline_is_correct)

                set_bridge_adjustments(
                    runtime,
                    slice_bridge_adjustments(runtime.bridge_mode, random_adjustments, row),
                )
                try:
                    random_pred = greedy_generate_answer(
                        runtime.qwen_model,
                        prompt_ids=prompt_ids,
                        answer_len=answer_len,
                        qwen_device=runtime.qwen_device,
                    )
                finally:
                    clear_lora(runtime.patched_layers)
                random_is_correct = int(torch.equal(random_pred.cpu(), answer_ids.cpu()))
                random_correct.append(random_is_correct)

                set_bridge_adjustments(
                    runtime,
                    slice_bridge_adjustments(runtime.bridge_mode, bridge_adjustments, row),
                )
                try:
                    bridge_pred = greedy_generate_answer(
                        runtime.qwen_model,
                        prompt_ids=prompt_ids,
                        answer_len=answer_len,
                        qwen_device=runtime.qwen_device,
                    )
                finally:
                    clear_lora(runtime.patched_layers)
                bridge_is_correct = int(torch.equal(bridge_pred.cpu(), answer_ids.cpu()))
                bridge_correct.append(bridge_is_correct)

                bridge_norm_values.append(float(bridge_sample_norms[row].item()))
                random_norm_values.append(float(random_sample_norms[row].item()))

                if save_eval_contexts and context is not None:
                    context_rows.append(
                        {
                            "fact_kind": batch["metadata"][row]["fact_kind"],
                            "answer_text": batch["answer_text"][row],
                            "question_text": batch["question_text"][row],
                            "context_vector": context[row].detach().cpu(),
                        }
                    )
                if save_eval_predictions and len(prediction_rows) < eval_prediction_samples:
                    prediction_rows.append(
                        {
                            "sample_id": sample_index,
                            "fact_kind": batch["metadata"][row]["fact_kind"],
                            "question_text": batch["question_text"][row],
                            "answer_text": batch["answer_text"][row],
                            "prompt_text": decode_tokens(runtime.qwen_tokenizer, prompt_ids),
                            "baseline_prediction": decode_tokens(runtime.qwen_tokenizer, baseline_pred),
                            "random_prediction": decode_tokens(runtime.qwen_tokenizer, random_pred),
                            "bridge_prediction": decode_tokens(runtime.qwen_tokenizer, bridge_pred),
                            "baseline_exact_match": bool(baseline_is_correct),
                            "random_exact_match": bool(random_is_correct),
                            "bridge_exact_match": bool(bridge_is_correct),
                            "context_norm": (
                                float(context_metrics["context_norm"][row].item())
                                if context is not None
                                else None
                            ),
                            "context_centroid_l2": (
                                float(context_metrics["context_centroid_l2"][row].item())
                                if context is not None
                                else None
                            ),
                            "context_centroid_cosine_distance": (
                                float(context_metrics["context_centroid_cosine_distance"][row].item())
                                if context is not None
                                else None
                            ),
                        }
                    )
                reconstruction_rows.append(
                    {
                        "sample_id": sample_index,
                        "fact_kind": batch["metadata"][row]["fact_kind"],
                        "question_text": batch["question_text"][row],
                        "answer_text": batch["answer_text"][row],
                    }
                )
                sample_index += 1

    context_path: Optional[str] = None
    predictions_path: Optional[str] = None
    reconstruction_path: Optional[str] = None
    reconstruction_stats: Optional[Dict[str, float]] = None
    if train_reconstruction_contexts is not None and eval_reconstruction_contexts and eval_reconstruction_targets:
        eval_context_tensor = torch.cat(eval_reconstruction_contexts, dim=0)
        eval_target_tensor = torch.cat(eval_reconstruction_targets, dim=0)
        reconstruction_mse = compute_reconstruction_probe_errors(
            train_contexts=train_reconstruction_contexts,
            train_targets=train_reconstruction_targets,
            eval_contexts=eval_context_tensor,
            eval_targets=eval_target_tensor,
        )
        if reconstruction_mse is not None:
            mse_values = [float(value) for value in reconstruction_mse.detach().cpu().tolist()]
            for row, mse_value in zip(reconstruction_rows, mse_values):
                row["reconstruction_mse"] = mse_value
            reconstruction_stats = summarize_named_metric_values({"reconstruction_mse": mse_values})
            if prediction_rows:
                mse_by_sample_id = {
                    row["sample_id"]: row["reconstruction_mse"]
                    for row in reconstruction_rows
                    if "reconstruction_mse" in row
                }
                for row in prediction_rows:
                    row["reconstruction_mse"] = mse_by_sample_id.get(row["sample_id"])

    if save_eval_contexts and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        context_path = str(output_dir / f"eval_epoch_{epoch_index:03d}_contexts.pt")
        torch.save(context_rows, context_path)
    if output_dir is not None and reconstruction_stats is not None and reconstruction_rows:
        output_dir.mkdir(parents=True, exist_ok=True)
        reconstruction_path = str(output_dir / f"eval_epoch_{epoch_index:03d}_reconstruction.json")
        with open(reconstruction_path, "w", encoding="utf-8") as fp:
            json.dump(reconstruction_rows, fp, ensure_ascii=False, indent=2)
    if save_eval_predictions and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        predictions_path = str(output_dir / f"eval_epoch_{epoch_index:03d}_predictions.json")
        with open(predictions_path, "w", encoding="utf-8") as fp:
            json.dump(prediction_rows, fp, ensure_ascii=False, indent=2)

    baseline_summary = summarize_accuracy(baseline_correct, bootstrap_resamples, seed + 11)
    random_summary = summarize_accuracy(random_correct, bootstrap_resamples, seed + 23)
    bridge_summary = summarize_accuracy(bridge_correct, bootstrap_resamples, seed + 37)
    p_value = paired_t_test_p_value(bridge_correct, baseline_correct)
    general_ppl = evaluate_language_model(
        runtime,
        general_loader,
        seed + 101,
        max_lora_delta_norm=max_lora_delta_norm,
        eval_adjustment_source=eval_adjustment_source,
        fixed_mean_adjustments=fixed_mean_adjustments,
    )
    compressed_state_stats = (
        summarize_named_metric_values(compressed_state_metric_values)
        if any(values for values in compressed_state_metric_values.values())
        else None
    )

    return EvalResults(
        bridge=bridge_summary,
        baseline=baseline_summary,
        random_control=random_summary,
        bridge_lora_norm_mean=(statistics.fmean(bridge_norm_values) if bridge_norm_values else 0.0),
        random_lora_norm_mean=(statistics.fmean(random_norm_values) if random_norm_values else 0.0),
        bridge_lora_clamp_fraction=(bridge_lora_clamped / bridge_lora_total if bridge_lora_total else 0.0),
        p_value_bridge_vs_baseline=p_value,
        context_vectors_path=context_path,
        predictions_path=predictions_path,
        reconstruction_path=reconstruction_path,
        general_ppl=general_ppl,
        compressed_state_stats=compressed_state_stats,
        reconstruction_stats=reconstruction_stats,
    )


def build_tokenizers(dry_run: bool) -> Tuple[Any, Any]:
    if dry_run:
        tokenizer = FakeTokenizer()
        return tokenizer, tokenizer

    mamba_tokenizer = AutoTokenizer.from_pretrained(MAMBA_MODEL_ID)
    qwen_tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_ID, use_fast=True)
    if qwen_tokenizer.pad_token_id is None:
        qwen_tokenizer.pad_token = qwen_tokenizer.eos_token
    return mamba_tokenizer, qwen_tokenizer


def build_real_runtime(args: argparse.Namespace) -> TrainingRuntime:
    qwen_device = resolve_device(args.device)
    mamba_device = resolve_mamba_device(args.mamba_device, qwen_device)
    hyper_device = (
        torch.device(args.hyper_device)
        if args.hyper_device
        else (torch.device("cpu") if mamba_device.type == "cpu" else qwen_device)
    )

    config = BridgeConfig(
        qwen_model_id=args.qwen_model_id,
        mamba_model_id=args.mamba_model_id,
        device=str(qwen_device),
        hyper_device=str(hyper_device),
        use_4bit=not args.no_4bit,
        startup_validation=False,
        target_layers=parse_target_layers(args.target_layers),
    )
    if args.context_dim > 0:
        config.context_dim = args.context_dim

    is_qwen_cpu = str(qwen_device) == "cpu"
    qwen_free_gib, qwen_total_gib = get_cuda_memory_stats_gib(qwen_device)
    qwen_model_kwargs: Dict[str, Any] = {"low_cpu_mem_usage": True}
    if not is_qwen_cpu:
        qwen_model_kwargs["device_map"] = "auto"

    if config.use_4bit and not is_qwen_cpu:
        if qwen_free_gib >= 40.0:
            LOGGER.warning(
                "4-bit Qwen loading is enabled on a GPU with %.1f GiB free (%.1f GiB total). "
                "Pass --no-4bit to avoid unnecessary dequantization overhead on large-memory hosts.",
                qwen_free_gib,
                qwen_total_gib,
            )
        from transformers import BitsAndBytesConfig

        qwen_model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        qwen_model_kwargs["torch_dtype"] = torch.float32 if is_qwen_cpu else torch.float16
    if is_qwen_cpu:
        LOGGER.info("Qwen load mode | precision=float32 | device=cpu")
    elif config.use_4bit:
        LOGGER.info(
            "Qwen load mode | precision=4bit-nf4 | gpu_free=%.1f GiB | gpu_total=%.1f GiB",
            qwen_free_gib,
            qwen_total_gib,
        )
    else:
        LOGGER.info(
            "Qwen load mode | precision=float16 (--no-4bit) | gpu_free=%.1f GiB | gpu_total=%.1f GiB",
            qwen_free_gib,
            qwen_total_gib,
        )

    LOGGER.info("Loading Qwen base model: %s", config.qwen_model_id)
    qwen_tokenizer = AutoTokenizer.from_pretrained(config.qwen_model_id, use_fast=True)
    if qwen_tokenizer.pad_token_id is None:
        qwen_tokenizer.pad_token = qwen_tokenizer.eos_token
    qwen_model = AutoModelForCausalLM.from_pretrained(config.qwen_model_id, **qwen_model_kwargs)
    qwen_model.eval()
    for param in qwen_model.parameters():
        param.requires_grad = False
    qwen_input_device = torch.device("cpu") if hasattr(qwen_model, "hf_device_map") else qwen_device

    uses_saved_fixed_mean_contexts = bool(
        args.eval_only
        and args.bridge_mode == "activation_bias"
        and args.eval_adjustment_source == "fixed_mean"
        and args.fixed_mean_contexts_path
    )
    requires_mamba = args.bridge_mode != "constant_bias" and not uses_saved_fixed_mean_contexts
    if requires_mamba:
        LOGGER.info("Loading Mamba model: %s", config.mamba_model_id)
        mamba_dtype = torch.float32 if mamba_device.type == "cpu" else torch.float16
        mamba_tokenizer = AutoTokenizer.from_pretrained(config.mamba_model_id)
        mamba_model = AutoModelForCausalLM.from_pretrained(
            config.mamba_model_id,
            torch_dtype=mamba_dtype,
            low_cpu_mem_usage=True,
        )
        if mamba_device.type != "cpu":
            mamba_model = mamba_model.to(mamba_device)
        mamba_model.eval()
        for param in mamba_model.parameters():
            param.requires_grad = False

        resolved_mamba_layers, resolved_mamba_d_model, resolved_mamba_d_state = resolve_mamba_state_geometry(
            mamba_model,
            config,
        )
        LOGGER.info(
            "Resolved Mamba state geometry | layers=%d | width=%d | state=%d",
            resolved_mamba_layers,
            resolved_mamba_d_model,
            resolved_mamba_d_state,
        )

        compressor, resolved_context_dim, context_mode = build_context_encoder(
            skip_compressor=args.skip_compressor,
            mamba_layers=resolved_mamba_layers,
            mamba_d_model=resolved_mamba_d_model,
            mamba_d_state=resolved_mamba_d_state,
            context_dim=config.context_dim,
            target_layer=config.mamba_target_layer,
        )
        if args.skip_compressor and args.context_dim > 0 and args.context_dim != resolved_context_dim:
            LOGGER.warning(
                "--context-dim=%d ignored because --skip-compressor uses raw width %d.",
                args.context_dim,
                resolved_context_dim,
            )
        config.context_dim = resolved_context_dim
    else:
        if args.bridge_mode == "constant_bias":
            if args.skip_compressor:
                LOGGER.warning("--skip-compressor ignored in constant_bias mode.")
            if args.context_dim > 0:
                LOGGER.warning("--context-dim=%d ignored in constant_bias mode.", args.context_dim)
            LOGGER.info("Bridge mode constant_bias: skipping Mamba and using learned static bias vectors.")
            config.context_dim = 1
            context_mode = "constant"
        else:
            LOGGER.info(
                "Eval-only fixed_mean mode with saved contexts: skipping live Mamba load and using %s",
                args.fixed_mean_contexts_path,
            )
            context_mode = "saved_fixed_mean"
        mamba_tokenizer = qwen_tokenizer
        mamba_model = nn.Identity()
        compressor = ZeroContextEncoder(output_dim=config.context_dim)

    LOGGER.info(
        "Runtime devices | qwen_input=%s | mamba=%s | hyper=%s",
        qwen_input_device,
        mamba_device,
        hyper_device,
    )
    LOGGER.info("Bridge mode: %s", args.bridge_mode)
    LOGGER.info(
        "Context path | mode=%s | target_layer=%d | context_dim=%d",
        context_mode,
        config.mamba_target_layer,
        config.context_dim,
    )

    target_specs = resolve_target_specs(qwen_model, config.target_layers)
    validate_target_specs(qwen_model, target_specs)
    target_dims = [
        (get_layer_module(qwen_model, spec).in_features, get_layer_module(qwen_model, spec).out_features)
        for spec in target_specs
    ]

    compressor = compressor.to(hyper_device)
    hypernetwork = build_bridge_hypernetwork(args.bridge_mode, config, target_dims).to(hyper_device)
    patched_layers = patch_qwen_model(qwen_model, target_specs, scaling=float(config.lora_scaling))

    return TrainingRuntime(
        bridge_config=config,
        qwen_model=qwen_model,
        mamba_model=mamba_model,
        compressor=compressor,
        hypernetwork=hypernetwork,
        patched_layers=patched_layers,
        target_specs=target_specs,
        qwen_device=qwen_input_device,
        mamba_device=mamba_device,
        hyper_device=hyper_device,
        qwen_tokenizer=qwen_tokenizer,
        mamba_tokenizer=mamba_tokenizer,
        bridge_mode=args.bridge_mode,
        context_mode=context_mode,
        requires_mamba=requires_mamba,
        skip_compressor=args.skip_compressor,
        dry_run=False,
    )


def build_dry_run_runtime(args: argparse.Namespace) -> TrainingRuntime:
    device = torch.device("cpu")
    config = BridgeConfig(
        qwen_model_id=args.qwen_model_id,
        mamba_model_id=args.mamba_model_id,
        mamba_layers=4,
        mamba_d_model=12,
        mamba_d_state=6,
        context_dim=args.context_dim if args.context_dim > 0 else 24,
        lora_rank=4,
        lora_alpha=8,
        hyper_hidden_dim=48,
        device="cpu",
        hyper_device="cpu",
        use_4bit=False,
        startup_validation=False,
        target_layers=[(0, "q_proj"), (0, "v_proj"), (2, "q_proj"), (2, "v_proj")],
    )

    vocab_size = 512
    mamba_tokenizer, qwen_tokenizer = build_tokenizers(dry_run=True)
    qwen_model = ToyCausalLM(vocab_size=vocab_size, hidden_size=16, num_layers=4)
    mamba_model = ToyMamba(
        vocab_size=vocab_size,
        num_layers=config.mamba_layers,
        d_model=config.mamba_d_model,
        d_state=config.mamba_d_state,
    )
    qwen_model.eval()
    mamba_model.eval()
    for param in qwen_model.parameters():
        param.requires_grad = False
    for param in mamba_model.parameters():
        param.requires_grad = False

    target_specs = resolve_target_specs(qwen_model, config.target_layers)
    validate_target_specs(qwen_model, target_specs)
    target_dims = [
        (get_layer_module(qwen_model, spec).in_features, get_layer_module(qwen_model, spec).out_features)
        for spec in target_specs
    ]
    requires_mamba = args.bridge_mode != "constant_bias"
    if requires_mamba:
        compressor, resolved_context_dim, context_mode = build_context_encoder(
            skip_compressor=args.skip_compressor,
            mamba_layers=config.mamba_layers,
            mamba_d_model=config.mamba_d_model,
            mamba_d_state=config.mamba_d_state,
            context_dim=config.context_dim,
            target_layer=config.mamba_target_layer,
        )
        if args.skip_compressor and args.context_dim > 0 and args.context_dim != resolved_context_dim:
            LOGGER.warning(
                "--context-dim=%d ignored because --skip-compressor uses raw width %d.",
                args.context_dim,
                resolved_context_dim,
            )
        config.context_dim = resolved_context_dim
    else:
        mamba_model = nn.Identity()
        mamba_tokenizer = qwen_tokenizer
        compressor = ZeroContextEncoder(output_dim=1)
        config.context_dim = 1
        context_mode = "constant"
    LOGGER.info(
        "Dry-run context path | mode=%s | target_layer=%d | context_dim=%d",
        context_mode,
        config.mamba_target_layer,
        config.context_dim,
    )
    hypernetwork = build_bridge_hypernetwork(args.bridge_mode, config, target_dims)
    patched_layers = patch_qwen_model(qwen_model, target_specs, scaling=float(config.lora_scaling))

    return TrainingRuntime(
        bridge_config=config,
        qwen_model=qwen_model,
        mamba_model=mamba_model,
        compressor=compressor,
        hypernetwork=hypernetwork,
        patched_layers=patched_layers,
        target_specs=target_specs,
        qwen_device=device,
        mamba_device=device,
        hyper_device=device,
        qwen_tokenizer=qwen_tokenizer,
        mamba_tokenizer=mamba_tokenizer,
        bridge_mode=args.bridge_mode,
        context_mode=context_mode,
        requires_mamba=requires_mamba,
        skip_compressor=args.skip_compressor,
        dry_run=True,
    )


def infer_total_fact_samples(
    train_samples: int,
    eval_samples: int,
    eval_split: str,
) -> int:
    if train_samples <= 0:
        raise ValueError("train_samples must be > 0")
    if eval_samples <= 0:
        raise ValueError("eval_samples must be > 0")

    total = max(3, train_samples + eval_samples + 1)
    search_limit = max(10_000, total * 32)
    for candidate in range(total, search_limit + 1):
        n_train, n_val, n_test = compute_split_counts(candidate)
        n_eval = n_val if eval_split == "val" else n_test
        if n_train >= train_samples and n_eval >= eval_samples:
            return candidate

    raise RuntimeError(
        "Could not infer a total fact-sample count that satisfies the requested "
        f"train/eval sizes (train={train_samples}, eval={eval_samples}, split={eval_split})."
    )


def maybe_limit_dataset(dataset: Dataset, limit: int, label: str) -> Dataset:
    if limit <= 0:
        raise ValueError(f"{label} limit must be > 0")
    dataset_size = len(dataset)
    if dataset_size < limit:
        raise ValueError(f"{label} dataset too small: requested {limit}, available {dataset_size}")
    if dataset_size == limit:
        return dataset
    return Subset(dataset, list(range(limit)))


def build_dataloaders(
    args: argparse.Namespace,
    runtime: TrainingRuntime,
) -> Tuple[DataLoader, DataLoader, Optional[DataLoader]]:
    include_text = False
    if runtime.dry_run:
        train_cfg = BridgeDatasetConfig(
            num_samples=max(4, args.batch_size * max(1, args.dry_run_steps)),
            mode="fact",
            mamba_context_tokens=args.dry_run_mamba_context_tokens,
            max_qwen_tokens=args.dry_run_max_qwen_tokens,
            min_post_target_tokens=16,
            max_post_target_tokens=32,
            seed=args.seed,
            include_text=include_text,
            qwen_prompt_format=args.qwen_prompt_format,
        )
        eval_cfg = BridgeDatasetConfig(
            num_samples=max(4, args.eval_batch_size * 2),
            mode="fact",
            mamba_context_tokens=args.dry_run_mamba_context_tokens,
            max_qwen_tokens=args.dry_run_max_qwen_tokens,
            min_post_target_tokens=16,
            max_post_target_tokens=32,
            seed=args.seed + 10_000,
            include_text=include_text,
            qwen_prompt_format=args.qwen_prompt_format,
        )
        general_cfg = BridgeDatasetConfig(
            num_samples=max(4, args.eval_batch_size * 2),
            mode="general",
            mamba_context_tokens=args.dry_run_mamba_context_tokens,
            max_qwen_tokens=args.dry_run_max_qwen_tokens,
            seed=args.seed + 20_000,
            include_text=include_text,
            qwen_prompt_format=args.qwen_prompt_format,
        )
        train_dataset: Dataset = BridgeDataset(
            config=train_cfg,
            mamba_tokenizer=runtime.mamba_tokenizer,
            qwen_tokenizer=runtime.qwen_tokenizer,
        )
        eval_dataset: Dataset = BridgeDataset(
            config=eval_cfg,
            mamba_tokenizer=runtime.mamba_tokenizer,
            qwen_tokenizer=runtime.qwen_tokenizer,
        )
    else:
        fact_total_samples = (
            args.fact_total_samples
            if args.fact_total_samples > 0
            else infer_total_fact_samples(
                train_samples=args.train_samples,
                eval_samples=args.eval_samples,
                eval_split=args.eval_split,
            )
        )
        fact_cfg = BridgeDatasetConfig(
            num_samples=fact_total_samples,
            mode="fact",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            min_post_target_tokens=args.min_post_target_tokens,
            max_post_target_tokens=args.max_post_target_tokens,
            seed=args.seed,
            include_text=include_text,
            qwen_prompt_format=args.qwen_prompt_format,
        )
        train_full, val_full, test_full = build_splits(
            fact_cfg,
            mamba_tokenizer=runtime.mamba_tokenizer,
            qwen_tokenizer=runtime.qwen_tokenizer,
        )
        if args.tiny_overfit:
            tiny_limit = min(args.tiny_overfit_samples, len(train_full))
            train_dataset = maybe_limit_dataset(train_full, tiny_limit, "tiny-overfit train")
            eval_limit = min(args.eval_samples, len(train_dataset))
            eval_dataset = maybe_limit_dataset(train_dataset, eval_limit, "tiny-overfit eval")
            LOGGER.info(
                "Using tiny-overfit mode | total=%d | shared_train_eval=%d | eval_from=train | holdout_val=%d | holdout_test=%d",
                fact_total_samples,
                len(train_dataset),
                len(val_full),
                len(test_full),
            )
        else:
            eval_full = val_full if args.eval_split == "val" else test_full
            train_dataset = maybe_limit_dataset(train_full, args.train_samples, "train")
            eval_dataset = maybe_limit_dataset(eval_full, args.eval_samples, f"{args.eval_split} eval")
            LOGGER.info(
                "Using disjoint fact splits | total=%d | train=%d/%d | eval(%s)=%d/%d | holdout_test=%d",
                fact_total_samples,
                len(train_dataset),
                len(train_full),
                args.eval_split,
                len(eval_dataset),
                len(eval_full),
                len(test_full),
            )
        general_cfg = BridgeDatasetConfig(
            num_samples=args.general_eval_samples,
            mode="general",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            seed=args.seed + 20_000,
            include_text=include_text,
            qwen_prompt_format=args.qwen_prompt_format,
        )

    general_dataset = (
        BridgeDataset(
            config=general_cfg,
            mamba_tokenizer=runtime.mamba_tokenizer,
            qwen_tokenizer=runtime.qwen_tokenizer,
        )
        if general_cfg.num_samples > 0
        else None
    )

    fact_dataset_for_pad = train_dataset.dataset if isinstance(train_dataset, Subset) else train_dataset
    collator = BridgeBatchCollator(qwen_pad_token_id=fact_dataset_for_pad.qwen_pad_token_id)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=not runtime.dry_run,
        num_workers=0,
        pin_memory=False,
        drop_last=False,
        collate_fn=collator,
    )
    eval_loader = DataLoader(
        eval_dataset,
        batch_size=args.eval_batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=False,
        drop_last=False,
        collate_fn=collator,
    )
    general_loader = None
    if general_dataset is not None:
        general_loader = DataLoader(
            general_dataset,
            batch_size=args.eval_batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=False,
            drop_last=False,
            collate_fn=collator,
        )

    return train_loader, eval_loader, general_loader


def save_checkpoint(
    runtime: TrainingRuntime,
    optimizer: AdamW,
    scheduler: LambdaLR,
    output_dir: Path,
    epoch: int,
    metrics: Dict[str, Any],
    best_bridge_acc: float,
    filename: Optional[str] = None,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (filename or f"bridge_epoch_{epoch:03d}.pt")
    torch.save(
        {
            "epoch": epoch,
            "metrics": metrics,
            "best_bridge_acc": best_bridge_acc,
            "bridge_mode": runtime.bridge_mode,
            "skip_compressor": runtime.skip_compressor,
            "bridge_config": asdict(runtime.bridge_config),
            "compressor_state_dict": runtime.compressor.state_dict(),
            "hypernetwork_state_dict": runtime.hypernetwork.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "target_specs": runtime.target_specs,
        },
        path,
    )
    return str(path)


def load_checkpoint(
    checkpoint_path: str,
    runtime: TrainingRuntime,
    optimizer: AdamW,
    scheduler: LambdaLR,
    load_compressor: bool = True,
    load_optimizer: bool = True,
    load_scheduler: bool = True,
) -> Dict[str, Any]:
    checkpoint = torch.load(
        checkpoint_path,
        map_location=str(runtime.hyper_device),
        weights_only=True,
    )

    expected_specs = checkpoint.get("target_specs")
    if expected_specs is not None and list(expected_specs) != list(runtime.target_specs):
        raise ValueError(
            "Checkpoint target_specs do not match the current runtime. "
            f"checkpoint={expected_specs} current={runtime.target_specs}"
        )

    checkpoint_bridge_mode = checkpoint.get("bridge_mode", "lora")
    if checkpoint_bridge_mode != runtime.bridge_mode:
        raise ValueError(
            "Checkpoint bridge_mode does not match the current runtime. "
            f"checkpoint={checkpoint_bridge_mode!r} current={runtime.bridge_mode!r}"
        )
    checkpoint_skip_compressor = bool(checkpoint.get("skip_compressor", False))
    if checkpoint_skip_compressor != runtime.skip_compressor:
        raise ValueError(
            "Checkpoint skip_compressor does not match the current runtime. "
            f"checkpoint={checkpoint_skip_compressor!r} current={runtime.skip_compressor!r}"
        )

    checkpoint_config = checkpoint.get("bridge_config", {})
    for field_name in (
        "qwen_model_id",
        "mamba_model_id",
        "context_dim",
        "lora_rank",
        "mamba_state_source",
        "mamba_target_layer",
    ):
        expected_value = checkpoint_config.get(field_name)
        current_value = getattr(runtime.bridge_config, field_name, None)
        if expected_value is not None and expected_value != current_value:
            raise ValueError(
                f"Checkpoint field {field_name!r}={expected_value!r} does not match current "
                f"runtime value {current_value!r}"
            )

    if load_compressor:
        runtime.compressor.load_state_dict(checkpoint["compressor_state_dict"])
    runtime.hypernetwork.load_state_dict(checkpoint["hypernetwork_state_dict"])
    if load_optimizer:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if load_scheduler:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

    return {
        "epoch": int(checkpoint["epoch"]),
        "best_bridge_acc": float(
            checkpoint.get(
                "best_bridge_acc",
                checkpoint.get("metrics", {}).get("eval", {}).get("bridge_accuracy", -1.0),
            )
        ),
        "metrics": checkpoint.get("metrics", {}),
    }


def train_one_epoch(
    runtime: TrainingRuntime,
    loader: DataLoader,
    optimizer: AdamW,
    scheduler: LambdaLR,
    epoch_index: int,
    max_grad_norm: float,
    dry_run_steps: int,
    max_lora_delta_norm: float,
    output_dir: Optional[Path],
    save_train_contexts: bool,
) -> Dict[str, Any]:
    runtime.compressor.train()
    runtime.hypernetwork.train()
    runtime.qwen_model.eval()
    runtime.mamba_model.eval()

    running_loss = 0.0
    running_norm_mean = 0.0
    running_norm_var = 0.0
    running_clamped_count = 0
    running_clamp_total = 0
    steps = 0
    context_rows: List[Dict[str, Any]] = []

    for step_index, batch in enumerate(loader, start=1):
        optimizer.zero_grad(set_to_none=True)

        context = build_batch_context(runtime, batch)
        if save_train_contexts and runtime.bridge_mode != "constant_bias":
            for row in range(context.shape[0]):
                context_rows.append(
                    {
                        "fact_kind": batch["metadata"][row]["fact_kind"],
                        "answer_text": batch["answer_text"][row],
                        "question_text": batch["question_text"][row],
                        "context_vector": context[row].detach().cpu(),
                    }
                )
        bridge_adjustments = runtime.hypernetwork(context)
        bridge_adjustments, batch_clamped_count, batch_clamp_total = clamp_bridge_adjustments(
            runtime.bridge_mode,
            bridge_adjustments,
            max_lora_delta_norm,
        )
        lora_norm_mean, lora_norm_var, _ = compute_bridge_norm_stats(runtime.bridge_mode, bridge_adjustments)
        clamp_fraction = (batch_clamped_count / batch_clamp_total) if batch_clamp_total else 0.0

        qwen_input_ids = move_batch_tensor(batch, "qwen_input_ids", runtime.qwen_device)
        qwen_attention_mask = move_batch_tensor(batch, "qwen_attention_mask", runtime.qwen_device)
        labels = move_batch_tensor(batch, "qwen_labels", runtime.qwen_device)

        set_bridge_adjustments(runtime, bridge_adjustments)
        try:
            logits = runtime.qwen_model(
                input_ids=qwen_input_ids,
                attention_mask=qwen_attention_mask,
            ).logits
            loss = compute_teacher_forcing_loss(logits, labels)
            loss.backward()
        finally:
            clear_lora(runtime.patched_layers)

        grad_norm = float(
            torch.nn.utils.clip_grad_norm_(
                list(runtime.compressor.parameters()) + list(runtime.hypernetwork.parameters()),
                max_grad_norm,
            ).item()
        )
        optimizer.step()
        scheduler.step()

        lr = float(optimizer.param_groups[0]["lr"])
        steps += 1
        running_loss += float(loss.item())
        running_norm_mean += lora_norm_mean
        running_norm_var += lora_norm_var
        running_clamped_count += batch_clamped_count
        running_clamp_total += batch_clamp_total

        norm_label = bridge_norm_label(runtime.bridge_mode)
        LOGGER.info(
            "train epoch=%d step=%d/%d loss=%.5f lr=%.3e grad_norm=%.5f %s_mean=%.5f %s_var=%.5f clamp=%.5f",
            epoch_index,
            step_index,
            len(loader),
            float(loss.item()),
            lr,
            grad_norm,
            norm_label,
            lora_norm_mean,
            norm_label,
            lora_norm_var,
            clamp_fraction,
        )

        if runtime.dry_run and step_index >= dry_run_steps:
            break

    context_path: Optional[str] = None
    if save_train_contexts and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        context_path = str(output_dir / f"train_epoch_{epoch_index:03d}_contexts.pt")
        torch.save(context_rows, context_path)

    return {
        "loss": running_loss / max(1, steps),
        "lora_norm_mean": running_norm_mean / max(1, steps),
        "lora_norm_var": running_norm_var / max(1, steps),
        "lora_clamp_fraction": (running_clamped_count / running_clamp_total if running_clamp_total else 0.0),
        "context_vectors_path": context_path,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the Mamba -> Qwen bridge.")
    parser.add_argument("--dry-run", action="store_true", help="Run stub models only; no model downloads.")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Skip training and run a single evaluation pass from --resume-from.",
    )
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--eval-batch-size", type=int, default=2)
    parser.add_argument("--train-samples", type=int, default=64)
    parser.add_argument("--eval-samples", type=int, default=32)
    parser.add_argument(
        "--fact-total-samples",
        type=int,
        default=0,
        help="Total fact samples to generate before disjoint train/val/test split; 0=auto-size.",
    )
    parser.add_argument(
        "--eval-split",
        type=str,
        choices=("val", "test"),
        default="val",
        help="Which disjoint fact split to use for evaluation during training.",
    )
    parser.add_argument("--general-eval-samples", type=int, default=16)
    parser.add_argument("--mamba-context-tokens", type=int, default=8192)
    parser.add_argument("--max-qwen-tokens", type=int, default=256)
    parser.add_argument("--min-post-target-tokens", type=int, default=1024)
    parser.add_argument("--max-post-target-tokens", type=int, default=4096)
    parser.add_argument(
        "--bridge-mode",
        type=str,
        choices=SUPPORTED_BRIDGE_MODES,
        default="lora",
        help="Bridge parameterization to train. Default keeps the current dynamic LoRA path.",
    )
    parser.add_argument(
        "--eval-adjustment-source",
        type=str,
        choices=("learned", "fixed_mean"),
        default="learned",
        help="Which bridge adjustments to evaluate. fixed_mean averages activation_bias outputs over the train loader.",
    )
    parser.add_argument(
        "--fixed-mean-contexts-path",
        type=str,
        default="",
        help="Optional saved train-context .pt file for fixed_mean eval. Lets C3 run without a live Mamba forward path.",
    )
    parser.add_argument(
        "--skip-compressor",
        action="store_true",
        help="Activation-bias only: bypass the learned compressor and feed raw Layer 3 state into the hypernetwork.",
    )
    parser.add_argument(
        "--context-dim",
        type=int,
        default=0,
        help="Override the learned compressor output width. 0 keeps the default. Ignored by --skip-compressor.",
    )
    parser.add_argument(
        "--qwen-prompt-format",
        type=str,
        choices=("completion", "chatml"),
        default="completion",
        help="Prompt surface for the frozen base model. Use completion for base-model-friendly prompting.",
    )
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--warmup-steps", type=int, default=200)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument(
        "--max-lora-delta-norm",
        type=float,
        default=0.0,
        help="Clamp each generated LoRA delta matrix to this max L2 norm per sample/layer; 0 disables clamping.",
    )
    parser.add_argument("--eval-every", type=int, default=1)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--mamba-device", type=str, default="auto")
    parser.add_argument("--hyper-device", type=str, default="")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit Qwen loading.")
    parser.add_argument("--target-layers", type=str, default="", help="Comma-separated layer:proj specs.")
    parser.add_argument("--output-dir", type=str, default="bridge_train_runs")
    parser.add_argument("--resume-from", type=str, default="", help="Checkpoint path to resume from.")
    parser.add_argument(
        "--save-eval-contexts",
        action="store_true",
        help="Save eval context vectors for PCA/collapse diagnostics.",
    )
    parser.add_argument(
        "--save-train-contexts",
        action="store_true",
        help="Save train context vectors per epoch for PCA/collapse diagnostics.",
    )
    parser.add_argument(
        "--save-eval-predictions",
        action="store_true",
        help="Save a small JSON sample of eval prompts, gold answers, and predictions.",
    )
    parser.add_argument(
        "--eval-prediction-samples",
        type=int,
        default=8,
        help="Maximum number of eval prediction rows to save per epoch.",
    )
    parser.add_argument("--save-checkpoints", action="store_true", help="Save/update bridge_best.pt on eval improvement.")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=0,
        help="If >0, save a resumable epoch checkpoint every N epochs.",
    )
    parser.add_argument(
        "--tiny-overfit",
        action="store_true",
        help="Debug mode: train and eval on the same tiny subset to verify the bridge can move off zero.",
    )
    parser.add_argument(
        "--tiny-overfit-samples",
        type=int,
        default=16,
        help="Shared train/eval subset size when --tiny-overfit is enabled.",
    )
    parser.add_argument("--dry-run-steps", type=int, default=2)
    parser.add_argument("--dry-run-mamba-context-tokens", type=int, default=128)
    parser.add_argument("--dry-run-max-qwen-tokens", type=int, default=256)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--model", "--qwen-model-id", dest="qwen_model_id", type=str, default=QWEN_MODEL_ID, help="HuggingFace model ID for the Qwen base model.")
    parser.add_argument("--mamba-model-id", type=str, default=MAMBA_MODEL_ID, help="HuggingFace model ID for the Mamba model.")
    return parser


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    for field_name in (
        "eval_split",
        "device",
        "mamba_device",
        "hyper_device",
        "target_layers",
        "output_dir",
        "resume_from",
        "qwen_model_id",
        "mamba_model_id",
        "bridge_mode",
        "eval_adjustment_source",
        "fixed_mean_contexts_path",
        "qwen_prompt_format",
    ):
        value = getattr(args, field_name, None)
        if isinstance(value, str):
            setattr(args, field_name, value.strip())
    return args


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.context_dim < 0:
        parser.error("--context-dim must be >= 0.")
    if args.skip_compressor and args.bridge_mode != "activation_bias":
        parser.error("--skip-compressor is only supported with --bridge-mode activation_bias.")
    if args.eval_adjustment_source == "fixed_mean" and args.bridge_mode != "activation_bias":
        parser.error("--eval-adjustment-source fixed_mean is only supported with --bridge-mode activation_bias.")
    if args.eval_only and not args.resume_from:
        parser.error("--eval-only requires --resume-from.")
    if args.fixed_mean_contexts_path and args.eval_adjustment_source != "fixed_mean":
        parser.error("--fixed-mean-contexts-path only makes sense with --eval-adjustment-source fixed_mean.")


def count_trainable_parameters(module: nn.Module) -> int:
    return sum(param.numel() for param in module.parameters() if param.requires_grad)


def main() -> int:
    parser = build_arg_parser()
    args = normalize_args(parser.parse_args())
    validate_args(parser, args)
    configure_logging(verbose=args.verbose)
    set_seed(args.seed)

    # TODO: cognitive_bridge.py inference still formats prompts as raw
    # [Game World] text. It should be migrated to the same prompt distribution
    # configured here before comparing deployment behavior to training.

    LOGGER.info("Starting bridge training. dry_run=%s bridge_mode=%s", args.dry_run, args.bridge_mode)
    runtime = build_dry_run_runtime(args) if args.dry_run else build_real_runtime(args)
    train_loader, eval_loader, general_loader = build_dataloaders(args, runtime)

    if runtime.bridge_mode == "constant_bias" and args.save_train_contexts:
        LOGGER.warning("--save-train-contexts ignored in constant_bias mode.")
    if args.eval_adjustment_source == "fixed_mean" and args.save_eval_contexts:
        LOGGER.warning("--save-eval-contexts is ignored for fixed_mean eval because no per-sample eval context is used.")

    context_encoder_params = count_trainable_parameters(runtime.compressor)
    hypernetwork_params = count_trainable_parameters(runtime.hypernetwork)
    total_trainable_params = context_encoder_params + hypernetwork_params
    LOGGER.info(
        "Trainable params | context_mode=%s | context_dim=%d | context_encoder=%d | hypernetwork=%d | total=%d",
        runtime.context_mode,
        runtime.bridge_config.context_dim,
        context_encoder_params,
        hypernetwork_params,
        total_trainable_params,
    )
    if runtime.skip_compressor:
        LOGGER.warning(
            "skip-compressor is active; this run is not parameter-matched to compressed-context baselines."
        )

    trainable_params: List[nn.Parameter] = list(runtime.compressor.parameters()) + list(
        runtime.hypernetwork.parameters()
    )
    optimizer = AdamW(trainable_params, lr=args.lr, weight_decay=args.weight_decay)
    train_steps = args.dry_run_steps if args.dry_run else len(train_loader)
    total_steps = args.epochs * max(1, train_steps)
    scheduler = build_lr_scheduler(optimizer, warmup_steps=args.warmup_steps, total_steps=total_steps)

    output_dir = Path(args.output_dir)
    best_bridge_acc = -1.0
    best_checkpoint_path = output_dir / "bridge_best.pt"
    best_checkpoint: Optional[str] = str(best_checkpoint_path) if best_checkpoint_path.exists() else None
    start_epoch = 1
    resumed_from: Optional[str] = None
    resume_state: Optional[Dict[str, Any]] = None

    if args.resume_from:
        load_saved_fixed_mean = bool(
            args.eval_only
            and args.bridge_mode == "activation_bias"
            and args.eval_adjustment_source == "fixed_mean"
            and args.fixed_mean_contexts_path
        )
        resume_state = load_checkpoint(
            checkpoint_path=args.resume_from,
            runtime=runtime,
            optimizer=optimizer,
            scheduler=scheduler,
            load_compressor=not load_saved_fixed_mean,
            load_optimizer=not load_saved_fixed_mean,
            load_scheduler=not load_saved_fixed_mean,
        )
        start_epoch = int(resume_state["epoch"]) + 1
        best_bridge_acc = float(resume_state["best_bridge_acc"])
        resumed_from = args.resume_from
        LOGGER.info(
            "Resumed checkpoint %s | next_epoch=%d | best_bridge_acc=%.5f",
            args.resume_from,
            start_epoch,
            best_bridge_acc,
        )

    if args.eval_only:
        fixed_mean_adjustments = None
        if args.eval_adjustment_source == "fixed_mean":
            if args.fixed_mean_contexts_path:
                LOGGER.info(
                    "Computing fixed-mean bias from saved contexts for eval-only C3 control: %s",
                    args.fixed_mean_contexts_path,
                )
                fixed_mean_adjustments = compute_fixed_mean_adjustments_from_saved_contexts(
                    runtime,
                    args.fixed_mean_contexts_path,
                )
            else:
                LOGGER.info("Computing fixed-mean bias from the train loader for eval-only C3 control.")
                fixed_mean_adjustments = compute_fixed_mean_adjustments(runtime, train_loader)

        eval_epoch = int(resume_state["epoch"]) if resume_state is not None else max(0, start_epoch - 1)
        train_stats = (
            dict(resume_state.get("metrics", {}).get("train", {}))
            if resume_state is not None
            else {}
        )
        train_stats.setdefault("loss", 0.0)
        train_stats.setdefault("lora_norm_mean", 0.0)
        train_stats.setdefault("lora_norm_var", 0.0)
        train_stats.setdefault("lora_clamp_fraction", 0.0)
        train_stats.setdefault("context_vectors_path", None)

        eval_results = evaluate_fact_accuracy(
            runtime=runtime,
            loader=eval_loader,
            reconstruction_probe_loader=train_loader,
            bootstrap_resamples=args.bootstrap_resamples,
            seed=args.seed + max(1, eval_epoch),
            epoch_index=eval_epoch,
            output_dir=output_dir,
            save_eval_contexts=args.save_eval_contexts,
            save_eval_predictions=args.save_eval_predictions,
            eval_prediction_samples=args.eval_prediction_samples,
            general_loader=general_loader,
            max_lora_delta_norm=args.max_lora_delta_norm,
            eval_adjustment_source=args.eval_adjustment_source,
            fixed_mean_adjustments=fixed_mean_adjustments,
        )
        comparison_path = write_eval_comparison_artifacts(
            output_dir=output_dir,
            runtime=runtime,
            epoch_index=eval_epoch,
            eval_split=args.eval_split,
            eval_adjustment_source=args.eval_adjustment_source,
            train_stats=train_stats,
            eval_results=eval_results,
        )
        LOGGER.info(
            "eval-only epoch=%d source=%s | %s | %s | %s | p=%.4g",
            eval_epoch,
            args.eval_adjustment_source,
            format_accuracy_summary("Bridge", eval_results.bridge),
            format_accuracy_summary("Baseline", eval_results.baseline),
            format_accuracy_summary("Random", eval_results.random_control),
            eval_results.p_value_bridge_vs_baseline,
        )
        if eval_results.reconstruction_stats is not None:
            LOGGER.info(
                "eval-only epoch=%d | reconstruction_mse_mean=%.7f reconstruction_mse_var=%.7f",
                eval_epoch,
                eval_results.reconstruction_stats["reconstruction_mse_mean"],
                eval_results.reconstruction_stats["reconstruction_mse_var"],
            )
        if eval_results.general_ppl is not None:
            LOGGER.info(
                "eval-only epoch=%d | general_ppl baseline=%.4f random=%.4f bridge=%.4f",
                eval_epoch,
                eval_results.general_ppl["baseline_ppl"],
                eval_results.general_ppl["random_ppl"],
                eval_results.general_ppl["bridge_ppl"],
            )
        if eval_results.reconstruction_path is not None:
            LOGGER.info("eval-only epoch=%d | saved_reconstruction=%s", eval_epoch, eval_results.reconstruction_path)
        LOGGER.info("eval-only epoch=%d | saved_comparison=%s", eval_epoch, comparison_path)
        LOGGER.info(
            "Training finished: %s",
            json.dumps(
                {
                    "dry_run": args.dry_run,
                    "eval_only": True,
                    "bridge_mode": args.bridge_mode,
                    "eval_adjustment_source": args.eval_adjustment_source,
                    "fixed_mean_contexts_path": args.fixed_mean_contexts_path or None,
                    "best_checkpoint": best_checkpoint,
                    "resumed_from": resumed_from,
                    "eval_split": args.eval_split,
                },
                indent=2,
            ),
        )
        return 0

    for epoch_index in range(start_epoch, args.epochs + 1):
        epoch_start = time.time()
        train_stats = train_one_epoch(
            runtime=runtime,
            loader=train_loader,
            optimizer=optimizer,
            scheduler=scheduler,
            epoch_index=epoch_index,
            max_grad_norm=args.max_grad_norm,
            dry_run_steps=args.dry_run_steps,
            max_lora_delta_norm=args.max_lora_delta_norm,
            output_dir=output_dir if args.save_train_contexts else None,
            save_train_contexts=args.save_train_contexts,
        )
        norm_label = bridge_norm_label(runtime.bridge_mode)

        LOGGER.info(
            "epoch=%d train_loss=%.5f %s_mean=%.5f %s_var=%.5f clamp=%.5f elapsed=%.2fs",
            epoch_index,
            train_stats["loss"],
            norm_label,
            train_stats["lora_norm_mean"],
            norm_label,
            train_stats["lora_norm_var"],
            train_stats["lora_clamp_fraction"],
            time.time() - epoch_start,
        )
        if train_stats.get("context_vectors_path") is not None:
            LOGGER.info("epoch=%d | saved_train_context_vectors=%s", epoch_index, train_stats["context_vectors_path"])

        latest_metrics: Dict[str, Any] = {"train": train_stats}
        if epoch_index % args.eval_every == 0:
            fixed_mean_adjustments = None
            if args.eval_adjustment_source == "fixed_mean":
                LOGGER.info("epoch=%d | computing fixed-mean bias from train loader before eval", epoch_index)
                fixed_mean_adjustments = compute_fixed_mean_adjustments(runtime, train_loader)
            eval_results = evaluate_fact_accuracy(
                runtime=runtime,
                loader=eval_loader,
                reconstruction_probe_loader=train_loader,
                bootstrap_resamples=args.bootstrap_resamples,
                seed=args.seed + epoch_index,
                epoch_index=epoch_index,
                output_dir=output_dir,
                save_eval_contexts=args.save_eval_contexts,
                save_eval_predictions=args.save_eval_predictions,
                eval_prediction_samples=args.eval_prediction_samples,
                general_loader=general_loader,
                max_lora_delta_norm=args.max_lora_delta_norm,
                eval_adjustment_source=args.eval_adjustment_source,
                fixed_mean_adjustments=fixed_mean_adjustments,
            )
            comparison_path = write_eval_comparison_artifacts(
                output_dir=output_dir,
                runtime=runtime,
                epoch_index=epoch_index,
                eval_split=args.eval_split,
                eval_adjustment_source=args.eval_adjustment_source,
                train_stats=train_stats,
                eval_results=eval_results,
            )

            LOGGER.info(
                "eval epoch=%d source=%s | %s | %s | %s | p=%.4g",
                epoch_index,
                args.eval_adjustment_source,
                format_accuracy_summary("Bridge", eval_results.bridge),
                format_accuracy_summary("Baseline", eval_results.baseline),
                format_accuracy_summary("Random", eval_results.random_control),
                eval_results.p_value_bridge_vs_baseline,
            )
            LOGGER.info(
                "eval epoch=%d | bridge_%s_norm=%.5f | random_%s_norm=%.5f | bridge_clamp=%.5f",
                epoch_index,
                norm_label,
                eval_results.bridge_lora_norm_mean,
                norm_label,
                eval_results.random_lora_norm_mean,
                eval_results.bridge_lora_clamp_fraction,
            )
            if eval_results.compressed_state_stats is not None:
                LOGGER.info(
                    "eval epoch=%d | compressed_state context_norm_mean=%.5f context_norm_var=%.5f "
                    "centroid_l2_mean=%.5f centroid_l2_var=%.5f "
                    "centroid_cosine_mean=%.5f centroid_cosine_var=%.5f",
                    epoch_index,
                    eval_results.compressed_state_stats["context_norm_mean"],
                    eval_results.compressed_state_stats["context_norm_var"],
                    eval_results.compressed_state_stats["context_centroid_l2_mean"],
                    eval_results.compressed_state_stats["context_centroid_l2_var"],
                    eval_results.compressed_state_stats["context_centroid_cosine_distance_mean"],
                    eval_results.compressed_state_stats["context_centroid_cosine_distance_var"],
                )
            if eval_results.reconstruction_stats is not None:
                LOGGER.info(
                    "eval epoch=%d | reconstruction_mse_mean=%.7f reconstruction_mse_var=%.7f",
                    epoch_index,
                    eval_results.reconstruction_stats["reconstruction_mse_mean"],
                    eval_results.reconstruction_stats["reconstruction_mse_var"],
                )
            if eval_results.general_ppl is not None:
                LOGGER.info(
                    "eval epoch=%d | general_ppl baseline=%.4f random=%.4f bridge=%.4f",
                    epoch_index,
                    eval_results.general_ppl["baseline_ppl"],
                    eval_results.general_ppl["random_ppl"],
                    eval_results.general_ppl["bridge_ppl"],
                )
            if eval_results.context_vectors_path is not None:
                LOGGER.info("eval epoch=%d | saved_context_vectors=%s", epoch_index, eval_results.context_vectors_path)
            if eval_results.predictions_path is not None:
                LOGGER.info("eval epoch=%d | saved_predictions=%s", epoch_index, eval_results.predictions_path)
            if eval_results.reconstruction_path is not None:
                LOGGER.info("eval epoch=%d | saved_reconstruction=%s", epoch_index, eval_results.reconstruction_path)
            LOGGER.info("eval epoch=%d | saved_comparison=%s", epoch_index, comparison_path)

            latest_metrics = {
                "train": train_stats,
                "eval": {
                    "bridge_accuracy": eval_results.bridge.accuracy,
                    "baseline_accuracy": eval_results.baseline.accuracy,
                    "random_accuracy": eval_results.random_control.accuracy,
                    "p_value": eval_results.p_value_bridge_vs_baseline,
                    "bridge_mode": runtime.bridge_mode,
                    "eval_adjustment_source": args.eval_adjustment_source,
                    "bridge_lora_norm_mean": eval_results.bridge_lora_norm_mean,
                    "random_lora_norm_mean": eval_results.random_lora_norm_mean,
                    "bridge_lora_clamp_fraction": eval_results.bridge_lora_clamp_fraction,
                    "compressed_state_stats": eval_results.compressed_state_stats,
                    "reconstruction_stats": eval_results.reconstruction_stats,
                    "general_ppl": eval_results.general_ppl,
                    "eval_split": args.eval_split,
                    "predictions_path": eval_results.predictions_path,
                    "reconstruction_path": eval_results.reconstruction_path,
                    "comparison_path": comparison_path,
                },
            }
            if args.save_checkpoints and eval_results.bridge.accuracy > best_bridge_acc:
                best_checkpoint = save_checkpoint(
                    runtime=runtime,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    output_dir=output_dir,
                    epoch=epoch_index,
                    metrics=latest_metrics,
                    best_bridge_acc=eval_results.bridge.accuracy,
                    filename="bridge_best.pt",
                )
                best_bridge_acc = eval_results.bridge.accuracy
                LOGGER.info("Saved checkpoint: %s", best_checkpoint)

        if args.checkpoint_every > 0 and (epoch_index % args.checkpoint_every == 0):
            periodic_checkpoint = save_checkpoint(
                runtime=runtime,
                optimizer=optimizer,
                scheduler=scheduler,
                output_dir=output_dir,
                epoch=epoch_index,
                metrics=latest_metrics,
                best_bridge_acc=best_bridge_acc,
            )
            LOGGER.info("Saved resumable checkpoint: %s", periodic_checkpoint)

        if args.dry_run:
            LOGGER.info("Dry-run epoch complete. Gradient flow and eval loop verified.")

    final_summary = {
        "dry_run": args.dry_run,
        "eval_only": args.eval_only,
        "bridge_mode": args.bridge_mode,
        "eval_adjustment_source": args.eval_adjustment_source,
        "fixed_mean_contexts_path": args.fixed_mean_contexts_path or None,
        "epochs": args.epochs,
        "start_epoch": start_epoch,
        "train_batches": len(train_loader),
        "eval_batches": len(eval_loader),
        "best_checkpoint": best_checkpoint,
        "resumed_from": resumed_from,
        "eval_split": args.eval_split,
        "tiny_overfit": args.tiny_overfit,
    }
    LOGGER.info("Training finished: %s", json.dumps(final_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
