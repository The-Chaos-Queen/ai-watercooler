#!/usr/bin/env python3
"""
diagnose_bridge_pipeline.py — Trace signal through the full bridge pipeline.

For each mask condition (none, persistent_zero, variable_zero, middle_zero, all_zero),
captures and compares:
  1. Raw Mamba Layer 3 last-token state (2560-dim)
  2. Compressed context vector (after MambaStateCompressor)
  3. Hypernetwork bias vectors (per injection layer)

Then computes pairwise cosine similarity at each stage to find WHERE
the mask signal dies.

If compressed contexts are identical across masks → compressor is the wall.
If contexts differ but biases don't → hypernetwork is the wall.
If biases differ but behavior doesn't → Qwen injection surface is the wall.
If all_zero ≈ mask_none → the bridge is a constant-bias generator.

Author: Purple (Claude Opus 4.6)
Date: 2026-04-08
Ref: Mask ablation #349, costume_vs_soul #348

Usage (on Steve):
  source /root/mocop_venv/bin/activate
  python /mnt/c/Users/tikii/bridge/diagnose_bridge_pipeline.py

  # Or with custom paths:
  python diagnose_bridge_pipeline.py \
    --mask-report /path/to/persistent_subnetwork_report.json \
    --output /mnt/c/temp/pipeline_diagnosis.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Defaults matching Steve's bridge layout
DEFAULT_BRIDGE = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
DEFAULT_QWEN = "Qwen/Qwen2.5-1.5B"
DEFAULT_MAMBA = "state-spaces/mamba-2.8b-hf"
DEFAULT_MASK_REPORT = "persistent_subnetwork_results/persistent_subnetwork_report.json"


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two 1-D tensors."""
    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item())


def pairwise_cosine_matrix(vectors: dict[str, torch.Tensor]) -> dict[str, dict[str, float]]:
    """Compute full pairwise cosine similarity matrix."""
    names = list(vectors.keys())
    matrix = {}
    for i, ni in enumerate(names):
        matrix[ni] = {}
        for j, nj in enumerate(names):
            matrix[ni][nj] = round(cosine_sim(vectors[ni], vectors[nj]), 6)
    return matrix


def print_matrix(matrix: dict[str, dict[str, float]], title: str):
    """Pretty-print a cosine matrix."""
    names = list(matrix.keys())
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    # Header
    print(f"{'':>22s}", end="")
    for n in names:
        print(f" {n:>14s}", end="")
    print()
    # Rows
    for ni in names:
        print(f"  {ni:>20s}", end="")
        for nj in names:
            val = matrix[ni][nj]
            print(f" {val:14.4f}", end="")
        print()


