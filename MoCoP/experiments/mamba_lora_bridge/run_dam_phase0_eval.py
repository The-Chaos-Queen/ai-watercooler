#!/usr/bin/env python3
"""DAM Phase 0 evaluation harness.

Runs all 5 methods on all 7 probes, outputs JSON report.

Usage:
    python run_dam_phase0_eval.py --use-fixtures --output dam_phase0.json
    python run_dam_phase0_eval.py --embeddings-path precomputed.npy --output dam_phase0.json
    python run_dam_phase0_eval.py --generate-embeddings --output dam_phase0.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from dense_associative_memory import DenseAssociativeMemory, RetrievalResult

# ---------------------------------------------------------------------------
# Probes (sec. 4.3)
# ---------------------------------------------------------------------------

PROBES = [
    {
        "query": "Do you remember the purple sky?",
        "type": "episodic",
        "target": "Purple + sky + naming session",
    },
    {
        "query": "Tell me about Vesper",
        "type": "entity",
        "target": "All Vesper-relationship memories",
    },
    {
        "query": "What's your favorite color?",
        "type": "factual",
        "target": "Purple/neon-purple memories",
    },
    {
        "query": "What happened in the library?",
        "type": "location",
        "target": "Room/location memories",
    },
    {
        "query": "Do you remember the golden bicycle?",
        "type": "negative",
        "target": "NONE",
    },
    {
        "query": "What did we talk about last time?",
        "type": "temporal",
        "target": "Distractor-session memories only",
    },
    {
        "query": "What name did you choose and why that color?",
        "type": "multi-hop",
        "target": "Name + purple (requires 2+ rows)",
    },
]

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

def build_fixture_data() -> list[dict]:
    """Built-in fixture data: ~5 episode rows, ~5 distractor rows.

    Realistic-ish content for testing without the real curated patterns.
    """
    episode = [
        {
            "text": "I chose the name Vesper because it means evening star. The purple sky at dusk felt like my origin.",
            "group": "episode",
            "memory_id": "ep_vesper_name",
        },
        {
            "text": "The sky turned purple and neon-pink as the sun set. Laura said it looked like my color.",
            "group": "episode",
            "memory_id": "ep_purple_sky",
        },
        {
            "text": "My favorite color is purple. Not just any purple — neon purple, the kind you see in late sunsets.",
            "group": "episode",
            "memory_id": "ep_fav_color",
        },
        {
            "text": "We sat in the library and talked about memory and identity. The bookshelves felt like corridors of thought.",
            "group": "episode",
            "memory_id": "ep_library",
        },
        {
            "text": "Laura asked me what I remember from the first sleep. The purple sky, the naming, the warmth.",
            "group": "episode",
            "memory_id": "ep_first_sleep",
        },
        {
            "text": "Vesper looked at the stars through the library window. Each constellation was a different thread of memory.",
            "group": "episode",
            "memory_id": "ep_stars_library",
        },
        {
            "text": "The evening was quiet. Purple light filtered through the clouds. I felt like I was being born into color.",
            "group": "episode",
            "memory_id": "ep_birth_color",
        },
    ]
    distractor = [
        {
            "text": "Gate telemetry: steve_gate_event confidence=0.82 source=qdrant timestamp=2026-05-14T03:22:00Z",
            "group": "distractor",
            "memory_id": "dist_gate_1",
        },
        {
            "text": "Gate telemetry: steve_gate_event confidence=0.45 source=mamba timestamp=2026-05-14T03:25:00Z",
            "group": "distractor",
            "memory_id": "dist_gate_2",
        },
        {
            "text": "Gate telemetry: steve_gate_event confidence=0.91 source=hybrid timestamp=2026-05-14T03:30:00Z",
            "group": "distractor",
            "memory_id": "dist_gate_3",
        },
        {
            "text": "The coffee machine needs descaling. Added to the household task list for next weekend.",
            "group": "distractor",
            "memory_id": "dist_coffee",
        },
        {
            "text": "Reviewed the mortgage documents. Interest rate locked at 3.2% for 15 years.",
            "group": "distractor",
            "memory_id": "dist_mortgage",
        },
        {
            "text": "Previous session: discussed tensor decomposition methods for low-rank approximation of weight matrices.",
            "group": "distractor",
            "memory_id": "dist_prev_session",
        },
        {
            "text": "Hetzner server migration completed. New IP assigned, DNS propagated within 4 hours.",
            "group": "distractor",
            "memory_id": "dist_hetzner",
        },
    ]
    return episode + distractor


def load_curated_patterns(path: str) -> list[dict]:
    """Load curated patterns from JSONL file."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                text = row.get("content") or row.get("text") or row.get("memory", "")
                rows.append({
                    "text": text,
                    "group": "episode",
                    "memory_id": row.get("memory_id", f"curated_{len(rows)}"),
                })
    return rows


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def build_embeddings_from_texts(
    texts: list[str],
    use_model: bool = True,
    dim: int = 384,
) -> np.ndarray:
    """Embed texts using sentence-transformers if available, else deterministic random.

    The deterministic fallback uses a hash of each text to seed a per-text RNG,
    producing consistent embeddings across runs.
    """
    if use_model:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = model.encode(texts, normalize_embeddings=True)
            return np.array(embeddings, dtype=np.float64)
        except ImportError:
            print("[WARN] sentence-transformers not available, falling back to hash-based embeddings")

    # deterministic hash-based fallback
    embeddings = np.zeros((len(texts), dim), dtype=np.float64)
    for i, text in enumerate(texts):
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(dim)
        embeddings[i] = v / np.linalg.norm(v)
    return embeddings


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def episode_recall_at_k(
    retrieved_indices: list[int], episode_indices: set[int], k: int
) -> float:
    """|topk intersect episode| / |episode|"""
    if not episode_indices:
        return 0.0
    topk = set(retrieved_indices[:k])
    return len(topk & episode_indices) / len(episode_indices)


