"""
bias_analysis.py — Steps 1 + 3 of the MoCoP Experiment Ladder.

Runs entirely on CPU. No Qwen, no Mamba, no GPU needed.
Loads only the hypernetwork from a checkpoint plus saved context vectors.

Computes:
  1. Per-sample bias vectors from the hypernetwork
  2. Full pairwise cosine similarity matrix
  3. Within-kind and between-kind statistics
  4. Bias PCA (effective rank, variance explained)
  5. C2 control: random bias vectors of same norm → cosine comparison
  6. C3 control: fixed-mean bias → cosine distance from per-sample biases

Usage:
  python bias_analysis.py --run-dir run_actbias --epoch 3
  python bias_analysis.py --run-dir run_actbias --epoch 3 --output report.json

Author: Cassian (Claude Opus 4.6)
Date: 2026-03-17
"""

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np

# Add parent dir so we can import models.py
sys.path.insert(0, str(Path(__file__).parent))
from models import build_activation_bias_hypernetwork


def load_hypernetwork_from_checkpoint(checkpoint_path: Path) -> tuple:
    """Load only the hypernetwork from a bridge checkpoint. CPU only."""
    print(f"Loading checkpoint: {checkpoint_path} (CPU only, extracting hypernetwork)")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    bridge_config = ckpt["bridge_config"]
    target_specs = ckpt["target_specs"]
    bridge_mode = ckpt.get("bridge_mode", "lora")

    if bridge_mode not in {"activation_bias", "gated_activation_bias"}:
        print(f"WARNING: checkpoint bridge_mode is '{bridge_mode}', not an activation-bias mode.")
        print("Bias analysis may not be meaningful for this checkpoint.")

    # Reconstruct target_dims from the hypernetwork state dict
    # ActivationBiasHypernetwork uses (in_dim, out_dim) tuples but only reads out_dim
    # bias_heads.N.bias has shape (out_dim,) for each target layer
    hsd = ckpt["hypernetwork_state_dict"]
    num_heads = sum(1 for k in hsd if k.startswith("bias_heads.") and k.endswith(".bias"))
    target_dims = [(0, hsd[f"bias_heads.{i}.bias"].shape[0]) for i in range(num_heads)]

    context_dim = bridge_config.get("context_dim", 2048)
    hidden_dim = bridge_config.get("hyper_hidden_dim", 1024)

    hypernet = build_activation_bias_hypernetwork(
        bridge_mode=bridge_mode,
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=hidden_dim,
        gate_kind=bridge_config.get("gate_kind", "vector"),
        initial_gate=float(bridge_config.get("initial_gate", 0.1)),
    )
    hypernet.load_state_dict(ckpt["hypernetwork_state_dict"])
    hypernet.eval()

    print(f"  bridge_mode: {bridge_mode}")
    print(f"  context_dim: {context_dim}")
    print(f"  target_layers: {len(target_dims)}")
    print(f"  target_dims: {target_dims}")

    return hypernet, ckpt


def load_contexts_and_predictions(run_dir: Path, epoch: int) -> tuple:
    """Load saved context vectors and prediction JSON for an epoch."""
    train_path = run_dir / f"train_epoch_{epoch:03d}_contexts.pt"
    eval_path = run_dir / f"eval_epoch_{epoch:03d}_contexts.pt"
    pred_path = run_dir / f"eval_epoch_{epoch:03d}_predictions.json"

    train_raw = torch.load(train_path, map_location="cpu", weights_only=False) if train_path.exists() else None
    eval_raw = torch.load(eval_path, map_location="cpu", weights_only=False) if eval_path.exists() else None

    # Contexts may be list-of-dicts with 'context_vector' key, or raw tensors
    def extract_contexts(raw):
        if raw is None:
            return None, []
        if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict):
            vectors = torch.stack([d["context_vector"] for d in raw])
            fact_kinds = [d.get("fact_kind", "unknown") for d in raw]
            return vectors, fact_kinds
        if isinstance(raw, torch.Tensor):
            return raw, ["unknown"] * raw.shape[0]
        if isinstance(raw, dict) and "context_vectors" in raw:
            return raw["context_vectors"], ["unknown"] * raw["context_vectors"].shape[0]
        raise ValueError(f"Unknown context format: {type(raw)}")

    train_ctx, train_kinds = extract_contexts(train_raw)
    eval_ctx, eval_kinds = extract_contexts(eval_raw)

    predictions = None
    if pred_path.exists():
        with open(pred_path, "r", encoding="utf-8") as f:
            predictions = json.load(f)

    if train_ctx is not None:
        print(f"  Train contexts: {train_ctx.shape}, {len(set(train_kinds))} fact kinds")
    if eval_ctx is not None:
        print(f"  Eval contexts: {eval_ctx.shape}, {len(set(eval_kinds))} fact kinds")
    if predictions is not None:
        print(f"  Predictions: {len(predictions)} samples")

    return train_ctx, eval_ctx, predictions, train_kinds, eval_kinds


