"""
train_bridge.py - Phase 2 trainer for the Mamba -> Qwen cognitive bridge.

This script trains only the MambaStateCompressor and LoRAHypernetwork.
Mamba and Qwen stay frozen. Training uses teacher forcing on ChatML data
from bridge_dataset.py, and evaluation uses strict exact-match recall on
held-out fact prompts.

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
from torch.utils.data import DataLoader, Dataset

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
)
from cognitive_bridge import BridgeConfig
from models import DynamicLoRALinear, LoRAHypernetwork, MambaStateCompressor

LOGGER = logging.getLogger("TrainBridge")


@dataclass
class TrainingRuntime:
    bridge_config: BridgeConfig
    qwen_model: nn.Module
    mamba_model: nn.Module
    compressor: MambaStateCompressor
    hypernetwork: LoRAHypernetwork
    patched_layers: List[DynamicLoRALinear]
    target_specs: List[Tuple[int, str]]
    qwen_device: torch.device
    mamba_device: torch.device
    hyper_device: torch.device
    qwen_tokenizer: Any
    mamba_tokenizer: Any
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
    p_value_bridge_vs_baseline: float
    context_vectors_path: Optional[str] = None
    general_ppl: Optional[Dict[str, float]] = None


class FakeTokenizer:
    """Tokenizer stub for --dry-run. It understands ChatML markers only."""

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


def greedy_generate_answer(
    qwen_model: nn.Module,
    prompt_ids: torch.Tensor,
    answer_len: int,
    qwen_device: torch.device,
) -> torch.Tensor:
    # TODO: Once eval correctness is fully locked, swap this Python token loop
    # for model.generate(max_new_tokens=answer_len, do_sample=False).
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

            mamba_state = run_mamba_state(runtime, batch["mamba_history_ids"])
            comp_dtype = next(runtime.compressor.parameters()).dtype
            context = runtime.compressor(mamba_state.to(runtime.hyper_device, dtype=comp_dtype))
            lora_pairs = runtime.hypernetwork(context)
            random_pairs = sample_norm_matched_random_lora(lora_pairs, generator=generator)

            qwen_input_ids = move_batch_tensor(batch, "qwen_input_ids", runtime.qwen_device)
            qwen_attention_mask = move_batch_tensor(batch, "qwen_attention_mask", runtime.qwen_device)

            clear_lora(runtime.patched_layers)
            baseline_logits = runtime.qwen_model(
                input_ids=qwen_input_ids,
                attention_mask=qwen_attention_mask,
            ).logits
            baseline_loss = compute_teacher_forcing_loss(baseline_logits, labels)

            set_lora(runtime.patched_layers, random_pairs)
            try:
                random_logits = runtime.qwen_model(
                    input_ids=qwen_input_ids,
                    attention_mask=qwen_attention_mask,
                ).logits
            finally:
                clear_lora(runtime.patched_layers)
            random_loss = compute_teacher_forcing_loss(random_logits, labels)

            set_lora(runtime.patched_layers, lora_pairs)
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
    bootstrap_resamples: int,
    seed: int,
    epoch_index: int,
    output_dir: Optional[Path],
    save_eval_contexts: bool,
    general_loader: Optional[DataLoader],
) -> EvalResults:
    runtime.compressor.eval()
    runtime.hypernetwork.eval()
    runtime.qwen_model.eval()
    runtime.mamba_model.eval()

    generator = torch.Generator(device=str(runtime.hyper_device))
    generator.manual_seed(seed)

    baseline_correct: List[int] = []
    random_correct: List[int] = []
    bridge_correct: List[int] = []
    bridge_norm_values: List[float] = []
    random_norm_values: List[float] = []
    context_rows: List[Dict[str, Any]] = []

    with torch.no_grad():
        for batch in loader:
            mamba_state = run_mamba_state(runtime, batch["mamba_history_ids"])
            comp_dtype = next(runtime.compressor.parameters()).dtype
            context = runtime.compressor(mamba_state.to(runtime.hyper_device, dtype=comp_dtype))
            lora_pairs = runtime.hypernetwork(context)
            random_pairs = sample_norm_matched_random_lora(lora_pairs, generator=generator)

            _, _, bridge_sample_norms = compute_lora_norm_stats(lora_pairs)
            _, _, random_sample_norms = compute_lora_norm_stats(random_pairs)

            batch_size = batch["qwen_prompt_ids"].shape[0]
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
                baseline_correct.append(int(torch.equal(baseline_pred.cpu(), answer_ids.cpu())))

                set_lora(
                    runtime.patched_layers,
                    [(A[row : row + 1], B[row : row + 1]) for A, B in random_pairs],
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
                random_correct.append(int(torch.equal(random_pred.cpu(), answer_ids.cpu())))

                set_lora(
                    runtime.patched_layers,
                    [(A[row : row + 1], B[row : row + 1]) for A, B in lora_pairs],
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
                bridge_correct.append(int(torch.equal(bridge_pred.cpu(), answer_ids.cpu())))

                bridge_norm_values.append(float(bridge_sample_norms[row].item()))
                random_norm_values.append(float(random_sample_norms[row].item()))

                if save_eval_contexts:
                    context_rows.append(
                        {
                            "fact_kind": batch["metadata"][row]["fact_kind"],
                            "answer_text": batch["answer_text"][row],
                            "question_text": batch["question_text"][row],
                            "context_vector": context[row].detach().cpu(),
                        }
                    )

    context_path: Optional[str] = None
    if save_eval_contexts and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        context_path = str(output_dir / f"eval_epoch_{epoch_index:03d}_contexts.pt")
        torch.save(context_rows, context_path)

    baseline_summary = summarize_accuracy(baseline_correct, bootstrap_resamples, seed + 11)
    random_summary = summarize_accuracy(random_correct, bootstrap_resamples, seed + 23)
    bridge_summary = summarize_accuracy(bridge_correct, bootstrap_resamples, seed + 37)
    p_value = paired_t_test_p_value(bridge_correct, baseline_correct)
    general_ppl = evaluate_language_model(runtime, general_loader, seed + 101)

    return EvalResults(
        bridge=bridge_summary,
        baseline=baseline_summary,
        random_control=random_summary,
        bridge_lora_norm_mean=(statistics.fmean(bridge_norm_values) if bridge_norm_values else 0.0),
        random_lora_norm_mean=(statistics.fmean(random_norm_values) if random_norm_values else 0.0),
        p_value_bridge_vs_baseline=p_value,
        context_vectors_path=context_path,
        general_ppl=general_ppl,
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
        qwen_model_id=QWEN_MODEL_ID,
        mamba_model_id=MAMBA_MODEL_ID,
        device=str(qwen_device),
        hyper_device=str(hyper_device),
        use_4bit=not args.no_4bit,
        startup_validation=False,
        target_layers=parse_target_layers(args.target_layers),
    )

    is_qwen_cpu = str(qwen_device) == "cpu"
    qwen_model_kwargs: Dict[str, Any] = {"low_cpu_mem_usage": True}
    if not is_qwen_cpu:
        qwen_model_kwargs["device_map"] = "auto"

    if config.use_4bit and not is_qwen_cpu:
        from transformers import BitsAndBytesConfig

        qwen_model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        qwen_model_kwargs["torch_dtype"] = torch.float32 if is_qwen_cpu else torch.float16

    LOGGER.info("Loading Qwen base model: %s", config.qwen_model_id)
    qwen_tokenizer = AutoTokenizer.from_pretrained(config.qwen_model_id, use_fast=True)
    if qwen_tokenizer.pad_token_id is None:
        qwen_tokenizer.pad_token = qwen_tokenizer.eos_token
    qwen_model = AutoModelForCausalLM.from_pretrained(config.qwen_model_id, **qwen_model_kwargs)
    qwen_model.eval()
    for param in qwen_model.parameters():
        param.requires_grad = False
    qwen_input_device = torch.device("cpu") if hasattr(qwen_model, "hf_device_map") else qwen_device

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

    LOGGER.info(
        "Runtime devices | qwen_input=%s | mamba=%s | hyper=%s",
        qwen_input_device,
        mamba_device,
        hyper_device,
    )

    target_specs = resolve_target_specs(qwen_model, config.target_layers)
    validate_target_specs(qwen_model, target_specs)
    target_dims = [
        (get_layer_module(qwen_model, spec).in_features, get_layer_module(qwen_model, spec).out_features)
        for spec in target_specs
    ]

    compressor = MambaStateCompressor(
        mamba_layers=resolved_mamba_layers,
        mamba_d_model=resolved_mamba_d_model,
        mamba_d_state=resolved_mamba_d_state,
        output_dim=config.context_dim,
        target_layer=config.mamba_target_layer,
    ).to(hyper_device)
    hypernetwork = LoRAHypernetwork(
        context_dim=config.context_dim,
        target_dims=target_dims,
        lora_rank=config.lora_rank,
        hidden_dim=config.hyper_hidden_dim,
    ).to(hyper_device)
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
        dry_run=False,
    )


def build_dry_run_runtime(args: argparse.Namespace) -> TrainingRuntime:
    device = torch.device("cpu")
    config = BridgeConfig(
        qwen_model_id=QWEN_MODEL_ID,
        mamba_model_id=MAMBA_MODEL_ID,
        mamba_layers=4,
        mamba_d_model=12,
        mamba_d_state=6,
        context_dim=24,
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
    compressor = MambaStateCompressor(
        mamba_layers=config.mamba_layers,
        mamba_d_model=config.mamba_d_model,
        mamba_d_state=config.mamba_d_state,
        output_dim=config.context_dim,
        target_layer=config.mamba_target_layer,
    )
    hypernetwork = LoRAHypernetwork(
        context_dim=config.context_dim,
        target_dims=target_dims,
        lora_rank=config.lora_rank,
        hidden_dim=config.hyper_hidden_dim,
    )
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
        dry_run=True,
    )


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
        )
        general_cfg = BridgeDatasetConfig(
            num_samples=max(4, args.eval_batch_size * 2),
            mode="general",
            mamba_context_tokens=args.dry_run_mamba_context_tokens,
            max_qwen_tokens=args.dry_run_max_qwen_tokens,
            seed=args.seed + 20_000,
            include_text=include_text,
        )
    else:
        train_cfg = BridgeDatasetConfig(
            num_samples=args.train_samples,
            mode="fact",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            min_post_target_tokens=args.min_post_target_tokens,
            max_post_target_tokens=args.max_post_target_tokens,
            seed=args.seed,
            include_text=include_text,
        )
        eval_cfg = BridgeDatasetConfig(
            num_samples=args.eval_samples,
            mode="fact",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            min_post_target_tokens=args.min_post_target_tokens,
            max_post_target_tokens=args.max_post_target_tokens,
            seed=args.seed + 10_000,
            include_text=include_text,
        )
        general_cfg = BridgeDatasetConfig(
            num_samples=args.general_eval_samples,
            mode="general",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            seed=args.seed + 20_000,
            include_text=include_text,
        )

    train_dataset = BridgeDataset(
        config=train_cfg,
        mamba_tokenizer=runtime.mamba_tokenizer,
        qwen_tokenizer=runtime.qwen_tokenizer,
    )
    eval_dataset = BridgeDataset(
        config=eval_cfg,
        mamba_tokenizer=runtime.mamba_tokenizer,
        qwen_tokenizer=runtime.qwen_tokenizer,
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

    collator = BridgeBatchCollator(qwen_pad_token_id=train_dataset.qwen_pad_token_id)
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
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"bridge_epoch_{epoch:03d}.pt"
    torch.save(
        {
            "epoch": epoch,
            "metrics": metrics,
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


def train_one_epoch(
    runtime: TrainingRuntime,
    loader: DataLoader,
    optimizer: AdamW,
    scheduler: LambdaLR,
    epoch_index: int,
    max_grad_norm: float,
    dry_run_steps: int,
) -> Dict[str, float]:
    runtime.compressor.train()
    runtime.hypernetwork.train()
    runtime.qwen_model.eval()
    runtime.mamba_model.eval()

    running_loss = 0.0
    running_norm_mean = 0.0
    running_norm_var = 0.0
    steps = 0

    for step_index, batch in enumerate(loader, start=1):
        optimizer.zero_grad(set_to_none=True)

        mamba_state = run_mamba_state(runtime, batch["mamba_history_ids"])
        comp_dtype = next(runtime.compressor.parameters()).dtype
        state_for_compressor = mamba_state.to(runtime.hyper_device, dtype=comp_dtype)
        context = runtime.compressor(state_for_compressor)
        lora_pairs = runtime.hypernetwork(context)
        lora_norm_mean, lora_norm_var, _ = compute_lora_norm_stats(lora_pairs)

        qwen_input_ids = move_batch_tensor(batch, "qwen_input_ids", runtime.qwen_device)
        qwen_attention_mask = move_batch_tensor(batch, "qwen_attention_mask", runtime.qwen_device)
        labels = move_batch_tensor(batch, "qwen_labels", runtime.qwen_device)

        set_lora(runtime.patched_layers, lora_pairs)
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

        LOGGER.info(
            "train epoch=%d step=%d/%d loss=%.5f lr=%.3e grad_norm=%.5f lora_mean=%.5f lora_var=%.5f",
            epoch_index,
            step_index,
            len(loader),
            float(loss.item()),
            lr,
            grad_norm,
            lora_norm_mean,
            lora_norm_var,
        )

        if runtime.dry_run and step_index >= dry_run_steps:
            break

    return {
        "loss": running_loss / max(1, steps),
        "lora_norm_mean": running_norm_mean / max(1, steps),
        "lora_norm_var": running_norm_var / max(1, steps),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the Mamba -> Qwen bridge.")
    parser.add_argument("--dry-run", action="store_true", help="Run stub models only; no model downloads.")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--eval-batch-size", type=int, default=2)
    parser.add_argument("--train-samples", type=int, default=64)
    parser.add_argument("--eval-samples", type=int, default=32)
    parser.add_argument("--general-eval-samples", type=int, default=16)
    parser.add_argument("--mamba-context-tokens", type=int, default=8192)
    parser.add_argument("--max-qwen-tokens", type=int, default=256)
    parser.add_argument("--min-post-target-tokens", type=int, default=1024)
    parser.add_argument("--max-post-target-tokens", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--warmup-steps", type=int, default=200)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--eval-every", type=int, default=1)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--mamba-device", type=str, default="auto")
    parser.add_argument("--hyper-device", type=str, default="")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit Qwen loading.")
    parser.add_argument("--target-layers", type=str, default="", help="Comma-separated layer:proj specs.")
    parser.add_argument("--output-dir", type=str, default="bridge_train_runs")
    parser.add_argument("--save-eval-contexts", action="store_true")
    parser.add_argument("--save-checkpoints", action="store_true")
    parser.add_argument("--dry-run-steps", type=int, default=2)
    parser.add_argument("--dry-run-mamba-context-tokens", type=int, default=128)
    parser.add_argument("--dry-run-max-qwen-tokens", type=int, default=256)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    configure_logging(verbose=args.verbose)
    set_seed(args.seed)

    # TODO: cognitive_bridge.py inference still formats prompts as raw
    # [Game World] text. It should be migrated to the same ChatML-style prompt
    # distribution used here before comparing deployment behavior to training.

    LOGGER.info("Starting bridge training. dry_run=%s", args.dry_run)
    runtime = build_dry_run_runtime(args) if args.dry_run else build_real_runtime(args)
    train_loader, eval_loader, general_loader = build_dataloaders(args, runtime)

    trainable_params: List[nn.Parameter] = list(runtime.compressor.parameters()) + list(
        runtime.hypernetwork.parameters()
    )
    optimizer = AdamW(trainable_params, lr=args.lr, weight_decay=args.weight_decay)
    train_steps = args.dry_run_steps if args.dry_run else len(train_loader)
    total_steps = args.epochs * max(1, train_steps)
    scheduler = build_lr_scheduler(optimizer, warmup_steps=args.warmup_steps, total_steps=total_steps)

    output_dir = Path(args.output_dir)
    best_bridge_acc = -1.0
    best_checkpoint: Optional[str] = None

    for epoch_index in range(1, args.epochs + 1):
        epoch_start = time.time()
        train_stats = train_one_epoch(
            runtime=runtime,
            loader=train_loader,
            optimizer=optimizer,
            scheduler=scheduler,
            epoch_index=epoch_index,
            max_grad_norm=args.max_grad_norm,
            dry_run_steps=args.dry_run_steps,
        )

        LOGGER.info(
            "epoch=%d train_loss=%.5f lora_mean=%.5f lora_var=%.5f elapsed=%.2fs",
            epoch_index,
            train_stats["loss"],
            train_stats["lora_norm_mean"],
            train_stats["lora_norm_var"],
            time.time() - epoch_start,
        )

        if epoch_index % args.eval_every == 0:
            eval_results = evaluate_fact_accuracy(
                runtime=runtime,
                loader=eval_loader,
                bootstrap_resamples=args.bootstrap_resamples,
                seed=args.seed + epoch_index,
                epoch_index=epoch_index,
                output_dir=output_dir if args.save_eval_contexts else None,
                save_eval_contexts=args.save_eval_contexts,
                general_loader=general_loader,
            )

            LOGGER.info(
                "eval epoch=%d | %s | %s | %s | p=%.4g",
                epoch_index,
                format_accuracy_summary("Bridge", eval_results.bridge),
                format_accuracy_summary("Baseline", eval_results.baseline),
                format_accuracy_summary("Random", eval_results.random_control),
                eval_results.p_value_bridge_vs_baseline,
            )
            LOGGER.info(
                "eval epoch=%d | bridge_lora_norm=%.5f | random_lora_norm=%.5f",
                epoch_index,
                eval_results.bridge_lora_norm_mean,
                eval_results.random_lora_norm_mean,
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

            if args.save_checkpoints and eval_results.bridge.accuracy > best_bridge_acc:
                metrics = {
                    "train": train_stats,
                    "eval": {
                        "bridge_accuracy": eval_results.bridge.accuracy,
                        "baseline_accuracy": eval_results.baseline.accuracy,
                        "random_accuracy": eval_results.random_control.accuracy,
                        "p_value": eval_results.p_value_bridge_vs_baseline,
                        "bridge_lora_norm_mean": eval_results.bridge_lora_norm_mean,
                        "random_lora_norm_mean": eval_results.random_lora_norm_mean,
                        "general_ppl": eval_results.general_ppl,
                    },
                }
                best_checkpoint = save_checkpoint(
                    runtime=runtime,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    output_dir=output_dir,
                    epoch=epoch_index,
                    metrics=metrics,
                )
                best_bridge_acc = eval_results.bridge.accuracy
                LOGGER.info("Saved checkpoint: %s", best_checkpoint)

        if args.dry_run:
            LOGGER.info("Dry-run epoch complete. Gradient flow and eval loop verified.")

    final_summary = {
        "dry_run": args.dry_run,
        "epochs": args.epochs,
        "train_batches": len(train_loader),
        "eval_batches": len(eval_loader),
        "best_checkpoint": best_checkpoint,
    }
    LOGGER.info("Training finished: %s", json.dumps(final_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
