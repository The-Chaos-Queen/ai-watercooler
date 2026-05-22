#!/usr/bin/env python3
"""
trajectory_state_spaces_probe.py

Option B probe: evaluate original state-spaces/mamba tokenwise inference-cache
route against Hugging Face references on the same fixture.

This script does NOT patch CUDA kernels and does NOT modify selective_scan APIs.
"""

import argparse
import importlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def parse_claude_json(filepath: str, conv_index: int) -> Tuple[List[dict], str, str]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    conv = data[conv_index]
    turns = []
    for msg in conv.get("chat_messages", []):
        sender = msg.get("sender", "unknown")
        role = "User" if sender == "human" else "Assistant"
        text = "".join(
            p.get("text", "") for p in msg.get("content", []) if p.get("type") == "text"
        ).strip()
        if text:
            turns.append({"role": role, "text": text})
    return turns, conv.get("name", ""), conv.get("created_at", "")


def parse_markdown_conversation(filepath: str) -> List[dict]:
    text = Path(filepath).read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    turns = []
    current_role = None
    current_lines: List[str] = []
    for line in lines:
        match = re.match(r"^##\s+(.+)$", line.strip())
        if match:
            if current_role is not None:
                turn_text = "\n".join(current_lines).strip()
                if turn_text:
                    turns.append({"role": current_role, "text": turn_text})
            current_role = match.group(1).strip()
            current_lines = []
        elif re.match(r"^---\s*$", line.strip()):
            continue
        elif line.startswith("# ") and not line.startswith("## "):
            continue
        else:
            if current_role is not None:
                current_lines.append(line)
    if current_role is not None:
        turn_text = "\n".join(current_lines).strip()
        if turn_text:
            turns.append({"role": current_role, "text": turn_text})
    return turns


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_turn_lines(turns: List[dict]) -> List[str]:
    return [f"{t['role']}: {t['text']}" for t in turns]


def build_full_text(turn_lines: List[str]) -> str:
    return "\n".join(turn_lines)


def compute_sample_message_indices(num_turns: int, sample_every: int) -> List[int]:
    indices = list(range(sample_every, num_turns + 1, sample_every))
    if indices and indices[-1] != num_turns:
        indices.append(num_turns)
    if not indices:
        indices = [num_turns]
    return indices


def compute_boundaries_by_turn_tokenization(tokenizer, turn_lines: List[str]) -> List[int]:
    boundaries = []
    cumulative_tokens = 0
    for i, line in enumerate(turn_lines):
        text = line if i == len(turn_lines) - 1 else line + "\n"
        token_ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        cumulative_tokens += len(token_ids)
        boundaries.append(max(0, cumulative_tokens - 1))
    return boundaries


def inspect_mamba_fast_path() -> dict:
    checks = {
        "selective_state_update": False,
        "selective_scan_fn": False,
        "causal_conv1d_fn": False,
        "causal_conv1d_update": False,
        "mamba_inner_fn": False,
    }
    errors = {}
    try:
        module = importlib.import_module("mamba_ssm.ops.triton.selective_state_update")
        checks["selective_state_update"] = (
            getattr(module, "selective_state_update", None) is not None
        )
    except Exception as exc:
        errors["selective_state_update"] = repr(exc)
    try:
        module = importlib.import_module("mamba_ssm.ops.selective_scan_interface")
        checks["selective_scan_fn"] = getattr(module, "selective_scan_fn", None) is not None
        checks["mamba_inner_fn"] = getattr(module, "mamba_inner_fn", None) is not None
    except Exception as exc:
        errors["selective_scan_interface"] = repr(exc)
    try:
        module = importlib.import_module("causal_conv1d")
        checks["causal_conv1d_fn"] = getattr(module, "causal_conv1d_fn", None) is not None
        checks["causal_conv1d_update"] = (
            getattr(module, "causal_conv1d_update", None) is not None
        )
    except Exception as exc:
        errors["causal_conv1d"] = repr(exc)
    return {"all_available": all(checks.values()), "checks": checks, "errors": errors}


