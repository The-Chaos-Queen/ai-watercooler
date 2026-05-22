#!/usr/bin/env python3
"""
record_prompt_suffix_trace_dataset.py

Build a matched prompt-suffix trace dataset for bridge training.

For each CHEESE shaping episode and each prompt in a small probe panel:
  1. record Qwen v_proj input traces for the prompt suffix alone
  2. record Qwen v_proj input traces for the same suffix after the episode

The prompt suffix tokens are aligned exactly, so each token position becomes a
clean source->target pair:

  source: prompt-only hidden input at token t
  target: episode-primed hidden input at the same suffix token t

CHEESE remains the conditioning source. This dataset only upgrades the
supervision surface from 3 last-token anchors to many matched prompt-token
pairs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-1.5B"
DEFAULT_EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
DEFAULT_PANEL_FILE = "step6_eval_panel.json"
DEFAULT_OUTPUT_PATH = "prompt_suffix_trace_dataset_step6.pt"
DEFAULT_TARGET_LAYERS = [12, 13, 14, 15]


def sanitize_episode_name(header: str) -> str:
    return (
        header.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "")
        .replace("/", "_")
    )


def parse_target_layers(raw: str) -> list[int]:
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def load_episodes(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    raw_episodes = content.split("## Episode ")[1:]
    episodes = []
    for raw_episode in raw_episodes:
        lines = raw_episode.splitlines()
        header = lines[0].strip()
        transcript = raw_episode.split("[Transcript]", 1)[1].strip()
        episodes.append(
            {
                "header": header,
                "episode_name": sanitize_episode_name(header),
                "transcript": transcript,
            }
        )
    return episodes


def load_panel(path: Path) -> list[dict]:
    panel = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(panel, list) or not panel:
        raise ValueError(f"Panel must be a non-empty JSON list: {path}")
    normalized = []
    for idx, item in enumerate(panel):
        if not isinstance(item, dict):
            raise ValueError(f"Panel item {idx} must be an object.")
        prompt = str(item.get("prompt", "")).strip()
        if not prompt:
            raise ValueError(f"Panel item {idx} is missing a non-empty 'prompt'.")
        normalized.append(
            {
                "id": str(item.get("id", f"prompt_{idx + 1:02d}")),
                "slice": str(item.get("slice", "")),
                "prompt": prompt,
            }
        )
    return normalized


class VProjInputTraceRecorder:
    def __init__(self, model, target_layers: list[int]):
        self.model = model
        self.target_layers = target_layers
        self.current: dict[int, torch.Tensor] = {}
        self.handles = []
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            module = self.model.model.layers[layer_idx].self_attn.v_proj
            self.handles.append(module.register_forward_pre_hook(self._make_hook(layer_idx)))

    def _make_hook(self, layer_idx: int):
        def hook_fn(_module, module_in):
            hidden_in = module_in[0] if isinstance(module_in, tuple) else module_in
            self.current[layer_idx] = hidden_in[0].detach().float().cpu()

        return hook_fn

    def get_snapshot(self) -> dict[int, torch.Tensor]:
        return {layer_idx: tensor.clone() for layer_idx, tensor in self.current.items()}

    def cleanup(self):
        for handle in self.handles:
            handle.remove()
        self.handles.clear()


def tokenize_left(tokenizer, text: str, max_length: int):
    old_side = getattr(tokenizer, "truncation_side", "right")
    tokenizer.truncation_side = "left"
    try:
        encoded = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
    finally:
        tokenizer.truncation_side = old_side
    return encoded


def build_suffix(prompt: str, user_label: str, assistant_label: str) -> str:
    return f"{user_label}: {prompt}\n{assistant_label}:"


def build_target_text(transcript: str, suffix: str) -> str:
    return f"{transcript}\n\n{suffix}"


def capture_suffix_trace(
    *,
    model,
    tokenizer,
    recorder: VProjInputTraceRecorder,
    device: str,
    text: str,
    suffix_token_ids: list[int],
    max_length: int,
    target_layers: list[int],
) -> tuple[dict[int, torch.Tensor], list[int]]:
    encoded = tokenize_left(tokenizer, text, max_length=max_length)
    input_ids = encoded["input_ids"][0].tolist()
    if len(input_ids) < len(suffix_token_ids):
        raise RuntimeError(
            "Encoded sequence is shorter than the suffix token sequence. "
            f"kept={len(input_ids)} suffix={len(suffix_token_ids)}"
        )
    if input_ids[-len(suffix_token_ids) :] != suffix_token_ids:
        raise RuntimeError(
            "Suffix token alignment failed after truncation. "
            "The kept sequence no longer ends with the expected prompt suffix."
        )

    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.no_grad():
        model(**encoded)
    snapshot = recorder.get_snapshot()

    missing_layers = [layer_idx for layer_idx in target_layers if layer_idx not in snapshot]
    if missing_layers:
        raise RuntimeError(
            "Missing v_proj input traces for layers: "
            + ", ".join(str(layer_idx) for layer_idx in missing_layers)
        )

    suffix_len = len(suffix_token_ids)
    suffix_trace = {
        layer_idx: snapshot[layer_idx][-suffix_len:].clone()
        for layer_idx in target_layers
    }
    return suffix_trace, input_ids


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record aligned prompt-suffix traces for CHEESE-conditioned bridge training."
    )
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--panel-file", default=DEFAULT_PANEL_FILE)
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--target-layers", type=parse_target_layers, default=DEFAULT_TARGET_LAYERS)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--user-label", default="User")
    parser.add_argument("--assistant-label", default="Assistant")
    return parser


def main(args: argparse.Namespace):
    script_dir = Path(__file__).resolve().parent
    episodes_path = script_dir / args.episodes_file
    panel_path = script_dir / args.panel_file
    output_path = script_dir / args.output_path

    episodes = load_episodes(episodes_path)
    panel = load_panel(panel_path)

    print(f"Loading {args.model_name} on {args.device}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if str(args.device).startswith("cuda") else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=dtype,
        device_map=args.device,
    )
    model.eval()

    recorder = VProjInputTraceRecorder(model, args.target_layers)
    samples = []

    try:
        for prompt_item in panel:
            suffix = build_suffix(
                prompt_item["prompt"],
                user_label=args.user_label,
                assistant_label=args.assistant_label,
            )
            suffix_token_ids = tokenize_left(
                tokenizer,
                suffix,
                max_length=args.max_length,
            )["input_ids"][0].tolist()

            source_trace, source_kept_ids = capture_suffix_trace(
                model=model,
                tokenizer=tokenizer,
                recorder=recorder,
                device=args.device,
                text=suffix,
                suffix_token_ids=suffix_token_ids,
                max_length=args.max_length,
                target_layers=args.target_layers,
            )

            for episode in episodes:
                target_text = build_target_text(episode["transcript"], suffix)
                target_trace, target_kept_ids = capture_suffix_trace(
                    model=model,
                    tokenizer=tokenizer,
                    recorder=recorder,
                    device=args.device,
                    text=target_text,
                    suffix_token_ids=suffix_token_ids,
                    max_length=args.max_length,
                    target_layers=args.target_layers,
                )
                samples.append(
                    {
                        "episode_name": episode["episode_name"],
                        "episode_header": episode["header"],
                        "prompt_id": prompt_item["id"],
                        "prompt_slice": prompt_item["slice"],
                        "prompt_text": prompt_item["prompt"],
                        "suffix_text": suffix,
                        "suffix_token_ids": torch.tensor(suffix_token_ids, dtype=torch.long),
                        "suffix_length": len(suffix_token_ids),
                        "source_trace": source_trace,
                        "target_trace": target_trace,
                        "source_kept_tokens": len(source_kept_ids),
                        "target_kept_tokens": len(target_kept_ids),
                    }
                )
                print(
                    f"[{episode['episode_name']}] {prompt_item['id']} "
                    f"suffix_tokens={len(suffix_token_ids)}"
                )
    finally:
        recorder.cleanup()

    payload = {
        "metadata": {
            "model_name": args.model_name,
            "episodes_file": str(episodes_path.name),
            "panel_file": str(panel_path.name),
            "target_layers": list(args.target_layers),
            "max_length": int(args.max_length),
            "user_label": args.user_label,
            "assistant_label": args.assistant_label,
            "sample_count": len(samples),
        },
        "samples": samples,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, output_path)
    print(f"Saved prompt-suffix trace dataset to {output_path}")


if __name__ == "__main__":
    main(build_arg_parser().parse_args())
