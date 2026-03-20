import argparse
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path

# PIVOT TO 1.5B FOR SPEED
MODEL_NAME = "Qwen/Qwen2.5-1.5B"
TARGET_LAYERS = [12, 13, 14, 15]
OUTPUT_DIR = "activation_sessions_1.5b"
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"


def sanitize_episode_name(header: str) -> str:
    return (
        header.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "")
        .replace("/", "_")
    )


def record_episodes():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model.eval()
    expected_widths = {
        layer_idx: int(model.model.layers[layer_idx].self_attn.v_proj.out_features)
        for layer_idx in TARGET_LAYERS
    }

    with open(EPISODES_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    
    for ep in episodes:
        lines = ep.split("\n")
        header = lines[0].strip()
        ep_name = sanitize_episode_name(header)
        transcript = ep.split("[Transcript]")[1].strip()
            
        print(f"Processing Episode: {header}...")
        inputs = tokenizer(transcript, return_tensors="pt").to(model.device)
        activations = {}

        def get_hook(layer_idx):
            def hook(module, module_in, module_out):
                activation = module_out[0, -1, :].detach().cpu()
                expected_width = expected_widths[layer_idx]
                if int(activation.shape[-1]) != expected_width:
                    raise RuntimeError(
                        "Recorded activation width does not match 1.5B v_proj width: "
                        f"layer={layer_idx} got={int(activation.shape[-1])} "
                        f"expected={expected_width}"
                    )
                activations[layer_idx] = activation
            return hook

        handles = []
        for layer_idx in TARGET_LAYERS:
            layer_module = model.model.layers[layer_idx].self_attn.v_proj
            handles.append(layer_module.register_forward_hook(get_hook(layer_idx)))

        with torch.no_grad():
            model(**inputs)

        for handle in handles:
            handle.remove()

        missing_layers = [layer_idx for layer_idx in TARGET_LAYERS if layer_idx not in activations]
        if missing_layers:
            raise RuntimeError(
                "Missing recorded activations for target layers: "
                + ", ".join(str(layer_idx) for layer_idx in missing_layers)
            )

        output_path = os.path.join(OUTPUT_DIR, f"target_cheese_{ep_name}.pt")
        torch.save(activations, output_path)
        print(f"  Saved: {output_path} (Dim: {activations[13].shape[0]})")

if __name__ == "__main__":
    record_episodes()
