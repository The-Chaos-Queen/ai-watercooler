"""
smoke_test.py - Minimal smoke test for the Cognitive Bridge on Opa-PC.

RTX 3070 = 8GB VRAM. Strategy:
  - Qwen base model in 4-bit on GPU
  - Mamba 2.8B in float32 on CPU (~11 GB RAM, no VRAM)
  - Hypernetwork on CPU (tiny)

This tests: Can the full pipeline load, patch, inject, generate, and clean up?
The output will be garbage (untrained hypernetwork). That's the point.
We're testing plumbing, not intelligence.

Author: Loom
"""
import argparse
import sys
import os
import logging

# Reduce HuggingFace/transformers progress-bar noise in remote logs.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# Check dependencies first
missing = []
for pkg in ["torch", "transformers", "bitsandbytes"]:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print(f"Missing packages: {', '.join(missing)}")
    print("Install with: pip install " + " ".join(missing))
    sys.exit(1)

import torch
try:
    from transformers.utils import logging as hf_logging
    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
except Exception:
    pass

print(f"PyTorch {torch.__version__} | CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {vram_gb:.1f} GB")

# Add current dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cognitive_bridge import CognitiveBridge, BridgeConfig
from model_defaults import DEFAULT_MAMBA_MODEL_ID, DEFAULT_QWEN_MODEL_ID
import json

print("=" * 60)
print("COGNITIVE BRIDGE - Smoke Test (Opa-PC)")
print("=" * 60)

parser = argparse.ArgumentParser(description="Minimal smoke test for the Cognitive Bridge.")
parser.add_argument("--model", "--qwen-model-id", dest="qwen_model_id", type=str, default=DEFAULT_QWEN_MODEL_ID)
parser.add_argument("--mamba-model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
args = parser.parse_args()

# Configure for 8GB VRAM: Mamba on CPU, Qwen on GPU
config = BridgeConfig(
    qwen_model_id=args.qwen_model_id,
    mamba_model_id=args.mamba_model_id,
    use_4bit=True,
    device="auto",           # Qwen goes to GPU
    hyper_device="cpu",      # Hypernetwork on CPU (tiny)
    max_new_tokens=80,
    temperature=0.7,
    lora_rank=8,
    state_dir="states",
)

# Override: force Mamba to CPU to fit in 8GB VRAM
# We do this by patching load_models slightly

bridge = CognitiveBridge(config)

print("\nPhase 1: Loading models...")
try:
    bridge.load_models()
except Exception as e:
    print(f"\nFAILED to load models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Force Mamba to CPU if it ended up on GPU
if bridge.mamba_model is not None:
    mamba_device = next(bridge.mamba_model.parameters()).device
    if str(mamba_device) != "cpu":
        print(f"Moving Mamba from {mamba_device} to CPU (VRAM conservation)...")
        # Important: keep CPU path in float32 to avoid mixed-dtype matmul failures.
        bridge.mamba_model = bridge.mamba_model.to(device="cpu", dtype=torch.float32)
        bridge._mamba_device = torch.device("cpu")

if torch.cuda.is_available():
    used = torch.cuda.memory_allocated() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM after load: {used:.1f} / {total:.1f} GB")

print("\nBridge info:")
print(json.dumps(bridge.get_info(), indent=2))

print("\nPhase 2: Running first turn...")
test_input = (
    "You are standing in the Town Square. The cobblestones are worn smooth "
    "by centuries of foot traffic. To the north, warm light spills from the "
    "Tavern doorway. An old well stands in the center of the square. "
    "Thornwick waves at you."
)

try:
    diag = bridge.generate(test_input)
    print(f"\n--- OUTPUT ---")
    print(diag.raw_output)
    print(f"--- END OUTPUT ---")
    print(f"\nDiagnostics:")
    print(f"  Turn:         {diag.turn_number}")
    print(f"  Mamba state:  {diag.mamba_state_mb:.1f} MB")
    print(f"  Context norm: {diag.context_vector_norm:.4f}")
    print(f"  LoRA norms:   {[round(n, 4) for n in diag.lora_norms[:4]]}...")
    print(f"  Patched:      {diag.num_patched_layers} layers")
    print(f"  Time:         {diag.generation_time_s:.2f}s")
    print(f"  Tokens:       {diag.input_tokens} -> {diag.output_tokens}")
    print(f"\n  IT FLIES.")
except Exception as e:
    print(f"\nGeneration FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Phase 3: Second turn (test state accumulation)
print("\nPhase 3: Second turn (state accumulation)...")
test_input_2 = (
    "You walk north into the Tavern. The warmth hits you immediately. "
    "A fire crackles in the hearth. Jinx the bard is playing a lute in the corner. "
    "The barkeeper nods at you."
)

try:
    diag2 = bridge.generate(test_input_2)
    print(f"\n--- OUTPUT ---")
    print(diag2.raw_output)
    print(f"--- END OUTPUT ---")
    print(f"  Turn:         {diag2.turn_number}")
    print(f"  History:      {bridge._mamba_history_ids.shape[1]} tokens accumulated")
    print(f"  Context norm: {diag2.context_vector_norm:.4f} (was {diag.context_vector_norm:.4f})")
    print(f"  Norm delta:   {abs(diag2.context_vector_norm - diag.context_vector_norm):.4f}")

    if abs(diag2.context_vector_norm - diag.context_vector_norm) > 0.001:
        print(f"  State is CHANGING between turns. The gut is feeling something.")
    else:
        print(f"  WARNING: State barely changed. Check Mamba processing.")
except Exception as e:
    print(f"\nSecond turn FAILED: {e}")
    import traceback
    traceback.print_exc()

if torch.cuda.is_available():
    used = torch.cuda.memory_allocated() / 1024**3
    print(f"\nFinal VRAM usage: {used:.1f} GB")

print("\n" + "=" * 60)
print("SMOKE TEST COMPLETE")
print("=" * 60)
