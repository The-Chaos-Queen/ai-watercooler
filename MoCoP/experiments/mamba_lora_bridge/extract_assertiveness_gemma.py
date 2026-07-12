#!/usr/bin/env python3
"""Extract a split-clean NEGATIVE-VALENCE hormonal direction at the G0b surface.

Sibling of ``extract_oxytocin_gemma.py``. Same Option-A actuator surface
(``value_norm_pre`` at teeth 29/35/41), same Method-A paired mean-delta unit
extraction, same skeleton-level holdout discipline — but for a NON-positive
contrast (default ``adversarial`` -> the assertiveness/agency axis; "testosterone"
is a metaphor handle only, per keeper ratification wc#918 / Codex #915 Q4):

    unit(mean_skeleton(value_norm_pre(adversarial) - value_norm_pre(neutral)))

This is an ATLAS-BUILDING, read-only extraction. It performs NO injection and NO
generation. The produced artifact is STRUCTURALLY WALLED from the positive-only C1
birth: it stamps ``c1_admissible=false`` and ``injection_admissible=false`` so the
family-by-digest C1 matrix cannot pick it up. The cold/adversarial *injection*
family remains deferred pending a fresh Domain-E seat review (Cairn #900, Isegrim
#881); this script only extracts the direction, it does not authorize using it.

The heavy machinery (model load, surface binding, capture, Method-A math) is reused
verbatim from ``extract_oxytocin_gemma`` so the C1-critical oxytocin path is never
touched. Only the artifact payload (with the wall tags) and the CLI differ.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch

from extract_oxytocin_gemma import (
    ACTUATOR_DECISION,
    EXPECTED_WIDTH,
    HOOK_SURFACE,
    METHOD_NAME,
    SURFACE_KIND,
    TARGET_LAYERS,
    SurfaceBinding,
    _resolve_path,
    _validate_code_revision,
    _validate_exact_revision,
    atomic_torch_save_no_overwrite,
    collect_activations,
    compute_method_a_directions,
    load_model_and_processor,
    object_provenance,
    resolve_surface_bindings,
)
from matched_delta_recording import load_sev_corpus
from sev_primary_holdout import (
    PrimaryHoldout,
    hormone_axis_spec,
    load_primary_holdout_manifest,
    sha256_file,
    training_pairs,
)

DEFAULT_CORPUS = Path("fixtures/sev_disposition_v0/sev_disposition_v0.jsonl")


def _default_output(axis_spec: Mapping[str, Any]) -> Path:
    return Path("results/hormone_atlas") / f"gemma4_12b_{axis_spec['axis']}_value_norm_pre_v1.pt"


def build_walled_artifact_payload(
    directions: Mapping[int, torch.Tensor],
    statistics: Mapping[int, Mapping[str, Any]],
    axis_spec: Mapping[str, Any],
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
    """Mirror the G0b payload, plus the negative-valence custody wall."""

    if axis_spec["c1_admissible"]:
        raise ValueError(
            "extract_assertiveness_gemma refuses a C1-admissible (positive) axis; "
            "use extract_oxytocin_gemma for the warm/oxytocin direction"
        )
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
    positive_class = axis_spec["positive_class"]
    return {
        "schema_version": axis_spec["artifact_schema_version"],
        "directions": stored_directions,
        "statistics": {int(layer): dict(values) for layer, values in statistics.items()},
        # The custody wall. Read by any consumer BEFORE the artifact may be used as
        # an injection direction. A false flag here is a hard non-admissibility.
        "wall": {
            "c1_admissible": False,
            "injection_admissible": False,
            "family": axis_spec["family"],
            "semantic_scope": axis_spec["axis"],
            "metaphor": axis_spec["metaphor"],
            "note": (
                "ATLAS/RESEARCH extraction only. Negative-valence injection family is "
                "deferred pending a fresh Domain-E seat review (Cairn #900 / Isegrim "
                "#881). This direction is NOT admissible for the positive-only C1 birth "
                "and must not enter the family-by-digest C1 matrix."
            ),
            # Cairn #924 ratified schema-porting invariant: these admissibility flags
            # MUST port verbatim to any substrate/format this atlas is migrated to.
            # Flipping either flag to true is a class-changing act that triggers a fresh
            # valence-asymmetric injection seat review (#820/#924) AT THE PORTING BOUNDARY,
            # not only at the injection boundary.
            "porting_invariant": (
                "c1_admissible / injection_admissible must port verbatim; flipping either "
                "to true triggers a fresh valence-asymmetric seat review at the porting "
                "boundary (Cairn #820/#924)."
            ),
        },
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
            "axis": axis_spec["axis"],
            "method": {
                "name": METHOD_NAME,
                "equation": (
                    f"unit(mean_skeleton(value_norm_pre({positive_class})"
                    f"-value_norm_pre(neutral)))"
                ),
                "positive_class": positive_class,
                "control_class": "neutral",
                "position": "last_input_token",
            },
            "envelope_status": "atlas_only_never_dq1a_c1",
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
                    "pairing": "skeleton_derived_non_warm",
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
                "modules": {binding.layer: dict(binding.descriptor) for binding in bindings},
            },
        },
    }


def publish_digest_sidecar(
    artifact_path: Path,
    *,
    artifact_sha256: str,
    axis_spec: Mapping[str, Any],
    code_revision: str,
    model_revision: str,
    primary_holdout: PrimaryHoldout,
) -> Path:
    sidecar_path = Path(str(artifact_path) + ".sha256.json")
    if sidecar_path.exists():
        raise FileExistsError(f"refusing to overwrite artifact digest sidecar: {sidecar_path}")
    payload = {
        "schema_version": "gemma-g0-atlas-digest-v1",
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "artifact_schema_version": axis_spec["artifact_schema_version"],
        "axis": axis_spec["axis"],
        "c1_admissible": False,
        "injection_admissible": False,
        "code_revision": code_revision,
        "model_revision": model_revision,
        "split_id": primary_holdout.frozen_split.split_id,
        "held_out_skeletons": list(primary_holdout.held_out_skeletons),
    }
    fd, temp_name = tempfile.mkstemp(prefix=f".{sidecar_path.name}.", suffix=".tmp",
                                     dir=sidecar_path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        os.replace(temp_path, sidecar_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return sidecar_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="google/gemma-4-12B")
    parser.add_argument("--revision", required=True, type=_validate_exact_revision)
    parser.add_argument("--code-revision", required=True, type=_validate_code_revision)
    parser.add_argument("--contrast-class", default="adversarial",
                        choices=("adversarial", "cold"),
                        help="negative-valence contrast against neutral (default adversarial)")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    axis_spec = hormone_axis_spec(args.contrast_class)
    if axis_spec["c1_admissible"]:
        raise SystemExit(
            f"--contrast-class {args.contrast_class!r} is C1-admissible; "
            "use extract_oxytocin_gemma.py for positive directions"
        )

    corpus_path = _resolve_path(args.corpus)
    split_manifest_path = _resolve_path(args.split_manifest)
    output_path = _resolve_path(args.out) if args.out is not None else _resolve_path(
        _default_output(axis_spec)
    )
    sidecar_path = Path(str(output_path) + ".sha256.json")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing atlas artifact: {output_path}")
    if sidecar_path.exists():
        raise FileExistsError(f"refusing to overwrite artifact digest sidecar: {sidecar_path}")

    primary_holdout = load_primary_holdout_manifest(split_manifest_path, corpus_path)
    corpus = load_sev_corpus(corpus_path)
    pairs = training_pairs(corpus, primary_holdout, positive_class=args.contrast_class)
    print(
        f"[split] axis={axis_spec['axis']} contrast={args.contrast_class} "
        f"manifest={primary_holdout.manifest_id} split={primary_holdout.frozen_split.split_id} "
        f"training_pairs={len(pairs)} held_out={list(primary_holdout.held_out_skeletons)}"
    )

    device = args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu"
    print(f"[init] Using device: {device}")
    model, encode, processor = load_model_and_processor(
        args.model, args.revision, args.local_files_only
    )
    model_provenance = object_provenance(
        model, identifier=args.model, requested_revision=args.revision, role="model"
    )
    processor_provenance = object_provenance(
        processor, identifier=args.model, requested_revision=args.revision, role="processor"
    )
    bindings = resolve_surface_bindings(model)
    positive, neutral = collect_activations(model, encode, pairs, bindings, device)
    directions, statistics = compute_method_a_directions(positive, neutral)
    payload = build_walled_artifact_payload(
        directions, statistics, axis_spec,
        model_id=args.model, revision=args.revision,
        model_provenance=model_provenance, processor_provenance=processor_provenance,
        bindings=bindings, primary_holdout=primary_holdout,
        split_manifest_path=split_manifest_path, corpus_path=corpus_path,
        code_revision=args.code_revision,
    )
    artifact_sha256 = atomic_torch_save_no_overwrite(payload, output_path)
    digest_path = publish_digest_sidecar(
        output_path, artifact_sha256=artifact_sha256, axis_spec=axis_spec,
        code_revision=args.code_revision, model_revision=args.revision,
        primary_holdout=primary_holdout,
    )
    print(
        f"[export] wrote WALLED atlas artifact {output_path} sha256={artifact_sha256} "
        f"schema={axis_spec['artifact_schema_version']} c1_admissible=False "
        f"digest_sidecar={digest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
