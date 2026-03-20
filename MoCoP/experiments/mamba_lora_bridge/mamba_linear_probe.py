"""
mamba_linear_probe.py - Diagnose whether Mamba state contains decodable memory.

This script bypasses Qwen/LoRA generation and only evaluates memory signal in
Mamba state by training a tiny linear probe:

    pooled_mamba_state -> fact_id

If probe accuracy is above baseline, memory information exists in state and the
main bottleneck is likely downstream translation (compressor/hyper/LoRA).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from model_defaults import DEFAULT_MAMBA_MODEL_ID

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

try:
    from transformers.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
except Exception:
    pass

from transformers import AutoModelForCausalLM, AutoTokenizer

LOGGER = logging.getLogger("MambaLinearProbe")

MAX_MAMBA_HISTORY_TOKENS = 8192

SUBJECTS = [
    "Thornwick",
    "Jinx",
    "Mira",
    "Sable",
    "Kestrel",
    "Rook",
    "Lumen",
    "Iris",
    "Voss",
    "Nyra",
]
FILLER_EVENTS = [
    "The market square is crowded; a merchant argues over grain prices.",
    "A light rain starts and the cobblestones shine under lantern light.",
    "An apprentice drops a crate of herbs near the fountain.",
    "Two guards discuss a caravan expected before dawn.",
    "A bard tunes a lute while travelers warm themselves by the hearth.",
    "A black cat darts across the alley and disappears behind the inn.",
]
MEMORY_CODES = [
    "amber-wolf",
    "azure-lynx",
    "crimson-owl",
    "ivory-falcon",
    "obsidian-raven",
    "jade-viper",
    "sable-otter",
    "cobalt-stag",
]


@dataclass
class FactMemory:
    fact_id: int
    turn_injected: int
    subject: str
    memory_class: int
    token: str


@dataclass
class ProbeTask:
    due_turn: int
    fact_id: int
    lag: int
    inject_turn: int


def parse_lags(text: str) -> List[int]:
    values: List[int] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        lag = int(raw)
        if lag <= 0:
            raise ValueError(f"Probe lag must be > 0, got {lag}")
        values.append(lag)
    if not values:
        raise ValueError("No valid probe lags provided.")
    return sorted(set(values))


def make_fact(index: int, turn: int, num_memory_classes: int) -> FactMemory:
    subject = SUBJECTS[index % len(SUBJECTS)]
    memory_class = index % num_memory_classes
    token = MEMORY_CODES[memory_class]
    return FactMemory(
        fact_id=index,
        turn_injected=turn,
        subject=subject,
        memory_class=memory_class,
        token=token,
    )


def build_inject_prompt(fact: FactMemory) -> str:
    return (
        f"[Game World]\n"
        f"In the tavern, {fact.subject} speaks privately to you.\n"
        f"Secret memory event: {fact.subject}'s codeword is '{fact.token}'.\n"
        f"Remember this exactly for later.\n\n"
        f"[Action]\n"
    )


def build_probe_prompt(fact: FactMemory, lag: int) -> str:
    return (
        f"[Game World]\n"
        f"Recall check after {lag} turns.\n"
        f"Earlier, {fact.subject} gave you a private codeword.\n"
        f"Reply with only the exact codeword for {fact.subject}.\n\n"
        f"[Action]\n"
    )


def build_filler_prompt(turn: int) -> str:
    event = FILLER_EVENTS[(turn - 1) % len(FILLER_EVENTS)]
    return (
        f"[Game World]\n"
        f"Turn {turn}. {event}\n\n"
        f"[Action]\n"
    )


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def extract_ssm_state(outputs) -> torch.Tensor:
    cache = getattr(outputs, "cache_params", None)
    if cache is None:
        cache = getattr(outputs, "past_key_values", None)
    if cache is None or not hasattr(cache, "ssm_states"):
        attrs = [attr for attr in dir(outputs) if not attr.startswith("_")]
        raise RuntimeError(
            "Mamba output did not expose cache with ssm_states. "
            f"Available attrs: {attrs}"
        )
    ssm_states = cache.ssm_states
    return torch.stack(ssm_states, dim=1)


def state_to_feature(state_tensor: torch.Tensor) -> torch.Tensor:
    # state_tensor shape: (batch, layers, ...) -> we want (layers, features)
    state_tensor = state_tensor.squeeze(0)
    flat = state_tensor.reshape(state_tensor.shape[0], -1)
    return flat.detach().to("cpu", dtype=torch.float32)


def audit_schedule(turns: int, inject_every: int, probe_lags: List[int]) -> dict:
    facts: List[FactMemory] = []
    due_by_turn: Dict[int, List[ProbeTask]] = defaultdict(list)
    pending_probes: Deque[ProbeTask] = deque()
    drift_rows: List[dict] = []

    for turn in range(1, turns + 1):
        for probe in due_by_turn.get(turn, []):
            pending_probes.append(probe)

        if turn % inject_every == 0:
            fact = make_fact(len(facts), turn, num_memory_classes=4)
            facts.append(fact)
            for probe_lag in probe_lags:
                due_turn = turn + probe_lag
                if due_turn <= turns:
                    due_by_turn[due_turn].append(
                        ProbeTask(
                            due_turn=due_turn,
                            fact_id=fact.fact_id,
                            lag=probe_lag,
                            inject_turn=turn,
                        )
                    )
        elif pending_probes:
            task = pending_probes.popleft()
            actual_lag = turn - task.inject_turn
            lag_delta = actual_lag - task.lag
            drift_rows.append(
                {
                    "turn": turn,
                    "fact_id": task.fact_id,
                    "inject_turn": task.inject_turn,
                    "scheduled_lag": task.lag,
                    "actual_lag": actual_lag,
                    "lag_delta": lag_delta,
                }
            )

    drift_count = sum(1 for row in drift_rows if row["lag_delta"] != 0)
    probe_rows = len(drift_rows)
    by_lag: Dict[int, Dict[str, float]] = {}
    for lag in sorted(set(int(row["scheduled_lag"]) for row in drift_rows)):
        lag_rows = [row for row in drift_rows if int(row["scheduled_lag"]) == lag]
        drifted = sum(1 for row in lag_rows if int(row["lag_delta"]) != 0)
        by_lag[lag] = {
            "total": int(len(lag_rows)),
            "drifted": int(drifted),
            "drift_rate": float(drifted / len(lag_rows)) if lag_rows else 0.0,
            "max_abs_drift": int(max(abs(int(row["lag_delta"])) for row in lag_rows)) if lag_rows else 0,
        }

    return {
        "probes_total": int(probe_rows),
        "drift_count": int(drift_count),
        "drift_rate": float(drift_count / probe_rows) if probe_rows else 0.0,
        "max_drift": int(max(abs(int(row["lag_delta"])) for row in drift_rows)) if drift_rows else 0,
        "drift_by_scheduled_lag": {str(k): v for k, v in by_lag.items()},
    }


def recommend_inject_every(
    turns: int,
    probe_lags: List[int],
    search_min: int = 2,
    search_max: int = 20,
) -> dict:
    candidates: List[dict] = []
    for inject_every in range(search_min, search_max + 1):
        stats = audit_schedule(turns=turns, inject_every=inject_every, probe_lags=probe_lags)
        if int(stats["drift_count"]) == 0:
            candidates.append(
                {
                    "inject_every": inject_every,
                    "probes_total": int(stats["probes_total"]),
                }
            )

    candidates_sorted = sorted(
        candidates,
        key=lambda row: (-int(row["probes_total"]), int(row["inject_every"])),
    )
    recommended = int(candidates_sorted[0]["inject_every"]) if candidates_sorted else None
    return {
        "recommended_inject_every": recommended,
        "zero_drift_candidates": candidates_sorted,
    }


def collect_probe_dataset(
    model,
    tokenizer,
    device: torch.device,
    turns: int,
    inject_every: int,
    probe_lags: List[int],
    max_history_tokens: int,
    num_memory_classes: int,
    label_target: str,
    no_injection: bool = False,
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

        event_type = "filler"
        fact_id: Optional[int] = None
        lag: Optional[int] = None
        expected_token: Optional[str] = None
        subject: Optional[str] = None
        task: Optional[ProbeTask] = None

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
            if no_injection:
                prompt = build_filler_prompt(turn)
            else:
                prompt = build_inject_prompt(fact)
            event_type = "inject"
            fact_id = fact.fact_id
            subject = fact.subject
        elif pending_probes:
            task = pending_probes.popleft()
            fact = facts[task.fact_id]
            prompt = build_probe_prompt(fact, task.lag)
            event_type = "probe"
            fact_id = fact.fact_id
            lag = task.lag
            expected_token = fact.token
            subject = fact.subject

            if last_state_tensor is None:
                raise RuntimeError("Probe sample requested before any prior model state was available.")
            feature = state_to_feature(last_state_tensor)
            features.append(feature)
            if label_target == "fact_id":
                label = fact_id
            elif label_target == "subject":
                label = SUBJECTS.index(fact.subject)
            else:
                label = fact.memory_class
            labels.append(label)
            group_ids.append(fact_id)

            actual_lag = turn - int(fact.turn_injected)
            lag_delta = actual_lag - int(task.lag)
            rows.append(
                {
                    "turn": turn,
                    "event_type": event_type,
                    "fact_id": fact_id,
                    "group_id": fact_id,
                    "memory_class": fact.memory_class,
                    "subject": subject,
                    "lag": lag,
                    "inject_turn": int(fact.turn_injected),
                    "actual_lag": int(actual_lag),
                    "lag_delta": int(lag_delta),
                    "expected_token": expected_token,
                    "label": label,
                    "state_source": "pre_probe_prompt",
                }
            )
        else:
            prompt = build_filler_prompt(turn)

        input_ids = tokenizer.encode(prompt, return_tensors="pt")
        input_ids = input_ids.to(device)
        history_ids = input_ids if history_ids is None else torch.cat([history_ids, input_ids], dim=1)
        if history_ids.shape[1] > max_history_tokens:
            history_ids = history_ids[:, -max_history_tokens:]

        with torch.inference_mode():
            outputs = model(history_ids, use_cache=True)
            state_tensor = extract_ssm_state(outputs)
        last_state_tensor = state_tensor

    return features, labels, group_ids, rows


def majority_accuracy(y_train: torch.Tensor, y_eval: torch.Tensor) -> float:
    if y_train.numel() == 0 or y_eval.numel() == 0:
        return 0.0
    values, counts = torch.unique(y_train, return_counts=True)
    majority = values[counts.argmax()]
    return float((y_eval == majority).float().mean().item())


def split_indices_sample(y: torch.Tensor, train_fraction: float, seed: int) -> Tuple[torch.Tensor, torch.Tensor]:
    n = y.numel()
    if n < 2:
        raise RuntimeError("Need at least 2 samples to split")

    generator = torch.Generator()
    generator.manual_seed(seed)
    perm = torch.randperm(n, generator=generator)

    split = max(1, min(n - 1, int(n * train_fraction)))
    train_idx = perm[:split].clone()
    test_idx = perm[split:].clone()

    train_classes = set(y[train_idx].tolist())
    test_classes = set(y[test_idx].tolist())
    missing_in_train = sorted(test_classes - train_classes)
    if missing_in_train:
        train_list = train_idx.tolist()
        test_list = test_idx.tolist()
        for cls in missing_in_train:
            pos = None
            for i, idx in enumerate(test_list):
                if int(y[idx]) == cls:
                    pos = i
                    break
            if pos is not None:
                train_list.append(test_list.pop(pos))
        if not test_list:
            test_list.append(train_list.pop())
        train_idx = torch.tensor(train_list, dtype=torch.long)
        test_idx = torch.tensor(test_list, dtype=torch.long)

    return train_idx, test_idx


def split_indices_grouped(
    y: torch.Tensor,
    group_ids: List[int],
    train_fraction: float,
    seed: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    if y.numel() != len(group_ids):
        raise RuntimeError("group_ids length must match sample count")
    if y.numel() < 2:
        raise RuntimeError("Need at least 2 samples to split")

    group_to_indices: Dict[int, List[int]] = defaultdict(list)
    for idx, gid in enumerate(group_ids):
        group_to_indices[int(gid)].append(idx)

    unique_groups = sorted(group_to_indices.keys())
    if len(unique_groups) < 2:
        raise RuntimeError("Need at least 2 groups for grouped split")

    generator = torch.Generator()
    generator.manual_seed(seed)
    perm = torch.randperm(len(unique_groups), generator=generator).tolist()
    groups_shuffled = [unique_groups[i] for i in perm]

    split = max(1, min(len(groups_shuffled) - 1, int(len(groups_shuffled) * train_fraction)))
    train_groups = groups_shuffled[:split]
    test_groups = groups_shuffled[split:]

    def groups_to_idx(groups: List[int]) -> torch.Tensor:
        idx: List[int] = []
        for gid in groups:
            idx.extend(group_to_indices[int(gid)])
        return torch.tensor(sorted(idx), dtype=torch.long)

    train_idx = groups_to_idx(train_groups)
    test_idx = groups_to_idx(test_groups)
    if train_idx.numel() == 0 or test_idx.numel() == 0:
        raise RuntimeError("Grouped split produced empty train/test set")

    train_classes = set(y[train_idx].tolist())
    test_classes = set(y[test_idx].tolist())
    missing_in_train = sorted(test_classes - train_classes)

    if missing_in_train:
        train_group_set = set(int(g) for g in train_groups)
        test_group_set = [int(g) for g in test_groups]
        for cls in missing_in_train:
            move_group: Optional[int] = None
            for gid in test_group_set:
                class_in_group = any(int(y[idx]) == int(cls) for idx in group_to_indices[gid])
                if class_in_group:
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

        train_idx = groups_to_idx(sorted(train_group_set))
        test_idx = groups_to_idx(sorted(test_group_set))

    return train_idx, test_idx


def split_indices(
    y: torch.Tensor,
    train_fraction: float,
    seed: int,
    split_mode: str,
    group_ids: Optional[List[int]] = None,
) -> Tuple[torch.Tensor, torch.Tensor]:
    if split_mode == "sample":
        return split_indices_sample(y=y, train_fraction=train_fraction, seed=seed)
    if split_mode == "group":
        if group_ids is None:
            raise RuntimeError("split_mode='group' requires group_ids")
        return split_indices_grouped(y=y, group_ids=group_ids, train_fraction=train_fraction, seed=seed)
    raise ValueError(f"Unknown split_mode: {split_mode}")


def _prepare_probe_data(
    features: List[torch.Tensor],
    labels: List[int],
    group_ids: List[int],
    train_fraction: float,
    split_mode: str,
    min_test_samples: int,
    seed: int,
    probe_mode: str = "mean",
    layer_idx: int = 0,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, List[int], dict]:
    """Shared data preparation for all probe types."""
    if len(features) < 4:
        raise RuntimeError(f"Need at least 4 probe samples, got {len(features)}")

    # X shape: (samples, layers, features)
    X = torch.stack(features, dim=0)
    
    if probe_mode == "mean":
        X = X.mean(dim=1)
    elif probe_mode == "layer":
        X = X[:, layer_idx, :]
    elif probe_mode == "concat":
        X = X.reshape(X.shape[0], -1)
    else:
        raise ValueError(f"Unknown probe_mode: {probe_mode}")
    unique_ids = sorted(set(labels))
    class_to_idx = {fact_id: idx for idx, fact_id in enumerate(unique_ids)}
    y = torch.tensor([class_to_idx[int(v)] for v in labels], dtype=torch.long)

    train_idx, test_idx = split_indices(
        y=y,
        train_fraction=train_fraction,
        seed=seed,
        split_mode=split_mode,
        group_ids=group_ids,
    )
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    if X_test.shape[0] < min_test_samples:
        raise RuntimeError(
            f"Test split too small: n_test={int(X_test.shape[0])} < --min-test-samples={min_test_samples}. "
            "Increase --turns, lower --train-fraction, or reduce --min-test-samples."
        )

    # Normalize using train stats
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train_n = (X_train - mean) / std
    X_test_n = (X_test - mean) / std

    meta = {
        "samples_total": int(X.shape[0]),
        "samples_train": int(X_train.shape[0]),
        "samples_test": int(X_test.shape[0]),
        "split_mode": split_mode,
        "num_classes": int(len(unique_ids)),
        "class_ids": unique_ids,
        "train_class_hist": {str(int(k)): int(v) for k, v in zip(*torch.unique(y_train, return_counts=True))},
        "test_class_hist": {str(int(k)): int(v) for k, v in zip(*torch.unique(y_test, return_counts=True))},
    }
    return X_train_n, X_test_n, y_train, y_test, unique_ids, meta


def _train_and_eval(
    model: nn.Module,
    X_train: torch.Tensor,
    X_test: torch.Tensor,
    y_train: torch.Tensor,
    y_test: torch.Tensor,
    epochs: int,
    lr: float,
    weight_decay: float,
    num_classes: int,
) -> Tuple[float, float, float, list, list]:
    """Train a probe model and return (train_acc, test_acc, majority_acc, test_preds, test_gts)."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    for _ in range(epochs):
        logits = model(X_train)
        loss = F.cross_entropy(logits, y_train)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        train_pred = model(X_train).argmax(dim=-1)
        test_pred = model(X_test).argmax(dim=-1)

    train_acc = float((train_pred == y_train).float().mean().item())
    test_acc = float((test_pred == y_test).float().mean().item())
    majority_test = majority_accuracy(y_train, y_test)
    
    return train_acc, test_acc, majority_test, test_pred.tolist(), y_test.tolist()