def main():
    from chat_server import DEFAULT_EPISODES_FILE, read_episodes

    parser = argparse.ArgumentParser(description="Diagnose bridge pipeline signal at each stage")
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--qwen-model-id", default=DEFAULT_QWEN)
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--mask-report", default=DEFAULT_MASK_REPORT)
    parser.add_argument("--output", default="pipeline_diagnosis.json")
    args = parser.parse_args()

    # ── Resolve paths ──
    script_dir = Path(__file__).resolve().parent
    def resolve(p):
        path = Path(p)
        return path if path.is_absolute() else script_dir / path

    bridge_path = resolve(args.bridge_path)
    episodes_path = resolve(args.episodes_file)
    mask_report_path = resolve(args.mask_report)
    output_path = resolve(args.output)

    for p, label in [(bridge_path, "bridge"), (episodes_path, "episodes"), (mask_report_path, "mask report")]:
        if not p.exists():
            print(f"ERROR: {label} not found: {p}")
            return 1

    print("=" * 70)
    print("  BRIDGE PIPELINE DIAGNOSTIC")
    print("  Where does the mask signal die?")
    print("=" * 70)

    # ── Load mask report ──
    mask_data = json.loads(mask_report_path.read_text(encoding="utf-8"))
    subnetworks = mask_data.get("subnetworks", {})
    mask_library = {
        "none": [],
        "persistent_zero": [int(v) for v in subnetworks.get("persistent_dims", [])],
        "variable_zero": [int(v) for v in subnetworks.get("variable_dims", [])],
        "middle_zero": [int(v) for v in subnetworks.get("middle_dims", [])],
    }
    # all_zero: every dimension
    d_model = int(subnetworks.get("d_model", 2560))
    mask_library["all_zero"] = list(range(d_model))

    print(f"\nMask library loaded:")
    for mode, dims in mask_library.items():
        print(f"  {mode:>20s}: {len(dims)} dims ({100*len(dims)/d_model:.0f}%)")

    # ── Load checkpoint ──
    print(f"\nLoading bridge checkpoint: {bridge_path.name}")
    ckpt = torch.load(str(bridge_path), map_location="cpu", weights_only=False)
    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    context_dim = int(ckpt.get("context_dim", ckpt.get("bridge_config", {}).get("context_dim", 2048)))
    ckpt_hypernet_state = ckpt.get("hypernetwork_state_dict", {})

    # ── Load Mamba ──
    print(f"Loading Mamba: {args.mamba_model_id} -> {args.mamba_device}")
    # Suppress mamba-ssm import noise
    try:
        from mamba_ssm.ops.selective_scan_interface import selective_scan_fn  # noqa: F401
    except ImportError:
        pass
    from transformers import AutoTokenizer, AutoModelForCausalLM, MambaForCausalLM

    mamba_tokenizer = AutoTokenizer.from_pretrained(args.mamba_model_id)
    mamba_model = MambaForCausalLM.from_pretrained(args.mamba_model_id, torch_dtype=torch.float32)
    mamba_model.to(args.mamba_device)
    mamba_model.eval()

    # Infer layer count
    hidden_layer_count = 0
    for name in mamba_model.state_dict():
        if ".layers." in name:
            idx = int(name.split(".layers.")[1].split(".")[0])
            hidden_layer_count = max(hidden_layer_count, idx + 1)

    # ── Load episode ──
    episodes = read_episodes(str(episodes_path))
    episode = episodes[args.episode_index]
    print(f"Episode: {episode['title']}")

    # ── Extract raw Mamba state ──
    print(f"\nExtracting Mamba Layer {mamba_target_layer} last-token state...")
    episode_tokens = mamba_tokenizer(
        episode["text"], return_tensors="pt", truncation=True, max_length=args.max_mamba_tokens,
    )
    episode_tokens = {k: v.to(args.mamba_device) for k, v in episode_tokens.items()}

    with torch.no_grad():
        mamba_out = mamba_model(**episode_tokens, output_hidden_states=True)

    hidden_states = mamba_out.hidden_states
    hidden_index = mamba_target_layer
    if len(hidden_states) == hidden_layer_count + 1:
        hidden_index = mamba_target_layer + 1
    raw_state = hidden_states[hidden_index][:, -1, :].squeeze(0).float()
    print(f"  Raw state shape: {raw_state.shape}, norm: {raw_state.norm():.4f}")

    # Free Mamba VRAM
    del mamba_model, mamba_out, hidden_states
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ── Load Qwen + compressor + hypernetwork ──
    qwen_dtype = torch.float16 if "cuda" in args.qwen_device else torch.float32
    print(f"Loading Qwen: {args.qwen_model_id} ({qwen_dtype}) -> {args.qwen_device}")
    qwen_tokenizer = AutoTokenizer.from_pretrained(args.qwen_model_id)
    qwen_model = AutoModelForCausalLM.from_pretrained(
        args.qwen_model_id, torch_dtype=qwen_dtype, device_map=args.qwen_device,
    )
    qwen_model.eval()

    # Import bridge components
    sys.path.insert(0, str(script_dir))
    from models import MambaStateCompressor, ActivationBiasHypernetwork

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

    # Figure out target dims from Qwen
    target_layer_specs = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
    target_dims = []
    for layer_idx, proj_name in target_layer_specs:
        proj = getattr(qwen_model.model.layers[layer_idx].self_attn, proj_name)
        target_dims.append((proj.in_features, proj.out_features))

    available_head_indices = sorted({
        int(key.split(".")[1])
        for key in ckpt_hypernet_state
        if key.startswith("bias_heads.") and key.endswith(".weight")
    })

    hypernet = ActivationBiasHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to(args.qwen_device).float()

    backbone_keys = {k: v for k, v in ckpt_hypernet_state.items() if k.startswith("backbone.")}
    hypernet.load_state_dict(backbone_keys, strict=False)
    for mapped_idx, ckpt_head_idx in enumerate(available_head_indices[:len(target_dims)]):
        head_keys = {
            k.replace(f"bias_heads.{ckpt_head_idx}.", ""): v
            for k, v in ckpt_hypernet_state.items()
            if k.startswith(f"bias_heads.{ckpt_head_idx}.")
        }
        hypernet.bias_heads[mapped_idx].load_state_dict(head_keys)
    hypernet.eval()

    # ═══════════════════════════════════════════════════════════════
    # STAGE 1: Raw Mamba states after masking
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  STAGE 1: Raw Mamba Layer 3 states after masking")
    print("=" * 70)

    raw_states = {}
    for mode, dims in mask_library.items():
        masked = raw_state.clone()
        if dims:
            masked[..., dims] = 0.0
        raw_states[mode] = masked.to(args.qwen_device)
        energy_removed = float(raw_state[..., dims].pow(2).sum() / raw_state.pow(2).sum()) if dims else 0.0
        print(f"  {mode:>20s}: norm {masked.norm():.4f} (energy removed: {100*energy_removed:.1f}%)")

    raw_matrix = pairwise_cosine_matrix(raw_states)
    print_matrix(raw_matrix, "STAGE 1: Raw state cosine matrix")

    # ═══════════════════════════════════════════════════════════════
    # STAGE 2: Compressed context vectors
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  STAGE 2: Compressed context vectors")
    print("=" * 70)

    contexts = {}
    with torch.no_grad():
        for mode, state in raw_states.items():
            ctx = compressor(state.unsqueeze(0) if state.dim() == 1 else state)
            contexts[mode] = ctx.squeeze(0)
            print(f"  {mode:>20s}: norm {contexts[mode].norm():.4f}")

    ctx_matrix = pairwise_cosine_matrix(contexts)
    print_matrix(ctx_matrix, "STAGE 2: Compressed context cosine matrix")

    # ═══════════════════════════════════════════════════════════════
    # STAGE 3: Hypernetwork bias vectors
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  STAGE 3: Hypernetwork bias vectors (per layer)")
    print("=" * 70)

    all_biases = {}  # mode -> list of bias tensors
    with torch.no_grad():
        for mode, ctx in contexts.items():
            biases = hypernet(ctx.unsqueeze(0) if ctx.dim() == 1 else ctx)
            all_biases[mode] = biases
            norms = [f"{b.norm():.4f}" for b in biases]
            print(f"  {mode:>20s}: bias norms = [{', '.join(norms)}]")

    # Per-layer bias cosine matrices
    layer_bias_matrices = {}
    for layer_i in range(len(target_dims)):
        layer_label = f"L{target_layer_specs[layer_i][0]}:{target_layer_specs[layer_i][1]}"
        layer_biases = {mode: biases[layer_i].squeeze(0) for mode, biases in all_biases.items()}
        matrix = pairwise_cosine_matrix(layer_biases)
        layer_bias_matrices[layer_label] = matrix
        print_matrix(matrix, f"STAGE 3: Bias cosine — {layer_label}")

    # Concatenated bias vector (all layers combined)
    concat_biases = {
        mode: torch.cat([b.squeeze(0) for b in biases])
        for mode, biases in all_biases.items()
    }
    concat_matrix = pairwise_cosine_matrix(concat_biases)
    print_matrix(concat_matrix, "STAGE 3: Bias cosine — ALL LAYERS CONCATENATED")
    allzero_bias_norm_ratio = float(
        concat_biases["all_zero"].norm().item() / concat_biases["none"].norm().item()
    ) if float(concat_biases["none"].norm().item()) > 0 else 0.0

    # ═══════════════════════════════════════════════════════════════
    # DIAGNOSIS
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  DIAGNOSIS: Where does the signal die?")
    print("=" * 70)

    # Key comparisons: none vs persistent_zero at each stage
    key_pairs = [
        ("none", "persistent_zero"),
        ("none", "variable_zero"),
        ("none", "middle_zero"),
        ("none", "all_zero"),
    ]

    print(f"\n  {'Comparison':<30s} {'Raw State':>12s} {'Compressed':>12s} {'Bias(cat)':>12s}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12}")

    for a, b in key_pairs:
        raw_cos = raw_matrix[a][b]
        ctx_cos = ctx_matrix[a][b]
        bias_cos = concat_matrix[a][b]
        label = f"{a} vs {b}"
        print(f"  {label:<30s} {raw_cos:12.4f} {ctx_cos:12.4f} {bias_cos:12.4f}")

    # The knife: all_zero
    print(f"\n  THE KNIFE (all_zero):")
    print(f"    Raw state norm after zeroing everything: {raw_states['all_zero'].norm():.6f}")
    print(f"    Compressed context norm from zero input: {contexts['all_zero'].norm():.6f}")
    print(f"    Bias norms from zero input: {[f'{b.norm():.4f}' for b in all_biases['all_zero']]}")
    print(f"    none vs all_zero (compressed): {ctx_matrix['none']['all_zero']:.6f}")
    print(f"    none vs all_zero (bias concat): {concat_matrix['none']['all_zero']:.6f}")
    print(f"    all_zero bias norm ratio vs none: {allzero_bias_norm_ratio:.6f}")

    if concat_matrix["none"]["all_zero"] > 0.95 and allzero_bias_norm_ratio > 0.95:
        print(f"\n  ⚠ CONSTANT BIAS DETECTED: all_zero bias cosine to none = {concat_matrix['none']['all_zero']:.4f}")
        print(f"    The bridge is effectively context-blind. Mamba input does not change the output.")
        print(f"    The entire Mamba→compress→hypernetwork pipeline may be a constant-bias generator.")
    elif concat_matrix["none"]["all_zero"] > 0.95:
        print(f"\n  ⚠ SAME DIRECTION, DIFFERENT MAGNITUDE: all_zero stays highly aligned to none")
        print(f"    Bias cosine is {concat_matrix['none']['all_zero']:.4f}, but norm ratio is {allzero_bias_norm_ratio:.4f}.")
        print(f"    This is attenuated-context behavior, not clean constant-bias proof.")
    elif ctx_matrix["none"]["all_zero"] > 0.95:
        print(f"\n  ⚠ COMPRESSOR WALL: compressed contexts are identical regardless of input.")
        print(f"    But the hypernetwork amplifies small differences into bias space.")
    else:
        print(f"\n  ✓ Signal survives through the pipeline. Check behavioral tests for Qwen sensitivity.")

    # ── Save results ──
    results = {
        "experiment": "bridge_pipeline_diagnosis",
        "author": "Purple",
        "date": "2026-04-08",
        "config": {
            "bridge_path": str(bridge_path.name),
            "episode_index": args.episode_index,
            "episode_title": episode["title"],
            "mamba_target_layer": mamba_target_layer,
            "context_dim": context_dim,
            "target_layer_specs": [f"{l}:{p}" for l, p in target_layer_specs],
            "d_model": d_model,
        },
        "mask_dims": {mode: len(dims) for mode, dims in mask_library.items()},
        "stage1_raw_state": {
            "norms": {mode: round(float(s.norm()), 6) for mode, s in raw_states.items()},
            "cosine_matrix": raw_matrix,
        },
        "stage2_compressed": {
            "norms": {mode: round(float(c.norm()), 6) for mode, c in contexts.items()},
            "cosine_matrix": ctx_matrix,
        },
        "stage3_bias_concat": {
            "norms": {mode: round(float(v.norm()), 6) for mode, v in concat_biases.items()},
            "cosine_matrix": concat_matrix,
        },
        "stage3_bias_per_layer": layer_bias_matrices,
        "key_comparisons": {
            f"{a}_vs_{b}": {
                "raw_state": raw_matrix[a][b],
                "compressed": ctx_matrix[a][b],
                "bias_concat": concat_matrix[a][b],
            }
            for a, b in key_pairs
        },
        "all_zero_knife": {
            "raw_norm": round(float(raw_states["all_zero"].norm()), 6),
            "compressed_norm": round(float(contexts["all_zero"].norm()), 6),
            "bias_norms": [round(float(b.norm()), 6) for b in all_biases["all_zero"]],
            "none_vs_allzero_compressed": ctx_matrix["none"]["all_zero"],
            "none_vs_allzero_bias": concat_matrix["none"]["all_zero"],
            "allzero_bias_norm_ratio": round(allzero_bias_norm_ratio, 6),
        },
    }

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
