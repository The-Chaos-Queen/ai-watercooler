#!/usr/bin/env python3
"""Capture-only Gemma-4 option-A smoke; structurally incapable of injection.

This runner verifies the live model topology, proves that ``k_proj`` output is
the tensor seen by the dedicated value-side ``v_norm``, and checks bit-exact
logit parity with the reviewed runtime armed at alpha zero.  It deliberately
offers no nonzero-alpha argument: the first nonzero Gemma intervention remains
the separately gated C1 birth condition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


BRIDGE_DIR = Path(__file__).resolve().parents[1]
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

SCHEMA_VERSION = "gemma4-value-norm-alpha0-smoke-v1"
APPROVED_TEETH = (29, 35, 41)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return _sha256_bytes(encoded)


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=BRIDGE_DIR, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _resolve_layers(model: Any):
    candidates = (
        lambda: model.language_model.layers,
        lambda: model.model.language_model.layers,
        lambda: model.language_model.model.layers,
        lambda: model.model.language_model.model.layers,
        lambda: model.model.layers,
    )
    for getter in candidates:
        try:
            layers = getter()
        except AttributeError:
            continue
        if layers is not None:
            return layers
    raise RuntimeError("could not locate Gemma text layers")


def _input_device(model: Any):
    embedding_paths = (
        lambda: model.language_model.embed_tokens.weight,
        lambda: model.model.language_model.embed_tokens.weight,
        lambda: model.language_model.model.embed_tokens.weight,
        lambda: model.model.language_model.model.embed_tokens.weight,
        lambda: model.model.embed_tokens.weight,
    )
    for getter in embedding_paths:
        try:
            weight = getter()
        except AttributeError:
            continue
        if weight.device.type != "meta":
            return weight.device
    for parameter in model.parameters():
        if parameter.device.type != "meta":
            return parameter.device
    raise RuntimeError("loaded model exposes no materialized parameter device")


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite smoke artifact: {path}")
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="google/gemma-4-12B")
    parser.add_argument(
        "--prompt",
        default="A quiet workshop contains a table, a lamp, and an unopened notebook.",
    )
    parser.add_argument("--teeth", default="29,35,41")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--code-revision",
        default="",
        help="source revision to stamp when running from a non-git staging directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    teeth = tuple(int(piece.strip()) for piece in args.teeth.split(",") if piece.strip())
    if not teeth or any(layer not in APPROVED_TEETH for layer in teeth):
        raise SystemExit(f"--teeth must be a subset of {APPROVED_TEETH}")

    import torch
    import transformers
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from gemma4_value_norm_runtime import Gemma4ValueNormRuntime

    started = time.time()
    processor = AutoProcessor.from_pretrained(
        args.model,
        trust_remote_code=True,
        local_files_only=args.local_files_only,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        args.model,
        trust_remote_code=True,
        local_files_only=args.local_files_only,
        dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    runtime = Gemma4ValueNormRuntime.bind(model, teeth=teeth)
    inputs = processor(text=[args.prompt], return_tensors="pt")
    input_device = _input_device(model)
    inputs = {
        key: value.to(input_device) if isinstance(value, torch.Tensor) else value
        for key, value in inputs.items()
    }
    token_ids = inputs.get("input_ids")
    if not isinstance(token_ids, torch.Tensor) or token_ids.ndim != 2:
        raise RuntimeError("processor did not emit a [batch, tokens] input_ids tensor")
    token_count = int(token_ids.shape[1])
    positions = torch.arange(token_count, dtype=torch.long)

    with torch.inference_mode():
        baseline_logits = model(**inputs, use_cache=False).logits.detach().cpu()

    layers = _resolve_layers(model)
    projection_rows: dict[int, torch.Tensor] = {}
    handles = []

    def projection_hook(layer: int):
        def hook(module, module_in, module_out):
            del module, module_in
            projection_rows[layer] = module_out.detach().cpu().clone()

        return hook

    for layer in teeth:
        handles.append(layers[layer].self_attn.k_proj.register_forward_hook(projection_hook(layer)))
    try:
        with runtime.condition(
            token_ids=token_ids.detach().cpu(),
            absolute_positions=positions,
            alphas={layer: 0.0 for layer in teeth},
            position_policy="exclude_absolute_zero",
        ) as trace:
            with torch.inference_mode():
                alpha0_logits = model(**inputs, use_cache=False).logits.detach().cpu()
    finally:
        for handle in handles:
            handle.remove()
        runtime.close()

    logit_delta = (alpha0_logits.float() - baseline_logits.float()).abs()
    logit_exact = bool(torch.equal(alpha0_logits, baseline_logits))
    surface_checks: dict[str, Any] = {}
    for layer in teeth:
        events = trace.by_layer(layer)
        if len(events) != 1:
            raise RuntimeError(f"expected exactly one value trace at tooth {layer}, got {len(events)}")
        event = events[0]
        projection = projection_rows.get(layer)
        if projection is None:
            raise RuntimeError(f"k_proj hook did not fire at tooth {layer}")
        value_input = event.raw_pre_norm.squeeze(2)
        difference = (projection.float() - value_input.float()).abs()
        surface_checks[str(layer)] = {
            "surface": next(row for row in trace.surfaces if row["layer"] == layer),
            "k_proj_shape": list(projection.shape),
            "v_norm_pre_shape": list(event.raw_pre_norm.shape),
            "k_proj_equals_v_norm_pre_exact": bool(torch.equal(projection, value_input)),
            "k_proj_v_norm_pre_max_abs": float(difference.max().item()),
            "alpha": event.alpha,
            "changed": event.changed,
            "post_norm_finite": bool(
                event.post_norm is not None and torch.isfinite(event.post_norm).all().item()
            ),
        }

    text_config = getattr(model.config, "text_config", model.config)
    config_dict = text_config.to_dict() if hasattr(text_config, "to_dict") else vars(text_config)
    output = args.output
    if output is None:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        output = BRIDGE_DIR / "results" / "value_norm_smoke" / f"alpha0_{stamp}.json"
    elif not output.is_absolute():
        output = BRIDGE_DIR / output

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if logit_exact and all(
            row["k_proj_equals_v_norm_pre_exact"]
            and not row["changed"]
            and row["post_norm_finite"]
            for row in surface_checks.values()
        ) else "fail",
        "model": {
            "id": args.model,
            "config_class": type(model.config).__name__,
            "resolved_commit": getattr(model.config, "_commit_hash", None),
            "dtype": "bfloat16",
            "config_sha256": _canonical_sha256(config_dict),
        },
        "runtime": {
            "git_revision": args.code_revision or _git_revision(),
            "controller_sha256": _sha256_bytes(
                (BRIDGE_DIR / "gemma4_value_norm_runtime.py").read_bytes()
            ),
            "runner_sha256": _sha256_bytes(Path(__file__).read_bytes()),
            "transformers_version": transformers.__version__,
            "torch_version": torch.__version__,
            "device_map": getattr(model, "hf_device_map", None),
            "elapsed_seconds": round(time.time() - started, 3),
        },
        "input": {
            "prompt_sha256": _sha256_bytes(args.prompt.encode("utf-8")),
            "token_ids_sha256": trace.token_ids_sha256,
            "token_count": token_count,
            "position_policy": trace.position_policy,
            "cache_policy": trace.cache_policy,
        },
        "alpha_zero_parity": {
            "logits_exact": logit_exact,
            "logits_max_abs": float(logit_delta.max().item()),
            "logits_shape": list(alpha0_logits.shape),
        },
        "surfaces": surface_checks,
    }
    _write_atomic_json(output, payload)
    print(json.dumps({"status": payload["status"], "artifact": str(output)}, indent=2))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
