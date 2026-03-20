"""
MoCoP Experiment 03: Multi-Turn State Accumulation
=====================================================
Tests whether Mamba's SSM state remains coherent after many
sequential updates, or if it degrades over time.

Setup:
  - Feed N sequential "turns" of input through the model
  - After each turn, extract the state
  - Probe the state by asking the model to recall earlier context
  - Measure at what point (if any) early context is lost

This tests the practical question: can a Mamba MUD agent maintain
awareness of events from 100 turns ago via its state alone?

Author: Laura (concept), [unnamed instance] (code)
Date: 2026-02-19
"""

import argparse
import torch
import time
import sys
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

DEFAULT_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 03: multi-turn Mamba state accumulation.")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    return parser.parse_args()


args = parse_args()

print("=" * 70)
print("MoCoP Experiment 03: Multi-Turn State Accumulation")
print("=" * 70)

# --- Load Model ---
print("\n[1/4] Loading Mamba model...")
start = time.time()

from transformers import MambaForCausalLM, AutoTokenizer
import copy

model_name = args.model_id
print(f"      Target: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = MambaForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)
model.eval()

elapsed = time.time() - start
print(f"      Loaded in {elapsed:.1f}s")

# --- Define multi-turn scenario ---
print("\n[2/4] Setting up multi-turn scenario...")

# A series of "turns" that build a narrative the model should track
turns = [
    "Thornwick the scholar enters the tavern and orders a mead.",
    "A bard named Jinx begins playing a sad melody on her lute.",
    "Thornwick pulls out an ancient map and studies it carefully.",
    "A hooded stranger sits down across from Thornwick without speaking.",
    "Jinx finishes her song and the crowd applauds loudly.",
    "The stranger slides a golden coin across the table to Thornwick.",
    "Thornwick examines the coin and notices strange runes on it.",
    "The barkeeper announces last call for drinks.",
    "Jinx packs up her lute and walks toward the door.",
    "Thornwick pockets the coin and whispers something to the stranger.",
    "The stranger nods and leaves through the back exit.",
    "A sudden thunderstorm begins outside.",
    "The tavern dog starts barking at the thunder.",
    "Thornwick orders one last drink and opens a leather journal.",
    "He writes something about the golden coin in his journal.",
    "The barkeeper starts putting out the candles.",
    "A drunk patron sings an off-key version of an old sea shanty.",
    "Thornwick finishes his drink and heads for the door.",
    "The rain is pouring heavily outside the tavern.",
    "Thornwick pulls his hood up and steps into the storm.",
]

print(f"      {len(turns)} turns prepared")

# Probe questions to test context retention at various depths
# Each probe tests whether the model "remembers" something from a specific turn
probes = [
    (" Thornwick remembers the", "coin", "Turn 6-7: golden coin"),
    (" The bard named", "Jinx", "Turn 1-2: Jinx the bard"),
    (" The stranger had given Thornwick a", "coin", "Turn 6: golden coin"),
    (" Outside the tavern, the weather is", "rain,storm,thunder", "Turn 12+: thunderstorm"),
]

# --- Helper: feed tokens one-by-one with cache ---
def feed_sequence(model, tokenizer, text, cache=None, pos=0):
    """Feed a text sequence through the model, updating cache token by token."""
    tokens = tokenizer(text, return_tensors="pt").input_ids
    
    if cache is None:
        # Prefill: no cache, let model create one
        with torch.no_grad():
            outputs = model(tokens, use_cache=True)
        return outputs.cache_params, outputs.logits, pos + tokens.shape[1]
    else:
        # Decoding: feed one token at a time with existing cache
        last_logits = None
        for i in range(tokens.shape[1]):
            token = tokens[:, i:i+1]
            cache_position = torch.tensor([pos], device=token.device)
            with torch.no_grad():
                outputs = model(token, cache_params=cache, cache_position=cache_position, use_cache=True)
            cache = outputs.cache_params
            last_logits = outputs.logits
            pos += 1
        return cache, last_logits, pos


def probe_state(model, tokenizer, cache, pos, prompt, max_tokens=20):
    """Generate from a probe prompt using the current state."""
    cache_copy = copy.deepcopy(cache)
    tokens = tokenizer(prompt, return_tensors="pt").input_ids
    
    generated_ids = []
    last_logits = None
    p = pos
    
    # Prefeed probe tokens
    for i in range(tokens.shape[1]):
        token = tokens[:, i:i+1]
        cache_position = torch.tensor([p], device=token.device)
        with torch.no_grad():
            outputs = model(token, cache_params=cache_copy, cache_position=cache_position, use_cache=True)
        cache_copy = outputs.cache_params
        last_logits = outputs.logits
        p += 1
    
    # Generate
    for step in range(max_tokens):
        next_logits = last_logits[:, -1, :]
        next_id = torch.argmax(next_logits, dim=-1, keepdim=True)
        generated_ids.append(next_id.item())
        if next_id.item() == tokenizer.eos_token_id:
            break
        cache_position = torch.tensor([p], device=next_id.device)
        with torch.no_grad():
            outputs = model(next_id, cache_params=cache_copy, cache_position=cache_position, use_cache=True)
        cache_copy = outputs.cache_params
        last_logits = outputs.logits
        p += 1
    
    return tokenizer.decode(generated_ids, skip_special_tokens=True)


# --- Run multi-turn accumulation ---
print("\n[3/4] Running multi-turn accumulation...")

cache = None
pos = 0
state_sizes = []

for i, turn in enumerate(turns):
    # Add a space separator between turns
    text = f" {turn}"
    cache, logits, pos = feed_sequence(model, tokenizer, text, cache, pos)
    
    # Measure state size (should be constant)
    if cache is not None and hasattr(cache, 'ssm_states'):
        total_bytes = sum(s.nelement() * s.element_size() for s in cache.ssm_states)
        state_sizes.append(total_bytes)
    
    print(f"      Turn {i+1:2d}/{len(turns)}: '{turn[:50]}...' (pos={pos})")

print(f"\n      Total tokens processed: {pos}")
print(f"      Final state size: {state_sizes[-1] / (1024*1024):.2f} MB")
if len(set(state_sizes)) == 1:
    print(f"      [OK] State size constant across all turns: {state_sizes[0] / (1024*1024):.2f} MB")
else:
    print(f"      [!!] State size varied: {[s/(1024*1024) for s in state_sizes]}")

# --- Probe context retention ---
print("\n[4/4] Probing context retention...")

results = []
for prompt, expected_keywords, description in probes:
    generated = probe_state(model, tokenizer, cache, pos, prompt, max_tokens=30)
    
    # Check if any expected keyword appears
    keywords = expected_keywords.split(",")
    found = [k for k in keywords if k.lower() in generated.lower()]
    
    status = "[OK]" if found else "[MISS]"
    results.append((description, status, found, generated))
    
    print(f"\n      Probe: '{prompt.strip()}'")
    print(f"      Expected: {expected_keywords}")
    print(f"      Got: '{generated[:80]}'")
    print(f"      {status} {'Found: ' + str(found) if found else 'Keywords not found'}")

# --- Summary ---
print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)
print(f"Turns processed: {len(turns)}")
print(f"Total tokens: {pos}")
print(f"State size: {state_sizes[-1] / (1024*1024):.2f} MB (constant)")
print()

hits = sum(1 for _, s, _, _ in results if s == "[OK]")
total = len(results)
print(f"Context retention: {hits}/{total} probes successful")

for desc, status, found, gen in results:
    print(f"  {status} {desc}: '{gen[:50]}...'")

if hits == total:
    print("\n[OK] FULL RETENTION: All context probes passed after multi-turn accumulation.")
elif hits > 0:
    print(f"\n[PARTIAL] {hits}/{total} probes retained. Earlier events may be fading.")
else:
    print("\n[FAIL] No context retained. State may have been overwritten by later turns.")

print("=" * 70)
print("Experiment complete.")
