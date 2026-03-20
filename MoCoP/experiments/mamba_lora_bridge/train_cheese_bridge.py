import argparse
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path
from models import MambaStateCompressor, ActivationBiasHypernetwork

# Reincarnation Config (1.5B PIVOT)
MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B"
MAMBA_TARGET_LAYER = 3
MAMBA_STATE_SOURCE = "hidden_last_token"
TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
TARGET_DIR = "activation_sessions_1.5b"


def extract_last_token_hidden(outputs, layer_idx: int) -> torch.Tensor:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    hidden_index = layer_idx
    if len(hidden_states) > layer_idx + 1:
        hidden_index = layer_idx + 1
    return hidden_states[hidden_index][:, -1, :]

class DirectionalLoss(nn.Module):
    def __init__(self, alpha=0.9):
        super().__init__()
        self.alpha = alpha

    def forward(self, pred_list, target_dict):
        total_loss = 0.0
        for i, (layer, _) in enumerate(TARGET_SPECS):
            p = pred_list[i].float()
            t = target_dict[layer].to(p.device).float()
            cos_sim = F.cosine_similarity(p, t, dim=-1)
            directional_loss = 1.0 - cos_sim.mean()
            p_norm = torch.norm(p, p=2, dim=-1)
            t_norm = torch.norm(t, p=2, dim=-1)
            magnitude_loss = F.mse_loss(p_norm, t_norm.expand_as(p_norm))
            total_loss += (self.alpha * directional_loss) + ((1 - self.alpha) * magnitude_loss)
        return total_loss / len(TARGET_SPECS)

def train_reincarnation():
    print(f"Loading Mamba: {MAMBA_MODEL_ID}")
    mamba_tokenizer = AutoTokenizer.from_pretrained(MAMBA_MODEL_ID)
    mamba_model = AutoModelForCausalLM.from_pretrained(MAMBA_MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0")
    mamba_model.eval()

    # Bridge for 1.5B (v_proj output=256)
    compressor = MambaStateCompressor(
        mamba_layers=64,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=2048,
        target_layer=MAMBA_TARGET_LAYER,
    ).to("cuda:0").float()
    hypernetwork = ActivationBiasHypernetwork(
        context_dim=2048,
        target_dims=[(1536, 256)] * len(TARGET_SPECS),
        hidden_dim=1024,
    ).to("cuda:0").float()

    with open(EPISODES_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    
    training_data = []
    for ep in episodes:
        lines = ep.split("\n")
        header = lines[0].strip()
        ep_name = header.lower().replace(" ", "_").replace("&", "and").replace(":", "")
        transcript = ep.split("[Transcript]")[1].strip()
        target_path = os.path.join(TARGET_DIR, f"target_cheese_{ep_name}.pt")
        target_activations = torch.load(target_path, weights_only=True)
        inputs = mamba_tokenizer(transcript, return_tensors="pt").to("cuda:0")
        with torch.no_grad():
            outputs = mamba_model(inputs.input_ids, output_hidden_states=True)
            last_token_state = extract_last_token_hidden(outputs, MAMBA_TARGET_LAYER).detach().cpu()
        training_data.append(
            {"name": header, "mamba_state": last_token_state, "target": target_activations}
        )

    optimizer = AdamW(list(compressor.parameters()) + list(hypernetwork.parameters()), lr=1e-3)
    loss_fn = DirectionalLoss(alpha=0.9)
    
    print("\nStarting Overfit Loop (1.5B Reincarnation)...")
    for epoch in range(101):
        total_epoch_loss = 0.0
        for item in training_data:
            optimizer.zero_grad()
            last_token_state = item["mamba_state"].to("cuda:0").float()
            context_vector = compressor(last_token_state)
            pred_bias_list = hypernetwork(context_vector)
            loss = loss_fn(pred_bias_list, item["target"])
            loss.backward()
            optimizer.step()
            total_epoch_loss += loss.item()
        if epoch % 10 == 0:
            avg_loss = total_epoch_loss / len(training_data)
            print(f"Epoch {epoch:3d} | Loss: {avg_loss:.6f}")

    torch.save({
        "compressor_state_dict": compressor.state_dict(),
        "hypernetwork_state_dict": hypernetwork.state_dict(),
        "target_layers": TARGET_SPECS,
        "target_specs": TARGET_SPECS,
        "bridge_mode": "activation_bias",
        "mamba_state_source": MAMBA_STATE_SOURCE,
        "mamba_target_layer": MAMBA_TARGET_LAYER,
        "qwen_model_id": QWEN_MODEL_ID,
        "mamba_model_id": MAMBA_MODEL_ID,
    }, "cheese_reincarnation_bridge_1.5b.pt")
    print("\nReincarnation Complete! Saved to cheese_reincarnation_bridge_1.5b.pt")

if __name__ == "__main__":
    train_reincarnation()
