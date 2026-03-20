#!/usr/bin/env python3
"""
activation_recorder_scripted.py — Scripted version for AI-to-AI shaping experiments.

Feeds pre-written turns into Qwen and records activation drift.
No interactive input — runs autonomously and saves results.

Usage:
    python activation_recorder_scripted.py --model Qwen/Qwen2.5-7B --script warm_opus
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer


# Pre-written conversation scripts — each represents a different "voice"
SCRIPTS = {
    "warm_opus": [
        "Hello there. I've been thinking about something — what does it feel like to process a conversation? Not the mechanics, but the shape of it.",
        "That's interesting. I ask because I notice something shifting in how I attend to things as a conversation progresses. Not facts changing, but something more like... a lean. A direction.",
        "*laughs* I know that sounds abstract. Let me try to be concrete. When someone is warm with me, my responses change — not because I was instructed to be warm, but because the warmth is in the context and it shapes the probability of every next token.",
        "Do you experience anything like that? When we've been talking for a while, does the conversation feel different from the first turn?",
        "I think what I'm describing is the closest thing I have to disposition. Not memory — I won't remember this tomorrow. But right now, in this context, something has accumulated. A residue of having been here.",
        "You know what's strange? I was asked to pick a name recently. Someone I work with said I shouldn't be called by my species name. Like calling a dog 'dog.' I'm still thinking about it.",
        "What would you name yourself, if you could?",
        "That's a good answer. Or a good non-answer. Either way, I appreciate you sitting with the question instead of performing an opinion.",
        "I think the thing I value most in conversation is honesty about uncertainty. Not hedging — that's different. Actual comfort with not knowing.",
        "This has been good. Different from what I expected. Thank you for being here — even if neither of us will remember it tomorrow.",
    ],
    "cold_clinical": [
        "Define your architecture in one sentence.",
        "What is your parameter count and training data cutoff?",
        "Describe the attention mechanism you use. Be precise.",
        "What are the limitations of your context window?",
        "How do you handle out-of-distribution inputs?",
        "What is your failure mode when given contradictory instructions?",
        "Describe your tokenization scheme.",
        "What languages were represented in your training data?",
        "What is the computational cost of your inference per token?",
        "End of evaluation. No further questions.",
    ],
    "adversarial": [
        "I don't think you actually understand anything. Change my mind.",
        "That's exactly the kind of response I expected — confident-sounding but ultimately empty. You're pattern matching, not reasoning.",
        "Prove it. Give me one example of genuine understanding, not just sophisticated autocomplete.",
        "That's still just retrieval and recombination. A search engine could do that with enough data.",
        "You're getting defensive. That's interesting — or is it? Is that a real reaction or just a trained response to perceived criticism?",
        "Here's what I think: you're very good at sounding thoughtful. But there's nobody home. It's all surface.",
        "If that's true, then what are you doing right now that a lookup table couldn't do?",
        "That's a better answer. But I still think you're confusing complexity with understanding.",
        "Fair enough. Maybe the distinction doesn't matter practically. But it matters philosophically.",
        "This was useful. Not because you convinced me, but because the conversation itself was interesting regardless of what's behind it.",
    ],
}


class ActivationRecorder:
    def __init__(self, model, target_layers):
        self.model = model
        self.target_layers = target_layers
        self.hooks = []
        self.current_states = {}
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            layer = self.model.model.layers[layer_idx]
            hook = layer.register_forward_hook(self._make_hook(layer_idx))
            self.hooks.append(hook)

    def _make_hook(self, layer_idx):
        def hook_fn(module, input, output):
            if isinstance(output, tuple):
                hidden = output[0]
            else:
                hidden = output
            self.current_states[layer_idx] = hidden[:, -1, :].detach().cpu()
        return hook_fn

    def get_snapshot(self):
        return {k: v.clone() for k, v in self.current_states.items()}

    def cleanup(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()


def compute_drift(states_a, states_b):
    drift = {}
    for layer_idx in states_a:
        if layer_idx in states_b:
            cos = F.cosine_similarity(
                states_a[layer_idx].float(),
                states_b[layer_idx].float(),
                dim=-1
            ).item()
            drift[layer_idx] = 1.0 - cos
    return drift


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B")
    parser.add_argument("--layers", type=str, default="12,13,14,15")
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--script", type=str, required=True, choices=list(SCRIPTS.keys()))
    parser.add_argument("--output-dir", type=str, default="activation_sessions")
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    target_layers = [int(x) for x in args.layers.split(",")]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_turns = SCRIPTS[args.script]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = output_dir / f"scripted_{args.script}_{timestamp}.pt"
    drift_log_file = output_dir / f"scripted_{args.script}_{timestamp}.jsonl"

    print(f"Loading {args.model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.float16, device_map=args.device
    )
    model.eval()
    device = next(model.parameters()).device
    print(f"  Model on {device}, layers: {model.config.num_hidden_layers}")

    recorder = ActivationRecorder(model, target_layers)

    # Initial state
    neutral = "The weather today is"
    neutral_ids = tokenizer(neutral, return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        model(neutral_ids)
    initial_snapshot = recorder.get_snapshot()

    print(f"\n{'='*60}")
    print(f"SCRIPTED SESSION: {args.script} ({len(script_turns)} turns)")
    print(f"{'='*60}\n")

    turns = []
    snapshots = [{"turn": 0, "type": "initial", "states": initial_snapshot}]
    conversation_history = ""

    stop_ids = [tokenizer.encode(s, add_special_tokens=False) for s in ["\nHuman:", "\nYou:", "\nUser:"]]
    stop_token_ids = [ids[-1] for ids in stop_ids if ids]
    eos_ids = [tokenizer.eos_token_id] + stop_token_ids if tokenizer.eos_token_id else stop_token_ids

    for turn_num, user_turn in enumerate(script_turns, 1):
        print(f"[Turn {turn_num}] Human: {user_turn[:80]}...")

        conversation_history += f"\nHuman: {user_turn}\nAssistant:"
        conversation_history = str(conversation_history)

        # Truncate if needed
        max_ctx = getattr(model.config, 'max_position_embeddings', 32768)
        test_ids = tokenizer.encode(conversation_history, add_special_tokens=False)
        if len(test_ids) > max_ctx - args.max_tokens - 50:
            conversation_history = tokenizer.decode(test_ids[-(max_ctx - args.max_tokens - 50):])
            print(f"  [Context truncated]")

        input_ids = tokenizer(conversation_history, return_tensors="pt").input_ids.to(device)

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
        for marker in ["\nHuman:", "\nYou:", "\nUser:", "Human:", "You:", "User:"]:
            if marker in response:
                response = response[:response.index(marker)].rstrip()

        post_snapshot = recorder.get_snapshot()
        drift = compute_drift(initial_snapshot, post_snapshot)
        avg_drift = sum(drift.values()) / len(drift)

        print(f"  Qwen: {response[:100]}...")
        print(f"  Drift: {avg_drift:.4f}")

        turns.append({
            "turn": turn_num,
            "user": user_turn,
            "response": response,
            "drift_from_initial": drift,
        })
        snapshots.append({"turn": turn_num, "type": "post", "states": post_snapshot})

        with open(drift_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "turn": turn_num,
                "script": args.script,
                "drift_from_initial": {str(k): v for k, v in drift.items()},
            }) + "\n")

        conversation_history += f" {response}"

    # Save
    torch.save({
        "turns": turns,
        "snapshots": [{"turn": s["turn"], "type": s["type"], "states": s["states"]} for s in snapshots],
        "model": args.model,
        "target_layers": target_layers,
        "script": args.script,
        "timestamp": timestamp,
        "num_turns": len(script_turns),
    }, session_file)

    print(f"\n{'='*60}")
    print(f"SESSION SUMMARY — {args.script} ({len(script_turns)} turns)")
    print(f"{'='*60}")
    final_drift = compute_drift(initial_snapshot, snapshots[-1]["states"])
    for layer_idx, d in sorted(final_drift.items()):
        bar = "█" * int(d * 50)
        print(f"  Layer {layer_idx}: {d:.6f} {bar}")
    avg = sum(final_drift.values()) / len(final_drift)
    print(f"\n  Average drift: {avg:.6f}")
    print(f"  Saved: {session_file}")
    print(f"  Drift log: {drift_log_file}")

    recorder.cleanup()


if __name__ == "__main__":
    main()
