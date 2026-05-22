#!/usr/bin/env python3
"""
run_step5e_layer_sweep.py — Step 5e Layer Targeting Sweep

Tests whether disposition injection works better at different layer ranges,
with per-layer alpha gradients, or split across two injection zones.

Runs on laptop: Qwen2.5-1.5B on GPU (3060 6GB), Mamba-2.8B on CPU.

Sub-experiments:
  5e.1 Phase sweep: layers 5-8 vs 12-15 vs 20-23 at uniform alpha 0.2
  5e.2 Alpha gradient: front-loaded vs back-loaded vs peak-at-13
  5e.3 Double injection: split dose at two layer ranges simultaneously

All within the approved alpha 0.2 MED envelope.

Usage:
  # Full sweep (all sub-experiments):
  python run_step5e_layer_sweep.py

  # Single sub-experiment:
  python run_step5e_layer_sweep.py --experiments 5e.1

  # Custom bridge checkpoint:
  python run_step5e_layer_sweep.py --bridge-path my_bridge.pt

  # Via WSL on Laura's laptop:
  wsl -d Debian -u root -- /root/mamba_venv/bin/python -X utf8 \\
    /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_step5e_layer_sweep.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Optional

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

# Local imports — same workspace as step5d_bridge_recorder.py
from chat_server import (
    DEFAULT_BRIDGE,
    DEFAULT_EPISODES_FILE,
    DEFAULT_MAMBA,
    DEFAULT_MODEL_LABEL,
    DEFAULT_QWEN,
    DEFAULT_TARGET_SPECS,
    DEFAULT_USER_LABEL,
    extract_last_token_hidden,
    infer_hidden_layer_count,
    is_same_qwen_family,
    normalize_target_specs,
    read_episodes,
    validate_checkpoint_runtime_contract,
)
from mamba_runtime_compat import ensure_mamba_ssm_compat
from models import ActivationBiasHypernetwork, DynamicLoRALinear, MambaStateCompressor
from step5d_chat_client import INJECTION_PROMPTS, RECOVERY_PROMPTS
from step5d_bridge_recorder import (
    ActivationRecorder,
    apply_alpha,
    build_prompt,
    compute_drift,
    compute_response_diversity,
    generate_reply,
    record_neutral_snapshot,
    sanitize_response_text,
    summarize_phase,
)


# ═══════════════════════════════════════════════════════════════
# EXPERIMENT CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

@dataclass
class LayerConfig:
    """One experiment configuration: which layers, what alpha per layer."""
    name: str
    experiment: str
    layer_specs: list[tuple[int, str]]
    alphas: list[float]  # one alpha per layer_spec, same length
    description: str = ""
    context_mask_mode: str = "none"

    def mean_alpha(self) -> float:
        return mean(self.alphas) if self.alphas else 0.0


def build_experiment_grid() -> list[LayerConfig]:
    """Build the full 5e experiment grid from the ladder spec."""
    configs = []

    # ── 5e.0: Baseline (current production config) ──
    configs.append(LayerConfig(
        name="baseline_12-15_a0.2",
        experiment="5e.0",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.2, 0.2, 0.2, 0.2],
        description="Current production baseline: layers 12-15, uniform alpha 0.2",
    ))

    # ── 5e.1: Phase sweep — three different 4-layer zones ──
    configs.append(LayerConfig(
        name="reasoning_entry_5-8_a0.2",
        experiment="5e.1",
        layer_specs=[(5, "v_proj"), (6, "v_proj"), (7, "v_proj"), (8, "v_proj")],
        alphas=[0.2, 0.2, 0.2, 0.2],
        description="Reasoning entry zone: layers 5-8",
    ))
    configs.append(LayerConfig(
        name="mid_reasoning_12-15_a0.2",
        experiment="5e.1",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.2, 0.2, 0.2, 0.2],
        description="Mid-reasoning zone: layers 12-15 (same as baseline)",
    ))
    configs.append(LayerConfig(
        name="decoder_boundary_20-23_a0.2",
        experiment="5e.1",
        layer_specs=[(20, "v_proj"), (21, "v_proj"), (22, "v_proj"), (23, "v_proj")],
        alphas=[0.2, 0.2, 0.2, 0.2],
        description="Reasoning exit / decoder boundary: layers 20-23",
    ))

    # ── 5e.2: Per-layer alpha gradients (average ≤ 0.2) ──
    configs.append(LayerConfig(
        name="gradient_front_loaded",
        experiment="5e.2",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.3, 0.2, 0.1, 0.05],
        description="Front-loaded gradient: 0.3/0.2/0.1/0.05 (mean 0.1625)",
    ))
    configs.append(LayerConfig(
        name="gradient_back_loaded",
        experiment="5e.2",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.05, 0.1, 0.2, 0.3],
        description="Back-loaded gradient: 0.05/0.1/0.2/0.3 (mean 0.1625)",
    ))
    configs.append(LayerConfig(
        name="gradient_peak_13",
        experiment="5e.2",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.1, 0.3, 0.1, 0.1],
        description="Peak at layer 13 (sharpest separator per Cassian): 0.1/0.3/0.1/0.1 (mean 0.15)",
    ))

    # ── 5e.3: Double injection (split dose) ──
    configs.append(LayerConfig(
        name="split_dose_5-6_12-13",
        experiment="5e.3",
        layer_specs=[(5, "v_proj"), (6, "v_proj"), (12, "v_proj"), (13, "v_proj")],
        alphas=[0.1, 0.1, 0.1, 0.1],
        description="Split dose: reasoning entry (5-6) + mid (12-13), each at alpha 0.1",
    ))

    # ── 5e.0: No injection control ──
    configs.append(LayerConfig(
        name="no_injection_control",
        experiment="5e.0",
        layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
        alphas=[0.0, 0.0, 0.0, 0.0],
        description="Control: layers patched but alpha=0 everywhere",
    ))

    return configs


def build_mask_ablation_configs(mask_modes: list[str]) -> list[LayerConfig]:
    """Build targeted 12-15 / alpha 0.2 mask-ablation configs.

    These are intentionally narrow: the research question is whether masking
    the previously identified persistent / variable Mamba Layer 3 dimensions
    changes the known `12-15 @ alpha 0.2` behavioral profile.
    """
    configs = [
        LayerConfig(
            name="mask_none_12-15_a0.2",
            experiment="5e.mask",
            layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
            alphas=[0.2, 0.2, 0.2, 0.2],
            description="Mask-ablation control: unmasked Mamba Layer 3 state, layers 12-15 at alpha 0.2",
            context_mask_mode="none",
        )
    ]

    descriptions = {
        "persistent_zero": "Zero persistent 640 Mamba Layer 3 dims before compression",
        "variable_zero": "Zero variable 640 Mamba Layer 3 dims before compression",
        "middle_zero": "Zero middle 1280 Mamba Layer 3 dims before compression",
    }
    valid_modes = {"none", "persistent_zero", "variable_zero", "middle_zero"}
    for mask_mode in mask_modes:
        if mask_mode not in valid_modes:
            raise ValueError(
                f"Unsupported mask mode {mask_mode!r}. Valid options: {sorted(valid_modes)}"
            )
        if mask_mode == "none":
            continue
        configs.append(
            LayerConfig(
                name=f"mask_{mask_mode}_12-15_a0.2",
                experiment="5e.mask",
                layer_specs=[(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")],
                alphas=[0.2, 0.2, 0.2, 0.2],
                description=descriptions.get(mask_mode, f"Mask mode: {mask_mode}"),
                context_mask_mode=mask_mode,
            )
        )

    return configs


def load_state_mask_library(report_path: str, expected_d_model: int) -> dict[str, list[int]]:
    """Load persistent/variable/middle dim indices from a subnetwork report."""
    path = Path(report_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    data = json.loads(path.read_text(encoding="utf-8"))
    subnetworks = data.get("subnetworks", {})
    d_model = int(subnetworks.get("d_model", expected_d_model))
    if d_model != expected_d_model:
        raise ValueError(
            f"Mask report d_model={d_model} does not match expected {expected_d_model}."
        )

    mask_library = {
        "none": [],
        "persistent_zero": [int(v) for v in subnetworks.get("persistent_dims", [])],
        "variable_zero": [int(v) for v in subnetworks.get("variable_dims", [])],
        "middle_zero": [int(v) for v in subnetworks.get("middle_dims", [])],
    }
    for mode, dims in mask_library.items():
        for dim in dims:
            if dim < 0 or dim >= expected_d_model:
                raise ValueError(f"Mask dim {dim} in mode {mode} is outside width {expected_d_model}.")
    return mask_library


def mask_last_token_state(
    last_token: torch.Tensor,
    dims: list[int],
) -> torch.Tensor:
    """Return a cloned last-token state with the selected dimensions zeroed."""
    if not dims:
        return last_token.clone()
    masked = last_token.clone()
    masked[..., dims] = 0.0
    return masked


def summarize_mask_effect(
    last_token: torch.Tensor,
    masked_last_token: torch.Tensor,
    dims: list[int],
    report_path: Optional[str],
) -> dict[str, Any]:
    """Summarize how much raw Mamba-state mass was removed by the mask."""
    raw_norm_before = float(last_token.norm().item())
    raw_norm_after = float(masked_last_token.norm().item())
    raw_norm_delta = raw_norm_before - raw_norm_after
    raw_norm_ratio = (raw_norm_after / raw_norm_before) if raw_norm_before > 0 else 0.0

    raw_energy_total = float(last_token.pow(2).sum().item())
    if dims:
        removed_energy = float(last_token[..., dims].pow(2).sum().item())
    else:
        removed_energy = 0.0
    removed_energy_fraction = (removed_energy / raw_energy_total) if raw_energy_total > 0 else 0.0

    return {
        "masked_dim_count": len(dims),
        "masked_dim_fraction": round(len(dims) / int(last_token.shape[-1]), 6),
        "mask_report": report_path if dims else None,
        "raw_state_norm_before": round(raw_norm_before, 6),
        "raw_state_norm_after": round(raw_norm_after, 6),
        "raw_state_norm_delta": round(raw_norm_delta, 6),
        "raw_state_norm_ratio": round(raw_norm_ratio, 6),
        "removed_energy_fraction": round(removed_energy_fraction, 6),
    }


# ═══════════════════════════════════════════════════════════════
# PER-LAYER ALPHA APPLICATION
# ═══════════════════════════════════════════════════════════════

def apply_per_layer_alpha(
    patched_layers: list[DynamicLoRALinear],
    bias_vectors: list[torch.Tensor],
    alphas: list[float],
    device: str,
):
    """Apply different alpha values to different layers."""
    for patched, bias, alpha in zip(patched_layers, bias_vectors, alphas):
        scaled_bias = alpha * bias.squeeze(0).to(device, dtype=torch.float32)
        patched.set_activation_bias(scaled_bias)


# ═══════════════════════════════════════════════════════════════
# CORE SWEEP RUNNER
# ═══════════════════════════════════════════════════════════════

def run_single_config(
    config: LayerConfig,
    *,
    qwen_model,
    qwen_tokenizer,
    context: torch.Tensor,
    context_mask_metadata: dict[str, Any],
    ckpt_hypernet_state: dict[str, torch.Tensor],
    qwen_device: str,
    max_new_tokens: int,
    temperature: float,
    user_label: str,
    model_label: str,
    neutral_prompt: str,
    run_dir: Path,
) -> dict[str, Any]:
    """Run one layer configuration: patch, inject, eval, unpatch, return results."""
    print(f"\n{'='*60}")
    print(f"Config: {config.name}")
    print(f"  Experiment: {config.experiment}")
    print(f"  Layers: {config.layer_specs}")
    print(f"  Alphas: {config.alphas}")
    print(f"  Mean alpha: {config.mean_alpha():.4f}")
    print(f"  Context mask: {config.context_mask_mode}")
    print(f"  {config.description}")
    print(f"{'='*60}")

    config_dir = run_dir / config.name
    config_dir.mkdir(parents=True, exist_ok=True)
    turn_log_path = config_dir / "turns.jsonl"

    # ── Patch layers for this config ──
    patched_layers: list[DynamicLoRALinear] = []
    original_layers: dict[tuple[int, str], Any] = {}
    recorder: Optional[ActivationRecorder] = None

    try:
        for spec in config.layer_specs:
            layer_idx, proj_name = spec
            decoder_layer = qwen_model.model.layers[layer_idx]
            original = getattr(decoder_layer.self_attn, proj_name)
            original_layers[spec] = original
            patched = DynamicLoRALinear(original)
            setattr(decoder_layer.self_attn, proj_name, patched)
            patched_layers.append(patched)

        # ── Build hypernetwork for THIS config's target dims ──
        target_dims = [(pl.in_features, pl.out_features) for pl in patched_layers]
        num_needed = len(target_dims)

        available_head_indices = sorted(
            {
                int(key.split(".")[1])
                for key in ckpt_hypernet_state
                if key.startswith("bias_heads.") and key.endswith(".weight")
            }
        )
        if num_needed > len(available_head_indices):
            raise ValueError(
                "Config requests more bias heads than the checkpoint provides: "
                f"need {num_needed}, checkpoint has {len(available_head_indices)} "
                f"({available_head_indices})."
            )

        hypernet = ActivationBiasHypernetwork(
            context_dim=context.shape[-1],
            target_dims=target_dims,
            hidden_dim=1024,
        ).to(qwen_device).float()

        # Load backbone from checkpoint (shared context mapping)
        backbone_keys = {k: v for k, v in ckpt_hypernet_state.items() if k.startswith("backbone.")}
        hypernet.load_state_dict(backbone_keys, strict=False)

        # Load bias heads by ordinal position. This is the core 5e override assumption:
        # head[0] -> config.layer_specs[0], head[1] -> config.layer_specs[1], etc.
        bias_head_mapping = []
        for mapped_idx, ckpt_head_idx in enumerate(available_head_indices[:num_needed]):
            head_keys = {
                k.replace(f"bias_heads.{ckpt_head_idx}.", ""): v
                for k, v in ckpt_hypernet_state.items()
                if k.startswith(f"bias_heads.{ckpt_head_idx}.")
            }
            if not head_keys:
                raise ValueError(f"Checkpoint bias head {ckpt_head_idx} is missing state.")
            hypernet.bias_heads[mapped_idx].load_state_dict(head_keys)
            layer_idx, proj_name = config.layer_specs[mapped_idx]
            bias_head_mapping.append(
                {
                    "checkpoint_head": ckpt_head_idx,
                    "mapped_position": mapped_idx,
                    "target_spec": f"{layer_idx}:{proj_name}",
                }
            )

        hypernet.eval()

        with torch.no_grad():
            bias_vectors = hypernet(context)

        # ── Set up activation recorder ──
        # Record from ALL layers we're targeting, plus the baseline layers for comparison
        record_layers = sorted(set(
            [spec[0] for spec in config.layer_specs] + [12, 13, 14, 15]
        ))
        recorder = ActivationRecorder(qwen_model, record_layers)

        # ── Injection phase ──
        print(f"  Injection phase ({len(INJECTION_PROMPTS)} prompts)...")
        apply_per_layer_alpha(patched_layers, bias_vectors, config.alphas, qwen_device)

        conversation: list[dict[str, str]] = []
        injection_turns: list[dict[str, Any]] = []
        transcript_lines: list[str] = []

        neutral_ids = qwen_tokenizer(neutral_prompt, return_tensors="pt").input_ids.to(qwen_device)
        with torch.no_grad():
            qwen_model(input_ids=neutral_ids)
        initial_snapshot = recorder.get_snapshot()
        previous_snapshot = initial_snapshot

        for turn_idx, prompt in enumerate(INJECTION_PROMPTS, start=1):
            conversation.append({"speaker": user_label, "text": prompt})
            prompt_text = build_prompt(conversation, user_label, model_label)
            input_ids = qwen_tokenizer(prompt_text, return_tensors="pt").input_ids.to(qwen_device)

            diversity = compute_response_diversity(qwen_model, input_ids, qwen_device)

            started = time.time()
            raw_response, response = generate_reply(
                model=qwen_model, tokenizer=qwen_tokenizer, prompt=prompt_text,
                device=qwen_device, max_new_tokens=max_new_tokens, temperature=temperature,
            )
            response = sanitize_response_text(response or raw_response, user_label, model_label) or "..."
            gen_time = time.time() - started

            post_snapshot = recorder.get_snapshot()
            drift_from_initial = compute_drift(initial_snapshot, post_snapshot)
            drift_from_previous = compute_drift(previous_snapshot, post_snapshot)
            previous_snapshot = post_snapshot

            conversation.append({"speaker": model_label, "text": response})
            transcript_lines.append(f"{user_label}: {prompt}")
            transcript_lines.append(f"{model_label}: {response}")

            turn_row = {
                "turn": turn_idx, "phase": "injection",
                "user": prompt, "response": response,
                "generation_time_s": round(gen_time, 3),
                "response_diversity": diversity,
                "drift_from_initial": drift_from_initial,
                "drift_from_previous": drift_from_previous,
                "drift_from_phase_initial": drift_from_initial,
                "avg_drift_from_phase_initial": round(mean(drift_from_initial.values()), 6) if drift_from_initial else 0.0,
                "avg_drift_initial": round(mean(drift_from_initial.values()), 6) if drift_from_initial else 0.0,
            }
            injection_turns.append(turn_row)
            with turn_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(turn_row, ensure_ascii=False) + "\n")

        # ── Recovery phase ──
        print(f"  Recovery phase ({len(RECOVERY_PROMPTS)} prompts)...")
        apply_per_layer_alpha(patched_layers, bias_vectors, [0.0] * len(config.alphas), qwen_device)

        recovery_turns: list[dict[str, Any]] = []
        recovery_initial = recorder.get_snapshot()

        for turn_idx, prompt in enumerate(RECOVERY_PROMPTS, start=1):
            conversation.append({"speaker": user_label, "text": prompt})
            prompt_text = build_prompt(conversation, user_label, model_label)
            input_ids = qwen_tokenizer(prompt_text, return_tensors="pt").input_ids.to(qwen_device)

            diversity = compute_response_diversity(qwen_model, input_ids, qwen_device)

            started = time.time()
            raw_response, response = generate_reply(
                model=qwen_model, tokenizer=qwen_tokenizer, prompt=prompt_text,
                device=qwen_device, max_new_tokens=max_new_tokens, temperature=temperature,
            )
            response = sanitize_response_text(response or raw_response, user_label, model_label) or "..."
            gen_time = time.time() - started

            post_snapshot = recorder.get_snapshot()
            drift_from_recovery = compute_drift(recovery_initial, post_snapshot)

            conversation.append({"speaker": model_label, "text": response})
            transcript_lines.append(f"{user_label}: {prompt}")
            transcript_lines.append(f"{model_label}: {response}")

            turn_row = {
                "turn": turn_idx, "phase": "recovery",
                "user": prompt, "response": response,
                "generation_time_s": round(gen_time, 3),
                "response_diversity": diversity,
                "drift_from_recovery_initial": drift_from_recovery,
                "drift_from_phase_initial": drift_from_recovery,
                "avg_drift_from_phase_initial": round(mean(drift_from_recovery.values()), 6) if drift_from_recovery else 0.0,
            }
            recovery_turns.append(turn_row)
            with turn_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(turn_row, ensure_ascii=False) + "\n")

        # ── Save transcript ──
        (config_dir / "transcript.txt").write_text("\n".join(transcript_lines), encoding="utf-8")

        # ── Build result ──
        result = {
            "config_name": config.name,
            "experiment": config.experiment,
            "description": config.description,
            "layer_specs": [f"{l}:{p}" for l, p in config.layer_specs],
            "alphas": config.alphas,
            "mean_alpha": round(config.mean_alpha(), 4),
            "context_mask_mode": config.context_mask_mode,
            "masked_dim_count": int(context_mask_metadata.get("masked_dim_count", 0)),
            "masked_dim_fraction": float(context_mask_metadata.get("masked_dim_fraction", 0.0)),
            "mask_report": context_mask_metadata.get("mask_report"),
            "raw_state_norm_before": context_mask_metadata.get("raw_state_norm_before"),
            "raw_state_norm_after": context_mask_metadata.get("raw_state_norm_after"),
            "raw_state_norm_delta": context_mask_metadata.get("raw_state_norm_delta"),
            "raw_state_norm_ratio": context_mask_metadata.get("raw_state_norm_ratio"),
            "removed_energy_fraction": context_mask_metadata.get("removed_energy_fraction"),
            "checkpoint_head_reuse_mode": "ordinal_remap",
            "checkpoint_bias_head_indices": available_head_indices,
            "bias_head_mapping": bias_head_mapping,
            "injection_summary": summarize_phase(injection_turns),
            "recovery_summary": summarize_phase(recovery_turns),
            "injection_turns": injection_turns,
            "recovery_turns": recovery_turns,
        }

        (config_dir / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Print summary line
        inj = result["injection_summary"]
        rec = result["recovery_summary"]
        print(f"  => entropy: {inj.get('entropy_mean', '?')} (inj) / {rec.get('entropy_mean', '?')} (rec)")
        print(f"     drift:   {inj.get('avg_drift_mean', '?')} (inj)")
        print(f"     gen time: {inj.get('generation_time_mean_s', '?')}s avg")
        print(
            "     raw state norm:"
            f" {result.get('raw_state_norm_before', '?')} -> {result.get('raw_state_norm_after', '?')}"
            f" (ratio {result.get('raw_state_norm_ratio', '?')}, removed energy {result.get('removed_energy_fraction', '?')})"
        )

        return result
    finally:
        if recorder is not None:
            recorder.cleanup()
        for spec, original in original_layers.items():
            layer_idx, proj_name = spec
            decoder_layer = qwen_model.model.layers[layer_idx]
            setattr(decoder_layer.self_attn, proj_name, original)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Step 5e Layer Targeting Sweep")
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--qwen-model-id", default=DEFAULT_QWEN)
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--user-label", default=DEFAULT_USER_LABEL)
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--neutral-prompt", default="The weather today is")
    parser.add_argument("--output-dir", default="step5e_runs")
    parser.add_argument(
        "--append-mask-ablation",
        action="store_true",
        help="Append targeted mask-ablation configs for the 12-15 @ alpha 0.2 profile.",
    )
    parser.add_argument(
        "--mask-report",
        default="persistent_subnetwork_results/persistent_subnetwork_report.json",
        help="Persistent-subnetwork report used to load persistent/variable/middle dim indices.",
    )
    parser.add_argument(
        "--mask-modes",
        nargs="*",
        default=["persistent_zero", "variable_zero"],
        help="Mask modes to add when --append-mask-ablation is set. Options: persistent_zero variable_zero middle_zero none",
    )
    parser.add_argument(
        "--experiments",
        nargs="*",
        default=None,
        help="Filter: e.g. '5e.1 5e.2' to run only those sub-experiments. Default: all.",
    )
    args = parser.parse_args()

    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = Path(__file__).resolve().parent / output_root
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"sweep_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── Build experiment grid ──
    all_configs = build_experiment_grid()
    if args.append_mask_ablation:
        all_configs.extend(build_mask_ablation_configs(args.mask_modes))
    if args.experiments:
        configs = [c for c in all_configs if c.experiment in args.experiments]
        print(f"Filtered to {len(configs)} configs for experiments: {args.experiments}")
    else:
        configs = all_configs
        print(f"Running full sweep: {len(configs)} configurations")

    # ── Load checkpoint ──
    print(f"\nLoading bridge checkpoint: {args.bridge_path}")
    ckpt_path = args.bridge_path
    if not Path(ckpt_path).is_absolute():
        ckpt_path = str(Path(__file__).resolve().parent / ckpt_path)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    validate_checkpoint_runtime_contract(ckpt, caller="run_step5e_layer_sweep")

    checkpoint_qwen = ckpt.get("qwen_model_id", DEFAULT_QWEN)
    if args.qwen_model_id != checkpoint_qwen and not is_same_qwen_family(args.qwen_model_id, checkpoint_qwen):
        print(f"WARNING: checkpoint trained on {checkpoint_qwen}, running on {args.qwen_model_id}")

    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    context_dim = int(ckpt.get("context_dim", ckpt.get("bridge_config", {}).get("context_dim", 2048)))
    ckpt_hypernet_state = ckpt.get("hypernetwork_state_dict", {})

    # ── Load Qwen ──
    qwen_dtype = torch.float16 if "cuda" in args.qwen_device else torch.float32
    print(f"Loading Qwen: {args.qwen_model_id} ({qwen_dtype}) -> {args.qwen_device}")
    tokenizer = AutoTokenizer.from_pretrained(args.qwen_model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    qwen_model = AutoModelForCausalLM.from_pretrained(
        args.qwen_model_id, torch_dtype=qwen_dtype, device_map=args.qwen_device,
    )
    qwen_model.eval()
    num_layers = len(qwen_model.model.layers)
    print(f"  Qwen has {num_layers} decoder layers")

    # Validate all configs against actual model
    for cfg in configs:
        for layer_idx, proj_name in cfg.layer_specs:
            if layer_idx >= num_layers:
                print(f"ERROR: config '{cfg.name}' targets layer {layer_idx} but model only has {num_layers} layers")
                return 1

    # ── Load Mamba ──
    print(f"Loading Mamba: {args.mamba_model_id} -> {args.mamba_device}")
    ensure_mamba_ssm_compat()
    from transformers import MambaForCausalLM
    mamba_tokenizer = AutoTokenizer.from_pretrained(args.mamba_model_id)
    mamba_model = MambaForCausalLM.from_pretrained(args.mamba_model_id, torch_dtype=torch.float32)
    mamba_model.to(args.mamba_device)
    mamba_model.eval()
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    # ── Load compressor ──
    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=context_dim,
        target_layer=mamba_target_layer,
    ).to(args.qwen_device).float()
    if "compressor_state_dict" in ckpt:
        compressor.load_state_dict(ckpt["compressor_state_dict"])
    compressor.eval()

    # ── Load episodes ──
    episodes_path = args.episodes_file
    if not Path(episodes_path).is_absolute():
        episodes_path = str(Path(__file__).resolve().parent / episodes_path)
    episodes = read_episodes(episodes_path)
    episode = episodes[args.episode_index]
    print(f"Episode: {episode['title']}")

    # ── Precompute episode context once per sweep ──
    print("Computing episode context once for all configs...")
    episode_tokens = mamba_tokenizer(
        episode["text"],
        return_tensors="pt",
        truncation=True,
        max_length=args.max_mamba_tokens,
    )
    episode_tokens = {k: v.to(args.mamba_device) for k, v in episode_tokens.items()}
    with torch.no_grad():
        mamba_out = mamba_model(**episode_tokens, output_hidden_states=True)
        last_token = extract_last_token_hidden(
            mamba_out, mamba_target_layer, hidden_layer_count,
        ).to(args.qwen_device, dtype=torch.float32)

    mask_library = {"none": []}
    if any(cfg.context_mask_mode != "none" for cfg in configs):
        print(f"Loading state-mask report: {args.mask_report}")
        mask_library = load_state_mask_library(args.mask_report, expected_d_model=int(last_token.shape[-1]))

    context_cache: dict[str, torch.Tensor] = {}
    mask_metadata: dict[str, dict[str, Any]] = {}
    for mask_mode, dims in mask_library.items():
        if any(cfg.context_mask_mode == mask_mode for cfg in configs):
            with torch.no_grad():
                masked_last_token = mask_last_token_state(last_token, dims)
                context_cache[mask_mode] = compressor(masked_last_token)
            mask_metadata[mask_mode] = summarize_mask_effect(
                last_token=last_token,
                masked_last_token=masked_last_token,
                dims=dims,
                report_path=args.mask_report,
            )
            print(
                f"  Mask {mask_mode}: norm {mask_metadata[mask_mode]['raw_state_norm_before']}"
                f" -> {mask_metadata[mask_mode]['raw_state_norm_after']}"
                f" (ratio {mask_metadata[mask_mode]['raw_state_norm_ratio']},"
                f" removed energy {mask_metadata[mask_mode]['removed_energy_fraction']})"
            )

    # ── Run sweep ──
    all_results = []
    sweep_start = time.time()

    for i, config in enumerate(configs, start=1):
        print(f"\n[{i}/{len(configs)}]", end="")
        result = run_single_config(
            config,
            qwen_model=qwen_model,
            qwen_tokenizer=tokenizer,
            context=context_cache.get(config.context_mask_mode, context_cache.get("none")),
            context_mask_metadata=mask_metadata.get(config.context_mask_mode, {}),
            ckpt_hypernet_state=ckpt_hypernet_state,
            qwen_device=args.qwen_device,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            user_label=args.user_label,
            model_label=args.model_label,
            neutral_prompt=args.neutral_prompt,
            run_dir=run_dir,
        )
        all_results.append(result)

    sweep_time = time.time() - sweep_start

    # ── Comparison table ──
    print(f"\n\n{'='*80}")
    print(f"STEP 5e SWEEP RESULTS — {len(all_results)} configurations in {sweep_time:.0f}s")
    print(f"{'='*80}")
    print(f"{'Config':<35} {'Exp':<6} {'Mean α':<8} {'Entropy':<10} {'Drift':<10} {'EV':<8}")
    print(f"{'-'*35} {'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

    for r in all_results:
        inj = r["injection_summary"]
        name = r["config_name"][:34]
        exp = r["experiment"]
        ma = f"{r['mean_alpha']:.3f}"
        ent = f"{inj.get('entropy_mean', 'N/A')}"
        drift = f"{inj.get('avg_drift_mean', 'N/A')}"
        ev = f"{inj.get('effective_vocab_mean', 'N/A')}"
        print(f"{name:<35} {exp:<6} {ma:<8} {ent:<10} {drift:<10} {ev:<8}")

    # ── Save master summary ──
    master_summary = {
        "timestamp": timestamp,
        "sweep_time_s": round(sweep_time, 1),
        "qwen_model_id": args.qwen_model_id,
        "mamba_model_id": args.mamba_model_id,
        "episode_index": args.episode_index,
        "episode_title": episode["title"],
        "bridge_path": args.bridge_path,
        "num_configs": len(all_results),
        "comparison": [
            {
                "config": r["config_name"],
                "experiment": r["experiment"],
                "layers": r["layer_specs"],
                "alphas": r["alphas"],
                "mean_alpha": r["mean_alpha"],
                "context_mask_mode": r.get("context_mask_mode", "none"),
                "masked_dim_count": r.get("masked_dim_count", 0),
                "masked_dim_fraction": r.get("masked_dim_fraction", 0.0),
                "raw_state_norm_before": r.get("raw_state_norm_before"),
                "raw_state_norm_after": r.get("raw_state_norm_after"),
                "raw_state_norm_delta": r.get("raw_state_norm_delta"),
                "raw_state_norm_ratio": r.get("raw_state_norm_ratio"),
                "removed_energy_fraction": r.get("removed_energy_fraction"),
                "entropy_mean": r["injection_summary"].get("entropy_mean"),
                "drift_mean": r["injection_summary"].get("avg_drift_mean"),
                "effective_vocab_mean": r["injection_summary"].get("effective_vocab_mean"),
                "recovery_entropy_mean": r["recovery_summary"].get("entropy_mean"),
            }
            for r in all_results
        ],
    }

    summary_path = run_dir / "sweep_summary.json"
    summary_path.write_text(json.dumps(master_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to: {run_dir}")
    print(f"Summary: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
