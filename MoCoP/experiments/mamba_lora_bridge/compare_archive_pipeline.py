#!/usr/bin/env python3
"""
compare_archive_pipeline.py - Compare archive-conditioned states through the bridge.

This is the direct follow-up to the cleaned relational-panel archive eval.
Instead of looking at downstream generations, it compares the archive episodes
inside the bridge pipeline itself:

  1. Raw Mamba last-token state
  2. Compressed context vector
  3. Raw hypernetwork bias vector (when available)
  4. Output / gated bias vector

An optional zero-input control is included so we can see whether the bridge is
merely tinting everything in the same direction.

Usage (Steve):
  /root/mocop_venv/bin/python3 -X utf8 compare_archive_pipeline.py \
    --episodes-file ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md \
    --episode-indices 2 3 4 \
    --output run_reincarnation/archive_pipeline_compare_20260413.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import combinations
from pathlib import Path

import torch
import torch.nn.functional as F

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

DEFAULT_BRIDGE = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
DEFAULT_MAMBA = "state-spaces/mamba-2.8b-hf"
DEFAULT_EPISODES_FILE = "ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md"


def read_episodes(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    episodes = text.split("## Episode ")[1:]
    parsed: list[dict[str, str]] = []
    for ep in episodes:
        header = ep.splitlines()[0].strip()
        transcript = ep.split("[Transcript]")[1].strip()
        parsed.append({"title": header, "text": transcript})
    return parsed


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item())


def pairwise_cosine_matrix(vectors: dict[str, torch.Tensor]) -> dict[str, dict[str, float]]:
    names = list(vectors.keys())
    matrix: dict[str, dict[str, float]] = {}
    for ni in names:
        matrix[ni] = {}
        for nj in names:
            matrix[ni][nj] = round(cosine_sim(vectors[ni], vectors[nj]), 6)
    return matrix


def print_matrix(matrix: dict[str, dict[str, float]], title: str) -> None:
    names = list(matrix.keys())
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")
    print(f"{'':>24s}", end="")
    for name in names:
        print(f" {name:>16s}", end="")
    print()
    for ni in names:
        print(f"  {ni:>22s}", end="")
        for nj in names:
            print(f" {matrix[ni][nj]:16.4f}", end="")
        print()


def offdiag_stats(matrix: dict[str, dict[str, float]]) -> dict[str, float]:
    names = list(matrix.keys())
    values = []
    for i, ni in enumerate(names):
        for nj in names[i + 1 :]:
            values.append(matrix[ni][nj])
    if not values:
        return {"mean": 1.0, "min": 1.0, "max": 1.0}
    return {
        "mean": round(sum(values) / len(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def infer_target_dims(hypernet_state: dict[str, torch.Tensor]) -> list[tuple[int, int]]:
    head_indices = sorted(
        {
            int(key.split(".")[1])
            for key in hypernet_state
            if key.startswith("bias_heads.") and key.endswith(".bias")
        }
    )
    return [(0, int(hypernet_state[f"bias_heads.{idx}.bias"].shape[0])) for idx in head_indices]


def short_label(title: str) -> str:
    if "[" in title and "]" in title:
        return title.split("[")[-1].split("]")[0].strip()
    return title[:32].strip().replace(" ", "_").lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare archive states through the bridge pipeline")
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-indices", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--mamba-device", default="cuda:0")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--include-zero-control", action="store_true")
    parser.add_argument("--output", default="archive_pipeline_compare.json")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    def resolve(path_str: str) -> Path:
        path = Path(path_str)
        return path if path.is_absolute() else script_dir / path

    bridge_path = resolve(args.bridge_path)
    episodes_path = resolve(args.episodes_file)
    output_path = resolve(args.output)

    if not bridge_path.exists():
        raise SystemExit(f"Bridge checkpoint not found: {bridge_path}")
    if not episodes_path.exists():
        raise SystemExit(f"Episodes file not found: {episodes_path}")

    print("=" * 80)
    print("  ARCHIVE PIPELINE COMPARISON")
    print("=" * 80)
    print(f"Bridge: {bridge_path.name}")
    print(f"Episodes: {episodes_path.name}")
    print(f"Indices: {args.episode_indices}")

    ckpt = torch.load(str(bridge_path), map_location="cpu", weights_only=False)
    bridge_mode = str(ckpt.get("bridge_mode", "activation_bias"))
    bridge_config = ckpt.get("bridge_config", {})
    context_dim = int(ckpt.get("context_dim", bridge_config.get("context_dim", 2048)))
    hidden_dim = int(bridge_config.get("hyper_hidden_dim", 1024))
    gate_kind = str(bridge_config.get("gate_kind", "vector"))
    initial_gate = float(bridge_config.get("initial_gate", 0.1))
    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    hypernet_state = ckpt.get("hypernetwork_state_dict", {})
    target_dims = infer_target_dims(hypernet_state)

    print(f"bridge_mode: {bridge_mode}")
    print(f"context_dim: {context_dim}")
    print(f"target_layer: {mamba_target_layer}")
    print(f"bias_heads: {len(target_dims)}")

    from transformers import AutoTokenizer, MambaForCausalLM

    print(f"\nLoading Mamba: {args.mamba_model_id} -> {args.mamba_device}")
    mamba_tokenizer = AutoTokenizer.from_pretrained(args.mamba_model_id)
    mamba_model = MambaForCausalLM.from_pretrained(args.mamba_model_id, torch_dtype=torch.float32)
    mamba_model.to(args.mamba_device)
    mamba_model.eval()

    hidden_layer_count = 0
    for name in mamba_model.state_dict():
        if ".layers." in name:
            idx = int(name.split(".layers.")[1].split(".")[0])
            hidden_layer_count = max(hidden_layer_count, idx + 1)

    episodes = read_episodes(episodes_path)
    selected = []
    for idx in args.episode_indices:
        if idx < 0 or idx >= len(episodes):
            raise SystemExit(f"Episode index out of range: {idx}")
        episode = episodes[idx]
        selected.append(
            {
                "index": idx,
                "title": episode["title"],
                "label": short_label(episode["title"]),
                "text": episode["text"],
            }
        )

    raw_states: dict[str, torch.Tensor] = {}
    with torch.no_grad():
        for item in selected:
            print(f"\nExtracting raw state for episode {item['index']}: {item['title']}")
            tokens = mamba_tokenizer(
                item["text"],
                return_tensors="pt",
                truncation=True,
                max_length=args.max_mamba_tokens,
            )
            tokens = {k: v.to(args.mamba_device) for k, v in tokens.items()}
            out = mamba_model(**tokens, output_hidden_states=True)
            hidden_states = out.hidden_states
            hidden_index = mamba_target_layer
            if len(hidden_states) == hidden_layer_count + 1:
                hidden_index = mamba_target_layer + 1
            raw_state = hidden_states[hidden_index][:, -1, :].squeeze(0).float().cpu()
            raw_states[item["label"]] = raw_state
            print(f"  label={item['label']} shape={tuple(raw_state.shape)} norm={raw_state.norm():.4f}")
            del out, hidden_states, tokens

    if args.include_zero_control and raw_states:
        exemplar = next(iter(raw_states.values()))
        raw_states["all_zero"] = torch.zeros_like(exemplar)
        print("\nAdded all_zero control.")

    del mamba_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    sys.path.insert(0, str(script_dir))
    from models import MambaStateCompressor, build_activation_bias_hypernetwork

    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=context_dim,
        target_layer=mamba_target_layer,
    ).cpu().float()
    if "compressor_state_dict" in ckpt:
        compressor.load_state_dict(ckpt["compressor_state_dict"])
    compressor.eval()

    hypernet = build_activation_bias_hypernetwork(
        bridge_mode=bridge_mode,
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=hidden_dim,
        gate_kind=gate_kind,
        initial_gate=initial_gate,
    ).cpu().float()
    hypernet.load_state_dict(hypernet_state)
    hypernet.eval()

    contexts: dict[str, torch.Tensor] = {}
    output_biases: dict[str, torch.Tensor] = {}
    raw_biases: dict[str, torch.Tensor] = {}

    with torch.no_grad():
        for label, raw_state in raw_states.items():
            ctx = compressor(raw_state.unsqueeze(0)).squeeze(0).cpu()
            contexts[label] = ctx

            if hasattr(hypernet, "export_hidden_gate_state"):
                exported = hypernet.export_hidden_gate_state(ctx.unsqueeze(0))
                raw_bias = torch.cat([entry["raw_bias"].squeeze(0).cpu() for entry in exported])
                raw_biases[label] = raw_bias
            else:
                bias_list = hypernet.forward_from_hidden(hypernet.encode_hidden(ctx.unsqueeze(0)))
                raw_biases[label] = torch.cat([b.squeeze(0).cpu() for b in bias_list])

            out_bias_list = hypernet(ctx.unsqueeze(0))
            output_biases[label] = torch.cat([b.squeeze(0).cpu() for b in out_bias_list])

    raw_matrix = pairwise_cosine_matrix(raw_states)
    ctx_matrix = pairwise_cosine_matrix(contexts)
    raw_bias_matrix = pairwise_cosine_matrix(raw_biases)
    out_bias_matrix = pairwise_cosine_matrix(output_biases)

    print_matrix(raw_matrix, "STAGE 1: Raw Mamba last-token state")
    print_matrix(ctx_matrix, "STAGE 2: Compressed context")
    print_matrix(raw_bias_matrix, "STAGE 3: Raw hypernetwork bias")
    print_matrix(out_bias_matrix, "STAGE 4: Output bias")

    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"Raw state off-diagonal mean:      {offdiag_stats(raw_matrix)['mean']:.6f}")
    print(f"Compressed context offdiag mean:  {offdiag_stats(ctx_matrix)['mean']:.6f}")
    print(f"Raw bias offdiag mean:            {offdiag_stats(raw_bias_matrix)['mean']:.6f}")
    print(f"Output bias offdiag mean:         {offdiag_stats(out_bias_matrix)['mean']:.6f}")

    if args.include_zero_control and "all_zero" in out_bias_matrix:
        print(f"Zero control vs output bias:")
        for label in output_biases:
            if label == "all_zero":
                continue
            print(
                f"  {label:>20s}: context={ctx_matrix[label]['all_zero']:.6f} "
                f"raw_bias={raw_bias_matrix[label]['all_zero']:.6f} "
                f"out_bias={out_bias_matrix[label]['all_zero']:.6f}"
            )

    pairwise = {}
    for a, b in combinations(raw_states.keys(), 2):
        pairwise[f"{a}_vs_{b}"] = {
            "raw_state": raw_matrix[a][b],
            "compressed_context": ctx_matrix[a][b],
            "raw_bias": raw_bias_matrix[a][b],
            "output_bias": out_bias_matrix[a][b],
        }

    results = {
        "experiment": "archive_pipeline_compare",
        "config": {
            "bridge_path": str(bridge_path.name),
            "episodes_file": str(episodes_path.name),
            "episode_indices": list(args.episode_indices),
            "bridge_mode": bridge_mode,
            "context_dim": context_dim,
            "hyper_hidden_dim": hidden_dim,
            "gate_kind": gate_kind,
            "initial_gate": initial_gate,
            "mamba_target_layer": mamba_target_layer,
            "include_zero_control": bool(args.include_zero_control),
        },
        "episodes": [
            {"index": item["index"], "label": item["label"], "title": item["title"]}
            for item in selected
        ],
        "stage1_raw_state": {
            "norms": {k: round(float(v.norm()), 6) for k, v in raw_states.items()},
            "cosine_matrix": raw_matrix,
            "offdiag": offdiag_stats(raw_matrix),
        },
        "stage2_context": {
            "norms": {k: round(float(v.norm()), 6) for k, v in contexts.items()},
            "cosine_matrix": ctx_matrix,
            "offdiag": offdiag_stats(ctx_matrix),
        },
        "stage3_raw_bias": {
            "norms": {k: round(float(v.norm()), 6) for k, v in raw_biases.items()},
            "cosine_matrix": raw_bias_matrix,
            "offdiag": offdiag_stats(raw_bias_matrix),
        },
        "stage4_output_bias": {
            "norms": {k: round(float(v.norm()), 6) for k, v in output_biases.items()},
            "cosine_matrix": out_bias_matrix,
            "offdiag": offdiag_stats(out_bias_matrix),
        },
        "pairwise": pairwise,
    }

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