def find_hf_mamba_layers(model):
    candidates = [
        ("backbone", "layers"),
        ("model", "layers"),
        ("model", "backbone", "layers"),
    ]
    for chain in candidates:
        obj = model
        ok = True
        for part in chain:
            if not hasattr(obj, part):
                ok = False
                break
            obj = getattr(obj, part)
        if ok and obj is not None and len(obj) > 0:
            return obj
    raise RuntimeError("Could not locate HF Mamba layer stack on model object.")


class LayerCaptureHook:
    def __init__(self, module):
        self.output_tensor = None
        self.handle = module.register_forward_hook(self._hook)

    def _hook(self, _module, _inputs, output):
        tensor = output[0] if isinstance(output, tuple) else output
        if not hasattr(tensor, "detach"):
            raise RuntimeError(f"Unexpected layer hook output type: {type(output)}")
        self.output_tensor = tensor.detach()

    def clear(self):
        self.output_tensor = None

    def remove(self):
        self.handle.remove()


def _extract_hidden_indexed_vector(hidden_tensor, token_index: int) -> np.ndarray:
    vec = hidden_tensor[0, token_index, :].detach().float().cpu().numpy().reshape(-1)
    return vec


def _get_peak_vram_bytes(device: str):
    import torch

    if "cuda" not in device:
        return None
    return int(torch.cuda.max_memory_allocated())


@dataclass
class EngineResult:
    states: np.ndarray
    sample_metadata: List[dict]
    elapsed_seconds: float
    tokens_per_second: float
    peak_vram_bytes: Optional[int]
    engine: str


def run_original_references(
    *,
    model_id: str,
    input_ids,
    sample_msg_indices: List[int],
    msg_to_token: Dict[int, int],
    msg_to_turn: Dict[int, dict],
    target_layer: int,
    device: str,
    dtype,
) -> EngineResult:
    import torch
    from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel
    from mamba_ssm.utils.generation import InferenceParams

    print(f"[original] loading model: {model_id}")
    model = MambaLMHeadModel.from_pretrained(model_id, device=device, dtype=dtype)
    model.eval()
    if target_layer < 0 or target_layer >= len(model.backbone.layers):
        raise ValueError(
            f"target_layer={target_layer} out of range for original model with "
            f"{len(model.backbone.layers)} layers"
        )

    hook = LayerCaptureHook(model.backbone.layers[target_layer])
    one_pass_states = None
    one_pass_meta: List[dict] = []
    sample_token_to_msg = {msg_to_token[m]: m for m in sample_msg_indices}
    states_by_msg: Dict[int, np.ndarray] = {}
    meta: List[dict] = []

    try:
        if "cuda" in device:
            torch.cuda.reset_peak_memory_stats()
        t0_one_pass = time.time()
        with torch.no_grad():
            _ = model(input_ids)
        hidden = hook.output_tensor
        if hidden is None:
            raise RuntimeError("Original one-pass hook did not capture hidden output.")
        one_pass_states = np.stack(
            [_extract_hidden_indexed_vector(hidden, msg_to_token[m]) for m in sample_msg_indices],
            axis=0,
        )
        for m in sample_msg_indices:
            one_pass_meta.append(
                {
                    "msg_idx": m,
                    "token_pos": msg_to_token[m],
                    "role": msg_to_turn[m]["role"],
                    "preview": msg_to_turn[m]["text"][:80].replace("\n", " "),
                }
            )
        one_pass_elapsed = time.time() - t0_one_pass
        one_pass_peak = _get_peak_vram_bytes(device)

        if "cuda" in device:
            torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        inference_params = InferenceParams(
            max_seqlen=int(input_ids.shape[1]),
            max_batch_size=int(input_ids.shape[0]),
        )
        for token_pos in range(int(input_ids.shape[1])):
            step = input_ids[:, token_pos : token_pos + 1]
            hook.clear()
            with torch.no_grad():
                _ = model(step, inference_params=inference_params, num_last_tokens=1)
            inference_params.seqlen_offset += int(step.shape[1])
            hidden = hook.output_tensor
            if hidden is None:
                raise RuntimeError(
                    f"Original tokenwise hook did not capture hidden output at token {token_pos}."
                )
            if token_pos in sample_token_to_msg:
                msg_idx = sample_token_to_msg[token_pos]
                state = _extract_hidden_indexed_vector(hidden, hidden.shape[1] - 1)
                states_by_msg[msg_idx] = state
    finally:
        hook.remove()

    elapsed = time.time() - t0
    missing = [m for m in sample_msg_indices if m not in states_by_msg]
    if missing:
        raise RuntimeError(f"Original tokenwise reference missing sample messages: {missing}")

    for m in sample_msg_indices:
        meta.append(
            {
                "msg_idx": m,
                "token_pos": msg_to_token[m],
                "role": msg_to_turn[m]["role"],
                "preview": msg_to_turn[m]["text"][:80].replace("\n", " "),
            }
        )
    states = np.stack([states_by_msg[m] for m in sample_msg_indices], axis=0)
    total_tokens = int(input_ids.shape[1])
    one_pass_tps = float(total_tokens / max(one_pass_elapsed, 1e-6))
    tps = float(total_tokens / max(elapsed, 1e-6))
    peak = _get_peak_vram_bytes(device)

    del model
    if "cuda" in device:
        torch.cuda.empty_cache()

    return (
        EngineResult(
            states=one_pass_states,
            sample_metadata=one_pass_meta,
            elapsed_seconds=float(one_pass_elapsed),
            tokens_per_second=one_pass_tps,
            peak_vram_bytes=one_pass_peak,
            engine="original_state_spaces_one_pass_reference",
        ),
        EngineResult(
            states=states,
            sample_metadata=meta,
            elapsed_seconds=float(elapsed),
            tokens_per_second=tps,
            peak_vram_bytes=peak,
            engine="original_state_spaces_tokenwise",
        ),
    )


