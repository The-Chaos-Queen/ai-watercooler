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
BRIDGE_PATH = "cheese_reincarnation_bridge_1.5b.pt"
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
DEFAULT_TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
DEFAULT_MAMBA_TARGET_LAYER = 3

def extract_last_token_hidden(outputs, layer_idx: int) -> torch.Tensor:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    hidden_index = layer_idx
    if len(hidden_states) > layer_idx + 1:
        hidden_index = layer_idx + 1
    return hidden_states[hidden_index][:, -1, :]


def normalize_target_specs(raw):
    if not raw:
        return DEFAULT_TARGET_SPECS

    specs = []
    for item in raw:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            specs.append((int(item[0]), str(item[1]).strip()))
        else:
            specs.append((int(item), "v_proj"))
    return specs


def patch_model(model, target_specs):
    patched_layers = []
    for layer_idx, proj_name in target_specs:
        layer = getattr(model.model.layers[layer_idx].self_attn, proj_name)
        dynamic_layer = DynamicLoRALinear(layer)
        setattr(model.model.layers[layer_idx].self_attn, proj_name, dynamic_layer)
        patched_layers.append(dynamic_layer)
    return patched_layers

def run_inference():
    print(f"Loading Qwen: {QWEN_MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(QWEN_MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0")
    model.eval()

    checkpoint = torch.load(BRIDGE_PATH, map_location="cuda:0", weights_only=False)
    target_specs = normalize_target_specs(
        checkpoint.get("target_specs") or checkpoint.get("target_layers")
    )
    mamba_target_layer = int(checkpoint.get("mamba_target_layer", DEFAULT_MAMBA_TARGET_LAYER))

    print(f"Patching Qwen target specs: {target_specs}...")
    patched_layers = patch_model(model, target_specs)
    target_dims = [
        (
            getattr(model.model.layers[layer_idx].self_attn, proj_name).in_features,
            getattr(model.model.layers[layer_idx].self_attn, proj_name).out_features,
        )
        for layer_idx, proj_name in target_specs
    ]

    print(f"Loading Mamba: {MAMBA_MODEL_ID}...")
    mamba_tokenizer = AutoTokenizer.from_pretrained(MAMBA_MODEL_ID)
    mamba_model = AutoModelForCausalLM.from_pretrained(MAMBA_MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0")
    mamba_model.eval()

    print(f"Loading Bridge: {BRIDGE_PATH}...")
    compressor = MambaStateCompressor(
        mamba_layers=64,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=2048,
        target_layer=mamba_target_layer,
    ).to("cuda:0")
    compressor.load_state_dict(checkpoint["compressor_state_dict"])
    compressor.eval()
    hypernetwork = ActivationBiasHypernetwork(
        context_dim=2048,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to("cuda:0")
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
        mamba_state = extract_last_token_hidden(outputs, mamba_target_layer).to(torch.float32)
        context_vector = compressor(mamba_state)
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