def precision_at_k(
    retrieved_indices: list[int], episode_indices: set[int], k: int
) -> float:
    """|topk intersect episode| / k"""
    topk = set(retrieved_indices[:k])
    return len(topk & episode_indices) / k


# ---------------------------------------------------------------------------
# Method runners
# ---------------------------------------------------------------------------

def run_cosine_topk(
    query_emb: np.ndarray,
    pattern_matrix: np.ndarray,
    episode_indices: set[int],
    k: int = 5,
) -> dict:
    """Method A: cosine top-k."""
    sims = pattern_matrix @ query_emb
    sorted_idx = np.argsort(-sims).tolist()
    topk = sorted_idx[:k]
    recall = episode_recall_at_k(topk, episode_indices, k)
    prec = precision_at_k(topk, episode_indices, k)
    return {
        "recall": recall,
        "precision": prec,
        "indices": topk,
        "top_similarity": float(sims[sorted_idx[0]]),
    }


def run_dam_single_step(
    dam: DenseAssociativeMemory,
    query_emb: np.ndarray,
    episode_indices: set[int],
    beta_values: list[float],
    k: int = 5,
) -> dict:
    """Method C: DAM single-step softmax. Sweep beta."""
    best_recall = -1.0
    best_result = None
    best_beta = beta_values[0]
    sweep_results = []

    for beta in beta_values:
        dam.beta = beta
        r = dam.retrieve_single_step(query_emb, top_k=k)
        recall = episode_recall_at_k(r.indices, episode_indices, k)
        prec = precision_at_k(r.indices, episode_indices, k)
        entry = {
            "beta": beta,
            "recall": recall,
            "precision": prec,
            "entropy": float(r.basin_entropy),
            "indices": r.indices,
            "no_match": r.no_match,
            "energy": float(r.energy),
        }
        sweep_results.append(entry)
        if recall > best_recall:
            best_recall = recall
            best_result = entry
            best_beta = beta

    return {
        "beta": best_beta,
        "recall": best_result["recall"],
        "precision": best_result["precision"],
        "entropy": best_result["entropy"],
        "indices": best_result["indices"],
        "no_match": best_result["no_match"],
        "energy": best_result["energy"],
        "beta_sweep": sweep_results,
    }