def run_hf_one_pass_reference(
    *,
    model,
    input_ids,
    sample_msg_indices: List[int],
    msg_to_token: Dict[int, int],
    msg_to_turn: Dict[int, dict],
    target_layer: int,
    device: str,
) -> EngineResult:
    import torch

    layers = find_hf_mamba_layers(model)
    if target_layer < 0 or target_layer >= len(layers):
        raise ValueError(
            f"target_layer={target_layer} out of range for HF model with {len(layers)} layers"
        )
    hook = LayerCaptureHook(layers[target_layer])
    if "cuda" in device:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    try:
        with torch.no_grad():
            _ = model(input_ids, use_cache=False)
        hidden = hook.output_tensor
        if hidden is None:
            raise RuntimeError("HF one-pass hook did not capture hidden output.")
        states = []
        meta = []
        for msg_idx in sample_msg_indices:
            token_pos = msg_to_token[msg_idx]
            states.append(_extract_hidden_indexed_vector(hidden, token_pos))
            meta.append(
                {
                    "msg_idx": msg_idx,
                    "token_pos": token_pos,
                    "role": msg_to_turn[msg_idx]["role"],
                    "preview": msg_to_turn[msg_idx]["text"][:80].replace("\n", " "),
                }
            )
    finally:
        hook.remove()

    elapsed = time.time() - t0
    total_tokens = int(input_ids.shape[1])
    tps = float(total_tokens / max(elapsed, 1e-6))
    peak = _get_peak_vram_bytes(device)
    return EngineResult(
        states=np.stack(states, axis=0),
        sample_metadata=meta,
        elapsed_seconds=float(elapsed),
        tokens_per_second=tps,
        peak_vram_bytes=peak,
        engine="hf_one_pass_reference",
    )