def get_bias_vectors(hypernet, contexts: torch.Tensor) -> torch.Tensor:
    """Forward contexts through hypernetwork, concatenate all layer biases into one vector per sample."""
    with torch.no_grad():
        biases_per_layer = hypernet(contexts)
    # Concatenate all layers: list of (batch, out_dim_i) → (batch, sum(out_dim_i))
    return torch.cat(biases_per_layer, dim=-1)


def pairwise_cosine(vectors: torch.Tensor) -> np.ndarray:
    """Compute full pairwise cosine similarity matrix."""
    normed = F.normalize(vectors.float(), dim=-1)
    return (normed @ normed.T).numpy()


def analyze_cosine_by_fact_kind(cosine_matrix: np.ndarray, fact_kinds: list) -> dict:
    """Compute within-kind and between-kind cosine statistics."""
    n = len(fact_kinds)
    unique_kinds = sorted(set(fact_kinds))

    within = {}
    between_pairs = []

    for kind in unique_kinds:
        indices = [i for i, fk in enumerate(fact_kinds) if fk == kind]
        if len(indices) < 2:
            within[kind] = {"mean": float("nan"), "count": 0}
            continue
        pairs = []
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                pairs.append(cosine_matrix[indices[i], indices[j]])
        within[kind] = {
            "mean": float(np.mean(pairs)),
            "std": float(np.std(pairs)),
            "min": float(np.min(pairs)),
            "max": float(np.max(pairs)),
            "count": len(pairs),
        }

    # Between-kind: all pairs where fact_kind differs
    between_values = []
    for i in range(n):
        for j in range(i + 1, n):
            if fact_kinds[i] != fact_kinds[j]:
                between_values.append(cosine_matrix[i, j])

    between_summary = {
        "mean": float(np.mean(between_values)),
        "std": float(np.std(between_values)),
        "min": float(np.min(between_values)),
        "max": float(np.max(between_values)),
        "count": len(between_values),
    }

    return {"within_kind": within, "between_kind": between_summary, "unique_kinds": unique_kinds}


def pca_analysis(vectors: torch.Tensor) -> dict:
    """PCA on bias vectors: effective rank, variance explained."""
    X = vectors.float().numpy()
    X_centered = X - X.mean(axis=0)
    if X_centered.shape[0] < 2:
        return {"error": "need at least 2 samples"}

    _, S, _ = np.linalg.svd(X_centered, full_matrices=False)
    var_explained = (S ** 2) / (S ** 2).sum()
    cumulative = np.cumsum(var_explained)

    # Effective rank (exponential of entropy of normalized singular values)
    p = (S ** 2) / (S ** 2).sum()
    p = p[p > 1e-12]
    effective_rank = float(np.exp(-np.sum(p * np.log(p))))

    return {
        "effective_rank": effective_rank,
        "total_dims": X.shape[1],
        "pc1_variance": float(var_explained[0]),
        "pc1_pc2_variance": float(cumulative[1]) if len(cumulative) > 1 else float(cumulative[0]),
        "dims_at_90pct": int(np.searchsorted(cumulative, 0.9) + 1),
        "dims_at_99pct": int(np.searchsorted(cumulative, 0.99) + 1),
        "top5_variance": [float(v) for v in var_explained[:5]],
    }


def random_bias_control(bias_vectors: torch.Tensor, n_trials: int = 10) -> dict:
    """C2: Generate random bias vectors of same per-sample L2 norm. Report cosine stats."""
    norms = bias_vectors.float().norm(dim=-1, keepdim=True)
    mean_norm = float(norms.mean())

    trial_means = []
    for _ in range(n_trials):
        random_vecs = torch.randn_like(bias_vectors.float())
        random_vecs = F.normalize(random_vecs, dim=-1) * norms
        cos_matrix = pairwise_cosine(random_vecs)
        # Upper triangle only
        n = cos_matrix.shape[0]
        upper = cos_matrix[np.triu_indices(n, k=1)]
        trial_means.append(float(np.mean(upper)))

    return {
        "mean_norm": mean_norm,
        "random_cosine_mean": float(np.mean(trial_means)),
        "random_cosine_std": float(np.std(trial_means)),
        "interpretation": (
            "If trained bias cosine ≈ random cosine, the learned directions carry no structure. "
            "If trained >> random, the hypernetwork learned meaningful directions."
        ),
    }


