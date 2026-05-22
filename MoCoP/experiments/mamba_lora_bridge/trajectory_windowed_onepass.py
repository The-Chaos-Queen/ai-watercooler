#!/usr/bin/env python3
"""
trajectory_windowed_onepass.py

Option A: Windowed one-pass Mamba trajectory analyzer.

This engine is intentionally approximate/windowed. It does NOT preserve the
exact lifelong recurrent state across an arbitrarily long transcript. It uses
overlapping local windows and marks sample states as warmup/measured.

Key properties:
- tokenizes the transcript once for model execution
- runs one full forward pass per window
- uses a target-layer forward hook (no full hidden-state stack request)
- records window metadata and warmup/measured status per sampled turn
- can emit a tiny-fixture equivalence/sanity report against one-pass and
  tokenwise references
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


def to_serializable_float_list(values: List[float]) -> List[float]:
    return [float(v) for v in values]


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


def find_mamba_layers(model):
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
    raise RuntimeError("Could not locate Mamba layer stack on model object.")


def find_mamba_backbone(model):
    candidates = [
        ("backbone",),
        ("model",),
        ("model", "backbone"),
    ]
    for chain in candidates:
        obj = model
        ok = True
        for part in chain:
            if not hasattr(obj, part):
                ok = False
                break
            obj = getattr(obj, part)
        if ok and hasattr(obj, "embeddings") and hasattr(obj, "layers"):
            if obj.layers is not None and len(obj.layers) > 0:
                return obj
    raise RuntimeError("Could not locate Mamba backbone with embeddings/layers.")


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


def build_windows(total_tokens: int, window_size: int, stride: int) -> List[Tuple[int, int]]:
    windows = []
    start = 0
    while start < total_tokens:
        end = min(total_tokens, start + window_size)
        windows.append((start, end))
        if end >= total_tokens:
            break
        start += stride
    return windows


def build_sample_centered_windows(
    *,
    total_tokens: int,
    sample_token_positions: List[int],
    window_size: int,
    warmup_tokens: int,
    post_context_tokens: int,
) -> List[Tuple[int, int]]:
    windows: List[Tuple[int, int]] = []
    if total_tokens <= 0:
        return windows

    for token_pos in sorted(set(sample_token_positions)):
        end = min(total_tokens, token_pos + 1 + max(0, post_context_tokens))
        start = max(0, end - window_size)

        # Keep sampled token in measured region when possible.
        if warmup_tokens > 0 and start > 0 and (token_pos - start) < warmup_tokens:
            adjusted_start = max(0, token_pos - warmup_tokens)
            if adjusted_start < start:
                start = adjusted_start
                end = min(total_tokens, max(token_pos + 1, start + window_size))

        # Hard safety: sampled token must remain in [start, end).
        if token_pos < start:
            start = token_pos
            end = min(total_tokens, max(token_pos + 1, start + window_size))
        if token_pos >= end:
            end = min(total_tokens, token_pos + 1)
            start = max(0, end - window_size)

        windows.append((int(start), int(end)))

    unique = sorted(set(windows), key=lambda x: (x[0], x[1]))
    return unique


def build_execution_windows(
    *,
    total_tokens: int,
    sample_msg_indices: List[int],
    msg_to_token: Dict[int, int],
    window_size: int,
    warmup_tokens: int,
    window_stride: int,
    window_selection: str,
    post_context_tokens: int,
) -> List[Tuple[int, int]]:
    if window_selection == "sliding":
        return build_windows(total_tokens, window_size, window_stride)
    if window_selection == "sample-centered":
        sample_token_positions = [msg_to_token[m] for m in sample_msg_indices]
        return build_sample_centered_windows(
            total_tokens=total_tokens,
            sample_token_positions=sample_token_positions,
            window_size=window_size,
            warmup_tokens=warmup_tokens,
            post_context_tokens=post_context_tokens,
        )
    raise ValueError(f"Unsupported window selection mode: {window_selection}")


def total_window_tokens(windows: List[Tuple[int, int]]) -> int:
    return int(sum(max(0, end - start) for start, end in windows))


@dataclass
class EngineResult:
    states: np.ndarray
    sample_metadata: List[dict]
    elapsed_seconds: float
    tokens_per_second: float
    peak_vram_bytes: Optional[int]
    engine: str
    total_window_tokens: Optional[int] = None
    num_windows: Optional[int] = None


def _extract_hidden_indexed_vector(hidden_tensor, token_index: int) -> np.ndarray:
    vec = hidden_tensor[0, token_index, :].detach().float().cpu().numpy().reshape(-1)
    return vec


def _get_peak_vram_bytes(device: str):
    import torch

    if "cuda" not in device:
        return None
    return int(torch.cuda.max_memory_allocated())


def run_windowed_approximate(
    *,
    model,
    input_ids,
    sample_msg_indices: List[int],
    msg_to_token: Dict[int, int],
    msg_to_turn: Dict[int, dict],
    target_layer: int,
    warmup_tokens: int,
    windows: List[Tuple[int, int]],
    forward_mode: str,
    device: str,
) -> EngineResult:
    import torch

    layers = find_mamba_layers(model)
    if target_layer < 0 or target_layer >= len(layers):
        raise ValueError(
            f"target_layer={target_layer} out of range for model with {len(layers)} layers"
        )
    if forward_mode not in {"full-model-hook", "partial-target-layer"}:
        raise ValueError(f"Unsupported forward mode: {forward_mode}")
    hook = LayerCaptureHook(layers[target_layer]) if forward_mode == "full-model-hook" else None
    backbone = find_mamba_backbone(model) if forward_mode == "partial-target-layer" else None

    sample_state: Dict[int, np.ndarray] = {}
    sample_meta: Dict[int, dict] = {}
    raw_captures: List[dict] = []

    if "cuda" in device:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    total_window_tokens = 0

    try:
        for window_idx, (start, end) in enumerate(windows):
            chunk = input_ids[:, start:end]
            effective_warmup = 0 if start == 0 else min(warmup_tokens, end - start)
            measured_start = start + effective_warmup
            total_window_tokens += int(end - start)

            if forward_mode == "full-model-hook":
                hook.clear()
                with torch.no_grad():
                    _ = model(chunk, use_cache=False)
                hidden = hook.output_tensor
            else:
                with torch.no_grad():
                    hidden = backbone.embeddings(chunk)
                    for layer_idx, mixer_block in enumerate(backbone.layers):
                        hidden = mixer_block(hidden, cache_params=None, attention_mask=None)
                        if layer_idx == target_layer:
                            break
            if hidden is None:
                raise RuntimeError("Layer hook did not capture hidden output.")
            if hidden.dim() != 3:
                raise RuntimeError(f"Unexpected hidden shape from hook: {tuple(hidden.shape)}")

            for msg_idx in sample_msg_indices:
                token_pos = msg_to_token[msg_idx]
                if token_pos < start or token_pos >= end:
                    continue
                local_pos = token_pos - start
                status = "warmup" if token_pos < measured_start else "measured"
                state = _extract_hidden_indexed_vector(hidden, local_pos)
                capture = {
                    "msg_idx": msg_idx,
                    "token_pos": token_pos,
                    "window_index": window_idx,
                    "window_start_token": start,
                    "window_end_token": end,
                    "window_size_tokens": end - start,
                    "warmup_tokens_effective": effective_warmup,
                    "sample_status": status,
                    "norm": float(np.linalg.norm(state)),
                }
                raw_captures.append(capture)

                if msg_idx in sample_state:
                    if sample_meta[msg_idx]["sample_status"] == "measured":
                        continue
                    if status == "warmup":
                        continue

                sample_state[msg_idx] = state
                sample_meta[msg_idx] = {
                    **capture,
                    "role": msg_to_turn[msg_idx]["role"],
                    "preview": msg_to_turn[msg_idx]["text"][:80].replace("\n", " "),
                    "forward_mode": forward_mode,
                }
    finally:
        if hook is not None:
            hook.remove()

    elapsed = time.time() - t0
    missing = [m for m in sample_msg_indices if m not in sample_state]
    if missing:
        raise RuntimeError(f"Missing windowed states for sample messages: {missing}")

    ordered_states = np.stack([sample_state[m] for m in sample_msg_indices], axis=0)
    ordered_meta = [sample_meta[m] for m in sample_msg_indices]
    for row in ordered_meta:
        row["approximate_windowed"] = True
        row["state_continuity"] = "approximate_windowed_local_context"
    tps = float(total_window_tokens / max(elapsed, 1e-6))
    peak = _get_peak_vram_bytes(device)
    ordered_meta_summary = {
        "raw_capture_count": len(raw_captures),
        "windows": [
            {"window_index": i, "start_token": w[0], "end_token": w[1], "size": w[1] - w[0]}
            for i, w in enumerate(windows)
        ],
    }
    for row in ordered_meta:
        row["windowed_capture_summary"] = ordered_meta_summary
    return EngineResult(
        states=ordered_states,
        sample_metadata=ordered_meta,
        elapsed_seconds=float(elapsed),
        tokens_per_second=tps,
        peak_vram_bytes=peak,
        engine="windowed_one_pass_approximate",
        total_window_tokens=int(total_window_tokens),
        num_windows=len(windows),
    )


def run_one_pass_reference(
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

    layers = find_mamba_layers(model)
    hook = LayerCaptureHook(layers[target_layer])
    if "cuda" in device:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    try:
        with torch.no_grad():
            _ = model(input_ids, use_cache=False)
        hidden = hook.output_tensor
        if hidden is None:
            raise RuntimeError("One-pass hook did not capture hidden output.")
        states = []
        meta = []
        for msg_idx in sample_msg_indices:
            token_pos = msg_to_token[msg_idx]
            state = _extract_hidden_indexed_vector(hidden, token_pos)
            states.append(state)
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
        engine="one_pass_reference",
    )


def run_tokenwise_reference(
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

    layers = find_mamba_layers(model)
    if target_layer < 0 or target_layer >= len(layers):
        raise ValueError(
            f"target_layer={target_layer} out of range for model with {len(layers)} layers"
        )
    hook = LayerCaptureHook(layers[target_layer])

    if "cuda" in device:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()

    sample_token_to_msg = {msg_to_token[m]: m for m in sample_msg_indices}
    states_by_msg: Dict[int, np.ndarray] = {}
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
                    f"Tokenwise hook did not capture hidden output at token {token_pos}."
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
        raise RuntimeError(f"Tokenwise reference missing sample messages: {missing}")
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
        engine="tokenwise_reference",
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
        "per_sample_cosine": to_serializable_float_list(per_sample_cos),
        "per_sample_l2": to_serializable_float_list(per_sample_l2),
        "mean_cosine": float(np.mean(per_sample_cos)) if per_sample_cos else None,
        "min_cosine": float(min(per_sample_cos)) if per_sample_cos else None,
        "final_state_cosine": float(cosine(a.states[-1], b.states[-1])),
        "final_state_l2": float(np.linalg.norm(a.states[-1] - b.states[-1])),
        "trajectory_delta_l2": drift_l2,
        "a_tokens_per_second": float(a.tokens_per_second),
        "b_tokens_per_second": float(b.tokens_per_second),
        "a_peak_vram_bytes": a.peak_vram_bytes,
        "b_peak_vram_bytes": b.peak_vram_bytes,
    }


def run_engine_on_conversation(
    *,
    model,
    tokenizer,
    turns: List[dict],
    sample_every: int,
    target_layer: int,
    window_size: int,
    warmup_tokens: int,
    window_stride: int,
    window_selection: str,
    post_context_tokens: int,
    forward_mode: str,
    device: str,
) -> Tuple[EngineResult, dict]:
    turn_lines = build_turn_lines(turns)
    full_text = build_full_text(turn_lines)
    encoded = tokenizer(full_text, return_tensors="pt", add_special_tokens=False)
    input_ids = encoded["input_ids"].to(device)
    total_tokens = int(input_ids.shape[1])

    sample_msg_indices = compute_sample_message_indices(len(turns), sample_every)
    boundaries = compute_boundaries_by_turn_tokenization(tokenizer, turn_lines)
    if not boundaries:
        raise RuntimeError("No turn boundaries produced from conversation.")
    msg_to_token = {
        i + 1: min(boundaries[i], total_tokens - 1) for i in range(len(boundaries))
    }
    msg_to_turn = {i + 1: turns[i] for i in range(len(turns))}
    windows = build_execution_windows(
        total_tokens=total_tokens,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        window_size=window_size,
        warmup_tokens=warmup_tokens,
        window_stride=window_stride,
        window_selection=window_selection,
        post_context_tokens=post_context_tokens,
    )
    planned_window_tokens = total_window_tokens(windows)

    result = run_windowed_approximate(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=target_layer,
        warmup_tokens=warmup_tokens,
        windows=windows,
        forward_mode=forward_mode,
        device=device,
    )
    context = {
        "full_text_chars": len(full_text),
        "total_tokens": total_tokens,
        "window_selection": window_selection,
        "post_context_tokens": int(post_context_tokens),
        "num_windows": len(windows),
        "planned_total_window_tokens": planned_window_tokens,
        "windows": windows,
        "sample_msg_indices": sample_msg_indices,
        "msg_to_token": msg_to_token,
        "msg_to_turn": msg_to_turn,
        "input_ids": input_ids,
    }
    return result, context


def save_main_outputs(
    *,
    out_dir: Path,
    args,
    label: str,
    source: str,
    turns: List[dict],
    context: dict,
    result: EngineResult,
):
    jumps = []
    for i in range(1, result.states.shape[0]):
        c = cosine(result.states[i], result.states[i - 1])
        jumps.append(
            {
                "from_msg": context["sample_msg_indices"][i - 1],
                "to_msg": context["sample_msg_indices"][i],
                "cosine": c,
                "delta": 1.0 - c,
            }
        )
    drift = []
    for i in range(result.states.shape[0]):
        c = cosine(result.states[i], result.states[0])
        drift.append(
            {
                "msg_idx": context["sample_msg_indices"][i],
                "cosine_vs_start": c,
                "drift": 1.0 - c,
            }
        )
    sample_status_counts: Dict[str, int] = {}
    for m in result.sample_metadata:
        status = m.get("sample_status", "unknown")
        sample_status_counts[status] = sample_status_counts.get(status, 0) + 1

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "windowed_approximate",
        "method": (
            "windowed_partial_target_layer"
            if args.forward_mode == "partial-target-layer"
            else "windowed_one_pass_hook"
        ),
        "analysis_label": "WINDOWED_APPROXIMATE",
        "state_continuity_label": "approximate_windowed_not_exact_full_recurrence",
        "conversation_label": label,
        "source": source,
        "total_turns": len(turns),
        "sample_every": args.sample_every,
        "sample_points": len(context["sample_msg_indices"]),
        "model_id": args.model_id,
        "target_layer": args.target_layer,
        "forward_mode": args.forward_mode,
        "forward_mode_status": (
            "experimental_unvalidated"
            if args.forward_mode == "partial-target-layer"
            else "baseline_full_model_hook"
        ),
        "window_size": args.window_size,
        "warmup_tokens": args.warmup_tokens,
        "window_stride": args.window_stride,
        "window_selection": args.window_selection,
        "post_context_tokens": args.post_context_tokens,
        "total_tokens": context["total_tokens"],
        "num_windows": context["num_windows"],
        "planned_total_window_tokens": context["planned_total_window_tokens"],
        "total_window_tokens": result.total_window_tokens,
        "engine": result.engine,
        "elapsed_seconds": result.elapsed_seconds,
        "tokens_per_second": result.tokens_per_second,
        "peak_vram_bytes": result.peak_vram_bytes,
        "sample_status_counts": sample_status_counts,
        "jumps": jumps,
        "drift": drift,
        "metadata": result.sample_metadata,
        "sample_metadata": result.sample_metadata,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "windowed_trajectory_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.savez(
        out_dir / "windowed_states.npz",
        states=result.states,
        sample_indices=np.asarray(context["sample_msg_indices"]),
    )
    return report_path


def maybe_run_sanity_equivalence(
    *,
    args,
    model,
    tokenizer,
    device: str,
) -> Optional[Path]:
    if not args.run_sanity_report:
        return None
    fixture_path = Path(args.sanity_fixture)
    if not fixture_path.exists():
        print(f"[sanity] fixture not found: {fixture_path}")
        return None
    turns = parse_markdown_conversation(str(fixture_path))
    if args.sanity_max_messages > 0:
        turns = turns[: args.sanity_max_messages]
    if not turns:
        print("[sanity] fixture parsed zero turns; skipping")
        return None

    turn_lines = build_turn_lines(turns)
    full_text = build_full_text(turn_lines)
    encoded = tokenizer(full_text, return_tensors="pt", add_special_tokens=False)
    input_ids = encoded["input_ids"].to(device)
    sample_msg_indices = compute_sample_message_indices(len(turns), args.sanity_sample_every)
    boundaries = compute_boundaries_by_turn_tokenization(tokenizer, turn_lines)
    msg_to_token = {i + 1: min(boundaries[i], int(input_ids.shape[1]) - 1) for i in range(len(boundaries))}
    msg_to_turn = {i + 1: turns[i] for i in range(len(turns))}
    windows = build_execution_windows(
        total_tokens=int(input_ids.shape[1]),
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        window_size=args.window_size,
        warmup_tokens=args.warmup_tokens,
        window_stride=args.window_stride,
        window_selection=args.window_selection,
        post_context_tokens=args.post_context_tokens,
    )
    planned_window_tokens = total_window_tokens(windows)

    print("[sanity] running windowed approximate engine...")
    windowed = run_windowed_approximate(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        warmup_tokens=args.warmup_tokens,
        windows=windows,
        forward_mode=args.forward_mode,
        device=device,
    )
    print("[sanity] running full-vs-partial windowed comparison...")
    windowed_full = run_windowed_approximate(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        warmup_tokens=args.warmup_tokens,
        windows=windows,
        forward_mode="full-model-hook",
        device=device,
    )
    windowed_full.engine = "windowed_full_model_hook_reference"
    windowed_partial = run_windowed_approximate(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        warmup_tokens=args.warmup_tokens,
        windows=windows,
        forward_mode="partial-target-layer",
        device=device,
    )
    windowed_partial.engine = "windowed_partial_target_layer"
    print("[sanity] running one-pass reference...")
    one_pass = run_one_pass_reference(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        device=device,
    )
    print("[sanity] running tokenwise reference...")
    tokenwise = run_tokenwise_reference(
        model=model,
        input_ids=input_ids,
        sample_msg_indices=sample_msg_indices,
        msg_to_token=msg_to_token,
        msg_to_turn=msg_to_turn,
        target_layer=args.target_layer,
        device=device,
    )

    comparisons = [
        compare_engines(source_name="trajectory_sanity_tiny", a=windowed_full, b=windowed_partial),
        compare_engines(source_name="trajectory_sanity_tiny", a=windowed, b=one_pass),
        compare_engines(source_name="trajectory_sanity_tiny", a=windowed, b=tokenwise),
        compare_engines(source_name="trajectory_sanity_tiny", a=one_pass, b=tokenwise),
    ]
    comparison_index = {f"{row['a_engine']}__vs__{row['b_engine']}": row for row in comparisons}
    one_vs_token = comparison_index["one_pass_reference__vs__tokenwise_reference"]
    full_vs_partial = comparison_index[
        "windowed_full_model_hook_reference__vs__windowed_partial_target_layer"
    ]
    comparison_index["full_model_hook__vs__partial_target_layer"] = full_vs_partial
    exact_threshold = 0.99999
    partial_mode_pass = bool(
        full_vs_partial["min_cosine"] >= exact_threshold
        and full_vs_partial["final_state_cosine"] >= exact_threshold
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fixture": str(fixture_path),
        "labeling": {
            "windowed_engine_label": "WINDOWED_APPROXIMATE",
            "continuity_label": "approximate_windowed_not_exact_full_recurrence",
        },
        "sanity_run_config": {
            "model_id": args.model_id,
            "target_layer": args.target_layer,
            "forward_mode": args.forward_mode,
            "window_size": args.window_size,
            "warmup_tokens": args.warmup_tokens,
            "window_stride": args.window_stride,
            "window_selection": args.window_selection,
            "post_context_tokens": args.post_context_tokens,
            "num_windows": len(windows),
            "planned_total_window_tokens": planned_window_tokens,
            "sample_every": args.sanity_sample_every,
        },
        "engines": {
            "windowed_one_pass_approximate": {
                "elapsed_seconds": windowed.elapsed_seconds,
                "tokens_per_second": windowed.tokens_per_second,
                "peak_vram_bytes": windowed.peak_vram_bytes,
            },
            "one_pass_reference": {
                "elapsed_seconds": one_pass.elapsed_seconds,
                "tokens_per_second": one_pass.tokens_per_second,
                "peak_vram_bytes": one_pass.peak_vram_bytes,
            },
            "tokenwise_reference": {
                "elapsed_seconds": tokenwise.elapsed_seconds,
                "tokens_per_second": tokenwise.tokens_per_second,
                "peak_vram_bytes": tokenwise.peak_vram_bytes,
            },
        },
        "comparisons": comparisons,
        "comparison_index": comparison_index,
        "sanity_assessment": {
            "exact_engine_pair": "one_pass_reference__vs__tokenwise_reference",
            "exact_cosine_threshold": exact_threshold,
            "one_pass_vs_tokenwise_min_cosine": one_vs_token["min_cosine"],
            "one_pass_vs_tokenwise_final_state_cosine": one_vs_token["final_state_cosine"],
            "passes_exact_threshold": bool(one_vs_token["min_cosine"] >= exact_threshold),
            "note": (
                "Windowed analyzer is expected to deviate on later samples when context exceeds "
                "window coverage; this is labeled approximate by design."
            ),
        },
        "partial_validation": {
            "comparison_key": "full_model_hook__vs__partial_target_layer",
            "threshold": exact_threshold,
            "min_cosine": full_vs_partial["min_cosine"],
            "final_state_cosine": full_vs_partial["final_state_cosine"],
            "passes_threshold": partial_mode_pass,
            "status": "validated" if partial_mode_pass else "experimental",
        },
    }
    report_path = out_dir / "windowed_sanity_equivalence_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Windowed one-pass Mamba trajectory analyzer (explicitly approximate)."
    )
    parser.add_argument("--conversation", help="Markdown conversation file")
    parser.add_argument("--conversation-json", help="Claude JSON export file")
    parser.add_argument("--conv-index", type=int, default=0)
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--sample-every", type=int, default=10)
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--window-size", type=int, default=1536)
    parser.add_argument("--warmup-tokens", type=int, default=768)
    parser.add_argument("--window-stride", type=int, default=0)
    parser.add_argument(
        "--window-selection",
        choices=["sliding", "sample-centered"],
        default="sliding",
    )
    parser.add_argument("--post-context-tokens", type=int, default=0)
    parser.add_argument(
        "--forward-mode",
        choices=["full-model-hook", "partial-target-layer"],
        default="full-model-hook",
    )
    parser.add_argument("--output-dir", default="trajectory_windowed_results")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--require-fast-path",
        action="store_true",
        help="Refuse to run if fast-path kernels are not available.",
    )
    parser.add_argument(
        "--run-sanity-report",
        action="store_true",
        help="Run tiny-fixture equivalence report (windowed vs one-pass vs tokenwise).",
    )
    parser.add_argument(
        "--sanity-fixture",
        default="MoCoP/experiments/mamba_lora_bridge/trajectory_sanity_tiny.md",
    )
    parser.add_argument("--sanity-sample-every", type=int, default=1)
    parser.add_argument("--sanity-max-messages", type=int, default=0)
    args = parser.parse_args()

    if args.window_size <= 0:
        print("Error: --window-size must be > 0")
        return 1
    if args.warmup_tokens < 0:
        print("Error: --warmup-tokens must be >= 0")
        return 1
    if args.window_stride <= 0:
        args.window_stride = max(1, args.window_size - args.warmup_tokens)
    if args.window_stride <= 0:
        print("Error: computed --window-stride must be > 0")
        return 1
    if args.post_context_tokens < 0:
        print("Error: --post-context-tokens must be >= 0")
        return 1

    if args.conversation_json:
        turns, name, _created = parse_claude_json(args.conversation_json, args.conv_index)
        source = args.conversation_json
        label = name or f"conv_{args.conv_index}"
    elif args.conversation:
        turns = parse_markdown_conversation(args.conversation)
        source = args.conversation
        label = Path(args.conversation).stem
    else:
        print("Error: --conversation or --conversation-json required")
        return 1
    turns = turns[: args.max_messages]
    if not turns:
        print("Error: parsed zero turns")
        return 1

    print("Engine label: WINDOWED_APPROXIMATE")
    print("Continuity label: approximate_windowed_not_exact_full_recurrence")
    print(f"Conversation: {label}")
    print(f"Source: {source}")
    print(f"Turns used: {len(turns)}")
    print(
        f"Window config: size={args.window_size}, warmup={args.warmup_tokens}, stride={args.window_stride}"
    )
    print(
        f"Window selection: {args.window_selection}, post_context={args.post_context_tokens}"
    )
    print(f"Forward mode: {args.forward_mode}")

    import torch

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

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

    from transformers import AutoTokenizer, MambaForCausalLM

    print(f"\nLoading tokenizer: {args.model_id}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if args.dry_run:
        turn_lines = build_turn_lines(turns)
        full_text = build_full_text(turn_lines)
        encoded = tokenizer(full_text, return_tensors="pt", add_special_tokens=False)
        total_tokens = int(encoded["input_ids"].shape[1])
        sample_indices = compute_sample_message_indices(len(turns), args.sample_every)
        boundaries = compute_boundaries_by_turn_tokenization(tokenizer, turn_lines)
        msg_to_token = {
            i + 1: min(boundaries[i], total_tokens - 1) for i in range(len(boundaries))
        }
        windows = build_execution_windows(
            total_tokens=total_tokens,
            sample_msg_indices=sample_indices,
            msg_to_token=msg_to_token,
            window_size=args.window_size,
            warmup_tokens=args.warmup_tokens,
            window_stride=args.window_stride,
            window_selection=args.window_selection,
            post_context_tokens=args.post_context_tokens,
        )
        print(f"[dry-run] sample points: {len(sample_indices)}")
        print(f"[dry-run] total tokens: {total_tokens}")
        print(f"[dry-run] windows planned: {len(windows)}")
        print(f"[dry-run] planned total window tokens: {total_window_tokens(windows)}")
        return 0

    print(f"Loading model: {args.model_id}")
    dtype = torch.float16 if "cuda" in device else torch.float32
    model = MambaForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype)
    model.to(device)
    model.eval()

    result, context = run_engine_on_conversation(
        model=model,
        tokenizer=tokenizer,
        turns=turns,
        sample_every=args.sample_every,
        target_layer=args.target_layer,
        window_size=args.window_size,
        warmup_tokens=args.warmup_tokens,
        window_stride=args.window_stride,
        window_selection=args.window_selection,
        post_context_tokens=args.post_context_tokens,
        forward_mode=args.forward_mode,
        device=device,
    )

    out_dir = Path(args.output_dir)
    report_path = save_main_outputs(
        out_dir=out_dir,
        args=args,
        label=label,
        source=source,
        turns=turns,
        context=context,
        result=result,
    )
    print(f"\nWindowed report: {report_path}")
    print(f"Windowed states: {out_dir / 'windowed_states.npz'}")
    print(
        f"Runtime: {result.elapsed_seconds:.1f}s, tokens/sec={result.tokens_per_second:.2f}, "
        f"peak_vram_bytes={result.peak_vram_bytes}, "
        f"window_tokens={result.total_window_tokens}, windows={result.num_windows}"
    )

    sanity_report_path = maybe_run_sanity_equivalence(
        args=args,
        model=model,
        tokenizer=tokenizer,
        device=device,
    )
    if sanity_report_path is not None:
        print(f"Sanity equivalence report: {sanity_report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