def run_hf_tokenwise_reference(
    *,
    model,
    input_ids,
    sample_msg_indices: List[int],
    msg_to_token: Dict[int, int],
    msg_to_turn: Dict[int, dict],
    target_layer: int,
    device: str,
) -> EngineResult:
    import torch

    layers = find_hf_mamba_layers(model)
    if target_layer < 0 or target_layer >= len(layers):
        raise ValueError(
            f"target_layer={target_layer} out of range for HF model with {len(layers)} layers"
        )
    hook = LayerCaptureHook(layers[target_layer])
    sample_token_to_msg = {msg_to_token[m]: m for m in sample_msg_indices}
    states_by_msg: Dict[int, np.ndarray] = {}

    if "cuda" in device:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    cache = None
    try:
        for token_pos in range(int(input_ids.shape[1])):
            step = input_ids[:, token_pos : token_pos + 1]
            hook.clear()
            with torch.no_grad():
                kwargs = {"use_cache": True}
                if cache is not None:
                    kwargs["cache_params"] = cache
                    kwargs["cache_position"] = torch.tensor([token_pos], device=device)
                outputs = model(step, **kwargs)
            cache = outputs.cache_params
            hidden = hook.output_tensor
            if hidden is None:
                raise RuntimeError(
                    f"HF tokenwise hook did not capture hidden output at token {token_pos}."
                )
            if token_pos in sample_token_to_msg:
                msg_idx = sample_token_to_msg[token_pos]
                state = _extract_hidden_indexed_vector(hidden, hidden.shape[1] - 1)
                states_by_msg[msg_idx] = state
    finally:
        hook.remove()

    elapsed = time.time() - t0
    missing = [m for m in sample_msg_indices if m not in states_by_msg]
    if missing:
        raise RuntimeError(f"HF tokenwise reference missing sample messages: {missing}")

    states = np.stack([states_by_msg[m] for m in sample_msg_indices], axis=0)
    meta = [
        {
            "msg_idx": m,
            "token_pos": msg_to_token[m],
            "role": msg_to_turn[m]["role"],
            "preview": msg_to_turn[m]["text"][:80].replace("\n", " "),
        }
        for m in sample_msg_indices
    ]
    total_tokens = int(input_ids.shape[1])
    tps = float(total_tokens / max(elapsed, 1e-6))
    peak = _get_peak_vram_bytes(device)
    return EngineResult(
        states=states,
        sample_metadata=meta,
        elapsed_seconds=float(elapsed),
        tokens_per_second=tps,
        peak_vram_bytes=peak,
        engine="hf_tokenwise_reference",
    )


