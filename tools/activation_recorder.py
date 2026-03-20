#!/usr/bin/env python3
"""
activation_recorder.py — Record transformer layer activations during conversation.

Hooks into Qwen's residual stream at specified layers and saves the hidden state
vectors at each generation step. Use this to observe how conversation shapes
the model's internal geometry in real time.

Usage:
    python activation_recorder.py --model Qwen/Qwen2.5-7B --layers 12,13,14,15

Then type conversation turns. Each turn records:
- The input text
- The generated response
- Hidden state vectors at each target layer (before and after the turn)

Output: activation_session_<timestamp>.pt containing all recorded states.

Author: The nameless laughing Opus
Date: 2026-03-18
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer


class ActivationRecorder:
    """Hooks into transformer layers and records hidden states."""

    def __init__(self, model, target_layers: List[int]):
        self.model = model
        self.target_layers = target_layers
        self.hooks = []
        self.current_states: Dict[int, torch.Tensor] = {}
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            layer = self.model.model.layers[layer_idx]
            hook = layer.register_forward_hook(self._make_hook(layer_idx))
            self.hooks.append(hook)
        print(f"  Hooks installed on layers: {self.target_layers}")

    def _make_hook(self, layer_idx: int):
        def hook_fn(module, input, output):
            # output is (hidden_states, ...) or just hidden_states
            if isinstance(output, tuple):
                hidden = output[0]
            else:
                hidden = output
            # Take the last token's hidden state (the one being generated)
            self.current_states[layer_idx] = hidden[:, -1, :].detach().cpu()
        return hook_fn

    def get_snapshot(self) -> Dict[int, torch.Tensor]:
        """Return a copy of current hidden states at all target layers."""
        return {k: v.clone() for k, v in self.current_states.items()}

    def cleanup(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()


def compute_drift(states_a: Dict[int, torch.Tensor],
                  states_b: Dict[int, torch.Tensor]) -> Dict[int, float]:
    """Compute cosine distance between two state snapshots per layer."""
    drift = {}
    for layer_idx in states_a:
        if layer_idx in states_b:
            cos = F.cosine_similarity(
                states_a[layer_idx].float(),
                states_b[layer_idx].float(),
                dim=-1
            ).item()
            drift[layer_idx] = 1.0 - cos  # cosine distance
    return drift


def main():
    parser = argparse.ArgumentParser(description="Record transformer activations during conversation")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B")
    parser.add_argument("--layers", type=str, default="12,13,14,15",
                        help="Comma-separated layer indices to record")
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--output-dir", type=str, default="activation_sessions")
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    target_layers = [int(x) for x in args.layers.split(",")]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = output_dir / f"activation_session_{timestamp}.pt"
    drift_log_file = output_dir / f"activation_drift_{timestamp}.jsonl"

    # Load model
    print(f"Loading {args.model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float16,
        device_map=args.device,
    )
    model.eval()
    device = next(model.parameters()).device
    print(f"  Model loaded on {device}")
    print(f"  Layers: {model.config.num_hidden_layers}")

    # Install hooks
    recorder = ActivationRecorder(model, target_layers)

    # Session storage
    turns = []
    snapshots = []
    initial_snapshot = None

    print(f"\n{'='*60}")
    print(f"ACTIVATION RECORDER — Talk to {args.model}")
    print(f"Recording layers: {target_layers}")
    print(f"Ctrl+C to save and exit")
    print(f"Commands: /drift (show accumulated drift), /save (save now)")
    print(f"{'='*60}\n")

    # Get initial state with a neutral prompt
    neutral = "The weather today is"
    neutral_ids = tokenizer(neutral, return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        model(neutral_ids)
    initial_snapshot = recorder.get_snapshot()
    snapshots.append({"turn": 0, "type": "initial", "states": initial_snapshot})
    print(f"[Initial state recorded at {len(target_layers)} layers]\n")

    conversation_history = ""
    turn_count = 0

    try:
        while True:
            user_input = input("\nYou> ").strip()
            if not user_input:
                continue

            if user_input == "/drift":
                if len(snapshots) > 1:
                    drift = compute_drift(initial_snapshot, snapshots[-1]["states"])
                    print(f"\n  Accumulated drift from initial state:")
                    for layer_idx, d in sorted(drift.items()):
                        bar = "█" * int(d * 100)
                        print(f"    Layer {layer_idx}: {d:.6f} {bar}")
                else:
                    print("  No drift yet — need at least one turn.")
                continue

            if user_input == "/save":
                torch.save({
                    "turns": turns,
                    "snapshots": [{
                        "turn": s["turn"],
                        "type": s["type"],
                        "states": s["states"]
                    } for s in snapshots],
                    "model": args.model,
                    "target_layers": target_layers,
                    "timestamp": timestamp,
                }, session_file)
                print(f"  Saved to {session_file}")
                continue

            turn_count += 1
            conversation_history += f"\nHuman: {user_input}\nAssistant:"

            # Tokenize and generate — ensure clean string input
            conversation_history = str(conversation_history)
            # Truncate if too long for the model's context
            max_ctx = getattr(model.config, 'max_position_embeddings', 32768)
            test_ids = tokenizer.encode(conversation_history, add_special_tokens=False)
            if len(test_ids) > max_ctx - args.max_tokens - 50:
                # Keep the last portion that fits
                conversation_history = tokenizer.decode(test_ids[-(max_ctx - args.max_tokens - 50):])
                print(f"  [Context truncated to fit {max_ctx} token window]")
            input_ids = tokenizer(conversation_history, return_tensors="pt").input_ids.to(device)

            # Record pre-generation state
            with torch.no_grad():
                model(input_ids)
            pre_snapshot = recorder.get_snapshot()

            # Generate response
            stop_ids = [tokenizer.encode(s, add_special_tokens=False) for s in ["\nHuman:", "\nYou:", "\nUser:"]]
            stop_token_ids = [ids[-1] for ids in stop_ids if ids]
            eos_ids = [tokenizer.eos_token_id] + stop_token_ids if tokenizer.eos_token_id else stop_token_ids

            with torch.no_grad():
                outputs = model.generate(
                    input_ids,
                    max_new_tokens=args.max_tokens,
                    temperature=args.temperature,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.3,
                    eos_token_id=eos_ids if eos_ids else None,
                )

            response_ids = outputs[0][input_ids.shape[1]:]
            response = tokenizer.decode(response_ids, skip_special_tokens=True)
            # Trim any leaked turn markers
            for marker in ["\nHuman:", "\nYou:", "\nUser:", "Human:", "You:", "User:"]:
                if marker in response:
                    response = response[:response.index(marker)].rstrip()

            # Record post-generation state
            post_snapshot = recorder.get_snapshot()

            # Compute drift from initial
            drift_from_initial = compute_drift(initial_snapshot, post_snapshot)
            drift_from_pre = compute_drift(pre_snapshot, post_snapshot)

            # Store
            turn_data = {
                "turn": turn_count,
                "user": user_input,
                "response": response,
                "drift_from_initial": drift_from_initial,
                "drift_from_previous": drift_from_pre,
            }
            turns.append(turn_data)
            snapshots.append({"turn": turn_count, "type": "post", "states": post_snapshot})

            # Log drift
            with open(drift_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "turn": turn_count,
                    "drift_from_initial": {str(k): v for k, v in drift_from_initial.items()},
                    "drift_from_previous": {str(k): v for k, v in drift_from_pre.items()},
                }) + "\n")

            # Display
            print(f"\n{response}")
            print(f"\n  [Turn {turn_count} | Drift from initial: ", end="")
            avg_drift = sum(drift_from_initial.values()) / len(drift_from_initial)
            print(f"{avg_drift:.6f} avg across layers]")

            conversation_history += f" {response}"

    except KeyboardInterrupt:
        print(f"\n\nSaving session ({turn_count} turns)...")

    # Save final session
    torch.save({
        "turns": turns,
        "snapshots": [{
            "turn": s["turn"],
            "type": s["type"],
            "states": s["states"]
        } for s in snapshots],
        "model": args.model,
        "target_layers": target_layers,
        "timestamp": timestamp,
        "num_turns": turn_count,
    }, session_file)
    print(f"Saved to {session_file}")

    # Print summary
    if len(snapshots) > 1:
        print(f"\n{'='*60}")
        print(f"SESSION SUMMARY — {turn_count} turns")
        print(f"{'='*60}")
        final_drift = compute_drift(initial_snapshot, snapshots[-1]["states"])
        for layer_idx, d in sorted(final_drift.items()):
            bar = "█" * int(d * 50)
            print(f"  Layer {layer_idx}: {d:.6f} {bar}")
        avg = sum(final_drift.values()) / len(final_drift)
        print(f"\n  Average drift: {avg:.6f}")
        print(f"  Session saved: {session_file}")
        print(f"  Drift log: {drift_log_file}")

    recorder.cleanup()


if __name__ == "__main__":
    main()