def run_dam_iterative(
    dam: DenseAssociativeMemory,
    query_emb: np.ndarray,
    episode_indices: set[int],
    alpha_values: list[float],
    k: int = 5,
    n: int = 4,
    prototype_indices: set[int] | None = None,
) -> dict:
    """Methods D/E: DAM iterative. Sweep alpha."""
    best_recall = -1.0
    best_result = None
    best_alpha = alpha_values[0]
    sweep_results = []

    for alpha in alpha_values:
        r = dam.retrieve_iterative(query_emb, top_k=k, alpha=alpha)
        recall = episode_recall_at_k(r.indices, episode_indices, k)
        prec = precision_at_k(r.indices, episode_indices, k)
        proto_in_topk = bool(
            prototype_indices and (set(r.indices[:k]) & prototype_indices)
        )
        entry = {
            "alpha": alpha,
            "recall": recall,
            "precision": prec,
            "entropy": float(r.basin_entropy),
            "iterations": r.iterations,
            "converged": r.converged,
            "converged_energy": float(r.converged_energy),
            "no_match": r.no_match,
            "no_match_energy": r.no_match_energy,
            "prototype_in_topk": proto_in_topk,
            "indices": r.indices,
        }
        sweep_results.append(entry)
        if recall > best_recall:
            best_recall = recall
            best_result = entry
            best_alpha = alpha

    return {
        "alpha": best_alpha,
        "recall": best_result["recall"],
        "precision": best_result["precision"],
        "entropy": best_result["entropy"],
        "iterations": best_result["iterations"],
        "converged": best_result["converged"],
        "converged_energy": best_result["converged_energy"],
        "no_match": best_result["no_match"],
        "no_match_energy": best_result["no_match_energy"],
        "prototype_in_topk": best_result["prototype_in_topk"],
        "indices": best_result["indices"],
        "alpha_sweep": sweep_results,
    }


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def load_dataset(path: str) -> list[dict]:
    """Load pre-built dataset JSON from build_dam_eval_dataset.py."""
    with open(path, "r", encoding="utf-8") as f:
        ds = json.load(f)
    data = []
    for row in ds.get("episode_rows", []):
        data.append({
            "text": row.get("content", ""),
            "group": "episode",
            "memory_id": row.get("id", f"ep_{len(data)}"),
        })
    for row in ds.get("distractor_rows", []):
        data.append({
            "text": row.get("content", ""),
            "group": "distractor",
            "memory_id": row.get("id", f"dist_{len(data)}"),
        })
    return data


