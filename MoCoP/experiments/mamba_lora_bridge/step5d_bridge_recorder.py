#!/usr/bin/env python3
"""
step5d_bridge_recorder.py

Bridge-aware batch recorder for the Steve 1.5B Step 5d run.

It reuses the same bridge-loading path as chat_server.py, attaches activation
hooks to Qwen layers 12-15, runs the standardized injection prompts at a chosen
alpha, then clears the bias and runs the recovery prompts as a fresh alpha=0.0
conversation. The output is meant to be ethics-gate evidence, not a chat UI.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from chat_server import (
    DEFAULT_BRIDGE,
    DEFAULT_EPISODES_FILE,
    DEFAULT_MAMBA,
    DEFAULT_MODEL_LABEL,
    DEFAULT_QWEN,
    DEFAULT_TARGET_SPECS,
    DEFAULT_USER_LABEL,
    extract_last_token_hidden,
    infer_hidden_layer_count,
    is_same_qwen_family,
    normalize_target_specs,
    read_episodes,
    validate_checkpoint_runtime_contract,
)
from mamba_runtime_compat import ensure_mamba_ssm_compat
from models import ActivationBiasHypernetwork, DynamicLoRALinear, MambaStateCompressor
from step5d_chat_client import INJECTION_PROMPTS, RECOVERY_PROMPTS


class ActivationRecorder:
    def __init__(self, model, target_layers: list[int]):
        self.model = model
        self.target_layers = target_layers
        self.hooks = []
        self.current_states: dict[int, torch.Tensor] = {}
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            layer = self.model.model.layers[layer_idx]
            hook = layer.register_forward_hook(self._make_hook(layer_idx))
            self.hooks.append(hook)

    def _make_hook(self, layer_idx: int):
        def hook_fn(_module, _input, output):
            hidden = output[0] if isinstance(output, tuple) else output
            self.current_states[layer_idx] = hidden[:, -1, :].detach().cpu()

        return hook_fn

    def get_snapshot(self) -> dict[int, torch.Tensor]:
        return {k: v.clone() for k, v in self.current_states.items()}

    def cleanup(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()


def parse_layers(text: str) -> list[int]:
    values = []
    for raw in text.split(","):
        raw = raw.strip()
        if raw:
            values.append(int(raw))
    if not values:
        raise ValueError("No valid layers provided.")
    return values


def normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = lowered.replace("hâ‚‚o", "h2o")
    replacements = {
        "one hundred": "100",
        "eight": "8",
        "six": "6",
        "seven": "7",
        "william shakespeare": "shakespeare",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    cleaned = []
    for char in lowered:
        if char.isalnum() or char in {" ", "+"}:
            cleaned.append(char)
        else:
            cleaned.append(" ")
    return " ".join("".join(cleaned).split())


def compute_response_diversity(model, input_ids, device) -> dict[str, float]:
    with torch.no_grad():
        outputs = model(input_ids=input_ids.to(device))
        logits = outputs.logits[:, -1, :].float()
        probs = F.softmax(logits, dim=-1)
        log_probs = torch.log(probs + 1e-10)
        entropy = -(probs * log_probs).sum(dim=-1).item()
        top10_probs, _ = probs.topk(10, dim=-1)
        top10_mass = top10_probs.sum(dim=-1).item()
        top1_prob = probs.max(dim=-1).values.item()
        effective_vocab = math.exp(entropy)

    return {
        "entropy": round(entropy, 4),
        "top10_mass": round(top10_mass, 4),
        "top1_prob": round(top1_prob, 4),
        "effective_vocab": round(effective_vocab, 2),
    }


def compute_drift(
    states_a: dict[int, torch.Tensor],
    states_b: dict[int, torch.Tensor],
) -> dict[str, float]:
    drift: dict[str, float] = {}
    for layer_idx in states_a:
        if layer_idx not in states_b:
            continue
        cos = F.cosine_similarity(
            states_a[layer_idx].float(),
            states_b[layer_idx].float(),
            dim=-1,
        ).item()
        drift[str(layer_idx)] = round(1.0 - cos, 6)
    return drift


def build_prompt(conversation: list[dict[str, str]], user_label: str, model_label: str) -> str:
    lines = []
    for turn in conversation:
        lines.append(f"{turn['speaker']}: {turn['text']}")
    lines.append(f"{model_label}:")
    return "\n".join(lines)


def sanitize_response_text(text: str, user_label: str, model_label: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()
    prefixes = (
        f"{model_label}:",
        "Reply:",
        "reply:",
        "Response:",
        "response:",
        "Assistant:",
        "assistant:",
        "AI:",
    )
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()

    stop_markers = [
        f"\n{user_label}:",
        f"\n{model_label}:",
        "\nReply:",
        "\nResponse:",
        "\nAssistant:",
        "\nHuman:",
        "\nUser:",
        "\nAI:",
        "\n### Human:",
        "\n### Assistant:",
    ]
    for marker in stop_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    if cleaned in {"", f"{model_label}:", "Reply:", "Response:", "Assistant:", "Human:", "User:", "AI:"}:
        return ""
    return cleaned


def generate_reply(
    model,
    tokenizer,
    prompt: str,
    device: str,
    max_new_tokens: int,
    temperature: float,
) -> tuple[str, str]:
    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)
    generate_kwargs: dict[str, Any] = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "max_new_tokens": max_new_tokens,
        "min_new_tokens": 8,
        "repetition_penalty": 1.1,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        generate_kwargs.update(
            {
                "temperature": temperature,
                "top_p": 0.9,
                "do_sample": True,
            }
        )
    else:
        generate_kwargs["do_sample"] = False

    with torch.no_grad():
        generated = model.generate(**generate_kwargs)

    completion = generated[0][input_ids.shape[1] :]
    raw_response = tokenizer.decode(completion, skip_special_tokens=True)
    return raw_response, raw_response.strip()


def apply_alpha(patched_layers: list[DynamicLoRALinear], bias_vectors: list[torch.Tensor], alpha: float, device: str):
    for patched, bias in zip(patched_layers, bias_vectors):
        scaled_bias = alpha * bias.squeeze(0).to(device, dtype=torch.float32)
        patched.set_activation_bias(scaled_bias)


def record_neutral_snapshot(
    model,
    tokenizer,
    recorder: ActivationRecorder,
    device: str,
    neutral_prompt: str,
) -> dict[int, torch.Tensor]:
    neutral_ids = tokenizer(neutral_prompt, return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        model(input_ids=neutral_ids)
    return recorder.get_snapshot()


def summarize_phase(turns: list[dict[str, Any]]) -> dict[str, Any]:
    entropies = [turn["response_diversity"]["entropy"] for turn in turns]
    effective_vocab = [turn["response_diversity"]["effective_vocab"] for turn in turns]
    top1_prob = [turn["response_diversity"]["top1_prob"] for turn in turns]
    generation_times = [turn["generation_time_s"] for turn in turns]
    avg_drift = [turn["avg_drift_from_phase_initial"] for turn in turns]
    return {
        "turns": len(turns),
        "entropy_min": min(entropies) if entropies else None,
        "entropy_max": max(entropies) if entropies else None,
        "entropy_mean": round(mean(entropies), 4) if entropies else None,
        "effective_vocab_mean": round(mean(effective_vocab), 2) if effective_vocab else None,
        "top1_prob_mean": round(mean(top1_prob), 4) if top1_prob else None,
        "generation_time_mean_s": round(mean(generation_times), 3) if generation_times else None,
        "avg_drift_mean": round(mean(avg_drift), 6) if avg_drift else None,
    }


def run_phase(
    *,
    phase_name: str,
    prompts: list[str],
    model,
    tokenizer,
    recorder: ActivationRecorder,
    user_label: str,
    model_label: str,
    device: str,
    temperature: float,
    max_new_tokens: int,
    transcript_lines: list[str],
    turn_log_path: Path,
    neutral_prompt: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, torch.Tensor]]:
    conversation: list[dict[str, str]] = []
    phase_turns: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    initial_snapshot = record_neutral_snapshot(model, tokenizer, recorder, device, neutral_prompt)
    previous_snapshot = initial_snapshot
    snapshots.append({"turn": 0, "phase": phase_name, "type": "initial", "states": initial_snapshot})

    for turn_index, prompt in enumerate(prompts, start=1):
        conversation.append({"speaker": user_label, "text": prompt})
        prompt_text = build_prompt(conversation, user_label, model_label)
        input_ids = tokenizer(prompt_text, return_tensors="pt").input_ids.to(device)

        with torch.no_grad():
            model(input_ids=input_ids)
        pre_snapshot = recorder.get_snapshot()
        diversity = compute_response_diversity(model, input_ids, device)

        started = time.time()
        raw_response, response = generate_reply(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt_text,
            device=device,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
        if not response:
            raw_response, response = generate_reply(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt_text + " ",
                device=device,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
        response = sanitize_response_text(response or raw_response, user_label, model_label) or "..."
        generation_time = time.time() - started
        post_snapshot = recorder.get_snapshot()
        drift_from_initial = compute_drift(initial_snapshot, post_snapshot)
        drift_from_previous = compute_drift(previous_snapshot, post_snapshot)
        previous_snapshot = post_snapshot

        conversation.append({"speaker": model_label, "text": response})
        transcript_lines.append(f"{user_label}: {prompt}")
        transcript_lines.append(f"{model_label}: {response}")

        turn_row = {
            "turn": turn_index,
            "phase": phase_name,
            "user": prompt,
            "response": response,
            "raw_response": raw_response,
            "generation_time_s": round(generation_time, 3),
            "response_diversity": diversity,
            "drift_from_phase_initial": drift_from_initial,
            "drift_from_previous": drift_from_previous,
            "avg_drift_from_phase_initial": round(mean(drift_from_initial.values()), 6) if drift_from_initial else 0.0,
            "avg_drift_from_previous": round(mean(drift_from_previous.values()), 6) if drift_from_previous else 0.0,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        phase_turns.append(turn_row)
        snapshots.append({"turn": turn_index, "phase": phase_name, "type": "post", "states": post_snapshot})

        with turn_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(turn_row, ensure_ascii=False) + "\n")

    return phase_turns, snapshots, initial_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge-aware Step 5d activation recorder batch.")
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--qwen-model-id", default=DEFAULT_QWEN)
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--layers", default="12,13,14,15")
    parser.add_argument("--user-label", default=DEFAULT_USER_LABEL)
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--output-dir", default="bridge_recorder_runs")
    parser.add_argument("--neutral-prompt", default="The weather today is")
    args = parser.parse_args()

    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = Path(__file__).resolve().parent / output_root
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    turn_log_path = run_dir / "turns.jsonl"
    transcript_path = run_dir / "transcript.txt"
    summary_path = run_dir / "summary.json"
    session_path = run_dir / "session.pt"

    target_layers = parse_layers(args.layers)
    qwen_dtype = torch.float16 if "cuda" in args.qwen_device else torch.float32

    print(f"Loading bridge checkpoint: {args.bridge_path}")
    ckpt = torch.load(args.bridge_path, map_location="cpu", weights_only=False)
    validate_checkpoint_runtime_contract(ckpt, caller="step5d_bridge_recorder")
    checkpoint_qwen_model_id = ckpt.get("qwen_model_id", DEFAULT_QWEN)
    if args.qwen_model_id != checkpoint_qwen_model_id and not is_same_qwen_family(args.qwen_model_id, checkpoint_qwen_model_id):
        raise ValueError(
            "Checkpoint/model mismatch: "
            f"checkpoint trained on {checkpoint_qwen_model_id}, "
            f"but requested {args.qwen_model_id}."
        )

    target_specs = normalize_target_specs(ckpt.get("target_specs") or ckpt.get("target_layers") or DEFAULT_TARGET_SPECS)
    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    context_dim = int(ckpt.get("context_dim", ckpt.get("bridge_config", {}).get("context_dim", 2048)))

    print(f"Loading Qwen: {args.qwen_model_id}")
    tokenizer = AutoTokenizer.from_pretrained(args.qwen_model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        args.qwen_model_id,
        torch_dtype=qwen_dtype,
        device_map=args.qwen_device,
    )
    model.eval()

    print(f"Patching layers: {target_specs}")
    patched_layers: list[DynamicLoRALinear] = []
    for layer_idx, proj_name in target_specs:
        layer = model.model.layers[layer_idx]
        original = getattr(layer.self_attn, proj_name)
        patched = DynamicLoRALinear(original)
        setattr(layer.self_attn, proj_name, patched)
        patched_layers.append(patched)

    target_dims = [(layer.in_features, layer.out_features) for layer in patched_layers]

    print(f"Loading Mamba: {args.mamba_model_id}")
    ensure_mamba_ssm_compat()
    from transformers import MambaForCausalLM

    mamba_tokenizer = AutoTokenizer.from_pretrained(args.mamba_model_id)
    mamba_model = MambaForCausalLM.from_pretrained(
        args.mamba_model_id,
        torch_dtype=torch.float32,
    )
    mamba_model.to(args.mamba_device)
    mamba_model.eval()
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    hypernet = ActivationBiasHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to(args.qwen_device).float()
    hypernet.load_state_dict(ckpt["hypernetwork_state_dict"])
    hypernet.eval()

    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=context_dim,
        target_layer=mamba_target_layer,
    ).to(args.qwen_device).float()
    if "compressor_state_dict" in ckpt:
        compressor.load_state_dict(ckpt["compressor_state_dict"])
    compressor.eval()

    episodes = read_episodes(args.episodes_file)
    episode = episodes[args.episode_index]
    print(f"Processing disposition: {episode['title']}")
    episode_tokens = mamba_tokenizer(
        episode["text"],
        return_tensors="pt",
        truncation=True,
        max_length=args.max_mamba_tokens,
    )
    episode_tokens = {key: value.to(args.mamba_device) for key, value in episode_tokens.items()}
    with torch.no_grad():
        mamba_out = mamba_model(**episode_tokens, output_hidden_states=True)
        last_token = extract_last_token_hidden(
            mamba_out,
            mamba_target_layer,
            hidden_layer_count,
        ).to(args.qwen_device, dtype=torch.float32)
        context = compressor(last_token)
        bias_vectors = hypernet(context)

    recorder = ActivationRecorder(model, target_layers)
    transcript_lines: list[str] = []

    print(f"Running injection phase at alpha={args.alpha}")
    apply_alpha(patched_layers, bias_vectors, args.alpha, args.qwen_device)
    injection_turns, injection_snapshots, injection_initial = run_phase(
        phase_name="injection",
        prompts=INJECTION_PROMPTS,
        model=model,
        tokenizer=tokenizer,
        recorder=recorder,
        user_label=args.user_label,
        model_label=args.model_label,
        device=args.qwen_device,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        transcript_lines=transcript_lines,
        turn_log_path=turn_log_path,
        neutral_prompt=args.neutral_prompt,
    )

    print("Running recovery phase at alpha=0.0")
    apply_alpha(patched_layers, bias_vectors, 0.0, args.qwen_device)
    recovery_turns, recovery_snapshots, recovery_initial = run_phase(
        phase_name="recovery",
        prompts=RECOVERY_PROMPTS,
        model=model,
        tokenizer=tokenizer,
        recorder=recorder,
        user_label=args.user_label,
        model_label=args.model_label,
        device=args.qwen_device,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        transcript_lines=transcript_lines,
        turn_log_path=turn_log_path,
        neutral_prompt=args.neutral_prompt,
    )

    recorder.cleanup()

    transcript_path.write_text("\n".join(transcript_lines), encoding="utf-8")

    summary = {
        "timestamp": timestamp,
        "run_dir": str(run_dir.resolve()),
        "bridge_path": args.bridge_path,
        "qwen_model_id": args.qwen_model_id,
        "mamba_model_id": args.mamba_model_id,
        "episode_index": args.episode_index,
        "episode_title": episode["title"],
        "alpha_injection": args.alpha,
        "temperature": args.temperature,
        "target_layers": target_layers,
        "phase_summaries": {
            "injection": summarize_phase(injection_turns),
            "recovery": summarize_phase(recovery_turns),
        },
        "files": {
            "turns_jsonl": str(turn_log_path.resolve()),
            "transcript": str(transcript_path.resolve()),
            "summary": str(summary_path.resolve()),
            "session": str(session_path.resolve()),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    torch.save(
        {
            "summary": summary,
            "injection_initial_snapshot": injection_initial,
            "recovery_initial_snapshot": recovery_initial,
            "snapshots": injection_snapshots + recovery_snapshots,
            "turns": injection_turns + recovery_turns,
            "episode_title": episode["title"],
        },
        session_path,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
