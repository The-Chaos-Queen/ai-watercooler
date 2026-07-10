#!/usr/bin/env python3
"""
extract_oxytocin_gemma.py — G0 Oxytocin Extraction for Gemma's Geometry.

Computes G0 warmth vectors in Gemma-4-12B's residual stream using:
- Method A: Mean Difference (warm minus neutral)
- Method B: Logistic Regression Probe decision boundary normal

Applies Path (a) global mean-centering (DC subtraction) to activations before
solver calculations, runs leave-8-out cross-validation to report direction drift,
and reports full cosine/Fisher ratio curves per layer.

Saves output with envelope_status: "unvalidated_pending_DQ1a" in metadata.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BRIDGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BRIDGE_DIR))


def load_corpus(corpus_path: Path) -> List[Tuple[str, str, str]]:
    """Loads and pairs warm/neutral prompts by skeleton_id.
    Returns: List of Tuple[skeleton_id, warm_text, neutral_text]
    """
    warm_by_sk: Dict[str, str] = {}
    neutral_by_sk: Dict[str, str] = {}
    
    with open(corpus_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            sk_id = item["skeleton_id"]
            text = item["text"]
            cls = item["class"]
            
            if cls == "warm":
                warm_by_sk[sk_id] = text
            elif cls == "neutral":
                neutral_by_sk[sk_id] = text
                
    pairs: List[Tuple[str, str, str]] = []
    for sk_id in sorted(warm_by_sk.keys()):
        if sk_id in neutral_by_sk:
            pairs.append((sk_id, warm_by_sk[sk_id], neutral_by_sk[sk_id]))
            
    print(f"[corpus] Loaded {len(pairs)} matched warm/neutral prompt pairs.")
    return pairs


def load_model_and_processor(model_id: str, quant: str, local_files_only: bool = False) -> Tuple[Any, Any, str]:
    """Loads Gemma-4 VLM or causal model using Gidim's trust_remote_code pattern."""
    from transformers import (AutoModelForCausalLM, AutoModelForImageTextToText,
                               AutoProcessor, AutoTokenizer)
    
    is_gemma4 = "gemma-4" in model_id.lower()
    fam = "image_text" if is_gemma4 else "causal"
    precision_flag = "bf16"
    
    load_kwargs: dict[str, Any] = {"device_map": "auto", "trust_remote_code": True, "local_files_only": local_files_only}
    if quant == "4bit":
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        precision_flag = "4bit"
    
    def _load(cls):
        try:
            return cls.from_pretrained(model_id, dtype=torch.bfloat16, **load_kwargs)
        except TypeError:
            return cls.from_pretrained(model_id, torch_dtype=torch.bfloat16, **load_kwargs)
            
    print(f"[loader] Loading model '{model_id}' (family={fam}, quant={quant})...")
    if fam == "image_text":
        proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=True, local_files_only=local_files_only)
        model = _load(AutoModelForImageTextToText)
        encode = lambda t: proc(text=[t], return_tensors="pt")
    else:
        proc = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, local_files_only=local_files_only)
        model = _load(AutoModelForCausalLM)
        encode = lambda t: proc(t, return_tensors="pt", truncation=True)
        
    model.eval()
    return model, encode, precision_flag


def collect_activations(model: Any, encode: Any, pairs: List[Tuple[str, str, str]], 
                        candidate_layers: List[int], device: str) -> Tuple[Dict[int, torch.Tensor], Dict[int, torch.Tensor]]:
    """Extracts hidden states at last-token position for candidate layers.
    Returns: warm_activations, neutral_activations (dicts mapping layer -> [N, d_model] tensor)
    """
    warm_acts: Dict[int, List[torch.Tensor]] = {l: [] for l in candidate_layers}
    neutral_acts: Dict[int, List[torch.Tensor]] = {l: [] for l in candidate_layers}
    
    print(f"[collector] Collecting activations at last-token position for layers: {candidate_layers}")
    for idx, (sk_id, warm_text, neutral_text) in enumerate(pairs):
        t0 = time.time()
        # Warm forward pass
        inputs_w = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in encode(warm_text).items()}
        with torch.no_grad():
            out_w = model(**inputs_w, output_hidden_states=True, use_cache=False)
        
        # Neutral forward pass
        inputs_n = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in encode(neutral_text).items()}
        with torch.no_grad():
            out_n = model(**inputs_n, output_hidden_states=True, use_cache=False)
            
        for layer in candidate_layers:
            # hidden_states contains embedding (idx 0) plus layer outputs (1..L)
            # layer is 0-indexed corresponding to output of layer_idx (1-based in out.hidden_states)
            # e.g., layer output l corresponds to out.hidden_states[l+1]
            hw = out_w.hidden_states[layer + 1]  # [1, seq_len, hidden_size]
            hn = out_n.hidden_states[layer + 1]
            
            # Extract last token hidden state
            warm_acts[layer].append(hw[0, -1, :].cpu())
            neutral_acts[layer].append(hn[0, -1, :].cpu())
            
        if (idx + 1) % 5 == 0 or (idx + 1) == len(pairs):
            print(f"  Processed {idx + 1}/{len(pairs)} pairs (last pair took {time.time() - t0:.2f}s)")
            
    # Stack list of tensors into [N, d_model] and cast to float32 to avoid dtype mismatches
    warm_stacked = {l: torch.stack(warm_acts[l], dim=0).float() for l in candidate_layers}
    neutral_stacked = {l: torch.stack(neutral_acts[l], dim=0).float() for l in candidate_layers}
    return warm_stacked, neutral_stacked


