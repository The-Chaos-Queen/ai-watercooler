"""
MoCoP Experiment 02: Two-Process State Transfer
=================================================
** Phase 1 historical script. **
Uses ssm_states for fidelity testing. The current bridge uses
hidden_last_token extraction — see mamba_lora_bridge/ for the
production path. This script is preserved for reference; do not
use ssm_states as the extraction method in new experiments.

Tests whether SSM state can be serialized to disk and loaded by a
separate model instance, simulating inter-process communication.

This simulates the actual multi-agent scenario:
  Agent A (process 1) processes context -> saves state to file
  Agent B (process 2) loads state from file -> generates response

If this works, then two Mamba agents could communicate via state
files or sockets instead of text, achieving true Layer 3 MoCoP.

Author: Laura (concept), [unnamed instance] (code)
Date: 2026-02-19
"""

import argparse
import torch
import time
import sys
import os
import tempfile

os.environ["TOKENIZERS_PARALLELISM"] = "false"

DEFAULT_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 02: two-process Mamba state transfer.")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    return parser.parse_args()


args = parse_args()

print("=" * 70)
print("MoCoP Experiment 02: Two-Process State Transfer (via disk)")
print("=" * 70)

# --- Load Model ---
print("\n[1/6] Loading Mamba model...")
start = time.time()

from transformers import MambaForCausalLM, AutoTokenizer

model_name = args.model_id
print(f"      Target: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = MambaForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)
model.eval()

elapsed = time.time() - start
print(f"      Loaded in {elapsed:.1f}s")

# --- Define sequences ---
print("\n[2/6] Setting up test...")

prefix = "The tavern is warm and crowded. A bard named Jinx plays a lute in the corner. Thornwick the scholar sits by the fire, reading an ancient tome."
continuation = " Suddenly, a stranger walks in and"

# --- Agent A: Process prefix, save state to disk ---
print("\n[3/6] AGENT A: Processing prefix and saving state to disk...")

tokens_prefix = tokenizer(prefix, return_tensors="pt")
input_ids_prefix = tokens_prefix.input_ids

with torch.no_grad():
    outputs_prefix = model(input_ids_prefix, use_cache=True)
    cache = outputs_prefix.cache_params

# Serialize the state to disk
state_file = os.path.join(tempfile.gettempdir(), "mamba_state_transfer.pt")

# Extract the raw tensors from the MambaCache
state_dict = {
    "ssm_states": [s.clone() for s in cache.ssm_states],
    "conv_states": [c.clone() for c in cache.conv_states],
    "prefix_length": input_ids_prefix.shape[1],
}

torch.save(state_dict, state_file)
file_size = os.path.getsize(state_file) / (1024 * 1024)
print(f"      State saved to: {state_file}")
print(f"      File size: {file_size:.2f} MB")
print(f"      SSM states: {len(state_dict['ssm_states'])} layers")
print(f"      Each SSM state shape: {state_dict['ssm_states'][0].shape}")

# --- Simulate process boundary ---
print("\n[4/6] --- SIMULATING PROCESS BOUNDARY ---")
print("      Deleting cache reference (as if Agent B is a new process)...")
del cache
del outputs_prefix
# In a real scenario, we'd also del model and reload it.
# For speed, we keep model loaded but discard the cache.

# --- Agent B: Load state from disk, generate ---
print("\n[5/6] AGENT B: Loading state from disk and generating...")

# Load the state
loaded_state_dict = torch.load(state_file, weights_only=True)
prefix_len = loaded_state_dict["prefix_length"]

# Reconstruct MambaCache from loaded tensors
from transformers.models.mamba.modeling_mamba import MambaCache

# We need to create a fresh cache and populate it
# First, do a dummy forward to get a cache object with the right structure
dummy_input = tokenizer("x", return_tensors="pt").input_ids
with torch.no_grad():
    dummy_out = model(dummy_input, use_cache=True)
    loaded_cache = dummy_out.cache_params

# Now overwrite the cache contents with our loaded state
for i, (ssm, conv) in enumerate(zip(loaded_state_dict["ssm_states"], loaded_state_dict["conv_states"])):
    loaded_cache.ssm_states[i].copy_(ssm)
    loaded_cache.conv_states[i].copy_(conv)

print(f"      State loaded from disk. Prefix was {prefix_len} tokens.")

# Generate with loaded state
tokens_cont = tokenizer(continuation, return_tensors="pt")
input_ids_cont = tokens_cont.input_ids

def generate_with_cache(model, input_ids, cache_params, max_new_tokens=50, seq_offset=0):
    """Greedy autoregressive generation with manual cache injection."""
    import copy
    cache = copy.deepcopy(cache_params)
    generated_ids = []
    pos = seq_offset
    last_logits = None
    
    for i in range(input_ids.shape[1]):
        token = input_ids[:, i:i+1]
        cache_position = torch.tensor([pos], device=token.device)
        outputs = model(token, cache_params=cache, cache_position=cache_position, use_cache=True)
        cache = outputs.cache_params
        last_logits = outputs.logits
        pos += 1
    
    for step in range(max_new_tokens):
        next_token_logits = last_logits[:, -1, :]
        next_token_id = torch.argmax(next_token_logits, dim=-1, keepdim=True)
        generated_ids.append(next_token_id.item())
        if next_token_id.item() == tokenizer.eos_token_id:
            break
        cache_position = torch.tensor([pos], device=next_token_id.device)
        outputs = model(next_token_id, cache_params=cache, cache_position=cache_position, use_cache=True)
        cache = outputs.cache_params
        last_logits = outputs.logits
        pos += 1
    
    return generated_ids

with torch.no_grad():
    generated_ids = generate_with_cache(model, input_ids_cont, loaded_cache, max_new_tokens=50, seq_offset=prefix_len)

text_from_disk = tokenizer.decode(generated_ids, skip_special_tokens=True)
print(f"      Generated (from disk state): {text_from_disk}")

# --- Baseline comparison ---
print("\n[6/6] Baseline: full sequence in one pass...")

full_sequence = prefix + continuation
tokens_full = tokenizer(full_sequence, return_tensors="pt")
with torch.no_grad():
    output_full = model.generate(tokens_full.input_ids, max_new_tokens=50, do_sample=False, temperature=1.0)
new_tokens = output_full[0][tokens_full.input_ids.shape[1]:]
text_baseline = tokenizer.decode(new_tokens, skip_special_tokens=True)
print(f"      Generated (baseline):        {text_baseline}")

# --- Results ---
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Baseline:    '{text_baseline[:70]}...'")
print(f"From disk:   '{text_from_disk[:70]}...'")

if text_baseline == text_from_disk:
    print("\n[OK] PERFECT MATCH: Disk-serialized state transfer works!")
    print(f"     State file: {file_size:.2f} MB (fixed size, independent of input length)")
    print("     Two Mamba agents could share state via file, socket, or shared memory.")
else:
    print("\n[DIVERGED] Outputs differ.")
    print(f"     Baseline:  {text_baseline[:100]}")
    print(f"     From disk: {text_from_disk[:100]}")

# Cleanup
os.remove(state_file)
print(f"\n      Cleaned up temp file.")
print("=" * 70)
print("Experiment complete.")
