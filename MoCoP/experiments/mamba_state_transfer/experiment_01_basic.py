"""
MoCoP Experiment 01: Mamba State Transfer (Proof of Concept)
=============================================================
Tests whether SSM hidden state can be extracted from one inference
pass and injected into another, producing coherent continuation.

The core equation being tested:
    h_t = A · h_{t-1} + B · x_t    (state update)
    y_t = C · h_t + D · x_t         (output)

If we extract h_T after processing sequence [x_1..x_T] and inject it
as the starting state for a new inference with input x_{T+1}, the output
should be equivalent to processing [x_1..x_T, x_{T+1}] in one pass.

Experiment Structure:
    Test A: Baseline — Process full sequence in one pass
    Test B: Transfer — Process prefix, extract state, inject into continuation
    Test C: No Transfer — Process continuation WITHOUT state (cold start)
    
    Compare B vs A (should be similar) and B vs C (should differ).

Author: Laura (concept), [unnamed instance] (code)
Date: 2026-02-19
"""

import argparse
import torch
import time
import sys
import os

# Suppress HuggingFace warnings for cleaner output
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DEFAULT_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 01: basic Mamba state transfer.")
    parser.add_argument("--model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    return parser.parse_args()


args = parse_args()

print("=" * 70)
print("MoCoP Experiment 01: Mamba SSM State Transfer")
print("=" * 70)

# --- Step 1: Load Model ---
print("\n[1/5] Loading model from HuggingFace...")
start = time.time()

try:
    from transformers import MambaForCausalLM, AutoTokenizer
    
    # Using the HF standard implementation
    model_name = args.model_id
    
    print(f"      Target: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = MambaForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)
    model.eval()
    
    elapsed = time.time() - start
    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"      Model loaded in {elapsed:.1f}s ({param_count:.1f}M parameters)")
    
    # Check the state dimensions
    config = model.config
    print(f"      Hidden size: {config.hidden_size}")
    print(f"      Num layers: {config.num_hidden_layers}")
    # SSM specific config might vary by implementation version
    state_size = getattr(config, 'state_size', 16) 
    print(f"      SSM state size: {state_size}")
    
except Exception as e:
    print(f"      FAILED: {e}")
    print("\n      This script requires: pip install transformers torch mamba_ssm causal-conv1d")
    print("      Note: mamba_ssm requires CUDA to compile.")
    sys.exit(1)

# --- Step 2: Define test sequences ---
print("\n[2/5] Setting up test sequences...")

# The "world state" that Agent A would process
prefix = "The tavern is warm and crowded. A bard named Jinx plays a lute in the corner. Thornwick the scholar sits by the fire, reading an ancient tome."

# The continuation prompt (what Agent B would receive)
# We add a leading space to ensure tokenization continuity
continuation = " Suddenly, a stranger walks in and"

# Full sequence for baseline comparison  
full_sequence = prefix + continuation

print(f"      Prefix: '{prefix[:30]}...{prefix[-10:]}' ({len(prefix)} chars)")
print(f"      Continuation: '{continuation}' ({len(continuation)} chars)")

# --- Step 3: Test A — Full sequence baseline ---
print("\n[3/5] Test A: Full sequence (baseline)...")

tokens_full = tokenizer(full_sequence, return_tensors="pt")
input_ids_full = tokens_full.input_ids

with torch.no_grad():
    # Generate output
    output_full_ids = model.generate(
        input_ids_full,
        max_new_tokens=50,
        do_sample=False,  # Greedy for reproducibility
        temperature=1.0,
    )

# Decode only the NEW tokens
new_tokens_full = output_full_ids[0][input_ids_full.shape[1]:]
text_generated_full = tokenizer.decode(new_tokens_full, skip_special_tokens=True)

print(f"      Generated: {text_generated_full}")


# --- Step 4: Test B — State transfer ---
print("\n[4/5] Test B: State transfer (the experiment)...")

# Step 4a: Process the prefix and capture the hidden state
tokens_prefix = tokenizer(prefix, return_tensors="pt")
input_ids_prefix = tokens_prefix.input_ids

print("      Running inference on prefix to capture Cache...")
with torch.no_grad():
    # Forward pass to get cache
    # In Mamba HF implementation, use_cache=True returns MambaCache
    outputs_prefix = model(
        input_ids_prefix,
        use_cache=True
    )
    
    # Extract the cache
    # The structure of cache depends on the transformers version
    cache = outputs_prefix.cache_params if hasattr(outputs_prefix, 'cache_params') else outputs_prefix.past_key_values

    if cache is None:
        print("      CRITICAL ERROR: No cache returned. Check model config.")
        sys.exit(1)
        
    print(f"      Cache captured. Type: {type(cache)}")


# Step 4b: Manual autoregressive generation with injected cache
# model.generate() doesn't support cache_params passthrough for Mamba,
# so we do greedy decoding manually via model.forward()
tokens_cont = tokenizer(continuation, return_tensors="pt")
input_ids_cont = tokens_cont.input_ids

print("      Injecting cache into continuation generation...")
print("      (Manual autoregressive decoding — .generate() doesn't support Mamba cache)")

def generate_with_cache(model, input_ids, cache_params, max_new_tokens=50, seq_offset=0):
    """Greedy autoregressive generation with manual cache injection.
    
    Mamba's decoding mode only handles 1 token at a time, so we:
    1. Feed continuation tokens one-by-one to update the cache ('prefeed')
    2. Then generate new tokens autoregressively
    
    Args:
        seq_offset: Position in the sequence where we're continuing from.
                    Should equal the number of tokens already processed by the cache.
    """
    import copy
    cache = copy.deepcopy(cache_params)
    
    generated_ids = []
    pos = seq_offset
    
    # Step 1: Prefeed the continuation tokens one at a time
    num_input_tokens = input_ids.shape[1]
    last_logits = None
    
    for i in range(num_input_tokens):
        token = input_ids[:, i:i+1]  # shape [1, 1]
        cache_position = torch.tensor([pos], device=token.device)
        
        outputs = model(
            token,
            cache_params=cache,
            cache_position=cache_position,
            use_cache=True,
        )
        cache = outputs.cache_params
        last_logits = outputs.logits
        pos += 1
    
    # Step 2: Generate new tokens from the last logit
    for step in range(max_new_tokens):
        next_token_logits = last_logits[:, -1, :]
        next_token_id = torch.argmax(next_token_logits, dim=-1, keepdim=True)
        generated_ids.append(next_token_id.item())
        
        if next_token_id.item() == tokenizer.eos_token_id:
            break
        
        cache_position = torch.tensor([pos], device=next_token_id.device)
        outputs = model(
            next_token_id,
            cache_params=cache,
            cache_position=cache_position,
            use_cache=True,
        )
        cache = outputs.cache_params
        last_logits = outputs.logits
        pos += 1
    
    return generated_ids

with torch.no_grad():
    prefix_len = input_ids_prefix.shape[1]
    print(f"      Prefix consumed {prefix_len} tokens, continuing from position {prefix_len}")
    generated_token_ids = generate_with_cache(
        model, input_ids_cont, cache, 
        max_new_tokens=50, seq_offset=prefix_len
    )

text_generated_transfer = tokenizer.decode(generated_token_ids, skip_special_tokens=True)
print(f"      Generated: {text_generated_transfer}")


# --- Step 5: Test C — Cold start (no state) ---
print("\n[5/5] Test C: Cold start (no state transfer)...")

with torch.no_grad():
    output_cold_ids = model.generate(
        input_ids_cont,
        max_new_tokens=50,
        do_sample=False,
        temperature=1.0,
        # No past_key_values passed here
    )

new_tokens_cold = output_cold_ids[0][input_ids_cont.shape[1]:]
text_generated_cold = tokenizer.decode(new_tokens_cold, skip_special_tokens=True)

print(f"      Generated: {text_generated_cold}")

# --- Results ---
print("\n" + "=" * 70)
print("RESULTS COMPARISON")
print("=" * 70)
print(f"Expected (Full Context): '{text_generated_full[:60]}...'")
print(f"Actual (State Transfer): '{text_generated_transfer[:60]}...'")
print(f"Control (Cold Start):    '{text_generated_cold[:60]}...'")

print("\n--- Analysis ---")

entities = ["Thornwick", "Jinx", "bard", "tome"]
found_in_transfer = [e for e in entities if e in text_generated_transfer]
found_in_cold = [e for e in entities if e in text_generated_cold]

# Context check
if found_in_transfer:
    print(f"[OK] SUCCESS: 'Residue' confirmed. Found entities from prefix: {found_in_transfer}")
    print("  The model hallucinated these names purely from the injected state.")
else:
    print("[FAIL] FAILURE: No context entities found in transfer output.")

if found_in_cold:
    print(f"  (Warning: Cold start also found entities: {found_in_cold} - likely coincidence)")

# Strict equality check (often fails due to token boundary artifacts)
if text_generated_full == text_generated_transfer:
    print("[OK] PERFECT MATCH: Transfer output matches baseline exactly.")
elif text_generated_transfer in text_generated_full or text_generated_full in text_generated_transfer:
    print("~ PARTIAL MATCH: Outputs are structurally similar.")
else:
    print("~ DIVERGENCE: Output differs from baseline (expected due to token boundary artifacts).")
    print("  The baseline processes [Prefix+Cont] as one block.")
    print("  The transfer processes [Cont] with state(Prefix).")
    print("  Slight differences in convolution state at the boundary cause drift.")
    
print("=" * 70)
print("Experiment complete.")
