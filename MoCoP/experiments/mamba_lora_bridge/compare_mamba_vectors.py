from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer, MambaForCausalLM

from extract_single_mamba_vector import resolve_device
from sleep_reconcile import extract_hidden_last_token


DEFAULT_MODEL_ID = "state-spaces/mamba-2.8b-hf"
DEFAULT_TARGET_LAYER = 3
DEFAULT_MAX_TOKENS = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Mamba vectors across multiple text chats.")
    parser.add_argument("--reference", required=True, help="Path to a .npy vector or a text transcript.")
    parser.add_argument("--candidate", action="append", required=True, help="Path to a candidate text transcript or .npy vector. Repeat for multiple inputs.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--target-layer", type=int, default=DEFAULT_TARGET_LAYER)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--device", default="cuda", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def load_or_encode_vector(
    path: Path,
    *,
    model,
    tokenizer,
    device: str,
    target_layer: int,
    max_tokens: int,
) -> tuple[np.ndarray, dict]:
    if path.suffix.lower() == ".npy":
        vec = np.load(path).astype(np.float32).reshape(-1)
        meta = {
            "path": str(path),
            "kind": "vector",
            "token_count_used": None,
            "truncated": None,
            "norm": float(np.linalg.norm(vec)),
        }
        return vec, meta

    text = path.read_text(encoding="utf-8", errors="replace")
    raw_tokens = tokenizer(text, return_tensors="pt", truncation=False)
    raw_token_count = int(raw_tokens["input_ids"].shape[1])
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_tokens,
    )
    token_count_used = int(inputs["input_ids"].shape[1])
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    expected_layers = getattr(model.config, "n_layer", None)
    if expected_layers is None:
        expected_layers = getattr(model.config, "num_hidden_layers", None)

    vec = extract_hidden_last_token(
        outputs,
        layer_idx=target_layer,
        expected_layers=expected_layers,
    ).astype(np.float32)
    meta = {
        "path": str(path),
        "kind": "text_one_shot",
        "raw_token_count": raw_token_count,
        "token_count_used": token_count_used,
        "truncated": bool(raw_token_count > token_count_used),
        "norm": float(np.linalg.norm(vec)),
    }
    return vec, meta


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    torch_dtype = torch.float16 if device.startswith("cuda") else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = MambaForCausalLM.from_pretrained(args.model_id, torch_dtype=torch_dtype)
    model.to(device)
    model.eval()

    ref_path = Path(args.reference)
    ref_vec, ref_meta = load_or_encode_vector(
        ref_path,
        model=model,
        tokenizer=tokenizer,
        device=device,
        target_layer=args.target_layer,
        max_tokens=args.max_tokens,
    )

    results = []
    for candidate_raw in args.candidate:
        candidate_path = Path(candidate_raw)
        cand_vec, cand_meta = load_or_encode_vector(
            candidate_path,
            model=model,
            tokenizer=tokenizer,
            device=device,
            target_layer=args.target_layer,
            max_tokens=args.max_tokens,
        )
        results.append(
            {
                "candidate": str(candidate_path),
                "cosine": cosine(ref_vec, cand_vec),
                "delta_norm": float(np.linalg.norm(ref_vec - cand_vec)),
                "mean_abs_diff": float(np.mean(np.abs(ref_vec - cand_vec))),
                "candidate_meta": cand_meta,
            }
        )

    results.sort(key=lambda row: row["cosine"], reverse=True)

    payload = {
        "reference": ref_meta,
        "model_id": args.model_id,
        "target_layer": args.target_layer,
        "max_tokens": args.max_tokens,
        "device": device,
        "results": results,
    }

    for row in results:
        meta = row["candidate_meta"]
        print(
            f"{row['cosine']:.4f}  Δ={row['delta_norm']:.4f}  "
            f"{Path(row['candidate']).name}  "
            f"(tokens={meta.get('token_count_used')}, truncated={meta.get('truncated')})"
        )

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[done] wrote {out_path}")


if __name__ == "__main__":
    main()
