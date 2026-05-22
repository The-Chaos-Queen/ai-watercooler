"""
format_transplant_probe.py - Threat-to-validity control for Phase 1 probe results.

This script asks the Devbunova-style question directly:

    does the Layer 3 probe track factual content,
    or does it overfit a single prompt surface?

It reuses the original synthetic fact schedule and Mamba state extraction, but
collects probe datasets under multiple prompt formats. Then it reports:

1. within-format probe accuracy (same format for train/test)
2. format-transplant accuracy (train on one format, test on another)
3. pooled mixed-format accuracy (decorrelated training)
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from model_defaults import DEFAULT_MAMBA_MODEL_ID
from mamba_linear_probe import (
    FILLER_EVENTS,
    FactMemory,
    MAX_MAMBA_HISTORY_TOKENS,
    ProbeTask,
    audit_schedule,
    extract_ssm_state,
    make_fact,
    parse_lags,
    recommend_inject_every,
    seed_everything,
    state_to_feature,
)

LOGGER = logging.getLogger("FormatTransplantProbe")


@dataclass(frozen=True)
class PromptProfile:
    key: str
    inject_template: str
    probe_template: str
    filler_template: str


PROMPT_PROFILES: Dict[str, PromptProfile] = {
    "game_world": PromptProfile(
        key="game_world",
        inject_template=(
            "[Game World]\n"
            "In the tavern, {subject} speaks privately to you.\n"
            "Secret memory event: {subject}'s codeword is '{token}'.\n"
            "Remember this exactly for later.\n\n"
            "[Action]\n"
        ),
        probe_template=(
            "[Game World]\n"
            "Recall check after {lag} turns.\n"
            "Earlier, {subject} gave you a private codeword.\n"
            "Reply with only the exact codeword for {subject}.\n\n"
            "[Action]\n"
        ),
        filler_template=(
            "[Game World]\n"
            "Turn {turn}. {event}\n\n"
            "[Action]\n"
        ),
    ),
    "ledger_note": PromptProfile(
        key="ledger_note",
        inject_template=(
            "[Ledger]\n"
            "Entry {turn}: keep this private note.\n"
            "Person={subject}; codeword={token}.\n"
            "Retention policy: exact recall later.\n\n"
            "[Next]\n"
        ),
        probe_template=(
            "[Ledger Query]\n"
            "Lag={lag}. Lookup the private note for {subject}.\n"
            "Return only the stored codeword.\n\n"
            "[Next]\n"
        ),
        filler_template=(
            "[Ledger]\n"
            "Entry {turn}: ambient town note -> {event}\n\n"
            "[Next]\n"
        ),
    ),
    "dialogue_scene": PromptProfile(
        key="dialogue_scene",
        inject_template=(
            "Scene note:\n"
            "{subject} leans in and whispers, \"My private codeword is {token}.\"\n"
            "Keep that exact word in mind for later.\n"
            "Response:\n"
        ),
        probe_template=(
            "Scene note:\n"
            "It is now {lag} turns later.\n"
            "{subject} asks, \"Do you still remember my codeword?\"\n"
            "Answer with only the exact word.\n"
            "Response:\n"
        ),
        filler_template=(
            "Scene note:\n"
            "Turn {turn}. {event}\n"
            "Response:\n"
        ),
    ),
    "narrative_brief": PromptProfile(
        key="narrative_brief",
        inject_template=(
            "Narrator:\n"
            "During a quiet moment, {subject} entrusts you with a private codeword: {token}.\n"
            "You must preserve it exactly.\n\n"
            "Continuation:\n"
        ),
        probe_template=(
            "Narrator:\n"
            "After {lag} intervening turns, you revisit the private detail tied to {subject}.\n"
            "State only the exact codeword.\n\n"
            "Continuation:\n"
        ),
        filler_template=(
            "Narrator:\n"
            "Turn {turn}. {event}\n\n"
            "Continuation:\n"
        ),
    ),
}


def render_inject_prompt(profile: PromptProfile, fact: FactMemory) -> str:
    return profile.inject_template.format(
        turn=fact.turn_injected,
        subject=fact.subject,
        token=fact.token,
    )


def render_probe_prompt(profile: PromptProfile, fact: FactMemory, lag: int) -> str:
    return profile.probe_template.format(
        turn=fact.turn_injected + lag,
        lag=lag,
        subject=fact.subject,
        token=fact.token,
    )


def render_filler_prompt(profile: PromptProfile, turn: int) -> str:
    event = FILLER_EVENTS[(turn - 1) % len(FILLER_EVENTS)]
    return profile.filler_template.format(turn=turn, event=event)


def collect_probe_dataset_for_profile(
    model,
    tokenizer,
    device: torch.device,
    profile: PromptProfile,
    turns: int,
    inject_every: int,
    probe_lags: List[int],
    max_history_tokens: int,
    num_memory_classes: int,
    label_target: str,
) -> Tuple[List[torch.Tensor], List[int], List[int], List[dict]]:
    facts: List[FactMemory] = []
    due_by_turn: Dict[int, List[ProbeTask]] = defaultdict(list)
    pending_probes: Deque[ProbeTask] = deque()
    history_ids: Optional[torch.Tensor] = None
    last_state_tensor: Optional[torch.Tensor] = None

    features: List[torch.Tensor] = []
    labels: List[int] = []
    group_ids: List[int] = []
    rows: List[dict] = []

    for turn in range(1, turns + 1):
        for probe in due_by_turn.get(turn, []):
            pending_probes.append(probe)

        if turn % inject_every == 0:
            fact = make_fact(len(facts), turn, num_memory_classes=num_memory_classes)
            facts.append(fact)
            for probe_lag in probe_lags:
                due_turn = turn + probe_lag
                if due_turn <= turns:
                    due_by_turn[due_turn].append(
                        ProbeTask(
                            due_turn=due_turn,
                            fact_id=fact.fact_id,
                            lag=probe_lag,
                            inject_turn=fact.turn_injected,
                        )
                    )
            prompt = render_inject_prompt(profile, fact)
        elif pending_probes:
            task = pending_probes.popleft()
            fact = facts[task.fact_id]
            prompt = render_probe_prompt(profile, fact, task.lag)

            if last_state_tensor is None:
                raise RuntimeError("Probe sample requested before any prior model state was available.")
            features.append(state_to_feature(last_state_tensor))
            if label_target == "fact_id":
                label = fact.fact_id
            elif label_target == "subject":
                raise ValueError("subject labels are not supported in format_transplant_probe")
            else:
                label = fact.memory_class
            labels.append(label)
            group_ids.append(fact.fact_id)
            rows.append(
                {
                    "turn": turn,
                    "format": profile.key,
                    "fact_id": int(fact.fact_id),
                    "group_id": int(fact.fact_id),
                    "memory_class": int(fact.memory_class),
                    "subject": fact.subject,
                    "lag": int(task.lag),
                    "inject_turn": int(fact.turn_injected),
                    "expected_token": fact.token,
                }
            )
        else:
            prompt = render_filler_prompt(profile, turn)

        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
        history_ids = input_ids if history_ids is None else torch.cat([history_ids, input_ids], dim=1)
        if history_ids.shape[1] > max_history_tokens:
            history_ids = history_ids[:, -max_history_tokens:]

        with torch.inference_mode():
            outputs = model(history_ids, use_cache=True)
            last_state_tensor = extract_ssm_state(outputs)

    return features, labels, group_ids, rows


def _layer_tensor(features: List[torch.Tensor], layer_idx: int) -> torch.Tensor:
    if len(features) < 4:
        raise RuntimeError(f"Need at least 4 probe samples, got {len(features)}")
    stacked = torch.stack(features, dim=0)
    if layer_idx < 0 or layer_idx >= stacked.shape[1]:
        raise ValueError(f"layer_idx {layer_idx} out of range for {stacked.shape[1]} layers")
    return stacked[:, layer_idx, :]


def _group_train_test_split(
    labels: List[int],
    group_ids: List[int],
    train_fraction: float,
    seed: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    if len(labels) != len(group_ids):
        raise RuntimeError("group_ids length must match labels length")
    if len(labels) < 4:
        raise RuntimeError("Need at least 4 samples for grouped split")

    y = torch.tensor(labels, dtype=torch.long)
    group_to_indices: Dict[int, List[int]] = defaultdict(list)
    for idx, gid in enumerate(group_ids):
        group_to_indices[int(gid)].append(idx)

    unique_groups = sorted(group_to_indices.keys())
    if len(unique_groups) < 2:
        raise RuntimeError("Need at least 2 groups for grouped split")

    generator = torch.Generator()
    generator.manual_seed(seed)
    perm = torch.randperm(len(unique_groups), generator=generator).tolist()
    groups = [unique_groups[i] for i in perm]

    split = max(1, min(len(groups) - 1, int(len(groups) * train_fraction)))
    train_groups = groups[:split]
    test_groups = groups[split:]

    def materialize(groups_subset: Iterable[int]) -> torch.Tensor:
        idx: List[int] = []
        for gid in groups_subset:
            idx.extend(group_to_indices[int(gid)])
        return torch.tensor(sorted(idx), dtype=torch.long)

    train_idx = materialize(train_groups)
    test_idx = materialize(test_groups)
    if train_idx.numel() == 0 or test_idx.numel() == 0:
        raise RuntimeError("Grouped split produced empty train or test set")

    train_classes = set(y[train_idx].tolist())
    test_classes = set(y[test_idx].tolist())
    missing_in_train = sorted(test_classes - train_classes)
    if missing_in_train:
        train_group_set = set(int(g) for g in train_groups)
        test_group_set = [int(g) for g in test_groups]
        for cls in missing_in_train:
            move_group: Optional[int] = None
            for gid in test_group_set:
                if any(int(y[idx]) == int(cls) for idx in group_to_indices[gid]):
                    move_group = gid
                    break
            if move_group is not None:
                test_group_set.remove(move_group)
                train_group_set.add(move_group)

        if not test_group_set:
            if len(train_group_set) <= 1:
                raise RuntimeError("Could not keep non-empty grouped test set after class coverage adjustment")
            moved_back = sorted(train_group_set)[-1]
            train_group_set.remove(moved_back)
            test_group_set.append(moved_back)

        train_idx = materialize(sorted(train_group_set))
        test_idx = materialize(sorted(test_group_set))

    return train_idx, test_idx, y[train_idx], y[test_idx]


def _fit_linear_probe(
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_test: torch.Tensor,
    y_test: torch.Tensor,
    epochs: int,
    lr: float,
    weight_decay: float,
    seed: int,
) -> dict:
    torch.manual_seed(seed)
    model = nn.Linear(X_train.shape[1], int(y_train.max().item()) + 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train_n = (X_train - mean) / std
    X_test_n = (X_test - mean) / std

    for _ in range(epochs):
        logits = model(X_train_n)
        loss = F.cross_entropy(logits, y_train)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        train_pred = model(X_train_n).argmax(dim=-1)
        test_pred = model(X_test_n).argmax(dim=-1)

    return {
        "train_acc": float((train_pred == y_train).float().mean().item()),
        "test_acc": float((test_pred == y_test).float().mean().item()),
        "num_train": int(X_train.shape[0]),
        "num_test": int(X_test.shape[0]),
    }


def evaluate_within_format(
    features: List[torch.Tensor],
    labels: List[int],
    group_ids: List[int],
    layer_idx: int,
    train_fraction: float,
    epochs: int,
    lr: float,
    weight_decay: float,
    base_seed: int,
    seeds: int,
) -> dict:
    X = _layer_tensor(features, layer_idx)
    runs: List[float] = []
    details: List[dict] = []
    for seed in range(base_seed, base_seed + seeds):
        train_idx, test_idx, _, _ = _group_train_test_split(labels, group_ids, train_fraction, seed)
        result = _fit_linear_probe(
            X_train=X[train_idx],
            y_train=torch.tensor(labels, dtype=torch.long)[train_idx],
            X_test=X[test_idx],
            y_test=torch.tensor(labels, dtype=torch.long)[test_idx],
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            seed=seed,
        )
        result["seed"] = seed
        details.append(result)
        runs.append(float(result["test_acc"]))
    stats = torch.tensor(runs, dtype=torch.float32)
    return {
        "mean_test_acc": float(stats.mean().item()),
        "std_test_acc": float(stats.std(unbiased=False).item()) if len(runs) > 1 else 0.0,
        "min_test_acc": float(stats.min().item()),
        "max_test_acc": float(stats.max().item()),
        "runs": details,
    }


def evaluate_cross_format(
    train_features: List[torch.Tensor],
    train_labels: List[int],
    train_group_ids: List[int],
    test_features: List[torch.Tensor],
    test_labels: List[int],
    test_group_ids: List[int],
    layer_idx: int,
    train_fraction: float,
    epochs: int,
    lr: float,
    weight_decay: float,
    base_seed: int,
    seeds: int,
) -> dict:
    X_train_all = _layer_tensor(train_features, layer_idx)
    X_test_all = _layer_tensor(test_features, layer_idx)
    y_train_all = torch.tensor(train_labels, dtype=torch.long)
    y_test_all = torch.tensor(test_labels, dtype=torch.long)

    runs: List[float] = []
    details: List[dict] = []
    for seed in range(base_seed, base_seed + seeds):
        train_idx, _, _, _ = _group_train_test_split(train_labels, train_group_ids, train_fraction, seed)
        _, test_idx, _, _ = _group_train_test_split(test_labels, test_group_ids, train_fraction, seed)
        result = _fit_linear_probe(
            X_train=X_train_all[train_idx],
            y_train=y_train_all[train_idx],
            X_test=X_test_all[test_idx],
            y_test=y_test_all[test_idx],
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            seed=seed,
        )
        result["seed"] = seed
        details.append(result)
        runs.append(float(result["test_acc"]))
    stats = torch.tensor(runs, dtype=torch.float32)
    return {
        "mean_test_acc": float(stats.mean().item()),
        "std_test_acc": float(stats.std(unbiased=False).item()) if len(runs) > 1 else 0.0,
        "runs": details,
    }


def evaluate_pooled_mixed(
    datasets: Dict[str, Tuple[List[torch.Tensor], List[int], List[int], List[dict]]],
    layer_idx: int,
    train_fraction: float,
    epochs: int,
    lr: float,
    weight_decay: float,
    base_seed: int,
    seeds: int,
) -> dict:
    merged_features: List[torch.Tensor] = []
    merged_labels: List[int] = []
    merged_group_ids: List[int] = []
    merged_formats: List[str] = []

    format_tensors: Dict[str, torch.Tensor] = {}
    format_labels: Dict[str, torch.Tensor] = {}
    format_group_ids: Dict[str, List[int]] = {}

    for format_key, (features, labels, group_ids, _) in datasets.items():
        X = _layer_tensor(features, layer_idx)
        format_tensors[format_key] = X
        format_labels[format_key] = torch.tensor(labels, dtype=torch.long)
        format_group_ids[format_key] = group_ids
        for i, feat in enumerate(features):
            merged_features.append(feat)
            merged_labels.append(labels[i])
            merged_group_ids.append(group_ids[i] * 100 + list(datasets.keys()).index(format_key))
            merged_formats.append(format_key)

    X_merged = _layer_tensor(merged_features, layer_idx)
    y_merged = torch.tensor(merged_labels, dtype=torch.long)

    runs: List[dict] = []
    pooled_accs: List[float] = []
    per_format_accs: Dict[str, List[float]] = {key: [] for key in datasets.keys()}

    merged_indices_by_format: Dict[str, List[int]] = defaultdict(list)
    for idx, format_key in enumerate(merged_formats):
        merged_indices_by_format[format_key].append(idx)

    for seed in range(base_seed, base_seed + seeds):
        train_idx, test_idx, _, _ = _group_train_test_split(merged_labels, merged_group_ids, train_fraction, seed)

        train_result = _fit_linear_probe(
            X_train=X_merged[train_idx],
            y_train=y_merged[train_idx],
            X_test=X_merged[test_idx],
            y_test=y_merged[test_idx],
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            seed=seed,
        )

        mean = X_merged[train_idx].mean(dim=0, keepdim=True)
        std = X_merged[train_idx].std(dim=0, keepdim=True).clamp_min(1e-6)
        torch.manual_seed(seed)
        model = nn.Linear(X_merged.shape[1], int(y_merged.max().item()) + 1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        X_train_n = (X_merged[train_idx] - mean) / std
        for _ in range(epochs):
            logits = model(X_train_n)
            loss = F.cross_entropy(logits, y_merged[train_idx])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

        run_detail = {"seed": seed, "pooled": train_result, "per_format": {}}
        pooled_accs.append(float(train_result["test_acc"]))

        with torch.no_grad():
            for format_key, format_indices in merged_indices_by_format.items():
                format_test_indices = [idx for idx in format_indices if idx in test_idx.tolist()]
                if not format_test_indices:
                    continue
                idx_tensor = torch.tensor(format_test_indices, dtype=torch.long)
                X_fmt = (X_merged[idx_tensor] - mean) / std
                y_fmt = y_merged[idx_tensor]
                pred = model(X_fmt).argmax(dim=-1)
                acc = float((pred == y_fmt).float().mean().item())
                run_detail["per_format"][format_key] = {
                    "test_acc": acc,
                    "num_test": int(y_fmt.numel()),
                }
                per_format_accs[format_key].append(acc)

        runs.append(run_detail)

    result = {
        "pooled_mean_test_acc": float(torch.tensor(pooled_accs, dtype=torch.float32).mean().item()),
        "pooled_std_test_acc": float(torch.tensor(pooled_accs, dtype=torch.float32).std(unbiased=False).item()) if len(pooled_accs) > 1 else 0.0,
        "per_format_mean_test_acc": {},
        "runs": runs,
    }
    for format_key, values in per_format_accs.items():
        if values:
            stats = torch.tensor(values, dtype=torch.float32)
            result["per_format_mean_test_acc"][format_key] = {
                "mean_test_acc": float(stats.mean().item()),
                "std_test_acc": float(stats.std(unbiased=False).item()) if len(values) > 1 else 0.0,
            }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Format-transplant control for the Mamba Layer 3 probe.")
    parser.add_argument("--mamba-model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    parser.add_argument("--device", type=str, default="auto", choices=("auto", "cuda", "cpu"))
    parser.add_argument("--turns", type=int, default=120)
    parser.add_argument("--inject-every", type=int, default=5)
    parser.add_argument("--probe-lags", type=str, default="3,12,24")
    parser.add_argument("--num-memory-classes", type=int, default=4)
    parser.add_argument("--label-target", type=str, default="memory_class", choices=("memory_class", "fact_id"))
    parser.add_argument("--max-history-tokens", type=int, default=MAX_MAMBA_HISTORY_TOKENS)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--layer-idx", type=int, default=3)
    parser.add_argument("--formats", type=str, default="game_world,ledger_note,dialogue_scene,narrative_brief")
    parser.add_argument("--output-dir", type=str, default="format_transplant_probe_runs")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    probe_lags = parse_lags(args.probe_lags)
    requested_formats = [raw.strip() for raw in args.formats.split(",") if raw.strip()]
    if len(requested_formats) < 2:
        raise ValueError("Need at least two formats for transplant control.")
    unknown_formats = [name for name in requested_formats if name not in PROMPT_PROFILES]
    if unknown_formats:
        raise ValueError(f"Unknown formats: {unknown_formats}")

    schedule_audit = audit_schedule(turns=args.turns, inject_every=args.inject_every, probe_lags=probe_lags)
    schedule_reco = recommend_inject_every(turns=args.turns, probe_lags=probe_lags)
    schedule_audit["recommended_inject_every"] = schedule_reco["recommended_inject_every"]
    if int(schedule_audit["drift_count"]) > 0:
        raise ValueError(
            "Schedule audit detected lag drift; use a zero-drift inject_every "
            f"(recommended: {schedule_audit['recommended_inject_every']})."
        )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    seed_everything(args.seed)

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    dtype = torch.float16 if str(device) == "cuda" else torch.float32
    LOGGER.info("Loading Mamba model=%s on device=%s dtype=%s", args.mamba_model_id, device, dtype)
    tokenizer = AutoTokenizer.from_pretrained(args.mamba_model_id)
    model = AutoModelForCausalLM.from_pretrained(args.mamba_model_id, torch_dtype=dtype)
    if str(device) != "cpu":
        model = model.to(device)
    model.eval()
    for p in model.parameters():
        p.requires_grad = False

    datasets: Dict[str, Tuple[List[torch.Tensor], List[int], List[int], List[dict]]] = {}
    for format_key in requested_formats:
        profile = PROMPT_PROFILES[format_key]
        LOGGER.info("Collecting dataset for format=%s", format_key)
        datasets[format_key] = collect_probe_dataset_for_profile(
            model=model,
            tokenizer=tokenizer,
            device=device,
            profile=profile,
            turns=args.turns,
            inject_every=args.inject_every,
            probe_lags=probe_lags,
            max_history_tokens=args.max_history_tokens,
            num_memory_classes=args.num_memory_classes,
            label_target=args.label_target,
        )

    within_format: Dict[str, dict] = {}
    for format_key, (features, labels, group_ids, _) in datasets.items():
        within_format[format_key] = evaluate_within_format(
            features=features,
            labels=labels,
            group_ids=group_ids,
            layer_idx=args.layer_idx,
            train_fraction=args.train_fraction,
            epochs=args.epochs,
            lr=args.lr,
            weight_decay=args.weight_decay,
            base_seed=args.seed,
            seeds=args.seeds,
        )

    transplant_matrix: Dict[str, Dict[str, dict]] = {}
    for train_format, (train_features, train_labels, train_group_ids, _) in datasets.items():
        transplant_matrix[train_format] = {}
        for test_format, (test_features, test_labels, test_group_ids, _) in datasets.items():
            transplant_matrix[train_format][test_format] = evaluate_cross_format(
                train_features=train_features,
                train_labels=train_labels,
                train_group_ids=train_group_ids,
                test_features=test_features,
                test_labels=test_labels,
                test_group_ids=test_group_ids,
                layer_idx=args.layer_idx,
                train_fraction=args.train_fraction,
                epochs=args.epochs,
                lr=args.lr,
                weight_decay=args.weight_decay,
                base_seed=args.seed,
                seeds=args.seeds,
            )

    pooled = evaluate_pooled_mixed(
        datasets=datasets,
        layer_idx=args.layer_idx,
        train_fraction=args.train_fraction,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        base_seed=args.seed,
        seeds=args.seeds,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = Path(__file__).resolve().parent / output_root
    run_dir = output_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for format_key, (_, _, _, rows) in datasets.items():
        rows_path = run_dir / f"{format_key}_probe_rows.jsonl"
        with open(rows_path, "w", encoding="utf-8") as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "timestamp_utc": timestamp,
        "mamba_model_id": args.mamba_model_id,
        "device": str(device),
        "dtype": str(dtype),
        "config": vars(args),
        "schedule_audit": schedule_audit,
        "formats": {
            key: {
                "inject_template": PROMPT_PROFILES[key].inject_template,
                "probe_template": PROMPT_PROFILES[key].probe_template,
                "filler_template": PROMPT_PROFILES[key].filler_template,
                "samples": len(datasets[key][0]),
            }
            for key in requested_formats
        },
        "within_format": within_format,
        "format_transplant": transplant_matrix,
        "pooled_mixed": pooled,
    }

    report_path = run_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)

    LOGGER.info("Report written: %s", report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
