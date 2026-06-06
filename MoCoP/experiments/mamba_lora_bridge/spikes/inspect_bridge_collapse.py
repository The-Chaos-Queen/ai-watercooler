"""Inspect the codexfix bridge checkpoint + recorded mamba states structure.

Read-only. Prints keys, config, and tensor shapes so the collapse-probe
script can be built against real shapes instead of guesses.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch

BRIDGE_DIR = r"C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge"
CKPT = os.path.join(BRIDGE_DIR, "cheese_reincarnation_bridge_1.5b_codexfix.pt")
STATES = os.path.join(BRIDGE_DIR, "mamba_layer3_states_v1.pt")


def describe(obj, prefix="", depth=0):
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, torch.Tensor):
                print(f"{pad}{prefix}{k}: Tensor {tuple(v.shape)} {v.dtype}")
            elif isinstance(v, dict):
                print(f"{pad}{prefix}{k}: dict[{len(v)}]")
                if depth < 2:
                    describe(v, prefix="", depth=depth + 1)
            elif isinstance(v, (list, tuple)):
                print(f"{pad}{prefix}{k}: {type(v).__name__}[{len(v)}] sample={v[:4]}")
            else:
                print(f"{pad}{prefix}{k}: {repr(v)[:120]}")
    else:
        print(f"{pad}{prefix}{type(obj)}")


print("=" * 70)
print("CHECKPOINT:", CKPT)
print("=" * 70)
ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
print("top-level type:", type(ckpt))
if isinstance(ckpt, dict):
    print("top-level keys:", list(ckpt.keys()))
    for key in ("config", "bridge_mode", "target_specs", "target_layers",
                "mamba_state_source", "mamba_target_layer"):
        if key in ckpt:
            print(f"  [{key}] = {ckpt[key]!r}"[:200])
    for sd_key in ("compressor_state_dict", "hypernetwork_state_dict"):
        if sd_key in ckpt:
            print(f"\n--- {sd_key} ---")
            sd = ckpt[sd_key]
            for name, t in list(sd.items())[:40]:
                if isinstance(t, torch.Tensor):
                    print(f"  {name}: {tuple(t.shape)} {t.dtype}")

print()
print("=" * 70)
print("STATES:", STATES)
print("=" * 70)
if os.path.exists(STATES):
    states = torch.load(STATES, map_location="cpu", weights_only=False)
    print("type:", type(states))
    if isinstance(states, torch.Tensor):
        print("Tensor shape:", tuple(states.shape), states.dtype)
    elif isinstance(states, dict):
        print("keys:", list(states.keys())[:20])
        describe(states)
    elif isinstance(states, (list, tuple)):
        print(f"{type(states).__name__}[{len(states)}]")
        if states and isinstance(states[0], torch.Tensor):
            print("  elem0:", tuple(states[0].shape), states[0].dtype)
        elif states:
            print("  elem0 type:", type(states[0]), repr(states[0])[:160])
else:
    print("NOT FOUND")
