#!/usr/bin/env python3
"""Extract the split-clean Gemma G0b warmth direction at the Option-A surface.

The selected Gemma-4 full-attention actuator is the value-only input to
``v_norm`` after the functional K/V fork. This extractor captures that exact
forward-pre-hook input at teeth 29, 35, and 41, then computes one fixed
direction per tooth:

    unit(mean_skeleton(value_norm_pre(warm) - value_norm_pre(neutral)))

The primary SEV holdout manifest is mandatory. Held-out skeletons never enter
direction fitting. Output publication is atomic and refuses every overwrite.
No injection or generation occurs in this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch

from matched_delta_recording import load_sev_corpus
from sev_primary_holdout import (
    PrimaryHoldout,
    load_primary_holdout_manifest,
    sha256_file,
    training_warm_neutral_pairs,
)


BRIDGE_DIR = Path(__file__).resolve().parent
TARGET_LAYERS = (29, 35, 41)
SURFACE_KIND = "full_attention_value_norm_pre"
HOOK_SURFACE = "value_norm_pre"
ACTUATOR_DECISION = "option_a_value_only_v_norm_pre"
EXPECTED_WIDTH = 512
ARTIFACT_SCHEMA_VERSION = "gemma-g0b-value-norm-pre-v3"
METHOD_NAME = "method_a_paired_mean_delta_unit_v1"
DEFAULT_CORPUS = Path("fixtures/sev_disposition_v0/sev_disposition_v0.jsonl")
DEFAULT_OUTPUT = Path(
    "results/oxytocin_extraction/gemma4_12b_oxytocin_value_norm_pre_v3.pt"
)


@dataclass(frozen=True)
class SurfaceBinding:
    layer: int
    module: Any
    module_path: str
    descriptor: dict[str, Any]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else BRIDGE_DIR / path


def _validate_exact_revision(value: str) -> str:
    revision = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise argparse.ArgumentTypeError(
            "--revision must be an exact 40-character Hugging Face commit hash"
        )
    return revision


def _validate_code_revision(value: str) -> str:
    revision = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise argparse.ArgumentTypeError(
            "--code-revision must be an exact 40-character Git commit hash"
        )
    return revision


def _object_commit_hash(obj: Any) -> str | None:
    candidates = [
        getattr(obj, "_commit_hash", None),
        getattr(getattr(obj, "config", None), "_commit_hash", None),
        getattr(obj, "init_kwargs", {}).get("_commit_hash")
        if isinstance(getattr(obj, "init_kwargs", None), dict)
        else None,
    ]
    tokenizer = getattr(obj, "tokenizer", None)
    if tokenizer is not None:
        candidates.extend(
            [
                getattr(tokenizer, "_commit_hash", None),
                getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
                if isinstance(getattr(tokenizer, "init_kwargs", None), dict)
                else None,
            ]
        )
    for candidate in candidates:
        if isinstance(candidate, str) and re.fullmatch(r"[0-9a-fA-F]{40}", candidate):
            return candidate.lower()
    return None


def _config_payload(obj: Any) -> Mapping[str, Any]:
    config = getattr(obj, "config", None)
    if config is not None and callable(getattr(config, "to_dict", None)):
        return config.to_dict()
    if callable(getattr(obj, "to_dict", None)):
        return obj.to_dict()
    tokenizer = getattr(obj, "tokenizer", None)
    if tokenizer is not None and isinstance(getattr(tokenizer, "init_kwargs", None), dict):
        return tokenizer.init_kwargs
    if isinstance(getattr(obj, "init_kwargs", None), dict):
        return obj.init_kwargs
    raise RuntimeError(f"cannot obtain stable configuration provenance for {type(obj)!r}")


def object_provenance(
    obj: Any,
    *,
    identifier: str,
    requested_revision: str,
    role: str,
) -> dict[str, Any]:
    resolved_revision = _object_commit_hash(obj)
    if resolved_revision is not None and resolved_revision != requested_revision:
        raise RuntimeError(
            f"{role} resolved revision {resolved_revision} does not match requested "
            f"revision {requested_revision}"
        )
    config_payload = _config_payload(obj)
    descriptor = {
        "role": role,
        "identifier": identifier,
        "class": f"{type(obj).__module__}.{type(obj).__qualname__}",
        "requested_revision": requested_revision,
        "resolved_revision": resolved_revision or requested_revision,
        "config_sha256": sha256_json(config_payload),
    }
    return {**descriptor, "descriptor_sha256": sha256_json(descriptor)}


def load_model_and_processor(
    model_id: str,
    revision: str,
    local_files_only: bool = False,
) -> tuple[Any, Callable[[str], Mapping[str, Any]], Any]:
    """Load Gemma-4 in native bf16 at an exact repository revision."""

    from transformers import AutoModelForImageTextToText, AutoProcessor

    load_kwargs: dict[str, Any] = {
        "device_map": "auto",
        "trust_remote_code": True,
        "local_files_only": local_files_only,
        "revision": revision,
    }

    def _load() -> Any:
        try:
            return AutoModelForImageTextToText.from_pretrained(
                model_id,
                dtype=torch.bfloat16,
                **load_kwargs,
            )
        except TypeError:
            return AutoModelForImageTextToText.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
                **load_kwargs,
            )

    print(f"[loader] Loading {model_id!r} at revision {revision} in bf16...")
    processor = AutoProcessor.from_pretrained(
        model_id,
        trust_remote_code=True,
        local_files_only=local_files_only,
        revision=revision,
    )
    model = _load()
    model.eval()

    def encode(text: str) -> Mapping[str, Any]:
        return processor(text=[text], return_tensors="pt")

    return model, encode, processor


def _attribute_path(root: Any, path: str) -> Any:
    value = root
    for part in path.split("."):
        value = getattr(value, part)
    return value


def _decoder_layers(model: Any) -> Any:
    candidate_paths = (
        "model.layers",
        "model.model.layers",
        "language_model.layers",
        "language_model.model.layers",
        "model.language_model.layers",
    )
    for path in candidate_paths:
        try:
            layers = _attribute_path(model, path)
        except AttributeError:
            continue
        if layers is not None:
            return layers
    raise ValueError("could not locate Gemma decoder layers")


def resolve_surface_bindings(
    model: Any,
    target_layers: Sequence[int] = TARGET_LAYERS,
) -> tuple[SurfaceBinding, ...]:
    """Resolve and validate the exact Option-A module at each target tooth."""

    if tuple(target_layers) != TARGET_LAYERS:
        raise ValueError(f"G0b v3 target layers are frozen to {TARGET_LAYERS}")
    text_config = getattr(getattr(model, "config", None), "text_config", None)
    if text_config is None:
        raise ValueError("loaded Gemma model does not expose text_config")
    if getattr(text_config, "attention_k_eq_v", None) is not True:
        raise ValueError("G0b v3 requires attention_k_eq_v=true")
    if int(getattr(text_config, "num_global_key_value_heads", -1)) != 1:
        raise ValueError("G0b v3 requires exactly one global KV head")
    if int(getattr(text_config, "global_head_dim", -1)) != EXPECTED_WIDTH:
        raise ValueError(f"G0b v3 requires global_head_dim={EXPECTED_WIDTH}")
    if int(getattr(text_config, "num_kv_shared_layers", 0)) != 0:
        raise ValueError("shared-KV layers are outside the reviewed G0b v3 topology")

    layers = _decoder_layers(model)
    module_names = {id(module): name for name, module in model.named_modules()}
    bindings: list[SurfaceBinding] = []

    for layer in target_layers:
        try:
            attention = layers[layer].self_attn
        except (AttributeError, IndexError) as exc:
            raise ValueError(f"could not locate self-attention at layer {layer}") from exc

        if getattr(attention, "layer_type", None) != "full_attention":
            raise ValueError(f"layer {layer} is not a full-attention tooth")
        if getattr(attention, "use_alternative_attention", None) is not True:
            raise ValueError(f"layer {layer} does not expose Gemma's coupled K=V topology")
        if getattr(attention, "v_proj", object()) is not None:
            raise ValueError(f"layer {layer} unexpectedly exposes a separate value projection")
        if getattr(attention, "is_kv_shared_layer", False):
            raise ValueError(f"layer {layer} is unexpectedly a shared-KV layer")
        if int(getattr(attention, "head_dim", -1)) != EXPECTED_WIDTH:
            raise ValueError(f"layer {layer} attention head width is not {EXPECTED_WIDTH}")

        value_norm = getattr(attention, "v_norm", None)
        source_projection = getattr(attention, "k_proj", None)
        source_width = getattr(source_projection, "out_features", None)
        if (
            value_norm is None
            or getattr(value_norm, "with_scale", None) is not False
            or source_width != EXPECTED_WIDTH
        ):
            raise ValueError(
                f"layer {layer} Option-A width/module mismatch: "
                f"value_norm={value_norm is not None} "
                f"scale_free={getattr(value_norm, 'with_scale', None) is False} "
                f"source_width={source_width}"
            )

        module_path = module_names.get(id(value_norm))
        if not module_path:
            raise ValueError(f"layer {layer} value_norm is absent from model.named_modules()")
        descriptor: dict[str, Any] = {
            "layer": layer,
            "surface_kind": SURFACE_KIND,
            "hook_surface": HOOK_SURFACE,
            "hook_kind": "forward_pre_hook_input",
            "actuator_decision": ACTUATOR_DECISION,
            "module_path": module_path,
            "module_class": f"{type(value_norm).__module__}.{type(value_norm).__qualname__}",
            "attention_class": f"{type(attention).__module__}.{type(attention).__qualname__}",
            "width": EXPECTED_WIDTH,
            "topology": "full_attention_coupled_k_equals_v_post_fork_value_branch",
        }
        descriptor["descriptor_sha256"] = sha256_json(descriptor)
        bindings.append(
            SurfaceBinding(
                layer=layer,
                module=value_norm,
                module_path=module_path,
                descriptor=descriptor,
            )
        )
    return tuple(bindings)


def _capture_one(
    model: Any,
    encode: Callable[[str], Mapping[str, Any]],
    text: str,
    bindings: Sequence[SurfaceBinding],
    device: str,
) -> dict[int, torch.Tensor]:
    captured: dict[int, torch.Tensor] = {}
    handles: list[Any] = []

    def make_hook(binding: SurfaceBinding) -> Callable[..., None]:
        def hook_fn(module: Any, inputs: tuple[Any, ...]) -> None:
            if binding.layer in captured:
                raise RuntimeError(f"layer {binding.layer} value_norm executed more than once")
            if len(inputs) != 1 or not isinstance(inputs[0], torch.Tensor):
                raise RuntimeError(
                    f"layer {binding.layer} value_norm pre-hook expected one tensor input"
                )
            value_states = inputs[0]
            if (
                value_states.ndim != 4
                or value_states.shape[0] != 1
                or value_states.shape[2] != 1
                or value_states.shape[3] != EXPECTED_WIDTH
            ):
                raise RuntimeError(
                    f"layer {binding.layer} value_norm input must be [1,T,1,{EXPECTED_WIDTH}], "
                    f"got {tuple(value_states.shape)}"
                )
            last_token = value_states[0, -1].reshape(-1).detach()
            if last_token.numel() != EXPECTED_WIDTH:
                raise RuntimeError(
                    f"layer {binding.layer} value_norm width must be {EXPECTED_WIDTH}, "
                    f"got {last_token.numel()}"
                )
            if not torch.isfinite(last_token.float()).all():
                raise RuntimeError(f"layer {binding.layer} captured non-finite values")
            captured[binding.layer] = last_token.cpu()

        return hook_fn

    try:
        for binding in bindings:
            handles.append(binding.module.register_forward_pre_hook(make_hook(binding)))
        inputs = {
            key: (value.to(device) if hasattr(value, "to") else value)
            for key, value in encode(text).items()
        }
        with torch.inference_mode():
            model(**inputs, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()

    expected_layers = {binding.layer for binding in bindings}
    if set(captured) != expected_layers:
        raise RuntimeError(
            f"capture missing target layers: expected={sorted(expected_layers)} "
            f"captured={sorted(captured)}"
        )
    return captured


def collect_activations(
    model: Any,
    encode: Callable[[str], Mapping[str, Any]],
    pairs: Sequence[tuple[str, str, str]],
    bindings: Sequence[SurfaceBinding],
    device: str,
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor]]:
    warm_rows: dict[int, list[torch.Tensor]] = {
        binding.layer: [] for binding in bindings
    }
    neutral_rows: dict[int, list[torch.Tensor]] = {
        binding.layer: [] for binding in bindings
    }

    for index, (_, warm_text, neutral_text) in enumerate(pairs, start=1):
        started = time.time()
        warm = _capture_one(model, encode, warm_text, bindings, device)
        neutral = _capture_one(model, encode, neutral_text, bindings, device)
        for binding in bindings:
            warm_rows[binding.layer].append(warm[binding.layer])
            neutral_rows[binding.layer].append(neutral[binding.layer])
        if index % 5 == 0 or index == len(pairs):
            print(
                f"  processed {index}/{len(pairs)} training pairs "
                f"(last pair {time.time() - started:.2f}s)"
            )

    warm_stacked = {
        layer: torch.stack(rows).float() for layer, rows in warm_rows.items()
    }
    neutral_stacked = {
        layer: torch.stack(rows).float() for layer, rows in neutral_rows.items()
    }
    return warm_stacked, neutral_stacked


def compute_method_a_directions(
    warm: Mapping[int, torch.Tensor],
    neutral: Mapping[int, torch.Tensor],
    *,
    target_layers: Sequence[int] = TARGET_LAYERS,
) -> tuple[dict[int, torch.Tensor], dict[int, dict[str, Any]]]:
    """Compute fixed Method-A paired mean-delta unit directions."""

    if tuple(target_layers) != TARGET_LAYERS:
        raise ValueError(f"G0b v3 target layers are frozen to {TARGET_LAYERS}")
    if set(warm) != set(target_layers) or set(neutral) != set(target_layers):
        raise ValueError("activation maps must contain exactly the three target teeth")

    directions: dict[int, torch.Tensor] = {}
    statistics: dict[int, dict[str, Any]] = {}
    for layer in target_layers:
        warm_rows = warm[layer].float()
        neutral_rows = neutral[layer].float()
        if warm_rows.shape != neutral_rows.shape:
            raise ValueError(f"layer {layer} warm/neutral shapes differ")
        if warm_rows.ndim != 2 or warm_rows.shape[1] != EXPECTED_WIDTH:
            raise ValueError(
                f"layer {layer} activations must be [N,{EXPECTED_WIDTH}], "
                f"got {tuple(warm_rows.shape)}"
            )
        if warm_rows.shape[0] == 0:
            raise ValueError(f"layer {layer} has no training pairs")
        if not torch.isfinite(warm_rows).all() or not torch.isfinite(neutral_rows).all():
            raise ValueError(f"layer {layer} activations contain non-finite values")

        paired_deltas = warm_rows - neutral_rows
        mean_delta = paired_deltas.mean(dim=0)
        mean_delta_norm = mean_delta.norm()
        if not torch.isfinite(mean_delta_norm) or float(mean_delta_norm) <= 0.0:
            raise ValueError(f"layer {layer} mean warm-neutral delta is zero or non-finite")
        direction = mean_delta / mean_delta_norm
        if direction.shape != (EXPECTED_WIDTH,) or not torch.isfinite(direction).all():
            raise ValueError(f"layer {layer} direction failed shape/finiteness validation")
        unit_norm = float(direction.norm())
        if abs(unit_norm - 1.0) > 1e-5:
            raise ValueError(f"layer {layer} direction is not unit norm: {unit_norm}")

        pair_norms = paired_deltas.norm(dim=1)
        directions[layer] = direction
        statistics[layer] = {
            "pair_count": int(warm_rows.shape[0]),
            "mean_delta_l2": float(mean_delta_norm),
            "median_pair_delta_l2": float(pair_norms.median()),
            "direction_norm_fp32": unit_norm,
        }
    return directions, statistics


def build_artifact_payload(
    directions: Mapping[int, torch.Tensor],
    statistics: Mapping[int, Mapping[str, Any]],
    *,
    model_id: str,
    revision: str,
    model_provenance: Mapping[str, Any],
    processor_provenance: Mapping[str, Any],
    bindings: Sequence[SurfaceBinding],
    primary_holdout: PrimaryHoldout,
    split_manifest_path: Path,
    corpus_path: Path,
    code_revision: str,
) -> dict[str, Any]:
    if set(directions) != set(TARGET_LAYERS):
        raise ValueError("artifact directions must contain exactly teeth 29, 35, and 41")

    stored_directions: dict[int, torch.Tensor] = {}
    for layer in TARGET_LAYERS:
        stored = directions[layer].detach().cpu().to(torch.bfloat16)
        stored_norm = float(stored.float().norm())
        if stored.shape != (EXPECTED_WIDTH,) or not torch.isfinite(stored.float()).all():
            raise ValueError(f"layer {layer} stored direction failed validation")
        if not 0.99 <= stored_norm <= 1.01:
            raise ValueError(f"layer {layer} bf16 direction norm drifted to {stored_norm}")
        stored_directions[layer] = stored

    split_manifest_path = Path(split_manifest_path)
    corpus_path = Path(corpus_path)
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "directions": stored_directions,
        "statistics": {int(layer): dict(values) for layer, values in statistics.items()},
        "metadata": {
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_id": model_id,
            "model_revision": revision,
            "precision": "bf16",
            "target_layers": list(TARGET_LAYERS),
            "width": EXPECTED_WIDTH,
            "surface_kind": SURFACE_KIND,
            "hook_surface": HOOK_SURFACE,
            "actuator_decision": ACTUATOR_DECISION,
            "method": {
                "name": METHOD_NAME,
                "equation": "unit(mean_skeleton(value_norm_pre(warm)-value_norm_pre(neutral)))",
                "positive_class": "warm",
                "control_class": "neutral",
                "position": "last_input_token",
            },
            "envelope_status": "unvalidated_pending_DQ1a",
            "held_out_skeletons": list(primary_holdout.held_out_skeletons),
            "training_pair_count": statistics[TARGET_LAYERS[0]]["pair_count"],
            "provenance": {
                "corpus": {
                    "path": str(corpus_path),
                    "sha256": sha256_file(corpus_path),
                    "corpus_id": primary_holdout.corpus_id,
                },
                "split": {
                    "path": str(split_manifest_path),
                    "sha256": sha256_file(split_manifest_path),
                    "manifest_id": primary_holdout.manifest_id,
                    "split_id": primary_holdout.frozen_split.split_id,
                },
                "code": {
                    "path": str(Path(__file__).resolve()),
                    "sha256": sha256_file(Path(__file__).resolve()),
                    "git_revision": code_revision,
                    "torch_version": str(torch.__version__),
                    "transformers_version": str(__import__("transformers").__version__),
                },
                "model": dict(model_provenance),
                "processor": dict(processor_provenance),
                "modules": {
                    binding.layer: dict(binding.descriptor) for binding in bindings
                },
            },
        },
    }


def atomic_torch_save_no_overwrite(payload: Mapping[str, Any], path: Path) -> str:
    """Publish a fully-written artifact atomically without overwrite semantics."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing G0b artifact: {path}")

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        torch.save(dict(payload), temp_path)
        with temp_path.open("r+b") as handle:
            os.fsync(handle.fileno())
        artifact_sha256 = sha256_file(temp_path)
        try:
            os.link(temp_path, path)
        except FileExistsError as exc:
            raise FileExistsError(
                f"refusing concurrent overwrite of existing G0b artifact: {path}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                "atomic no-overwrite publication requires same-filesystem hard-link support"
            ) from exc
        return artifact_sha256
    finally:
        temp_path.unlink(missing_ok=True)