def compare_engines(
    *,
    source_name: str,
    a: EngineResult,
    b: EngineResult,
) -> dict:
    if a.states.shape != b.states.shape:
        raise ValueError(f"Shape mismatch for comparison: {a.states.shape} vs {b.states.shape}")
    per_sample_cos = [cosine(a.states[i], b.states[i]) for i in range(a.states.shape[0])]
    per_sample_l2 = [float(np.linalg.norm(a.states[i] - b.states[i])) for i in range(a.states.shape[0])]
    deltas_a = [1.0 - cosine(a.states[i], a.states[i - 1]) for i in range(1, a.states.shape[0])]
    deltas_b = [1.0 - cosine(b.states[i], b.states[i - 1]) for i in range(1, b.states.shape[0])]
    drift_l2 = (
        float(np.linalg.norm(np.asarray(deltas_a) - np.asarray(deltas_b)))
        if deltas_a and deltas_b
        else 0.0
    )
    return {
        "source": source_name,
        "a_engine": a.engine,
        "b_engine": b.engine,
        "num_samples": int(a.states.shape[0]),
        "per_sample_cosine": [float(v) for v in per_sample_cos],
        "per_sample_l2": [float(v) for v in per_sample_l2],
        "mean_cosine": float(np.mean(per_sample_cos)) if per_sample_cos else None,
        "min_cosine": float(min(per_sample_cos)) if per_sample_cos else None,
        "final_state_cosine": float(cosine(a.states[-1], b.states[-1])),
        "final_state_l2": float(np.linalg.norm(a.states[-1] - b.states[-1])),
        "trajectory_delta_l2": drift_l2,
        "a_tokens_per_second": a.tokens_per_second,
        "b_tokens_per_second": b.tokens_per_second,
        "a_peak_vram_bytes": a.peak_vram_bytes,
        "b_peak_vram_bytes": b.peak_vram_bytes,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Option B probe: original state-spaces/mamba tokenwise vs HF references."
    )
    parser.add_argument("--conversation", help="Markdown conversation file")
    parser.add_argument("--conversation-json", help="Claude JSON export file")
    parser.add_argument("--conv-index", type=int, default=0)
    parser.add_argument("--max-messages", type=int, default=0)
    parser.add_argument("--sample-every", type=int, default=1)
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", default="trajectory_option_b_probe")
    parser.add_argument("--hf-model-id", default="state-spaces/mamba-130m-hf")
    parser.add_argument("--original-model-id", default="state-spaces/mamba-130m")
    parser.add_argument("--exact-cosine-threshold", type=float, default=0.99999)
    parser.add_argument("--require-fast-path", action="store_true")
    parser.add_argument(
        "--sanity-fixture",
        default="MoCoP/experiments/mamba_lora_bridge/trajectory_sanity_tiny.md",
        help="Used only when --conversation and --conversation-json are omitted.",
    )
    args = parser.parse_args()

    if args.sample_every <= 0:
        print("Error: --sample-every must be > 0")
        return 1

    if args.conversation_json:
        turns, name, _created = parse_claude_json(args.conversation_json, args.conv_index)
        source = args.conversation_json
        label = name or f"conv_{args.conv_index}"
    else:
        source_path = args.conversation or args.sanity_fixture
        turns = parse_markdown_conversation(source_path)
        source = source_path
        label = Path(source_path).stem

    if args.max_messages > 0:
        turns = turns[: args.max_messages]
    if not turns:
        print("Error: parsed zero turns")
        return 1

    import torch
    from transformers import AutoTokenizer, MambaForCausalLM

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if "cuda" in device else torch.float32

    print("Engine label: OPTION_B_ORIGINAL_TOKENWISE_PROBE")
    print(f"Conversation: {label}")
    print(f"Source: {source}")
    print(f"Turns used: {len(turns)}")
    print(f"Device: {device}")
    print(f"Original model: {args.original_model_id}")
    print(f"HF model: {args.hf_model_id}")
    print(f"Target layer: {args.target_layer}")

    fast_path = inspect_mamba_fast_path()
    if fast_path["all_available"]:
        print("Mamba fast-path preflight: OK")
    else:
        missing = [name for name, ok in fast_path["checks"].items() if not ok]
        print(f"Mamba fast-path preflight: missing {', '.join(missing)}")
        for key, value in fast_path["errors"].items():
            print(f"  {key}: {value}")
        if args.require_fast_path:
            print("Error: --require-fast-path was set, refusing slow fallback.")
            return 2

    tokenizer = AutoTokenizer.from_pretrained(args.hf_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    turn_lines = build_turn_lines(turns)
    full_text = build_full_text(turn_lines)
    encoded = tokenizer(full_text, return_tensors="pt", add_special_tokens=False)
    input_ids = encoded["input_ids"].to(device)

    sample_msg_indices = compute_sample_message_indices(len(turns), args.sample_every)
    boundaries = compute_boundaries_by_turn_tokenization(tokenizer, turn_lines)
    msg_to_token = {i + 1: min(boundaries[i], int(input_ids.shape[1]) - 1) for i in range(len(boundaries))}
    msg_to_turn = {i + 1: turns[i] for i in range(len(turns))}

    original_one_pass, original = run_original_references(
        model_id=args.original_model_id,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        device=device,
        dtype=dtype,
    )

    print(f"[hf] loading model: {args.hf_model_id}")
    hf_model = MambaForCausalLM.from_pretrained(args.hf_model_id, torch_dtype=dtype)
    hf_model.to(device)
    hf_model.eval()
    hf_one_pass = run_hf_one_pass_reference(
        model=hf_model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        device=device,
    )
    hf_tokenwise = run_hf_tokenwise_reference(
        model=hf_model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        device=device,
    )

    comparisons = [
        compare_engines(source_name=label, a=original_one_pass, b=original),
        compare_engines(source_name=label, a=original, b=hf_one_pass),
        compare_engines(source_name=label, a=original, b=hf_tokenwise),
        compare_engines(source_name=label, a=hf_one_pass, b=hf_tokenwise),
    ]
    comparison_index = {f"{c['a_engine']}__vs__{c['b_engine']}": c for c in comparisons}
    key_original_self = "original_state_spaces_one_pass_reference__vs__original_state_spaces_tokenwise"
    key_vs_hf_tokenwise = "original_state_spaces_tokenwise__vs__hf_tokenwise_reference"
    orig_self = comparison_index[key_original_self]
    orig_vs_hf_tokenwise = comparison_index[key_vs_hf_tokenwise]
    original_self_passes = bool(orig_self["min_cosine"] >= args.exact_cosine_threshold)
    passes = bool(orig_vs_hf_tokenwise["min_cosine"] >= args.exact_cosine_threshold)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "option_b_original_tokenwise_probe",
        "method": "state_spaces_inference_params_step",
        "conversation_label": label,
        "source": source,
        "total_turns": len(turns),
        "total_tokens": int(input_ids.shape[1]),
        "sample_every": args.sample_every,
        "sample_points": len(sample_msg_indices),
        "target_layer": args.target_layer,
        "models": {
            "original_model_id": args.original_model_id,
            "hf_model_id": args.hf_model_id,
        },
        "engines": {
            original_one_pass.engine: {
                "elapsed_seconds": original_one_pass.elapsed_seconds,
                "tokens_per_second": original_one_pass.tokens_per_second,
                "peak_vram_bytes": original_one_pass.peak_vram_bytes,
            },
            original.engine: {
                "elapsed_seconds": original.elapsed_seconds,
                "tokens_per_second": original.tokens_per_second,
                "peak_vram_bytes": original.peak_vram_bytes,
            },
            hf_one_pass.engine: {
                "elapsed_seconds": hf_one_pass.elapsed_seconds,
                "tokens_per_second": hf_one_pass.tokens_per_second,
                "peak_vram_bytes": hf_one_pass.peak_vram_bytes,
            },
            hf_tokenwise.engine: {
                "elapsed_seconds": hf_tokenwise.elapsed_seconds,
                "tokens_per_second": hf_tokenwise.tokens_per_second,
                "peak_vram_bytes": hf_tokenwise.peak_vram_bytes,
            },
        },
        "comparisons": comparisons,
        "comparison_index": comparison_index,
        "equivalence_assessment": {
            "pair": key_vs_hf_tokenwise,
            "exact_cosine_threshold": args.exact_cosine_threshold,
            "min_cosine": orig_vs_hf_tokenwise["min_cosine"],
            "final_state_cosine": orig_vs_hf_tokenwise["final_state_cosine"],
            "passes_threshold": passes,
        },
        "original_selfcheck_assessment": {
            "pair": key_original_self,
            "exact_cosine_threshold": args.exact_cosine_threshold,
            "min_cosine": orig_self["min_cosine"],
            "final_state_cosine": orig_self["final_state_cosine"],
            "passes_threshold": original_self_passes,
        },
        "sample_indices": sample_msg_indices,
        "sample_metadata": original.sample_metadata,
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "option_b_probe_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.savez(
        out_dir / "option_b_states.npz",
        sample_indices=np.asarray(sample_msg_indices),
        original_one_pass_states=original_one_pass.states,
        original_states=original.states,
        hf_one_pass_states=hf_one_pass.states,
        hf_tokenwise_states=hf_tokenwise.states,
    )

    print(f"\nReport: {report_path}")
    print(f"States: {out_dir / 'option_b_states.npz'}")
    print(
        f"Original vs HF tokenwise min cosine: {orig_vs_hf_tokenwise['min_cosine']:.9f} "
        f"(threshold {args.exact_cosine_threshold}) -> "
        f"{'PASS' if passes else 'FAIL'}"
    )
    print(
        f"Runtime tokens/sec: original_step={original.tokens_per_second:.2f}, "
        f"original_one_pass={original_one_pass.tokens_per_second:.2f}, "
        f"hf_tokenwise={hf_tokenwise.tokens_per_second:.2f}, "
        f"hf_one_pass={hf_one_pass.tokens_per_second:.2f}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