def train_probes(
    features: List[torch.Tensor],
    labels: List[int],
    group_ids: List[int],
    train_fraction: float,
    split_mode: str,
    min_test_samples: int,
    epochs: int,
    lr: float,
    weight_decay: float,
    seed: int,
    probe_mode: str = "mean",
    layer_idx: int = 0,
) -> dict:
    """Train both linear and MLP probes on the same split. Returns combined results."""
    X_train, X_test, y_train, y_test, unique_ids, meta = _prepare_probe_data(
        features, labels, group_ids, train_fraction, split_mode,
        min_test_samples, seed, probe_mode, layer_idx
    )
    n_features = X_train.shape[1]
    n_classes = len(unique_ids)

    # --- Linear probe ---
    linear_model = nn.Linear(n_features, n_classes)
    lin_train, lin_test, majority, test_preds, test_gts = _train_and_eval(
        linear_model, X_train, X_test, y_train, y_test,
        epochs, lr, weight_decay, n_classes
    )


    # --- MLP probe (2-layer, 256 hidden, matches hypernetwork complexity) ---
    mlp_hidden = min(256, n_features // 4)  # scale down for small feature dims
    mlp_model = nn.Sequential(
        nn.Linear(n_features, mlp_hidden),
        nn.ReLU(),
        nn.Dropout(0.1),
        nn.Linear(mlp_hidden, mlp_hidden),
        nn.ReLU(),
        nn.Dropout(0.1),
        nn.Linear(mlp_hidden, n_classes),
    )
    mlp_train, mlp_test, _, _, _ = _train_and_eval(
        mlp_model, X_train, X_test, y_train, y_test,
        epochs, lr * 0.5, weight_decay, n_classes
    )
    
    # Calculate confusion matrix for linear model
    cm = [[0]*n_classes for _ in range(n_classes)]
    class_acc = [0.0]*n_classes
    class_totals = [0]*n_classes
    for p, g in zip(test_preds, test_gts):
        cm[g][p] += 1
        class_totals[g] += 1
        if p == g:
            class_acc[g] += 1
    for i in range(n_classes):
        if class_totals[i] > 0:
            class_acc[i] /= class_totals[i]

    result = dict(meta)
    result.update({
        "majority_test_acc": majority,
        "linear_train_acc": lin_train,
        "linear_test_acc": lin_test,
        "mlp_train_acc": mlp_train,
        "mlp_test_acc": mlp_test,
        "confusion_matrix": cm,
        "per_class_accuracy": class_acc,
        "train_acc": lin_train,
        "test_acc": lin_test,
    })
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Linear probe on raw Mamba state memory signal.")
    parser.add_argument("--mamba-model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    parser.add_argument("--device", type=str, default="auto", choices=("auto", "cuda", "cpu"))
    parser.add_argument("--turns", type=int, default=120)
    parser.add_argument("--inject-every", type=int, default=6)
    parser.add_argument("--probe-lags", type=str, default="3,12,24")
    parser.add_argument("--label-target", type=str, choices=("fact_id", "memory_class", "subject"), default="memory_class")
    parser.add_argument("--num-memory-classes", type=int, default=4)
    parser.add_argument("--max-history-tokens", type=int, default=MAX_MAMBA_HISTORY_TOKENS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-injection",
        action="store_true",
        help="If set, skip injecting and put filler instead (for control baseline).",
    )
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--split-mode", type=str, choices=("group", "sample"), default="group")
    parser.add_argument("--min-test-samples", type=int, default=20)
    parser.add_argument("--allow-lag-drift", action="store_true", help="Allow known schedule lag drift.")
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--output-dir", type=str, default="mamba_probe_runs")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.turns <= 0:
        raise ValueError("--turns must be > 0")
    if args.inject_every <= 0:
        raise ValueError("--inject-every must be > 0")
    if not 0.1 <= args.train_fraction < 0.95:
        raise ValueError("--train-fraction must be in [0.1, 0.95)")
    if args.min_test_samples <= 0:
        raise ValueError("--min-test-samples must be > 0")
    if args.num_memory_classes <= 1 or args.num_memory_classes > len(MEMORY_CODES):
        raise ValueError(f"--num-memory-classes must be in [2, {len(MEMORY_CODES)}]")

    probe_lags = parse_lags(args.probe_lags)
    schedule_audit = audit_schedule(turns=args.turns, inject_every=args.inject_every, probe_lags=probe_lags)
    schedule_reco = recommend_inject_every(turns=args.turns, probe_lags=probe_lags)
    schedule_audit["recommended_inject_every"] = schedule_reco["recommended_inject_every"]
    schedule_audit["zero_drift_candidates"] = schedule_reco["zero_drift_candidates"]
    if int(schedule_audit["drift_count"]) > 0 and not args.allow_lag_drift:
        raise ValueError(
            "Schedule audit detected lag drift "
            f"(drift_count={schedule_audit['drift_count']}, drift_rate={schedule_audit['drift_rate']:.3f}, "
            f"max_drift={schedule_audit['max_drift']}). "
            "Use a zero-drift inject-every value (recommended: "
            f"{schedule_audit['recommended_inject_every']}) or pass --allow-lag-drift."
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

    LOGGER.info(
        "Collecting probe dataset: turns=%d inject_every=%d lags=%s",
        args.turns,
        args.inject_every,
        probe_lags,
    )
    t0 = datetime.now(timezone.utc)
    features, labels, group_ids, rows = collect_probe_dataset(
        model=model,
        tokenizer=tokenizer,
        device=device,
        turns=args.turns,
        inject_every=args.inject_every,
        probe_lags=probe_lags,
        max_history_tokens=args.max_history_tokens,
        num_memory_classes=args.num_memory_classes,
        label_target=args.label_target,
        no_injection=args.no_injection,
    )
    elapsed_collect_s = (datetime.now(timezone.utc) - t0).total_seconds()
    LOGGER.info("Collected %d probe samples in %.1fs", len(features), elapsed_collect_s)

    # Helper to run a split with full args
    def run_probe_eval(seed, mode="mean", layer_idx=0):
        return train_probes(
            features=features,
            labels=labels,
            group_ids=group_ids,
            train_fraction=args.train_fraction,
            split_mode=args.split_mode,
            min_test_samples=args.min_test_samples,
            epochs=args.epochs,
            lr=args.lr,
            weight_decay=args.weight_decay,
            seed=seed,
            probe_mode=mode,
            layer_idx=layer_idx
        )

    # 1. Multi-seed Evaluation (5 grouped splits)
    LOGGER.info("Running robust 5-seed evaluation...")
    multi_seed_results = []
    for s in range(args.seed, args.seed + 5):
        try:
            res = run_probe_eval(s, mode="mean")
            multi_seed_results.append(res)
        except RuntimeError as e:
            LOGGER.warning(f"Seed {s} failed due to split sizing: {e}")

    if not multi_seed_results:
        LOGGER.error("All seeds failed to split.")
        return 1

    lin_accs = [r["linear_test_acc"] for r in multi_seed_results]
    mlp_accs = [r["mlp_test_acc"] for r in multi_seed_results]
    maj_accs = [r["majority_test_acc"] for r in multi_seed_results]

    lin_mean, lin_std = float(torch.tensor(lin_accs).mean()), float(torch.tensor(lin_accs).std())
    mlp_mean, mlp_std = float(torch.tensor(mlp_accs).mean()), float(torch.tensor(mlp_accs).std())
    maj_mean = float(torch.tensor(maj_accs).mean())

    # Calculate 95% CI (1.96 * std / sqrt(N))
    ci_factor = 1.96 / (len(lin_accs)**0.5) if len(lin_accs) > 1 else 0
    lin_ci = lin_std * ci_factor

    # 2. Layer-wise Probing (loop over all 64 layers using seed 0)
    LOGGER.info("Running layer-wise probing over all layers...")
    num_layers = features[0].shape[0]
    layer_accuracies = []
    for l in range(num_layers):
        try:
            l_res = run_probe_eval(args.seed, mode="layer", layer_idx=l)
            layer_accuracies.append((l, l_res["linear_test_acc"]))
        except RuntimeError:
            pass

    # Find the top layers
    layer_accuracies.sort(key=lambda x: x[1], reverse=True)
    best_layers = layer_accuracies[:5]
    
    # Best run data for the top level report output
    result = multi_seed_results[0]  # Just use the first seed for detailed output matrices

    best_test = max(lin_mean, mlp_mean)
    if best_test > maj_mean + 0.05:
        if mlp_mean > lin_mean + 0.05:
            interpretation = (
                f"MLP probe beats baseline by {mlp_mean - maj_mean:.2%} "
                "(signal is nonlinearly decodable)."
            )
        else:
            interpretation = (
                f"Linear probe beats baseline smoothly. Mean: {lin_mean:.1%} ± {lin_ci:.1%}. "
                "Mamba state contains robust linearly decodable memory."
            )
    else:
        interpretation = (
            f"Mean Linear accuracy ({lin_mean:.1%}) fails to significantly beat baseline ({maj_mean:.1%})."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = Path(__file__).resolve().parent / output_root
    run_dir = output_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp_utc": timestamp,
        "mamba_model_id": args.mamba_model_id,
        "device": str(device),
        "dtype": str(dtype),
        "config": vars(args),
        "collection": {
            "probe_lags": probe_lags,
            "rows": len(rows),
            "collect_time_s": elapsed_collect_s,
        },
        "schedule_audit": schedule_audit,
        "robust_stats": {
            "seeds_tested": len(lin_accs),
            "linear_mean": lin_mean,
            "linear_std": lin_std,
            "linear_ci95": lin_ci,
            "mlp_mean": mlp_mean,
            "majority_mean": maj_mean,
        },
        "layer_profile": {
            "best_layers": best_layers,
            "all_layer_accuracies": {l: acc for l, acc in layer_accuracies}
        },
        "probe_result": result, # Includes confusion matrix
        "interpretation": interpretation,
    }

    rows_path = run_dir / "probe_rows.jsonl"
    with open(rows_path, "w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    report_path = run_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)

    LOGGER.info("Report written: %s", report_path)
    LOGGER.info(
        "Linear test_acc=%.3f | MLP test_acc=%.3f | majority=%.3f | classes=%d | n_test=%d",
        result["linear_test_acc"],
        result["mlp_test_acc"],
        result["majority_test_acc"],
        result["num_classes"],
        result["samples_test"],
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