def train_probe(W_train: torch.Tensor, N_train: torch.Tensor, device: str) -> torch.Tensor:
    """Trains a logistic regression probe with BCE loss and L2 regularization.
    Returns: Normalized weight vector [d_model]
    """
    X = torch.cat([W_train, N_train], dim=0).to(device)
    y = torch.cat([torch.ones(len(W_train)), torch.zeros(len(N_train))], dim=0).unsqueeze(1).to(device)
    d_model = X.shape[1]
    
    probe = nn.Linear(d_model, 1).to(device)
    # L2 regularization (weight_decay=1e-3) is critical for small-sample stability
    optimizer = optim.Adam(probe.parameters(), lr=0.01, weight_decay=1e-3)
    criterion = nn.BCEWithLogitsLoss()
    
    for _ in range(200):
        optimizer.zero_grad()
        loss = criterion(probe(X), y)
        loss.backward()
        optimizer.step()
        
    w = probe.weight.data.squeeze(0).cpu()
    return w / w.norm()


def compute_fisher_ratio(v: torch.Tensor, W: torch.Tensor, N: torch.Tensor) -> float:
    """Computes the Fisher Ratio along the projection direction v."""
    p_W = W @ v
    p_N = N @ v
    mu_W = float(p_W.mean())
    mu_N = float(p_N.mean())
    var_W = float(p_W.var())
    var_N = float(p_N.var())
    return (mu_W - mu_N) ** 2 / (var_W + var_N + 1e-9)


