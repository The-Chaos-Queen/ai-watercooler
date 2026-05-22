from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer, MambaForCausalLM

from sleep_reconcile import extract_hidden_last_token
from trajectory_sequential import parse_markdown_conversation


DEFAULT_MODEL_ID = "state-spaces/mamba-2.8b-hf"
DEFAULT_TARGET_LAYER = 3
DEFAULT_MAX_TOKENS = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a single Mamba hidden-last-token vector from a text transcript."
    )
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--target-layer", type=int, default=DEFAULT_TARGET_LAYER)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    parser.add_argument(
        "--mode",
        default="one_shot",
        choices=["one_shot", "rolling_chunked", "rolling_turnwise"],
        help="one_shot mirrors the bootstrap truncation path; rolling_chunked carries Mamba cache across token chunks; rolling_turnwise mirrors live accumulation structure.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=128,
        help="Chunk size for rolling_chunked mode.",
    )
    parser.add_argument(
        "--progress-every-chunks",
        type=int,
        default=50,
        help="Emit a progress line every N chunks in rolling_chunked mode.",
    )
    return parser.parse_args()


def resolve_device(raw: str) -> str:
    if raw == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return raw


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8", errors="replace")
    resolved_device = resolve_device(args.device)
    torch_dtype = torch.float16 if resolved_device.startswith("cuda") else torch.float32

    print(f"[info] input={input_path}")
    print(f"[info] model_id={args.model_id}")
    print(f"[info] target_layer={args.target_layer}")
    print(f"[info] max_tokens={args.max_tokens}")
    print(f"[info] device={resolved_device}")
    print(f"[info] mode={args.mode}")

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    raw_tokens = tokenizer(text, return_tensors="pt", truncation=False)
    raw_token_count = int(raw_tokens["input_ids"].shape[1])

    model = MambaForCausalLM.from_pretrained(args.model_id, torch_dtype=torch_dtype)
    model.to(resolved_device)
    model.eval()

    expected_layers = getattr(model.config, "n_layer", None)
    if expected_layers is None:
        expected_layers = getattr(model.config, "num_hidden_layers", None)

    if args.mode == "one_shot":
        truncated = raw_token_count > args.max_tokens
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_tokens,
        )
        token_count_used = int(inputs["input_ids"].shape[1])
        inputs = {key: value.to(resolved_device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)

        vector = extract_hidden_last_token(
            outputs,
            layer_idx=args.target_layer,
            expected_layers=expected_layers,
        ).astype(np.float32)
    elif args.mode == "rolling_chunked":
        token_ids = raw_tokens["input_ids"]
        if args.max_tokens > 0:
            token_ids = token_ids[:, : args.max_tokens]
        token_count_used = int(token_ids.shape[1])
        truncated = raw_token_count > token_count_used

        cache = None
        outputs = None
        total_chunks = (token_count_used + args.chunk_size - 1) // args.chunk_size
        for chunk_index, chunk_start in enumerate(range(0, token_count_used, args.chunk_size), start=1):
            chunk_end = min(chunk_start + args.chunk_size, token_count_used)
            chunk_ids = token_ids[:, chunk_start:chunk_end].to(resolved_device)

            kwargs = {"output_hidden_states": True, "use_cache": True}
            if cache is not None:
                kwargs["cache_params"] = cache
                kwargs["cache_position"] = torch.arange(chunk_start, chunk_end, device=resolved_device)

            with torch.no_grad():
                outputs = model(chunk_ids, **kwargs)
            cache = getattr(outputs, "cache_params", None)

            if (
                chunk_index == 1
                or chunk_index == total_chunks
                or (args.progress_every_chunks > 0 and chunk_index % args.progress_every_chunks == 0)
            ):
                print(
                    f"[progress] chunk {chunk_index}/{total_chunks} "
                    f"tokens={chunk_end}/{token_count_used}"
                )

        if outputs is None:
            raise RuntimeError("rolling_chunked mode produced no outputs.")

        vector = extract_hidden_last_token(
            outputs,
            layer_idx=args.target_layer,
            expected_layers=expected_layers,
        ).astype(np.float32)
    else:
        turns = parse_markdown_conversation(str(input_path))
        if not turns:
            raise RuntimeError("rolling_turnwise mode parsed zero turns from markdown export.")

        total_turns = len(turns)
        cache = None
        outputs = None
        token_count_used = 0

        for turn_index, turn in enumerate(turns, start=1):
            if args.max_tokens > 0 and token_count_used >= args.max_tokens:
                break

            turn_text = f"{turn['role']}: {turn['text']}\n"
            turn_tokens = tokenizer(
                turn_text,
                return_tensors="pt",
                add_special_tokens=False,
                truncation=False,
            )["input_ids"]

            if args.max_tokens > 0:
                remaining = args.max_tokens - token_count_used
                turn_tokens = turn_tokens[:, :remaining]

            seq_len = int(turn_tokens.shape[1])
            if seq_len == 0:
                continue

            for offset in range(seq_len):
                global_token_pos = token_count_used
                capture_hidden = False
                if args.max_tokens > 0:
                    capture_hidden = global_token_pos == args.max_tokens - 1
                else:
                    capture_hidden = turn_index == total_turns and offset == seq_len - 1

                step_ids = turn_tokens[:, offset : offset + 1].to(resolved_device)
                kwargs = {"use_cache": True, "output_hidden_states": capture_hidden}
                if cache is not None:
                    kwargs["cache_params"] = cache
                    kwargs["cache_position"] = torch.tensor([global_token_pos], device=resolved_device)

                with torch.no_grad():
                    outputs = model(step_ids, **kwargs)
                cache = getattr(outputs, "cache_params", None)
                token_count_used += 1

                if capture_hidden:
                    break

            if (
                turn_index == 1
                or turn_index == total_turns
                or (args.progress_every_chunks > 0 and turn_index % args.progress_every_chunks == 0)
            ):
                print(
                    f"[progress] turn {turn_index}/{total_turns} "
                    f"tokens={token_count_used}"
                )

            if args.max_tokens > 0 and token_count_used >= args.max_tokens:
                break

        truncated = raw_token_count > token_count_used
        if outputs is None:
            raise RuntimeError("rolling_turnwise mode produced no outputs.")

        vector = extract_hidden_last_token(
            outputs,
            layer_idx=args.target_layer,
            expected_layers=expected_layers,
        ).astype(np.float32)

    stem = input_path.stem
    mode_suffix = args.mode
    npy_path = output_dir / f"{stem}.mamba_l{args.target_layer}.{mode_suffix}.hidden_last_token.npy"
    json_path = output_dir / f"{stem}.mamba_l{args.target_layer}.{mode_suffix}.hidden_last_token.json"

    np.save(npy_path, vector)

    preview = [float(x) for x in vector[:16]]
    metadata = {
        "input_path": str(input_path),
        "model_id": args.model_id,
        "target_layer": int(args.target_layer),
        "max_tokens": int(args.max_tokens),
        "device": resolved_device,
        "mode": args.mode,
        "chunk_size": int(args.chunk_size) if args.mode == "rolling_chunked" else None,
        "raw_token_count": raw_token_count,
        "token_count_used": token_count_used,
        "truncated": bool(truncated),
        "shape": list(vector.shape),
        "dtype": str(vector.dtype),
        "l2_norm": float(np.linalg.norm(vector)),
        "mean": float(vector.mean()),
        "std": float(vector.std()),
        "min": float(vector.min()),
        "max": float(vector.max()),
        "preview_first_16": preview,
        "vector_npy_path": str(npy_path),
    }
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("[done] wrote:")
    print(f"  - {npy_path}")
    print(f"  - {json_path}")
    print("[stats]")
    print(f"  raw_token_count={raw_token_count}")
    print(f"  token_count_used={token_count_used}")
    print(f"  truncated={truncated}")
    print(f"  shape={tuple(vector.shape)}")
    print(f"  l2_norm={metadata['l2_norm']:.6f}")
    print(f"  mean={metadata['mean']:.6f}")
    print(f"  std={metadata['std']:.6f}")
    print(f"  min={metadata['min']:.6f}")
    print(f"  max={metadata['max']:.6f}")
    print(f"  preview_first_16={preview}")


if __name__ == "__main__":
    main()
