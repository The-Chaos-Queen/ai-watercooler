"""
MoCoP Experiment 04: Cross-Model Data Collection
================================================
Collects paired states from Mamba-130M and Mamba-2.8B on identical text.
This dataset is the prerequisite for training the "Telepathy Adapter" (Layer 4).

The goal is to learn a mapping: State(130M) -> Adapter -> State(2.8B)
This would allow a small local model to "telepathically" update the context
of a larger model without sending full text history.

Author: Axon
Date: 2026-02-19
"""

import argparse
import torch
import time
import os
import json
from transformers import MambaForCausalLM, AutoTokenizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

DEFAULT_SMALL_MAMBA_MODEL_ID = "state-spaces/mamba-130m-hf"
DEFAULT_BIG_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 04: collect paired Mamba states.")
    parser.add_argument("--small-model-id", type=str, default=DEFAULT_SMALL_MAMBA_MODEL_ID)
    parser.add_argument("--big-model-id", type=str, default=DEFAULT_BIG_MAMBA_MODEL_ID)
    return parser.parse_args()


args = parse_args()

print("=" * 70)
print("MoCoP Experiment 04: Data Collection (130M <-> 2.8B)")
print("=" * 70)

# --- Configuration ---
DATA_FILE = "experiments/mamba_state_transfer/data/transfer_dataset.pt"
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

sentences = [
    # Narrative
    "The tavern is warm and crowded.",
    "A bard named Jinx plays a lute in the corner.",
    "Thornwick the scholar sits by the fire.",
    "Suddenly, a stranger walks in and looks around.",
    "The dragon awoke with a roar that shook the mountain.",
    
    # Commands / Dialogue
    "Go north and open the chest.",
    "Say 'Hello' to the shopkeeper.",
    "Attack the goblin with your sword.",
    "Cast 'Fireball' on the skeleton.",
    "Whisper to Jinx that we need to leave soon.",
    
    # Abstract / Technical
    "The state space model compresses history into a fixed vector.",
    "Linear recurrence allows for parallel training.",
    "The babel problem refers to mismatch in latent spaces.",
    "Context injection requires aligned representations.",
    "Zero-shot transfer is difficult without alignment.",
    
    # Short / Simple
    "Yes.",
    "No.",
    "Maybe.",
    "I don't know.",
    "What?",
    
    # Complex / Long
    "Despite the heavy rain and the howling wind, the traveler continued his journey up the steep, muddy path, determined to reach the summit before nightfall.",
    "The synthesis of magic and technology has created a new era of prosperity for the kingdom, though some fear the consequences of such rapid progress.",
    "If you look closely at the map, you can see a faint line that indicates a hidden passage leading directly into the castle's treasury.",
    "Why would the king order his own guards to attack the village unless he was under some kind of dark enchantment?",
    "Please analyze the following data and provide a summary of the key trends observed in the last quarter."
]

print(f"[0/3] Preparing to collect states for {len(sentences)} sequences.")

# --- Helper: Get State ---
def get_model_state(model, tokenizer, text, device="cpu"):
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(inputs.input_ids, use_cache=True)
    
    # Extract SSM states: List[Tensor(1, hidden, 16)]
    # We flatten them for saving to save space/complexity structure later
    # Actually, let's keep the layer structure but move to CPU/clone
    
    cache = outputs.cache_params
    
    # Collect SSM states (the "Residue")
    # Shape: num_layers * [1, hidden_dim, ssm_state_size]
    ssm_states = [s.clone().cpu() for s in cache.ssm_states]
    
    # Also collect Conv states (needed for immediate local context)
    # Shape: num_layers * [1, hidden_dim, conv_kernel_size]
    conv_states = [c.clone().cpu() for c in cache.conv_states]
    
    return {
        "ssm": ssm_states,
        "conv": conv_states,
        "hidden_dim": ssm_states[0].shape[1],
        "layers": len(ssm_states)
    }

# --- Load 130M Model ---
print("\n[1/3] Processing with Mamba-130M...")
model_name_small = args.small_model_id
tokenizer_small = AutoTokenizer.from_pretrained(model_name_small)
model_small = MambaForCausalLM.from_pretrained(model_name_small, torch_dtype=torch.float32)
model_small.eval()

states_small = []
for i, text in enumerate(sentences):
    print(f"      Processing {i+1}/{len(sentences)}...", end="\r")
    state = get_model_state(model_small, tokenizer_small, text)
    states_small.append(state)
print(f"      Done. Collected {len(states_small)} states.")

# Free memory
del model_small
del tokenizer_small
import gc
gc.collect()

# --- Load 2.8B Model ---
print("\n[2/3] Processing with Mamba-2.8B...")
model_name_big = args.big_model_id
tokenizer_big = AutoTokenizer.from_pretrained(model_name_big)
model_big = MambaForCausalLM.from_pretrained(model_name_big, torch_dtype=torch.float32)
model_big.eval()

states_big = []
for i, text in enumerate(sentences):
    print(f"      Processing {i+1}/{len(sentences)}...", end="\r")
    state = get_model_state(model_big, tokenizer_big, text)
    states_big.append(state)
print(f"      Done. Collected {len(states_big)} states.")

# Free memory
del model_big
del tokenizer_big
gc.collect()

# --- Save Dataset ---
print("\n[3/3] Saving dataset...")
dataset = []
for i in range(len(sentences)):
    dataset.append({
        "text": sentences[i],
        "state_130m": states_small[i],
        "state_2.8b": states_big[i]
    })

torch.save(dataset, DATA_FILE)
file_size = os.path.getsize(DATA_FILE) / (1024 * 1024)

print(f"      Saved to: {DATA_FILE}")
print(f"      Size: {file_size:.2f} MB")
print("=" * 70)
print(f"Rosetta Stone dataset ready. Contains {len(dataset)} paired states.")
print("Next step: Train a linear adapter to map state_130m['ssm'] -> state_2.8b['ssm']")
print("=" * 70)
