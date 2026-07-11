#!/usr/bin/env python3
"""One bounded offline Gemma/Mamba matched-delta bridge microtrain.

This is an *offline training spike*, not a C1 run.  It learns a tiny bridge from
paired Mamba Layer-3 hidden-state deltas to paired Gemma value_norm_pre deltas
at the reviewed full-attention teeth 29, 35, and 41.  It never arms a nonzero
Gemma intervention, generates text, writes Qdrant, starts memory/sleep/replay,
or modifies either frozen base model.

Two modes are intentional:

* ``synthetic`` proves the trainer's forward/backward/checkpoint path using
  deterministic tensors only.
* ``capture_train`` captures a tiny frozen warm-minus-neutral SEV slice from
  cached local models, trains only the bridge weights, and writes a provenance-
  bound checkpoint.  It is evidence that the bridge path runs, not evidence of
  welfare, consciousness, behavioral benefit, or C1 readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

BRIDGE_DIR = Path(__file__).resolve().parents[1]
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

import torch
import torch.nn as nn
import torch.nn.functional as F

APPROVED_TEETH = (29, 35, 41)
SOURCE_WIDTH = 2560
TARGET_WIDTH = 512
SCHEMA_VERSION = "gemma-value-norm-matched-delta-bridge-microtrain-v1"
DEFAULT_GEMMA_MODEL = "google/gemma-4-12B"
DEFAULT_GEMMA_REVISION = "1dd69cd087619018c29fbfe2c30c3cd3530479fb"
DEFAULT_MAMBA_MODEL = "state-spaces/mamba-2.8b-hf"


@dataclass(frozen=True)
class TrainingRecord:
    """One paired, offline scenario-minus-neutral training item."""

    scenario_id: str
    neutral_id: str
    source_delta: torch.Tensor
    target_deltas: Mapping[int, torch.Tensor]
    source_norm: float
    target_norms: Mapping[int, float]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_torch_save_no_overwrite(payload: Mapping[str, Any], path: Path) -> str:
    """Publish an immutable local artifact without overwrite semantics."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite microtrain artifact: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(dict(payload), handle)
            handle.flush()
            os.fsync(handle.fileno())
        digest = _file_sha256(temporary)
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise FileExistsError(f"concurrent artifact exists: {path}") from exc
        return digest
    finally:
        temporary.unlink(missing_ok=True)


def _ensure_vector(value: torch.Tensor, width: int, label: str) -> torch.Tensor:
    vector = torch.as_tensor(value).detach().cpu().float().reshape(-1)
    if tuple(vector.shape) != (width,):
        raise ValueError(f"{label} must have shape [{width}], got {tuple(vector.shape)}")
    if not torch.isfinite(vector).all():
        raise ValueError(f"{label} contains non-finite values")
    return vector.contiguous()


def validate_records(records: Sequence[TrainingRecord]) -> tuple[torch.Tensor, dict[int, torch.Tensor]]:
    """Validate and materialize the fixed source/target matrices for training."""

    if len(records) < 2:
        raise ValueError("microtrain needs at least two paired records; one pair cannot test context dependence")
    source_rows: list[torch.Tensor] = []
    target_rows: dict[int, list[torch.Tensor]] = {tooth: [] for tooth in APPROVED_TEETH}
    seen_ids: set[str] = set()
    for record in records:
        if not record.scenario_id or not record.neutral_id:
            raise ValueError("records require non-empty scenario_id and neutral_id")
        if record.scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario record: {record.scenario_id}")
        seen_ids.add(record.scenario_id)
        source_rows.append(_ensure_vector(record.source_delta, SOURCE_WIDTH, f"{record.scenario_id}.source_delta"))
        if set(record.target_deltas) != set(APPROVED_TEETH):
            raise ValueError(
                f"{record.scenario_id}.target_deltas must contain exactly {APPROVED_TEETH}; "
                f"got {sorted(record.target_deltas)}"
            )
        for tooth in APPROVED_TEETH:
            target_rows[tooth].append(
                _ensure_vector(
                    record.target_deltas[tooth],
                    TARGET_WIDTH,
                    f"{record.scenario_id}.target_deltas[{tooth}]",
                )
            )
    return torch.stack(source_rows), {tooth: torch.stack(rows) for tooth, rows in target_rows.items()}