def fixed_mean_control(bias_vectors: torch.Tensor) -> dict:
    """C3: Compute mean bias vector, measure cosine distance from per-sample biases."""
    mean_bias = bias_vectors.float().mean(dim=0, keepdim=True)
    per_sample_cos = F.cosine_similarity(bias_vectors.float(), mean_bias.expand_as(bias_vectors.float()), dim=-1)

    return {
        "mean_bias_norm": float(mean_bias.norm()),
        "cosine_to_mean_mean": float(per_sample_cos.mean()),
        "cosine_to_mean_std": float(per_sample_cos.std()),
        "cosine_to_mean_min": float(per_sample_cos.min()),
        "cosine_to_mean_max": float(per_sample_cos.max()),
        "interpretation": (
            "If cosine_to_mean ≈ 1.0 for all samples, the bias is effectively constant. "
            "If there is meaningful spread, per-sample variation exists."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Bias diversity analysis (Steps 1+3 of Experiment Ladder)")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory with checkpoints + contexts")
    parser.add_argument("--epoch", type=int, default=3, help="Which epoch's contexts to analyze")
    parser.add_argument("--output", type=str, default="", help="Output JSON path (default: run_dir/bias_analysis.json)")
    parser.add_argument("--random-trials", type=int, default=10, help="Number of random trials for C2 control")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    checkpoint_path = run_dir / "bridge_best.pt"
    if not checkpoint_path.exists():
        print(f"ERROR: {checkpoint_path} not found")
        return 1

    # Load hypernetwork
    hypernet, ckpt = load_hypernetwork_from_checkpoint(checkpoint_path)

    # Load contexts and predictions
    print(f"\nLoading epoch {args.epoch} data...")
    train_ctx, eval_ctx, predictions, train_kinds, eval_kinds = load_contexts_and_predictions(run_dir, args.epoch)

    # Prefer fact kinds from context files, fall back to predictions
    if not eval_kinds or all(k == "unknown" for k in eval_kinds):
        if predictions:
            eval_kinds = [p["fact_kind"] for p in predictions]

    results = {"run_dir": str(run_dir), "epoch": args.epoch, "bridge_mode": ckpt.get("bridge_mode", "unknown")}

    # --- BIAS VECTORS ---
    for split_name, contexts, fact_kinds in [
        ("train", train_ctx, train_kinds),
        ("eval", eval_ctx, eval_kinds),
    ]:
        if contexts is None:
            continue

        print(f"\n{'='*60}")
        print(f"Analyzing {split_name} split ({contexts.shape[0]} samples)")
        print(f"{'='*60}")

        bias_vecs = get_bias_vectors(hypernet, contexts)
        print(f"  Bias vector shape: {bias_vecs.shape}")
        print(f"  Bias L2 norms: mean={bias_vecs.float().norm(dim=-1).mean():.4f}, "
              f"std={bias_vecs.float().norm(dim=-1).std():.4f}")

        # Pairwise cosine
        cos_matrix = pairwise_cosine(bias_vecs)
        n = cos_matrix.shape[0]
        upper = cos_matrix[np.triu_indices(n, k=1)]

        cosine_stats = {
            "mean": float(np.mean(upper)),
            "std": float(np.std(upper)),
            "min": float(np.min(upper)),
            "max": float(np.max(upper)),
            "pct_above_090": float(np.mean(upper > 0.90) * 100),
            "pct_above_095": float(np.mean(upper > 0.95) * 100),
            "pct_above_099": float(np.mean(upper > 0.99) * 100),
        }
        print(f"\n  Pairwise cosine: mean={cosine_stats['mean']:.4f}, "
              f"std={cosine_stats['std']:.4f}")
        print(f"  >0.90: {cosine_stats['pct_above_090']:.1f}%, "
              f">0.95: {cosine_stats['pct_above_095']:.1f}%, "
              f">0.99: {cosine_stats['pct_above_099']:.1f}%")

        # PCA
        pca = pca_analysis(bias_vecs)
        print(f"\n  PCA: effective_rank={pca['effective_rank']:.2f}/{pca['total_dims']}, "
              f"PC1={pca['pc1_variance']*100:.1f}%")

        # C2: Random bias control
        random_ctrl = random_bias_control(bias_vecs, n_trials=args.random_trials)
        print(f"\n  C2 Random control: random cosine mean={random_ctrl['random_cosine_mean']:.4f} "
              f"(vs trained {cosine_stats['mean']:.4f})")

        # C3: Fixed-mean control
        mean_ctrl = fixed_mean_control(bias_vecs)
        print(f"  C3 Fixed-mean control: cosine-to-mean={mean_ctrl['cosine_to_mean_mean']:.4f} "
              f"(std={mean_ctrl['cosine_to_mean_std']:.4f})")

        # Fact-kind analysis (eval only)
        kind_analysis = None
        if fact_kinds:
            kind_analysis = analyze_cosine_by_fact_kind(cos_matrix, fact_kinds)
            print(f"\n  Fact-kind analysis:")
            print(f"  Between-kind cosine: {kind_analysis['between_kind']['mean']:.4f}")
            print(f"  Within-kind cosines:")
            for kind in kind_analysis["unique_kinds"]:
                wk = kind_analysis["within_kind"].get(kind, {})
                if wk.get("count", 0) > 0:
                    print(f"    {kind:25s}: {wk['mean']:.4f} (n={wk['count']})")

        results[split_name] = {
            "n_samples": contexts.shape[0],
            "bias_shape": list(bias_vecs.shape),
            "cosine": cosine_stats,
            "pca": pca,
            "c2_random_control": random_ctrl,
            "c3_fixed_mean_control": mean_ctrl,
        }
        if kind_analysis:
            results[split_name]["fact_kind_analysis"] = kind_analysis

    # --- VERDICTS ---
    print(f"\n{'='*60}")
    print("VERDICTS")
    print(f"{'='*60}")

    if "eval" in results:
        ev = results["eval"]
        cos_mean = ev["cosine"]["mean"]
        eff_rank = ev["pca"]["effective_rank"]
        random_cos = ev["c2_random_control"]["random_cosine_mean"]
        mean_cos = ev["c3_fixed_mean_control"]["cosine_to_mean_mean"]

        print(f"\n  Bias cosine mean:     {cos_mean:.4f}")
        print(f"  Random cosine mean:   {random_cos:.4f}")
        print(f"  Cosine to mean bias:  {mean_cos:.4f}")
        print(f"  Bias effective rank:  {eff_rank:.2f}")

        if cos_mean > 0.95:
            print("\n  VERDICT: Bias is effectively constant. Step 1 FAIL (constant offset).")
        elif cos_mean > 0.80:
            print("\n  VERDICT: Gray zone. Some variation exists but limited.")
        else:
            print("\n  VERDICT: Meaningful per-sample variation. Step 1 tentative PASS.")

        if random_cos > cos_mean - 0.05:
            print("  C2: Trained bias structure is NOT significantly above random. RED FLAG.")
        else:
            print(f"  C2: Trained bias is more structured than random ({cos_mean:.3f} vs {random_cos:.3f}). GOOD.")

        if mean_cos > 0.99:
            print("  C3: Per-sample biases are near-identical to the mean. Effectively constant. RED FLAG.")
        elif mean_cos > 0.95:
            print("  C3: Per-sample biases have very limited variation around the mean.")
        else:
            print(f"  C3: Meaningful spread around mean bias (cos={mean_cos:.4f}). GOOD.")

        if "fact_kind_analysis" in ev:
            fka = ev["fact_kind_analysis"]
            between = fka["between_kind"]["mean"]
            within_means = [v["mean"] for v in fka["within_kind"].values() if v.get("count", 0) > 0]
            avg_within = np.mean(within_means) if within_means else 0
            if between < avg_within - 0.05:
                print(f"  Fact-kind separation: between ({between:.3f}) < within ({avg_within:.3f}). "
                      f"Clusters ARE separated. GOOD.")
            else:
                print(f"  Fact-kind separation: between ({between:.3f}) ≈ within ({avg_within:.3f}). "
                      f"No meaningful clustering. WEAK.")

    # Save results
    output_path = Path(args.output) if args.output else run_dir / "bias_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
