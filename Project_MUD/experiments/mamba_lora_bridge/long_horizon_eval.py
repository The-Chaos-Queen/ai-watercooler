"""
long_horizon_eval.py - Long-horizon memory evaluation harness.

Purpose:
- Stress-test memory continuity over 50/250/1000+ turns.
- Inject canonical "facts" at controlled intervals.
- Probe delayed recall at configured lags.
- Export per-turn diagnostics, probe accuracy, and optional context vectors.

Run:
    python long_horizon_eval.py --turns 50 --probe-lags 5,25
    python long_horizon_eval.py --turns 250 --probe-lags 5,25,100 --lora-mode both
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import statistics
import sys
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

# Keep remote logs concise.
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

import torch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cognitive_bridge import BridgeConfig, CognitiveBridge


LOGGER = logging.getLogger("LongHorizonEval")

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
COLORS = ["amber", "azure", "crimson", "ivory", "obsidian", "jade", "sable", "cobalt"]
ANIMALS = ["wolf", "falcon", "otter", "lynx", "raven", "viper", "owl", "stag"]
FILLER_EVENTS = [
    "The market square is crowded; a merchant argues over grain prices.",
    "A light rain starts and the cobblestones shine under lantern light.",
    "An apprentice drops a crate of herbs near the fountain.",
    "Two guards discuss a caravan expected before dawn.",
    "A bard tunes a lute while travelers warm themselves by the hearth.",
    "A black cat darts across the alley and disappears behind the inn.",
]
CODEWORD_TOKEN_RE = re.compile(r"[a-z]+-[a-z]+-\d+")


@dataclass
class FactMemory:
    fact_id: int
    turn_injected: int
    subject: str
    token: str


@dataclass
class ProbeTask:
    due_turn: int
    fact_id: int
    lag: int


def parse_lags(text: str) -> List[int]:
    values: List[int] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        lag = int(raw)
        if lag <= 0:
            raise ValueError(f"Probe lag must be > 0, got: {lag}")
        values.append(lag)
    if not values:
        raise ValueError("No valid probe lags provided.")
    return sorted(set(values))


def make_fact(index: int, turn: int) -> FactMemory:
    subject = SUBJECTS[index % len(SUBJECTS)]
    color = COLORS[index % len(COLORS)]
    animal = ANIMALS[(index * 3) % len(ANIMALS)]
    token = f"{color}-{animal}-{100 + index}"
    return FactMemory(
        fact_id=index,
        turn_injected=turn,
        subject=subject,
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


def build_probe_prompt_json(fact: FactMemory, lag: int) -> str:
    return (
        f"[Game World]\n"
        f"Recall check after {lag} turns.\n"
        f"Earlier, {fact.subject} gave you a private codeword.\n"
        f"Return exactly one minified JSON object with keys "
        f"\"subject\" and \"codeword\".\n"
        f"- subject must be \"{fact.subject}\"\n"
        f"- codeword must be the exact codeword only\n"
        f"No markdown, no code fences, no extra text.\n\n"
        f"[Action]\n"
    )


def build_filler_prompt(turn: int) -> str:
    event = FILLER_EVENTS[(turn - 1) % len(FILLER_EVENTS)]
    return (
        f"[Game World]\n"
        f"Turn {turn}. {event}\n\n"
        f"[Action]\n"
    )


def extract_probe_token(output_text: str) -> str:
    """
    Extract the model's best token answer for probe scoring.

    Preference order:
    1) Exact codeword-shaped token found on first line (color-animal-number).
    2) First whitespace token on first line, punctuation-normalized.
    """
    text = (output_text or "").strip().lower()
    if not text:
        return ""

    first_line = text.splitlines()[0].strip().strip("`\"' \t")
    if not first_line:
        return ""

    match = CODEWORD_TOKEN_RE.search(first_line)
    if match:
        return match.group(0)

    first_token = first_line.split()[0] if first_line.split() else ""
    return first_token.strip(".,!?;:()[]{}\"'`")


def extract_probe_token_from_json(output_text: str) -> str:
    """
    Parse the first JSON object in output_text and return its `codeword` value.
    Returns empty string if no valid JSON object/codeword is found.
    """
    text = (output_text or "").strip()
    if not text:
        return ""

    start = text.find("{")
    if start == -1:
        return ""

    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(text[start:])
    except Exception:
        return ""

    if not isinstance(obj, dict):
        return ""
    codeword = obj.get("codeword")
    if not isinstance(codeword, str):
        return ""
    return codeword.strip().lower().strip(".,!?;:()[]{}\"'`")


def maybe_make_plots(
    run_dir: Path,
    rows: List[dict],
    lag_stats: Dict[int, Dict[str, int]],
) -> Optional[List[str]]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None

    generated: List[str] = []
    turns = [r["turn"] for r in rows]
    context_norms = [r["context_norm"] for r in rows]
    gen_times = [r["generation_time_s"] for r in rows]

    fig1 = plt.figure(figsize=(10, 4))
    plt.plot(turns, context_norms, linewidth=1.5)
    plt.title("Context Norm vs Turn")
    plt.xlabel("Turn")
    plt.ylabel("Context Norm")
    plt.tight_layout()
    path1 = run_dir / "context_norm_vs_turn.png"
    fig1.savefig(path1, dpi=120)
    plt.close(fig1)
    generated.append(path1.name)

    fig2 = plt.figure(figsize=(10, 4))
    plt.plot(turns, gen_times, linewidth=1.5)
    plt.title("Generation Time vs Turn")
    plt.xlabel("Turn")
    plt.ylabel("Seconds")
    plt.tight_layout()
    path2 = run_dir / "generation_time_vs_turn.png"
    fig2.savefig(path2, dpi=120)
    plt.close(fig2)
    generated.append(path2.name)

    if lag_stats:
        lags = sorted(lag_stats.keys())
        acc = []
        for lag in lags:
            total = lag_stats[lag]["total"]
            correct = lag_stats[lag]["correct"]
            acc.append((correct / total) if total else 0.0)

        fig3 = plt.figure(figsize=(8, 4))
        plt.bar([str(v) for v in lags], acc)
        plt.title("Probe Accuracy by Lag")
        plt.xlabel("Lag (turns)")
        plt.ylabel("Accuracy")
        plt.ylim(0.0, 1.0)
        plt.tight_layout()
        path3 = run_dir / "probe_accuracy_by_lag.png"
        fig3.savefig(path3, dpi=120)
        plt.close(fig3)
        generated.append(path3.name)

    return generated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Long-horizon memory evaluation for CognitiveBridge.")
    parser.add_argument("--turns", type=int, default=50, help="Total turns to simulate.")
    parser.add_argument("--inject-every", type=int, default=10, help="Inject one memory fact every N turns.")
    parser.add_argument("--probe-lags", type=str, default="5,25", help="Comma-separated lag turns for recall probes.")
    parser.add_argument(
        "--probe-response-format",
        type=str,
        choices=("plain", "json"),
        default="plain",
        help="Expected probe response format.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")

    parser.add_argument("--qwen-model-id", type=str, default="Qwen/Qwen3-4B")
    parser.add_argument("--mamba-model-id", type=str, default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--context-dim", type=int, default=2048)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--repetition-penalty", type=float, default=1.05)

    parser.add_argument("--device", type=str, default="auto", help="auto/cuda/cpu")
    parser.add_argument("--hyper-device", type=str, default="cpu")
    parser.add_argument("--use-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--force-mamba-cpu", action="store_true", help="Move Mamba to CPU after load.")
    parser.add_argument("--disable-startup-validation", action="store_true")
    parser.add_argument(
        "--lora-mode",
        type=str,
        choices=("on", "off", "both"),
        default="on",
        help="Ablation mode: LoRA enabled, disabled, or both (side-by-side).",
    )

    parser.add_argument("--save-state-every", type=int, default=0, help="Save state every N turns (0=off).")
    parser.add_argument(
        "--export-context-vectors",
        action="store_true",
        help="Write per-turn context vectors to context_vectors.jsonl.",
    )
    parser.add_argument(
        "--log-output-preview-chars",
        type=int,
        default=0,
        help="If >0, log first N chars of generated output each turn.",
    )
    parser.add_argument("--output-dir", type=str, default="long_horizon_runs")
    parser.add_argument("--no-plots", action="store_true", help="Disable matplotlib plot generation.")
    return parser


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def reset_bridge_runtime_state(bridge: CognitiveBridge) -> None:
    bridge.turn_count = 0
    bridge.diagnostics_history.clear()
    bridge._mamba_cache = None
    bridge._mamba_history_ids = None
    bridge._last_context_vector = None
    bridge._clear_lora()


def set_lora_enabled(bridge: CognitiveBridge, enabled: bool):
    original_inject = bridge._inject_lora
    if enabled:
        return lambda: None

    def inject_disabled(_context_vector: torch.Tensor) -> List[float]:
        return [0.0 for _ in bridge._patched_layers]

    bridge._inject_lora = inject_disabled  # type: ignore[assignment]

    def restore() -> None:
        bridge._inject_lora = original_inject  # type: ignore[assignment]

    return restore


def run_single_mode(
    bridge: CognitiveBridge,
    args: argparse.Namespace,
    probe_lags: List[int],
    run_dir: Path,
    model_load_time_s: float,
    lora_enabled: bool,
) -> Dict[str, Any]:
    mode_label = "lora_on" if lora_enabled else "lora_off"
    run_dir.mkdir(parents=True, exist_ok=True)
    states_dir = run_dir / "states"
    if args.save_state_every > 0:
        states_dir.mkdir(parents=True, exist_ok=True)

    reset_bridge_runtime_state(bridge)
    seed_everything(args.seed)
    restore_lora = set_lora_enabled(bridge, enabled=lora_enabled)
    mode_start = time.time()

    facts: List[FactMemory] = []
    due_by_turn: Dict[int, List[ProbeTask]] = defaultdict(list)
    pending_probes: Deque[ProbeTask] = deque()
    turn_rows: List[dict] = []
    probe_rows: List[dict] = []
    saved_states: List[dict] = []

    context_vectors_fp = None
    turns_live_fp = None
    probes_live_fp = None
    run_error: Optional[Dict[str, Any]] = None
    abort_exc: Optional[BaseException] = None
    current_turn = 0
    if args.export_context_vectors:
        context_vectors_fp = open(run_dir / "context_vectors.jsonl", "w", encoding="utf-8")
    turns_live_fp = open(run_dir / "turns_live.jsonl", "w", encoding="utf-8")
    probes_live_fp = open(run_dir / "probes_live.jsonl", "w", encoding="utf-8")

    try:
        for turn in range(1, args.turns + 1):
            current_turn = turn
            for probe in due_by_turn.get(turn, []):
                pending_probes.append(probe)

            event_type = "filler"
            expected_token: Optional[str] = None
            subject: Optional[str] = None
            lag: Optional[int] = None
            fact_id: Optional[int] = None

            if turn % args.inject_every == 0:
                fact = make_fact(len(facts), turn)
                facts.append(fact)
                for probe_lag in probe_lags:
                    due_turn = turn + probe_lag
                    if due_turn <= args.turns:
                        due_by_turn[due_turn].append(
                            ProbeTask(due_turn=due_turn, fact_id=fact.fact_id, lag=probe_lag)
                        )
                input_text = build_inject_prompt(fact)
                event_type = "inject"
                subject = fact.subject
                fact_id = fact.fact_id
            elif pending_probes:
                task = pending_probes.popleft()
                fact = facts[task.fact_id]
                if args.probe_response_format == "json":
                    input_text = build_probe_prompt_json(fact, task.lag)
                else:
                    input_text = build_probe_prompt(fact, task.lag)
                event_type = "probe"
                expected_token = fact.token
                subject = fact.subject
                lag = task.lag
                fact_id = fact.fact_id
            else:
                input_text = build_filler_prompt(turn)

            diag = bridge.generate(input_text)
            output_text = diag.raw_output

            correct: Optional[bool] = None
            parsed_token: Optional[str] = None
            if event_type == "probe":
                if args.probe_response_format == "json":
                    parsed_token = extract_probe_token_from_json(output_text)
                else:
                    parsed_token = extract_probe_token(output_text)
                correct = bool(expected_token and parsed_token == expected_token.lower())
                probe_row = {
                    "turn": turn,
                    "fact_id": fact_id,
                    "subject": subject,
                    "lag": lag,
                    "expected_token": expected_token,
                    "parsed_token": parsed_token,
                    "correct": int(bool(correct)),
                    "context_norm": diag.context_vector_norm,
                    "generation_time_s": diag.generation_time_s,
                    "output": output_text,
                }
                probe_rows.append(probe_row)
                if probes_live_fp is not None:
                    probes_live_fp.write(json.dumps(probe_row, ensure_ascii=False) + "\n")
                    probes_live_fp.flush()

            lora_norm_mean = statistics.fmean(diag.lora_norms) if diag.lora_norms else 0.0
            row = {
                "turn": turn,
                "event_type": event_type,
                "fact_id": fact_id,
                "subject": subject,
                "lag": lag,
                "expected_token": expected_token,
                "parsed_token": parsed_token,
                "correct": correct,
                "context_norm": diag.context_vector_norm,
                "mamba_state_mb": diag.mamba_state_mb,
                "generation_time_s": diag.generation_time_s,
                "input_tokens": diag.input_tokens,
                "output_tokens": diag.output_tokens,
                "lora_norm_mean": lora_norm_mean,
                "input_text": input_text,
                "output_text": output_text,
            }
            turn_rows.append(row)
            if turns_live_fp is not None:
                turns_live_fp.write(json.dumps(row, ensure_ascii=False) + "\n")
                turns_live_fp.flush()

            if context_vectors_fp is not None:
                ctx = bridge.get_last_context_vector()
                if ctx is not None:
                    ctx_row = {
                        "turn": turn,
                        "event_type": event_type,
                        "fact_id": fact_id,
                        "subject": subject,
                        "lag": lag,
                        "context_norm": float(ctx.norm()),
                        "vector": ctx.squeeze(0).tolist(),
                    }
                    context_vectors_fp.write(json.dumps(ctx_row, ensure_ascii=False) + "\n")
                    context_vectors_fp.flush()

            if args.save_state_every > 0 and (turn % args.save_state_every == 0):
                state_path = bridge.save_state(str(states_dir / f"state_turn_{turn}.pt"))
                saved_states.append({"turn": turn, "path": state_path})

            if args.log_output_preview_chars > 0:
                preview = " ".join(output_text.split())
                if len(preview) > args.log_output_preview_chars:
                    preview = preview[: args.log_output_preview_chars] + "..."
                LOGGER.info("[%s] Output t=%d: %s", mode_label, turn, preview)

            if (turn % max(1, args.turns // 20) == 0) or event_type == "probe":
                LOGGER.info(
                    "[%s] Turn %d/%d | %s | ctx=%.3f | time=%.2fs%s",
                    mode_label,
                    turn,
                    args.turns,
                    event_type,
                    diag.context_vector_norm,
                    diag.generation_time_s,
                    (f" | probe_correct={int(bool(correct))}" if event_type == "probe" else ""),
                )
    except KeyboardInterrupt as exc:
        run_error = {
            "turn": current_turn,
            "type": type(exc).__name__,
            "message": "Interrupted by user",
        }
        abort_exc = exc
        LOGGER.warning("[%s] Interrupted at turn %d. Saving partial artifacts.", mode_label, current_turn)
    except Exception as exc:
        run_error = {
            "turn": current_turn,
            "type": type(exc).__name__,
            "message": str(exc),
        }
        abort_exc = exc
        LOGGER.exception("[%s] Aborted at turn %d due to error. Saving partial artifacts.", mode_label, current_turn)
    finally:
        if context_vectors_fp is not None:
            context_vectors_fp.close()
        if turns_live_fp is not None:
            turns_live_fp.close()
        if probes_live_fp is not None:
            probes_live_fp.close()
        restore_lora()

    total_runtime_s = time.time() - mode_start
    probe_total = len(probe_rows)
    probe_correct = sum(int(r["correct"]) for r in probe_rows)
    probe_accuracy = (probe_correct / probe_total) if probe_total else 0.0

    lag_stats: Dict[int, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in probe_rows:
        lag_key = int(r["lag"])
        lag_stats[lag_key]["total"] += 1
        lag_stats[lag_key]["correct"] += int(r["correct"])

    generation_times = [r["generation_time_s"] for r in turn_rows]
    context_norms = [r["context_norm"] for r in turn_rows]
    lora_norm_means = [r["lora_norm_mean"] for r in turn_rows]

    summary: Dict[str, Any] = {
        "run_dir": str(run_dir.resolve()),
        "mode": mode_label,
        "status": "aborted" if run_error else "ok",
        "error": run_error,
        "turns_requested": args.turns,
        "turns_completed": len(turn_rows),
        "inject_every": args.inject_every,
        "probe_lags": probe_lags,
        "facts_injected": len(facts),
        "probes_total": probe_total,
        "probes_correct": probe_correct,
        "probe_accuracy": probe_accuracy,
        "probe_accuracy_by_lag": {
            str(k): {
                "total": v["total"],
                "correct": v["correct"],
                "accuracy": (v["correct"] / v["total"]) if v["total"] else 0.0,
            }
            for k, v in sorted(lag_stats.items())
        },
        "avg_generation_time_s": statistics.fmean(generation_times) if generation_times else None,
        "avg_context_norm": statistics.fmean(context_norms) if context_norms else None,
        "avg_lora_norm_mean": statistics.fmean(lora_norm_means) if lora_norm_means else None,
        "context_norm_start": context_norms[0] if context_norms else None,
        "context_norm_end": context_norms[-1] if context_norms else None,
        "total_runtime_s": total_runtime_s,
        "model_load_time_s": model_load_time_s,
        "bridge_info_end": bridge.get_info(),
        "saved_states": saved_states,
        "config": vars(args),
    }

    turns_jsonl = run_dir / "turns.jsonl"
    with open(turns_jsonl, "w", encoding="utf-8") as fp:
        for row in turn_rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    turns_csv = run_dir / "turns.csv"
    with open(turns_csv, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "turn",
                "event_type",
                "fact_id",
                "subject",
                "lag",
                "expected_token",
                "parsed_token",
                "correct",
                "context_norm",
                "mamba_state_mb",
                "generation_time_s",
                "input_tokens",
                "output_tokens",
                "lora_norm_mean",
                "input_text",
                "output_text",
            ],
        )
        writer.writeheader()
        writer.writerows(turn_rows)

    probes_csv = run_dir / "probes.csv"
    with open(probes_csv, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "turn",
                "fact_id",
                "subject",
                "lag",
                "expected_token",
                "parsed_token",
                "correct",
                "context_norm",
                "generation_time_s",
                "output",
            ],
        )
        writer.writeheader()
        writer.writerows(probe_rows)

    facts_json = run_dir / "facts.json"
    with open(facts_json, "w", encoding="utf-8") as fp:
        json.dump([asdict(f) for f in facts], fp, indent=2, ensure_ascii=False)

    if not args.no_plots:
        plot_files = maybe_make_plots(run_dir, turn_rows, lag_stats)
        summary["plots"] = plot_files if plot_files is not None else "matplotlib not available"

    summary_json = run_dir / "summary.json"
    with open(summary_json, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2, ensure_ascii=False)

    LOGGER.info("[%s] Run complete. Summary: %s", mode_label, summary_json)
    LOGGER.info(
        "[%s] Probe accuracy: %.3f (%d/%d)",
        mode_label,
        probe_accuracy,
        probe_correct,
        probe_total,
    )
    if abort_exc is not None:
        if isinstance(abort_exc, KeyboardInterrupt):
            raise KeyboardInterrupt()
        raise RuntimeError(
            f"[{mode_label}] Run aborted at turn {run_error.get('turn') if run_error else '?'}: "
            f"{run_error.get('message') if run_error else 'unknown error'}"
        ) from abort_exc
    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.turns <= 0:
        raise ValueError("--turns must be > 0")
    if args.inject_every <= 0:
        raise ValueError("--inject-every must be > 0")
    if args.save_state_every < 0:
        raise ValueError("--save-state-every must be >= 0")

    probe_lags = parse_lags(args.probe_lags)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    seed_everything(args.seed)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = SCRIPT_DIR / output_root
    run_dir = output_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Starting long-horizon evaluation: turns=%d, inject_every=%d, lags=%s",
                args.turns, args.inject_every, probe_lags)
    LOGGER.info("Run directory: %s", run_dir)

    config = BridgeConfig(
        qwen_model_id=args.qwen_model_id,
        mamba_model_id=args.mamba_model_id,
        context_dim=args.context_dim,
        lora_rank=args.lora_rank,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        repetition_penalty=args.repetition_penalty,
        device=args.device,
        hyper_device=args.hyper_device,
        use_4bit=args.use_4bit,
        state_dir=str(run_dir / "states"),
        startup_validation=not args.disable_startup_validation,
    )

    bridge = CognitiveBridge(config)
    load_start = time.time()
    bridge.load_models()
    load_time_s = time.time() - load_start
    LOGGER.info("Models loaded in %.1fs", load_time_s)

    if args.force_mamba_cpu and bridge.mamba_model is not None:
        mamba_device = next(bridge.mamba_model.parameters()).device
        if str(mamba_device) != "cpu":
            LOGGER.info("Force-moving Mamba from %s to CPU (float32).", mamba_device)
            bridge.mamba_model = bridge.mamba_model.to(device="cpu", dtype=torch.float32)
            bridge._mamba_device = torch.device("cpu")

    if args.lora_mode == "both":
        summary_on = run_single_mode(
            bridge=bridge,
            args=args,
            probe_lags=probe_lags,
            run_dir=run_dir / "lora_on",
            model_load_time_s=load_time_s,
            lora_enabled=True,
        )
        summary_off = run_single_mode(
            bridge=bridge,
            args=args,
            probe_lags=probe_lags,
            run_dir=run_dir / "lora_off",
            model_load_time_s=load_time_s,
            lora_enabled=False,
        )

        comparison = {
            "timestamp_utc": timestamp,
            "mode": "both",
            "run_dir": str(run_dir.resolve()),
            "on": {
                "probe_accuracy": summary_on.get("probe_accuracy"),
                "probes_total": summary_on.get("probes_total"),
                "avg_generation_time_s": summary_on.get("avg_generation_time_s"),
                "avg_context_norm": summary_on.get("avg_context_norm"),
                "avg_lora_norm_mean": summary_on.get("avg_lora_norm_mean"),
            },
            "off": {
                "probe_accuracy": summary_off.get("probe_accuracy"),
                "probes_total": summary_off.get("probes_total"),
                "avg_generation_time_s": summary_off.get("avg_generation_time_s"),
                "avg_context_norm": summary_off.get("avg_context_norm"),
                "avg_lora_norm_mean": summary_off.get("avg_lora_norm_mean"),
            },
            "delta": {
                "probe_accuracy_on_minus_off": (
                    float(summary_on.get("probe_accuracy", 0.0))
                    - float(summary_off.get("probe_accuracy", 0.0))
                ),
                "avg_generation_time_s_on_minus_off": (
                    float(summary_on.get("avg_generation_time_s", 0.0))
                    - float(summary_off.get("avg_generation_time_s", 0.0))
                ),
            },
        }
        comparison_path = run_dir / "comparison.json"
        with open(comparison_path, "w", encoding="utf-8") as fp:
            json.dump(comparison, fp, indent=2, ensure_ascii=False)
        LOGGER.info("Ablation comparison written: %s", comparison_path)
    else:
        run_single_mode(
            bridge=bridge,
            args=args,
            probe_lags=probe_lags,
            run_dir=run_dir,
            model_load_time_s=load_time_s,
            lora_enabled=(args.lora_mode == "on"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
