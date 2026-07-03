#!/usr/bin/env python3
"""4-cell DC-removal x RMS-scaling ablation harness (OpenCLAW #127).

Sweeps the two locked bridge-injection operations across four cells:

    fixed     neither flag            alpha in {0.2,0.4,0.6,0.8,1.0,1.2}
    rms_only  --rms-scale             alpha in {1,2,4,8,16}
    dc_only   --dc-remove             alpha in {0.2,0.4,0.6,0.8,1.0,1.2}
    dc_rms    --dc-remove --rms-scale alpha in {1,2,4,8,16}

Per (cell, alpha) it captures two things:

  * geometry  -- per-target-layer cross-context (per-disposition) mean-pairwise-cosine of
                 the injected bias directions. Alpha-independent and rms-independent (rms
                 renormalizes magnitude, not direction), so it depends only on dc_remove and
                 is computed once per DC state and shared across the cell's alpha sweep. This
                 runs CPU-only (compressor + hypernet + calibration states); it directly
                 reproduces the #517/#518 collapse -> DC-removal recovery (~0.96 -> ~0.10).
  * probe score total -- behavioral D2 panel run through the live bridge with the cell's
                 flags. This needs the full Qwen + Mamba stack and only runs with
                 --run-behavior on a GPU box (ML-WS). It is NOT run here.

Results stream incrementally to results/dc_rms_ablation/dc_rms_ablation_<ts>.json.

CPU / no-GPU usage:
    python spikes/run_dc_rms_ablation.py --dry-run          # validate wiring + geometry
The dry run enumerates every (cell, alpha), validates the calibration file and that
apply_bridge_adjustments accepts the DC/RMS kwargs, computes the geometry if the bridge
checkpoint + states are present, and writes the planned chat_server command per cell --
all without loading Qwen or Mamba. The real behavioral run is the parent's job on ML-WS.
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import inspect
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

import torch
import torch.nn.functional as F

BRIDGE_DIR = Path(__file__).resolve().parents[1]
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

# Geometry needs only the two small bridge modules (torch-only, no Qwen/Mamba).
from models import ActivationBiasHypernetwork, MambaStateCompressor  # noqa: E402

# Geometry construction mirrors spikes/precompute_dc_vectors.py and
# run_monk_bridge_dc_geometry_probe.py so the numbers land in the validated space.
TARGET_DIMS = [(2048, 256)] * 4
DEFAULT_TARGET_LAYERS = [12, 13, 14, 15]

FIXED_ALPHAS = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]
RMS_ALPHAS = [1.0, 2.0, 4.0, 8.0, 16.0]

CELLS = [
    {"name": "fixed", "dc_remove": False, "rms_scale": False},
    {"name": "rms_only", "dc_remove": False, "rms_scale": True},
    {"name": "dc_only", "dc_remove": True, "rms_scale": False},
    {"name": "dc_rms", "dc_remove": True, "rms_scale": True},
]


# ---------- cell / alpha enumeration (the core wiring) ----------

def cell_alphas(cell: dict, fixed_alphas: list, rms_alphas: list) -> list:
    """rms cells sweep the rms alpha ladder; fixed cells sweep the fixed ladder."""
    return list(rms_alphas) if cell["rms_scale"] else list(fixed_alphas)


def iter_runs(cells: list, fixed_alphas: list, rms_alphas: list) -> Iterator[tuple]:
    for cell in cells:
        for alpha in cell_alphas(cell, fixed_alphas, rms_alphas):
            yield cell, float(alpha)


def planned_chat_server_command(cell: dict, alpha: float, args) -> list:
    """The exact chat_server.py invocation that drives the runtime for this cell/alpha."""
    cmd = ["python", "chat_server.py", "--alpha", f"{alpha:g}"]
    if cell["dc_remove"]:
        cmd += ["--dc-remove", "--dc-calibration-path", str(args.dc_calibration_path)]
    if cell["rms_scale"]:
        cmd += ["--rms-scale"]
    return cmd


# ---------- geometry (CPU-only) ----------

def mean_pairwise_cosine(x: torch.Tensor) -> float:
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    if n <= 1:
        return 0.0
    return float((sim.sum() - sim.diag().sum()) / (n * (n - 1)))


def load_dc_vectors(path: Path) -> tuple[list, list]:
    blob = torch.load(path, map_location="cpu", weights_only=False)
    return list(blob["dc_vectors"]), list(blob.get("target_layers", DEFAULT_TARGET_LAYERS))


def compute_disposition_biases(bridge_ckpt: Path, states_path: Path) -> list:
    """Return one [n_disposition, dim] bias tensor per target layer (CPU, no Qwen/Mamba).

    Mirrors precompute_dc_vectors.py: compressor(states) -> hypernet -> per-head bias. The
    calibration states are the disposition/context basis for the cross-context geometry.
    """
    states = torch.load(states_path, map_location="cpu", weights_only=False)["states"].float()
    ckpt = torch.load(bridge_ckpt, map_location="cpu", weights_only=False)
    comp = MambaStateCompressor(64, 2560, 1, 2048, target_layer=3).eval()
    comp.load_state_dict(ckpt["compressor_state_dict"])
    hyper = ActivationBiasHypernetwork(2048, TARGET_DIMS, hidden_dim=1024).eval()
    hyper.load_state_dict(ckpt["hypernetwork_state_dict"])
    with torch.no_grad():
        biases = hyper(comp(states))
    return [b.float() for b in biases]


def geometry_for_dc(
    biases: list,
    dc_remove: bool,
    dc_vectors: Optional[list],
    target_layers: list,
) -> dict:
    """Per-head + aggregate mean-pairwise-cosine, optionally after DC removal."""
    per_head = []
    for idx, b in enumerate(biases):
        vec = b
        mag_retained = 1.0
        if dc_remove:
            if dc_vectors is None:
                raise ValueError("geometry_for_dc: dc_remove set but dc_vectors is None.")
            vec = b - dc_vectors[idx].to(b.dtype)
            mag_retained = float(vec.norm(dim=-1).mean() / b.norm(dim=-1).mean())
        layer = target_layers[idx] if idx < len(target_layers) else DEFAULT_TARGET_LAYERS[idx]
        per_head.append(
            {
                "head": f"L{layer}:v_proj",
                "mean_pairwise_cosine": mean_pairwise_cosine(vec),
                "magnitude_retained_fraction": mag_retained,
            }
        )
    n = len(per_head)
    aggregate = {
        "mean_pairwise_cosine_avg": sum(h["mean_pairwise_cosine"] for h in per_head) / n,
        "magnitude_retained_fraction_avg": sum(h["magnitude_retained_fraction"] for h in per_head) / n,
        "n_dispositions": int(biases[0].shape[0]),
    }
    return {"dc_remove": dc_remove, "per_head": per_head, "aggregate": aggregate}


# ---------- wiring validation (dry run) ----------

def validate_apply_signature() -> dict:
    """Confirm apply_bridge_adjustments accepts the DC/RMS kwargs (imports the wiring)."""
    from reincarnated_inference import apply_bridge_adjustments  # noqa: E402

    params = set(inspect.signature(apply_bridge_adjustments).parameters)
    required = {"dc_remove", "dc_vectors", "rms_scale"}
    missing = sorted(required - params)
    if missing:
        raise RuntimeError(f"apply_bridge_adjustments is missing kwargs: {missing}")
    return {"apply_params": sorted(params), "accepts_dc_rms_kwargs": True}


# ---------- behavioral D2 panel (GPU; parent runs on ML-WS) ----------

def run_behavioral_panel(engine: "BehavioralEngine", cell: dict, alpha: float) -> dict:
    """Drive the bridge with this cell's flags and score the D2 probe panel.

    Requires the full Qwen + Mamba stack (engine). Only called under --run-behavior.
    """
    return engine.run(cell, alpha)


class BehavioralEngine:
    """Loads Qwen + Mamba + bridge once and re-applies the bridge per (cell, alpha).

    Kept behind --run-behavior; not exercised on CPU. Reuses reincarnated_inference's
    building blocks (same functions chat_server.py uses at startup) plus the scored probe
    panel from run_base_improv_bakeoff, so behavior matches the live runtime path.
    """

    def __init__(self, args):
        import reincarnated_inference as ri
        import run_base_improv_bakeoff as bakeoff

        self.ri = ri
        self.bakeoff = bakeoff
        self.args = args

        self.bridge_ckpt = torch.load(args.bridge, map_location=args.bridge_device, weights_only=False)
        self.target_specs = ri.resolve_target_specs(self.bridge_ckpt, "")
        self.tokenizer, self.qwen = ri.load_model_and_tokenizer(args.qwen_model_id, args.qwen_device)
        self.patched_layers = ri.patch_model(self.qwen, self.target_specs)
        target_dims = self.bridge_ckpt.get("target_dims") or ri.infer_target_dims(self.qwen, self.target_specs)
        self.mamba_tokenizer, self.mamba = ri.load_model_and_tokenizer(args.mamba_model_id, args.mamba_device)
        (
            self.context_encoder,
            self.hypernet,
            self.target_layer,
            self.hidden_layer_count,
            self.context_mode,
            self.bridge_mode,
        ) = ri.build_context_encoder_and_hypernetwork(
            checkpoint=self.bridge_ckpt,
            mamba_model=self.mamba,
            target_dims=target_dims,
            bridge_device=args.bridge_device,
        )

        # DC calibration (validated against the patched layer count).
        self.dc_vectors = None
        dc_vecs, _layers = load_dc_vectors(_resolve_calibration_path(args))
        if len(dc_vecs) != len(self.patched_layers):
            raise RuntimeError(
                f"DC calibration vector count ({len(dc_vecs)}) != patched target layers "
                f"({len(self.patched_layers)})."
            )
        self.dc_vectors = [v.to(args.bridge_device) for v in dc_vecs]

        # Condition the bridge on the target disposition (fixed across the sweep; geometry
        # captures the cross-disposition axis separately).
        episodes = ri.load_episodes(Path(args.episodes_file))
        episode = ri.select_episode(episodes, args)
        tok = self.mamba_tokenizer(
            episode["transcript"], return_tensors="pt", truncation=True, max_length=args.max_mamba_tokens
        )
        tok = {k: v.to(args.mamba_device) for k, v in tok.items()}
        with torch.no_grad():
            out = self.mamba(**tok, output_hidden_states=True)
            state = ri.extract_last_token_hidden(
                out, layer_idx=self.target_layer, expected_layers=self.hidden_layer_count
            ).to(args.bridge_device, dtype=torch.float32)
            context = self.context_encoder(state)
            self.bridge_adjustments, _ = ri.resolve_bridge_adjustments(
                hypernetwork=self.hypernet, context_vector=context, bridge_mode=self.bridge_mode
            )
        self.probes = list(bakeoff.PROBES)

    def run(self, cell: dict, alpha: float) -> dict:
        ri = self.ri
        bakeoff = self.bakeoff
        args = self.args
        ri.apply_bridge_adjustments(
            patched_layers=self.patched_layers,
            bridge_adjustments=self.bridge_adjustments,
            bridge_mode=self.bridge_mode,
            alpha=alpha,
            dc_remove=cell["dc_remove"],
            dc_vectors=self.dc_vectors,
            rms_scale=cell["rms_scale"],
        )
        candidate = {"name": f"dc_rms::{cell['name']}::a{alpha:g}", "prompt_style": "plain"}
        rows = []
        for probe in self.probes:
            prompt = bakeoff.build_plain_prompt(candidate, probe)
            inputs = self.tokenizer([prompt], return_tensors="pt").to(self.qwen.device)
            with torch.inference_mode():
                gen = self.qwen.generate(
                    **inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
            raw = ri.decode_new_tokens(self.tokenizer, gen, inputs["input_ids"].shape[-1])
            answer, trimmed, marker = bakeoff.extract_first_answer(raw)
            scoring = bakeoff.score_answer(probe, answer)
            rows.append({"probe_id": probe.pid, "answer": answer, **scoring})
        return {"probe_score_total": sum(r["score"] for r in rows), "probes": rows}


# ---------- driver ----------

def _resolve_calibration_path(args) -> Path:
    path = Path(args.dc_calibration_path)
    if not path.is_absolute():
        path = BRIDGE_DIR / path
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(description="4-cell DC-removal x RMS-scaling ablation (OpenCLAW #127)")
    parser.add_argument("--out", default=f"results/dc_rms_ablation/dc_rms_ablation_{ts}.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate wiring + geometry without loading Qwen/Mamba.")
    parser.add_argument("--run-behavior", action="store_true", help="Run the behavioral D2 panel (needs GPU; ML-WS only).")
    parser.add_argument("--bridge", default=str(BRIDGE_DIR / "cheese_reincarnation_bridge_1.5b_codexfix.pt"))
    parser.add_argument("--states", default=str(BRIDGE_DIR / "mamba_layer3_states_v1.pt"))
    parser.add_argument("--dc-calibration-path", default="dc_calibration_v1.pt")
    parser.add_argument("--episodes-file", default=str(BRIDGE_DIR / "CHEESE_SHAPING_EPISODES.md"))
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--episode-name", default="")
    parser.add_argument("--qwen-model-id", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--mamba-model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--bridge-device", default="cuda:0")
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--fixed-alphas", default=",".join(f"{a:g}" for a in FIXED_ALPHAS))
    parser.add_argument("--rms-alphas", default=",".join(f"{a:g}" for a in RMS_ALPHAS))
    parser.add_argument("--only-cell", default="", help="Restrict to one cell name (fixed|rms_only|dc_only|dc_rms).")
    return parser


def _parse_alphas(text: str) -> list:
    return [float(x) for x in str(text).split(",") if x.strip()]


def write_incremental(out_path: Path, payload: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: Optional[list] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    out_path = Path(args.out)
    fixed_alphas = _parse_alphas(args.fixed_alphas)
    rms_alphas = _parse_alphas(args.rms_alphas)
    cells = [c for c in CELLS if not args.only_cell or c["name"] == args.only_cell]
    if not cells:
        raise SystemExit(f"--only-cell {args.only_cell!r} matched no cell in {[c['name'] for c in CELLS]}")

    calibration_path = _resolve_calibration_path(args)
    dc_vectors, target_layers = (None, DEFAULT_TARGET_LAYERS)
    calibration_info: dict[str, Any] = {"path": str(calibration_path), "loaded": False}
    if calibration_path.exists():
        dc_vectors, target_layers = load_dc_vectors(calibration_path)
        calibration_info.update(loaded=True, n_vectors=len(dc_vectors), target_layers=target_layers)

    payload: dict[str, Any] = {
        "namespace": "dc-rms-ablation-127",
        "task": "OpenCLAW #127",
        "created": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "run_behavior": bool(args.run_behavior),
        "config": {
            "bridge": args.bridge,
            "states": args.states,
            "calibration": calibration_info,
            "fixed_alphas": fixed_alphas,
            "rms_alphas": rms_alphas,
            "target_layers": target_layers,
        },
        "cells": [
            {**cell, "alphas": cell_alphas(cell, fixed_alphas, rms_alphas)} for cell in cells
        ],
        "wiring": None,
        "geometry": {},
        "runs": [],
    }

    # Wiring check: apply_bridge_adjustments must accept the DC/RMS kwargs.
    try:
        payload["wiring"] = validate_apply_signature()
    except Exception as exc:  # surface, do not crash the manifest
        payload["wiring"] = {"error": f"{type(exc).__name__}: {exc}"}
    write_incremental(out_path, payload)

    # Geometry (CPU): one value per DC state, shared across each cell's alpha sweep.
    biases = None
    if Path(args.bridge).exists() and Path(args.states).exists():
        biases = compute_disposition_biases(Path(args.bridge), Path(args.states))
    for dc_remove in sorted({c["dc_remove"] for c in cells}):
        key = "dc" if dc_remove else "no_dc"
        if biases is None:
            payload["geometry"][key] = {"error": "bridge checkpoint or states file not found"}
        elif dc_remove and dc_vectors is None:
            payload["geometry"][key] = {"error": "dc_remove requested but calibration not loaded"}
        else:
            payload["geometry"][key] = geometry_for_dc(biases, dc_remove, dc_vectors, target_layers)
        write_incremental(out_path, payload)

    # Behavioral engine (GPU) — only when explicitly requested and not a dry run.
    engine = None
    if args.run_behavior and not args.dry_run:
        engine = BehavioralEngine(args)

    for cell, alpha in iter_runs(cells, fixed_alphas, rms_alphas):
        geo_key = "dc" if cell["dc_remove"] else "no_dc"
        record: dict[str, Any] = {
            "cell": cell["name"],
            "dc_remove": cell["dc_remove"],
            "rms_scale": cell["rms_scale"],
            "alpha": alpha,
            "planned_command": planned_chat_server_command(cell, alpha, args),
            "geometry_ref": geo_key,
            "geometry_cosine_avg": (
                payload["geometry"].get(geo_key, {}).get("aggregate", {}).get("mean_pairwise_cosine_avg")
            ),
            "probe_score_total": None,
            "behavioral_ran": False,
        }
        if engine is not None:
            result = run_behavioral_panel(engine, cell, alpha)
            record.update(probe_score_total=result["probe_score_total"], probes=result["probes"], behavioral_ran=True)
        payload["runs"].append(record)
        write_incremental(out_path, payload)
        print(
            f"[{cell['name']}][alpha={alpha:g}] geo_cos_avg="
            f"{record['geometry_cosine_avg']} probe_total={record['probe_score_total']}",
            flush=True,
        )

    payload["completed"] = datetime.now(timezone.utc).isoformat()
    write_incremental(out_path, payload)
    print(f"Wrote {out_path} ({len(payload['runs'])} runs, dry_run={args.dry_run})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