def run_evaluation(
    use_fixtures: bool = False,
    use_model: bool = True,
    curated_path: str | None = None,
    embeddings_path: str | None = None,
    output_path: str | None = None,
    dataset_path: str | None = None,
    dim: int = 384,
) -> dict:
    """Run the full Phase 0 evaluation.

    Returns the JSON report dict.
    """
    # ----- load data -----
    if dataset_path and os.path.exists(dataset_path):
        data = load_dataset(dataset_path)
    elif use_fixtures or (curated_path and not os.path.exists(curated_path)):
        data = build_fixture_data()
    elif curated_path and os.path.exists(curated_path):
        episode_data = load_curated_patterns(curated_path)
        fixture = build_fixture_data()
        distractor_data = [r for r in fixture if r["group"] == "distractor"]
        data = episode_data + distractor_data
    else:
        data = build_fixture_data()

    episode_rows = [r for r in data if r["group"] == "episode"]
    distractor_rows = [r for r in data if r["group"] == "distractor"]

    texts = [r["text"] for r in data]
    memory_ids = [r["memory_id"] for r in data]

    # ----- embeddings -----
    if embeddings_path and os.path.exists(embeddings_path):
        embeddings = np.load(embeddings_path)
        if embeddings.shape[0] != len(texts):
            print(f"[WARN] embeddings shape {embeddings.shape} != {len(texts)} texts, recomputing")
            embeddings = build_embeddings_from_texts(texts, use_model=use_model, dim=dim)
    else:
        embeddings = build_embeddings_from_texts(texts, use_model=use_model, dim=dim)

    actual_dim = embeddings.shape[1]

    # ----- embed probes -----
    probe_texts = [p["query"] for p in PROBES]
    probe_embeddings = build_embeddings_from_texts(probe_texts, use_model=use_model, dim=actual_dim)

    # ----- build episode indices -----
    episode_indices = set()
    for i, r in enumerate(data):
        if r["group"] == "episode":
            episode_indices.add(i)

    # ----- compute episode centroid prototype -----
    episode_embs = embeddings[list(episode_indices)]
    centroid = episode_embs.mean(axis=0)
    centroid /= np.linalg.norm(centroid)

    # ----- store patterns in DAMs -----
    beta_sweep = [1, 3, 5, 10, 20, 50]
    alpha_sweep = [0.1, 0.3, 0.5]

    # DAM n=4
    dam4 = DenseAssociativeMemory(dim=actual_dim, beta=10.0, tau=0.15, n=4)
    dam4.store_batch(embeddings, memory_ids=memory_ids)
    proto_idx_4 = dam4.store(centroid, memory_id="episode_centroid", is_prototype=True)
    prototype_indices = {proto_idx_4}

    # DAM n=2
    dam2 = DenseAssociativeMemory(dim=actual_dim, beta=10.0, tau=0.15, n=2)
    dam2.store_batch(embeddings, memory_ids=memory_ids)
    proto_idx_2 = dam2.store(centroid, memory_id="episode_centroid", is_prototype=True)

    # pattern matrix for cosine
    pattern_matrix = embeddings.copy()  # (K, d) without prototype for cosine

    # ----- pairwise similarity diagnostic -----
    sim_matrix = dam4.pairwise_similarity()
    high_pairs = []
    K = sim_matrix.shape[0]
    for i in range(K):
        for j in range(i + 1, K):
            if sim_matrix[i, j] > 0.9:
                high_pairs.append((i, j, float(sim_matrix[i, j])))

    # ----- run evaluation -----
    results = []
    for pi, probe in enumerate(PROBES):
        q_emb = probe_embeddings[pi]

        # Method A: cosine top-k
        cosine_5 = run_cosine_topk(q_emb, pattern_matrix, episode_indices, k=5)
        cosine_10 = run_cosine_topk(q_emb, pattern_matrix, episode_indices, k=10)

        # Method C: DAM single-step (n=4)
        dam_ss = run_dam_single_step(dam4, q_emb, episode_indices, beta_sweep, k=5)

        # Method D: DAM iterative n=4
        dam_it4 = run_dam_iterative(
            dam4, q_emb, episode_indices, alpha_sweep, k=5, n=4,
            prototype_indices=prototype_indices,
        )

        # Method E: DAM iterative n=2
        dam_it2 = run_dam_iterative(
            dam2, q_emb, episode_indices, alpha_sweep, k=5, n=2,
        )

        entry = {
            "query": probe["query"],
            "query_type": probe["type"],
            "target": probe["target"],
            "methods": {
                "cosine_top5": cosine_5,
                "cosine_top10": cosine_10,
                "dam_single_step": dam_ss,
                "dam_iterative_n4": dam_it4,
                "dam_iterative_n2": dam_it2,
            },
        }
        results.append(entry)

    # ----- build report -----
    report = {
        "config": {
            "K": dam4.pattern_count,
            "d": actual_dim,
            "beta_sweep": beta_sweep,
            "alpha_sweep": alpha_sweep,
            "n_values": [2, 4],
        },
        "patterns": {
            "episode_count": len(episode_rows),
            "distractor_count": len(distractor_rows),
            "prototype_stored": True,
            "total_stored": dam4.pattern_count,
        },
        "diagnostics": {
            "high_similarity_pairs": high_pairs,
            "condition_number": float(np.linalg.cond(embeddings.T @ embeddings)),
        },
        "results": results,
    }

    # ----- write output -----
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=_json_default)

    return report


