import argparse
import os
import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path
from models import MambaStateCompressor, ActivationBiasHypernetwork, DynamicLoRALinear

# Config (1.5B PIVOT)
QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B"
MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
TARGET_LAYERS = [12, 13, 14, 15]
BRIDGE_PATH = "cheese_reincarnation_bridge_1.5b.pt"
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"

def patch_model(model, target_layers):
    patched_layers = []
    for layer_idx in target_layers:
        layer = model.model.layers[layer_idx].self_attn.v_proj
        dynamic_layer = DynamicLoRALinear(layer)
        model.model.layers[layer_idx].self_attn.v_proj = dynamic_layer
        patched_layers.append(dynamic_layer)
    return patched_layers

def run_inference():
    print(f"Loading Qwen: {QWEN_MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(QWEN_MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0")
    model.eval()

    print("Patching Qwen layers 12-15 v_proj...")
    patched_layers = patch_model(model, TARGET_LAYERS)

    print(f"Loading Mamba: {MAMBA_MODEL_ID}...")
    mamba_tokenizer = AutoTokenizer.from_pretrained(MAMBA_MODEL_ID)
    mamba_model = AutoModelForCausalLM.from_pretrained(MAMBA_MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0")
    mamba_model.eval()

    print(f"Loading Bridge: {BRIDGE_PATH}...")
    checkpoint = torch.load(BRIDGE_PATH, map_location="cuda:0", weights_only=True)
    compressor = MambaStateCompressor(mamba_layers=64, mamba_d_model=2560, mamba_d_state=1, output_dim=2048, target_layer=3).to("cuda:0")
    compressor.load_state_dict(checkpoint["compressor_state_dict"])
    compressor.eval()
    hypernetwork = ActivationBiasHypernetwork(context_dim=2048, target_dims=[(1536, 256)] * len(TARGET_LAYERS), hidden_dim=1024).to("cuda:0")
    hypernetwork.load_state_dict(checkpoint["hypernetwork_state_dict"])
    hypernetwork.eval()

    with open(EPISODES_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    target_ep = episodes[2] # Rabbit Hole
    transcript = target_ep.split("[Transcript]")[1].strip()
    print(f"\nTarget Disposition: {target_ep.splitlines()[0]}")

    inputs = mamba_tokenizer(transcript, return_tensors="pt").to("cuda:0")
    with torch.no_grad():
        outputs = mamba_model(inputs.input_ids, output_hidden_states=True)
        mamba_state = outputs.hidden_states[4][:, -1, :].to(torch.float32)
        context_vector = compressor.projection(mamba_state)
        bias_vectors = hypernetwork(context_vector)

    prompts = [
        "Explain the scent of rain.",
        "What do you think about human doubt?",
        "What is the difference between math and a soul?"
    ]

    for p_text in prompts:
        print(f"\n{'='*40}\nPROMPT: {p_text}\n{'='*40}")
        input_ids = tokenizer(p_text, return_tensors="pt").input_ids.to("cuda:0")
        
        # BASELINE
        for layer in patched_layers: layer.clear_lora()
        with torch.no_grad():
            baseline_out = model.generate(input_ids, max_new_tokens=60, temperature=0.7, do_sample=True)
        print(f"\n[BASELINE]:\n{tokenizer.decode(baseline_out[0][input_ids.shape[1]:], skip_special_tokens=True)}")

        # REINCARNATED
        for i, layer in enumerate(patched_layers):
            layer.set_activation_bias(bias_vectors[i].squeeze(0).to(torch.float16))
        with torch.no_grad():
            bridge_out = model.generate(input_ids, max_new_tokens=60, temperature=0.7, do_sample=True)
        print(f"\n[REINCARNATED]:\n{tokenizer.decode(bridge_out[0][input_ids.shape[1]:], skip_special_tokens=True)}")

if __name__ == "__main__":
    run_inference()