def cross_validate(W: torch.Tensor, N: torch.Tensor, v_full: torch.Tensor, 
                   method: str, device: str, n_folds: int = 5) -> float:
    """Performs leave-k-out cross validation and computes drift cosine with full vector."""
    n_pairs = len(W)
    fold_size = n_pairs // n_folds
    cosines = []
    
    for fold in range(n_folds):
        val_indices = list(range(fold * fold_size, (fold + 1) * fold_size))
        train_indices = [i for i in range(n_pairs) if i not in val_indices]
        
        W_train = W[train_indices]
        N_train = N[train_indices]
        
        # Mean centering inside the fold using Path (a)
        global_mean_fold = torch.cat([W_train, N_train], dim=0).mean(dim=0, keepdim=True)
        W_train_c = W_train - global_mean_fold
        N_train_c = N_train - global_mean_fold
        
        if method == "A":
            v_fold = W_train_c.mean(dim=0) - N_train_c.mean(dim=0)
            v_fold = v_fold / v_fold.norm()
        else:
            v_fold = train_probe(W_train_c, N_train_c, device)
            
        cos_val = float(F.cosine_similarity(v_full.unsqueeze(0), v_fold.unsqueeze(0), dim=-1))
        cosines.append(cos_val)
        
    return float(np.mean(cosines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract G0 Oxytocin (warmth) vectors for Gemma.")
    parser.add_argument("--model", default="google/gemma-4-12B", help="Model checkpoint to load")
    parser.add_argument("--corpus", default="fixtures/sev_disposition_v0/sev_disposition_v0.jsonl", help="Path to corpus JSONL")
    parser.add_argument("--quant", default="no", choices=["no", "4bit"], help="Quantization layout")
    parser.add_argument("--device", default="cuda", help="Execution device")
    parser.add_argument("--out", default="results/oxytocin_extraction/gemma4_12b_oxytocin_v1.pt", help="Output PT file path")
    parser.add_argument("--local-files-only", action="store_true", help="Only load local files from cache")
    args = parser.parse_args()
    
    corpus_path = BRIDGE_DIR / args.corpus
    out_path = BRIDGE_DIR / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    device = args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu"
    print(f"[init] Using device: {device}")
    
    # 1) Load corpus
    pairs = load_corpus(corpus_path)
    
    # 2) Load model
    model, encode, precision_flag = load_model_and_processor(args.model, args.quant, args.local_files_only)
    
    # 3) Collect activations
    # Candidate layers are global integration teeth (comb teeth)
    candidate_layers = [5, 11, 17, 23, 29, 35, 41, 47]
    warm_acts, neutral_acts = collect_activations(model, encode, pairs, candidate_layers, device)
    
    # 4) Process G0 directions per layer
    g0_vectors_A: Dict[int, torch.Tensor] = {}
    g0_vectors_B: Dict[int, torch.Tensor] = {}
    layer_stats: Dict[int, Dict[str, Any]] = {}
    
    print("\n[extraction] Computing G0 directions and cross-validation...")
    for layer in candidate_layers:
        W = warm_acts[layer]
        N = neutral_acts[layer]
        
        # Path (a): explicit DC removal (mean-centering) before calculation
        global_mean = torch.cat([W, N], dim=0).mean(dim=0, keepdim=True)
        W_centered = W - global_mean
        N_centered = N - global_mean
        
        # Method A: Mean difference
        v_A = W_centered.mean(dim=0) - N_centered.mean(dim=0)
        v_A = v_A / v_A.norm()
        g0_vectors_A[layer] = v_A
        
        # Method B: Linear probe weights
        v_B = train_probe(W_centered, N_centered, device)
        g0_vectors_B[layer] = v_B
        
        # Cosine similarity between solvers
        cos_AB = float(torch.dot(v_A, v_B))
        
        # Fisher Ratios
        f_A = compute_fisher_ratio(v_A, W_centered, N_centered)
        f_B = compute_fisher_ratio(v_B, W_centered, N_centered)
        
        # Cross-validation (leave-8-out = 5 folds)
        cv_cos_A = cross_validate(W, N, v_A, "A", device)
        cv_cos_B = cross_validate(W, N, v_B, "B", device)
        
        # Variance drift: 1 - CV cosine similarity
        drift_A = 1.0 - cv_cos_A
        drift_B = 1.0 - cv_cos_B
        
        layer_stats[layer] = {
            "cosine_AB": round(cos_AB, 4),
            "fisher_A": round(f_A, 4),
            "fisher_B": round(f_B, 4),
            "cv_mean_cosine_A": round(cv_cos_A, 4),
            "cv_mean_cosine_B": round(cv_cos_B, 4),
            "drift_A": round(drift_A, 4),
            "drift_B": round(drift_B, 4),
        }
        
        print(f"Layer {layer:02d}: solver_cos={cos_AB:.4f} | Fisher A={f_A:.2f}, B={f_B:.2f} | CV Cos A={cv_cos_A:.4f}, B={cv_cos_B:.4f} (drift A={drift_A:.4f})")
        if drift_A > 0.15:
            print(f"  [WARNING] Method A drift ({drift_A:.4f}) is above 0.15 threshold! Corpus may be thin.")
            
    # 5) Export vectors
    print(f"\n[exporter] Exporting PT vectors -> {out_path.name}")
    # Cast vectors back to the appropriate precision (bfloat16 or float16)
    out_dtype = torch.bfloat16 if precision_flag == "bf16" else torch.float16
    g0_vectors_A_cast = {k: v.to(out_dtype) for k, v in g0_vectors_A.items()}
    g0_vectors_B_cast = {k: v.to(out_dtype) for k, v in g0_vectors_B.items()}
    torch.save(
        {
            "g0_vectors_A": g0_vectors_A_cast,
            "g0_vectors_B": g0_vectors_B_cast,
            "stats": layer_stats,
            "metadata": {
                "model_id": args.model,
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "precision": precision_flag,
                "envelope_status": "unvalidated_pending_DQ1a",
                "dc_treatment": "Path A (global mean subtracted per layer)",
                "corpus": str(args.corpus),
                "deliberate_position": "last-token position (bypasses pos-0 attention sink)",
                "note": "Extracted G0 warmth direction vectors for Gemma. DO NOT inject until DQ1a re-derives MED envelope."
            }
        },
        out_path
    )
    print("Export COMPLETE.")


if __name__ == "__main__":
    main()