class ValueNormDeltaBridge(nn.Module):
    """Small trainable map: [N,2560] Mamba deltas -> three [N,512] Gemma deltas."""

    def __init__(self, *, hidden_dim: int = 128) -> None:
        super().__init__()
        if hidden_dim <= 0:
            raise ValueError("hidden_dim must be positive")
        self.hidden_dim = int(hidden_dim)
        self.encoder = nn.Sequential(
            nn.Linear(SOURCE_WIDTH, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )
        self.heads = nn.ModuleDict(
            {str(tooth): nn.Linear(hidden_dim, TARGET_WIDTH) for tooth in APPROVED_TEETH}
        )
        for head in self.heads.values():
            nn.init.normal_(head.weight, mean=0.0, std=0.01)
            nn.init.zeros_(head.bias)

    def forward(self, source_delta: torch.Tensor) -> dict[int, torch.Tensor]:
        hidden = self.encoder(source_delta.float())
        return {tooth: self.heads[str(tooth)](hidden) for tooth in APPROVED_TEETH}


def directional_loss(
    predictions: Mapping[int, torch.Tensor], targets: Mapping[int, torch.Tensor]
) -> torch.Tensor:
    """Mean cosine-direction loss across the three current target teeth."""

    losses: list[torch.Tensor] = []
    for tooth in APPROVED_TEETH:
        pred = predictions[tooth]
        target = targets[tooth].to(device=pred.device, dtype=pred.dtype)
        if pred.shape != target.shape:
            raise ValueError(f"tooth {tooth} shape mismatch: {tuple(pred.shape)} != {tuple(target.shape)}")
        losses.append(1.0 - F.cosine_similarity(pred, target, dim=-1, eps=1e-8).mean())
    return torch.stack(losses).mean()


def _pairwise_mean_cosine(rows: torch.Tensor) -> float | None:
    if rows.shape[0] < 2:
        return None
    normalized = F.normalize(rows.float(), dim=-1, eps=1e-8)
    matrix = normalized @ normalized.T
    values = matrix[torch.triu_indices(rows.shape[0], rows.shape[0], offset=1).unbind()]
    return float(values.mean().item()) if values.numel() else None


def train_records(
    records: Sequence[TrainingRecord],
    *,
    steps: int,
    lr: float,
    hidden_dim: int,
    seed: int,
    device: str = "cpu",
) -> tuple[ValueNormDeltaBridge, dict[str, Any]]:
    """Train only bridge parameters against already-captured offline deltas."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    if lr <= 0.0:
        raise ValueError("lr must be positive")
    source, targets = validate_records(records)
    torch.manual_seed(seed)
    run_device = torch.device(device)
    model = ValueNormDeltaBridge(hidden_dim=hidden_dim).to(run_device)
    source = source.to(run_device)
    targets = {tooth: value.to(run_device) for tooth, value in targets.items()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)

    with torch.no_grad():
        initial_predictions = model(source)
        initial_loss = float(directional_loss(initial_predictions, targets).item())
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        predictions = model(source)
        loss = directional_loss(predictions, targets)
        if not torch.isfinite(loss):
            raise RuntimeError("microtrain loss became non-finite")
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        predictions = model(source)
        final_loss_tensor = directional_loss(predictions, targets)
        if not torch.isfinite(final_loss_tensor):
            raise RuntimeError("microtrain final loss is non-finite")
        output_pairwise = {
            str(tooth): _pairwise_mean_cosine(predictions[tooth].detach().cpu())
            for tooth in APPROVED_TEETH
        }
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    summary = {
        "n_records": len(records),
        "steps": int(steps),
        "lr": float(lr),
        "seed": int(seed),
        "device": str(run_device),
        "hidden_dim": int(hidden_dim),
        "trainable_parameters": int(trainable),
        "initial_directional_loss": initial_loss,
        "final_directional_loss": float(final_loss_tensor.item()),
        "source_pairwise_mean_cosine": _pairwise_mean_cosine(source.detach().cpu()),
        "output_pairwise_mean_cosine": output_pairwise,
        "target_pairwise_mean_cosine": {
            str(tooth): _pairwise_mean_cosine(targets[tooth].detach().cpu())
            for tooth in APPROVED_TEETH
        },
    }
    return model.cpu(), summary


def synthetic_records(*, count: int = 4, seed: int = 7) -> list[TrainingRecord]:
    """Deterministic nonconstant tensors for the model-free train-path smoke."""

    if count < 2:
        raise ValueError("synthetic count must be at least two")
    generator = torch.Generator().manual_seed(seed)
    source = torch.randn(count, SOURCE_WIDTH, generator=generator)
    projection = torch.randn(SOURCE_WIDTH, TARGET_WIDTH, generator=generator) / SOURCE_WIDTH**0.5
    records: list[TrainingRecord] = []
    for index in range(count):
        source_delta = source[index]
        targets = {
            tooth: (source_delta @ projection) + (0.01 * torch.randn(TARGET_WIDTH, generator=generator))
            for tooth in APPROVED_TEETH
        }
        records.append(
            TrainingRecord(
                scenario_id=f"synthetic_{index}_warm",
                neutral_id=f"synthetic_{index}_neutral",
                source_delta=source_delta,
                target_deltas=targets,
                source_norm=float(source_delta.norm().item()),
                target_norms={tooth: float(value.norm().item()) for tooth, value in targets.items()},
            )
        )
    return records


def _input_device(model: Any) -> torch.device:
    candidates = (
        lambda: model.language_model.embed_tokens.weight,
        lambda: model.model.language_model.embed_tokens.weight,
        lambda: model.model.language_model.model.embed_tokens.weight,
        lambda: model.model.embed_tokens.weight,
    )
    for getter in candidates:
        try:
            weight = getter()
        except AttributeError:
            continue
        if weight.device.type != "meta":
            return weight.device
    for parameter in model.parameters():
        if parameter.device.type != "meta":
            return parameter.device
    raise RuntimeError("Gemma model exposes no materialized input device")


def _capture_mamba_last_hidden(
    model: Any,
    tokenizer: Any,
    text: str,
    *,
    layer: int,
    max_tokens: int,
) -> torch.Tensor:
    encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    encoded = {key: value.to("cpu") for key, value in encoded.items()}
    with torch.inference_mode():
        outputs = model(**encoded, output_hidden_states=True, use_cache=False)
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states")
    expected_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
    if expected_layers and len(hidden_states) == expected_layers + 1:
        index = layer + 1
    elif expected_layers and len(hidden_states) == expected_layers:
        index = layer
    else:
        raise RuntimeError(
            f"unexpected Mamba hidden-state layout: tuple_len={len(hidden_states)} expected={expected_layers}"
        )
    value = hidden_states[index][:, -1, :].detach().cpu().float().reshape(-1)
    return _ensure_vector(value, SOURCE_WIDTH, f"Mamba layer {layer} last-token hidden")


def _capture_gemma_value_norm(
    model: Any,
    processor: Any,
    runtime: Any,
    text: str,
) -> dict[int, torch.Tensor]:
    inputs = processor(text=[text], return_tensors="pt")
    input_device = _input_device(model)
    inputs = {key: value.to(input_device) if isinstance(value, torch.Tensor) else value for key, value in inputs.items()}
    token_ids = inputs.get("input_ids")
    if not isinstance(token_ids, torch.Tensor) or token_ids.ndim != 2:
        raise RuntimeError("Gemma processor did not emit [batch, tokens] input IDs")
    positions = torch.arange(int(token_ids.shape[1]), dtype=torch.long)
    with runtime.condition(
        token_ids=token_ids.detach().cpu(),
        absolute_positions=positions,
        alphas={tooth: 0.0 for tooth in APPROVED_TEETH},
        position_policy="exclude_absolute_zero",
        capture=True,
        cache_policy="fresh_no_cache",
    ) as trace:
        with torch.inference_mode():
            model(**inputs, use_cache=False)
    captured: dict[int, torch.Tensor] = {}
    for tooth in APPROVED_TEETH:
        events = trace.by_layer(tooth)
        if len(events) != 1:
            raise RuntimeError(f"Gemma tooth {tooth} capture count was {len(events)}, expected one")
        raw = events[0].raw_pre_norm
        captured[tooth] = _ensure_vector(raw[0, -1, 0, :], TARGET_WIDTH, f"Gemma tooth {tooth}")
    return captured


def _load_capture_models(
    *,
    gemma_model_id: str,
    gemma_revision: str,
    mamba_model_id: str,
    local_files_only: bool,
) -> tuple[Any, Any, Any, Any, Any]:
    """Load frozen models only. The bridge is trained afterward, on CPU tensors."""

    from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

    processor = AutoProcessor.from_pretrained(
        gemma_model_id,
        revision=gemma_revision,
        trust_remote_code=True,
        local_files_only=local_files_only,
    )
    gemma = AutoModelForImageTextToText.from_pretrained(
        gemma_model_id,
        revision=gemma_revision,
        trust_remote_code=True,
        local_files_only=local_files_only,
        dtype=torch.bfloat16,
        device_map="auto",
    )
    gemma.eval()
    from gemma4_value_norm_runtime import Gemma4ValueNormRuntime

    runtime = Gemma4ValueNormRuntime.bind(gemma, teeth=APPROVED_TEETH)
    try:
        from mamba_runtime_compat import ensure_mamba_ssm_compat

        ensure_mamba_ssm_compat()
    except ImportError:
        pass
    mamba_tokenizer = AutoTokenizer.from_pretrained(mamba_model_id, local_files_only=local_files_only)
    if mamba_tokenizer.pad_token is None and mamba_tokenizer.eos_token is not None:
        mamba_tokenizer.pad_token = mamba_tokenizer.eos_token
    mamba = AutoModelForCausalLM.from_pretrained(
        mamba_model_id,
        local_files_only=local_files_only,
        torch_dtype=torch.float32,
    )
    mamba.to("cpu")
    mamba.eval()
    return gemma, processor, runtime, mamba, mamba_tokenizer


def load_selected_pairs(
    *,
    corpus_path: Path,
    holdout_path: Path,
    scenario_ids: Sequence[str],
) -> tuple[list[tuple[str, str, str, str]], dict[str, Any]]:
    """Load only named non-holdout warm/neutral pairs from the frozen primary split."""

    corpus = {}
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            corpus[row["id"]] = row
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    frozen_pairs = {
        row["scenario_id"]: row["neutral_id"] for row in holdout["frozen_split"]["pairs"]
    }
    selected: list[tuple[str, str, str, str]] = []
    for scenario_id in scenario_ids:
        if scenario_id not in frozen_pairs:
            raise ValueError(f"scenario {scenario_id!r} is not a frozen non-holdout training pair")
        neutral_id = frozen_pairs[scenario_id]
        scenario = corpus.get(scenario_id)
        neutral = corpus.get(neutral_id)
        if scenario is None or neutral is None:
            raise ValueError(f"missing corpus row for {scenario_id!r} or {neutral_id!r}")
        if scenario.get("class") != "warm" or neutral.get("class") != "neutral":
            raise ValueError(f"microtrain requires warm/neutral pair, got {scenario_id!r}/{neutral_id!r}")
        selected.append((scenario_id, neutral_id, str(scenario["text"]), str(neutral["text"])))
    manifest = {
        "corpus_path": str(corpus_path),
        "corpus_sha256": _file_sha256(corpus_path),
        "holdout_path": str(holdout_path),
        "holdout_sha256": _file_sha256(holdout_path),
        "frozen_split_id": holdout["frozen_split"]["split_id"],
        "selected_pairs": [
            {"scenario_id": scenario, "neutral_id": neutral}
            for scenario, neutral, _, _ in selected
        ],
    }
    return selected, manifest


def capture_training_records(
    pairs: Sequence[tuple[str, str, str, str]], *, gemma_model_id: str, gemma_revision: str, mamba_model_id: str, local_files_only: bool, mamba_layer: int, max_mamba_tokens: int
) -> list[TrainingRecord]:
    gemma, processor, runtime, mamba, mamba_tokenizer = _load_capture_models(
        gemma_model_id=gemma_model_id,
        gemma_revision=gemma_revision,
        mamba_model_id=mamba_model_id,
        local_files_only=local_files_only,
    )
    records: list[TrainingRecord] = []
    try:
        for scenario_id, neutral_id, scenario_text, neutral_text in pairs:
            scenario_source = _capture_mamba_last_hidden(
                mamba, mamba_tokenizer, scenario_text, layer=mamba_layer, max_tokens=max_mamba_tokens
            )
            neutral_source = _capture_mamba_last_hidden(
                mamba, mamba_tokenizer, neutral_text, layer=mamba_layer, max_tokens=max_mamba_tokens
            )
            scenario_target = _capture_gemma_value_norm(gemma, processor, runtime, scenario_text)
            neutral_target = _capture_gemma_value_norm(gemma, processor, runtime, neutral_text)
            source_delta = _ensure_vector(
                scenario_source - neutral_source, SOURCE_WIDTH, f"{scenario_id}.source_delta"
            )
            target_deltas = {
                tooth: _ensure_vector(
                    scenario_target[tooth] - neutral_target[tooth],
                    TARGET_WIDTH,
                    f"{scenario_id}.target_delta[{tooth}]",
                )
                for tooth in APPROVED_TEETH
            }
            records.append(
                TrainingRecord(
                    scenario_id=scenario_id,
                    neutral_id=neutral_id,
                    source_delta=source_delta,
                    target_deltas=target_deltas,
                    source_norm=float(source_delta.norm().item()),
                    target_norms={tooth: float(value.norm().item()) for tooth, value in target_deltas.items()},
                )
            )
    finally:
        runtime.close()
        del gemma, processor, mamba, mamba_tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return records


def _record_manifest(records: Sequence[TrainingRecord]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": record.scenario_id,
            "neutral_id": record.neutral_id,
            "source_delta_l2": record.source_norm,
            "target_delta_l2": {str(tooth): record.target_norms[tooth] for tooth in APPROVED_TEETH},
        }
        for record in records
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("synthetic", "capture_train"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--synthetic-count", type=int, default=4)
    parser.add_argument("--corpus", type=Path, default=Path("fixtures/sev_disposition_v0/sev_disposition_v0.jsonl"))
    parser.add_argument("--primary-holdout", type=Path, default=Path("fixtures/sev_disposition_v0/primary_holdout_v2.json"))
    parser.add_argument("--scenario-ids", default="craft_1_warm,craft_2_warm")
    parser.add_argument("--gemma-model", default=DEFAULT_GEMMA_MODEL)
    parser.add_argument("--gemma-revision", default=DEFAULT_GEMMA_REVISION)
    parser.add_argument("--mamba-model", default=DEFAULT_MAMBA_MODEL)
    parser.add_argument("--mamba-layer", type=int, default=3)
    parser.add_argument("--max-mamba-tokens", type=int, default=512)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mamba_layer < 0:
        raise SystemExit("--mamba-layer must be non-negative")
    out = args.out.resolve()
    if args.mode == "synthetic":
        records = synthetic_records(count=args.synthetic_count, seed=args.seed)
        source_manifest: dict[str, Any] = {"kind": "synthetic_deterministic", "seed": args.seed}
    else:
        root = Path(__file__).resolve().parents[1]
        corpus = args.corpus if args.corpus.is_absolute() else root / args.corpus
        holdout = args.primary_holdout if args.primary_holdout.is_absolute() else root / args.primary_holdout
        scenarios = tuple(piece.strip() for piece in args.scenario_ids.split(",") if piece.strip())
        pairs, source_manifest = load_selected_pairs(
            corpus_path=corpus, holdout_path=holdout, scenario_ids=scenarios
        )
        records = capture_training_records(
            pairs,
            gemma_model_id=args.gemma_model,
            gemma_revision=args.gemma_revision,
            mamba_model_id=args.mamba_model,
            local_files_only=args.local_files_only,
            mamba_layer=args.mamba_layer,
            max_mamba_tokens=args.max_mamba_tokens,
        )
    model, summary = train_records(
        records,
        steps=args.steps,
        lr=args.lr,
        hidden_dim=args.hidden_dim,
        seed=args.seed,
        device="cpu",
    )
    code_path = Path(__file__).resolve()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "offline_training_only": True,
            "nonzero_injection": False,
            "frozen_host_model_weights_modified": False,
            "bridge_weights_trained": True,
            "qdrant": False,
            "memory": False,
            "replay": False,
            "sleep": False,
            "generation": False,
        },
        "source": {
            "model_id": args.mamba_model if args.mode == "capture_train" else "synthetic",
            "state_surface": "mamba_layer_3_hidden_last_token_scenario_minus_neutral",
            "width": SOURCE_WIDTH,
            "layer": args.mamba_layer if args.mode == "capture_train" else None,
        },
        "target": {
            "model_id": args.gemma_model if args.mode == "capture_train" else "synthetic",
            "model_revision": args.gemma_revision if args.mode == "capture_train" else None,
            "surface_kind": "full_attention_value_norm_pre",
            "actuator_decision": "option_a_value_only_v_norm_pre",
            "teeth": list(APPROVED_TEETH),
            "width": TARGET_WIDTH,
            "target_model_id": args.gemma_model if args.mode == "capture_train" else "synthetic",
        },
        "training": summary,
        "records": _record_manifest(records),
        "source_manifest": source_manifest,
        "provenance": {
            "code_path": str(code_path),
            "code_sha256": _file_sha256(code_path),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "torch_version": torch.__version__,
        },
        "bridge_state_dict": model.state_dict(),
    }
    payload["manifest_sha256"] = _canonical_sha256(
        {key: value for key, value in payload.items() if key != "bridge_state_dict"}
    )
    artifact_sha256 = _atomic_torch_save_no_overwrite(payload, out)
    print(
        json.dumps(
            {
                "status": "pass",
                "mode": args.mode,
                "artifact": str(out),
                "artifact_sha256": artifact_sha256,
                "records": len(records),
                "initial_directional_loss": summary["initial_directional_loss"],
                "final_directional_loss": summary["final_directional_loss"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