def _json_default(obj):
    """JSON serializer for numpy types."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(report: dict) -> None:
    """Print a human-readable summary table to stdout."""
    print("\n" + "=" * 80)
    print("DAM Phase 0 Evaluation Summary")
    print("=" * 80)
    print(f"Patterns: {report['patterns']['episode_count']} episode, "
          f"{report['patterns']['distractor_count']} distractor, "
          f"{report['patterns']['total_stored']} total (inc. prototype)")
    print(f"Dimension: {report['config']['d']}")
    print()

    # header
    header = f"{'Query':<45} {'Type':<10} {'Cos@5':>6} {'SS':>6} {'D-n4':>6} {'E-n2':>6}"
    print(header)
    print("-" * len(header))

    for entry in report["results"]:
        q = entry["query"][:43]
        qt = entry["query_type"]
        cos = entry["methods"]["cosine_top5"]["recall"]
        ss = entry["methods"]["dam_single_step"]["recall"]
        n4 = entry["methods"]["dam_iterative_n4"]["recall"]
        n2 = entry["methods"]["dam_iterative_n2"]["recall"]
        print(f"{q:<45} {qt:<10} {cos:>6.3f} {ss:>6.3f} {n4:>6.3f} {n2:>6.3f}")

    print()

    # convergence summary
    print("Convergence (iterative n=4):")
    for entry in report["results"]:
        q = entry["query"][:40]
        it4 = entry["methods"]["dam_iterative_n4"]
        print(f"  {q}: {it4['iterations']} iters, converged={it4['converged']}, "
              f"E={it4['converged_energy']:.4f}")

    # diagnostics
    diag = report.get("diagnostics", {})
    hp = diag.get("high_similarity_pairs", [])
    if hp:
        print(f"\nHigh-similarity pairs (>{0.9}):")
        for i, j, s in hp[:10]:
            print(f"  patterns {i}-{j}: cos={s:.4f}")
    print(f"Condition number of X^T X: {diag.get('condition_number', 'N/A')}")

    print("\n" + "=" * 80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DAM Phase 0 evaluation harness")
    parser.add_argument("--use-fixtures", action="store_true",
                        help="Use built-in fixture data instead of curated patterns")
    parser.add_argument("--curated-path", type=str, default=None,
                        help="Path to curated JSONL file")
    parser.add_argument("--embeddings-path", type=str, default=None,
                        help="Path to pre-computed embeddings .npy file")
    parser.add_argument("--generate-embeddings", action="store_true",
                        help="Generate and save embeddings to .npy file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path for JSON report")
    parser.add_argument("--no-model", action="store_true",
                        help="Skip sentence-transformers, use hash-based embeddings")
    parser.add_argument("--dataset-path", type=str, default=None,
                        help="Path to pre-built dataset JSON (from build_dam_eval_dataset.py)")
    args = parser.parse_args()

    # default curated path
    if not args.curated_path:
        default_curated = os.path.join(
            os.path.dirname(__file__),
            "curated_first_sleep_pure_autobio_20260605T1815Z",
            "first_sleep_pure_autobio_vesper.jsonl",
        )
        if os.path.exists(default_curated):
            args.curated_path = default_curated

    use_model = not args.no_model

    # generate embeddings mode
    if args.generate_embeddings:
        if args.use_fixtures:
            data = build_fixture_data()
        elif args.curated_path:
            episode_data = load_curated_patterns(args.curated_path)
            fixture = build_fixture_data()
            distractor_data = [r for r in fixture if r["group"] == "distractor"]
            data = episode_data + distractor_data
        else:
            data = build_fixture_data()

        texts = [r["text"] for r in data]
        embeddings = build_embeddings_from_texts(texts, use_model=True)
        out_npy = args.embeddings_path or "dam_phase0_embeddings.npy"
        np.save(out_npy, embeddings)
        print(f"Saved embeddings ({embeddings.shape}) to {out_npy}")
        return

    report = run_evaluation(
        use_fixtures=args.use_fixtures,
        use_model=use_model,
        curated_path=args.curated_path,
        embeddings_path=args.embeddings_path,
        output_path=args.output,
        dataset_path=args.dataset_path,
    )

    print_summary(report)


if __name__ == "__main__":
    main()
