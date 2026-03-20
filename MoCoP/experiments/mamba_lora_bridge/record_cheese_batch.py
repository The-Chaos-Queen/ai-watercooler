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

def record_episodes():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model.eval()

    with open(EPISODES_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    
    for ep in episodes:
        lines = ep.split("\n")
        header = lines[0].strip()
        ep_name = header.lower().replace(" ", "_").replace("&", "and").replace(":", "")
        transcript = ep.split("[Transcript]")[1].strip()
            
        print(f"Processing Episode: {header}...")
        inputs = tokenizer(transcript, return_tensors="pt").to(model.device)
        activations = {}

        def get_hook(layer_idx):
            def hook(module, module_in, module_out):
                # v_proj output for 1.5B is 256-dim
                activations[layer_idx] = module_out[0, -1, :].detach().cpu()
            return hook

        handles = []
        for layer_idx in TARGET_LAYERS:
            layer_module = model.model.layers[layer_idx].self_attn.v_proj
            handles.append(layer_module.register_forward_hook(get_hook(layer_idx)))

        with torch.no_grad():
            model(**inputs)

        for handle in handles:
            handle.remove()

        output_path = os.path.join(OUTPUT_DIR, f"target_cheese_{ep_name}.pt")
        torch.save(activations, output_path)
        print(f"  Saved: {output_path} (Dim: {activations[13].shape[0]})")

if __name__ == "__main__":
    record_episodes()