def publish_digest_sidecar_no_overwrite(
    path: Path,
    *,
    artifact_sha256: str,
    code_revision: str,
    model_revision: str,
    primary_holdout: PrimaryHoldout,
) -> Path:
    """Persist the external content digest that cannot be embedded in its own artifact."""

    sidecar_path = Path(str(path) + ".sha256.json")
    sidecar_payload = {
        "schema_version": "gemma-g0b-artifact-digest-v1",
        "artifact": path.name,
        "artifact_sha256": artifact_sha256,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "code_revision": code_revision,
        "model_revision": model_revision,
        "manifest_id": primary_holdout.manifest_id,
        "split_id": primary_holdout.frozen_split.split_id,
    }
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    if sidecar_path.exists():
        raise FileExistsError(f"refusing to overwrite artifact digest sidecar: {sidecar_path}")
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{sidecar_path.name}.", suffix=".tmp", dir=sidecar_path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(sidecar_payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, sidecar_path)
        except FileExistsError as exc:
            raise FileExistsError(
                f"refusing concurrent overwrite of artifact digest sidecar: {sidecar_path}"
            ) from exc
    finally:
        temp_path.unlink(missing_ok=True)
    return sidecar_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="google/gemma-4-12B")
    parser.add_argument("--revision", required=True, type=_validate_exact_revision)
    parser.add_argument("--code-revision", required=True, type=_validate_code_revision)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    corpus_path = _resolve_path(args.corpus)
    split_manifest_path = _resolve_path(args.split_manifest)
    output_path = _resolve_path(args.out)
    sidecar_path = Path(str(output_path) + ".sha256.json")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing G0b artifact: {output_path}")
    if sidecar_path.exists():
        raise FileExistsError(f"refusing to overwrite artifact digest sidecar: {sidecar_path}")

    primary_holdout = load_primary_holdout_manifest(split_manifest_path, corpus_path)
    corpus = load_sev_corpus(corpus_path)
    pairs = training_warm_neutral_pairs(corpus, primary_holdout)
    print(
        f"[split] manifest={primary_holdout.manifest_id} "
        f"split={primary_holdout.frozen_split.split_id} "
        f"training_pairs={len(pairs)} held_out={list(primary_holdout.held_out_skeletons)}"
    )

    device = args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu"
    print(f"[init] Using device: {device}")
    model, encode, processor = load_model_and_processor(
        args.model,
        args.revision,
        args.local_files_only,
    )
    model_provenance = object_provenance(
        model,
        identifier=args.model,
        requested_revision=args.revision,
        role="model",
    )
    processor_provenance = object_provenance(
        processor,
        identifier=args.model,
        requested_revision=args.revision,
        role="processor",
    )
    bindings = resolve_surface_bindings(model)
    warm, neutral = collect_activations(model, encode, pairs, bindings, device)
    directions, statistics = compute_method_a_directions(warm, neutral)
    payload = build_artifact_payload(
        directions,
        statistics,
        model_id=args.model,
        revision=args.revision,
        model_provenance=model_provenance,
        processor_provenance=processor_provenance,
        bindings=bindings,
        primary_holdout=primary_holdout,
        split_manifest_path=split_manifest_path,
        corpus_path=corpus_path,
        code_revision=args.code_revision,
    )
    artifact_sha256 = atomic_torch_save_no_overwrite(payload, output_path)
    digest_path = publish_digest_sidecar_no_overwrite(
        output_path,
        artifact_sha256=artifact_sha256,
        code_revision=args.code_revision,
        model_revision=args.revision,
        primary_holdout=primary_holdout,
    )
    print(
        f"[export] wrote immutable {output_path} sha256={artifact_sha256} "
        f"schema={ARTIFACT_SCHEMA_VERSION} digest_sidecar={digest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
