import argparse
import os
import shutil
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

from models import MambaStateCompressor, ActivationBiasHypernetwork


MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B"
MAMBA_TARGET_LAYER = 3
TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
TARGET_DIR = "activation_sessions_1.5b"
DEFAULT_OUTPUT_NAME = "cheese_reincarnation_bridge_1.5b.pt"
LEGACY_OUTPUT_NAME = "cheese_reincarnation_bridge.pt"


def sanitize_episode_name(header: str) -> str:
    return (
        header.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "")
        .replace("/", "_")
    )


def torch_dtype_for_device(device: str) -> torch.dtype:
    return torch.float16 if str(device).startswith("cuda") else torch.float32


def infer_hidden_layer_count(model) -> int:
    config_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
    if config_layers > 0:
        return config_layers
    if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
        return len(model.backbone.layers)
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return len(model.model.layers)
    raise RuntimeError("Could not infer Mamba hidden layer count.")


def extract_last_token_hidden(
    outputs,
    layer_idx: int,
    expected_layers: int,
) -> torch.Tensor:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    if len(hidden_states) == expected_layers + 1:
        hidden_index = layer_idx + 1
    elif len(hidden_states) == expected_layers:
        hidden_index = layer_idx
    else:
        raise RuntimeError(
            "Unexpected hidden_states layout: "
            f"tuple_len={len(hidden_states)} expected_layers={expected_layers}"
        )

    return hidden_states[hidden_index][:, -1, :]


def load_model_and_tokenizer(model_id: str, device: str):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype_for_device(device),
    )
    model.to(device)
    model.eval()
    return tokenizer, model


def infer_qwen_target_dims(model_id: str, target_specs):
    qwen_config = AutoConfig.from_pretrained(model_id)
    hidden_size = int(getattr(qwen_config, "hidden_size"))
    num_attention_heads = int(getattr(qwen_config, "num_attention_heads"))
    head_dim = int(getattr(qwen_config, "head_dim", hidden_size // num_attention_heads))
    num_key_value_heads = int(
        getattr(qwen_config, "num_key_value_heads", num_attention_heads)
    )

    target_dims = []
    for layer_idx, proj_name in target_specs:
        if proj_name in {"q_proj", "o_proj"}:
            out_dim = hidden_size
        elif proj_name in {"k_proj", "v_proj"}:
            out_dim = num_key_value_heads * head_dim
        else:
            raise ValueError(f"Unsupported target projection: {proj_name}")
        target_dims.append((hidden_size, out_dim))
    return target_dims


def validate_target_activations(target_activations, target_specs, target_dims, ep_name: str):
    for (layer_idx, proj_name), (_, expected_out_dim) in zip(target_specs, target_dims):
        if layer_idx not in target_activations:
            raise KeyError(
                f"Missing recorded activation for layer {layer_idx} in episode {ep_name}."
            )

        recorded = target_activations[layer_idx]
        recorded_width = int(recorded.shape[-1]) if recorded.ndim > 0 else int(recorded.numel())
        if recorded_width != expected_out_dim:
            raise ValueError(
                "Recorded activation width does not match the 1.5B runtime target surface: "
                f"episode={ep_name} layer={layer_idx} proj={proj_name} "
                f"recorded={recorded_width} expected={expected_out_dim}. "
                "Re-record activations before training."
            )


class DirectionalLoss(nn.Module):
    def __init__(self, alpha: float = 0.9):
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
            total_loss += (self.alpha * directional_loss) + (
                (1 - self.alpha) * magnitude_loss
            )
        return total_loss / len(TARGET_SPECS)


def train_reincarnation(args: argparse.Namespace):
    script_dir = Path(__file__).resolve().parent
    episodes_path = script_dir / args.episodes_file
    target_dir = script_dir / args.target_dir
    output_path = script_dir / args.output_name
    legacy_output_path = script_dir / args.legacy_output_name

    print(f"Loading Mamba: {MAMBA_MODEL_ID} on {args.mamba_device}")
    mamba_tokenizer, mamba_model = load_model_and_tokenizer(
        MAMBA_MODEL_ID, args.mamba_device
    )
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    target_dims = infer_qwen_target_dims(QWEN_MODEL_ID, TARGET_SPECS)

    with open(episodes_path, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]

    training_data = []
    for ep in episodes:
        lines = ep.split("\n")
        header = lines[0].strip()
        ep_name = sanitize_episode_name(header)
        transcript = ep.split("[Transcript]")[1].strip()
        target_path = target_dir / f"target_cheese_{ep_name}.pt"
        target_activations = torch.load(target_path, map_location="cpu", weights_only=True)
        validate_target_activations(target_activations, TARGET_SPECS, target_dims, ep_name)

        inputs = mamba_tokenizer(
            transcript,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_mamba_tokens,
        )
        inputs = {key: value.to(args.mamba_device) for key, value in inputs.items()}
        with torch.no_grad():
            outputs = mamba_model(**inputs, output_hidden_states=True)
            last_token_state = extract_last_token_hidden(
                outputs,
                MAMBA_TARGET_LAYER,
                hidden_layer_count,
            ).detach().cpu()
        training_data.append(
            {"name": header, "mamba_state": last_token_state, "target": target_activations}
        )

    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=2048,
        target_layer=MAMBA_TARGET_LAYER,
    ).to(args.bridge_device).float()
    hypernetwork = ActivationBiasHypernetwork(
        context_dim=2048,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to(args.bridge_device).float()

    optimizer = AdamW(
        list(compressor.parameters()) + list(hypernetwork.parameters()),
        lr=args.lr,
    )
    loss_fn = DirectionalLoss(alpha=args.alpha)

    print("\nStarting Overfit Loop (1.5B Reincarnation)...")
    for epoch in range(args.epochs + 1):
        total_epoch_loss = 0.0
        for item in training_data:
            optimizer.zero_grad()
            last_token_state = item["mamba_state"].to(args.bridge_device).float()
            context_vector = compressor(last_token_state)
            pred_bias_list = hypernetwork(context_vector)
            loss = loss_fn(pred_bias_list, item["target"])
            loss.backward()
            optimizer.step()
            total_epoch_loss += loss.item()
        if epoch % args.log_every == 0:
            avg_loss = total_epoch_loss / len(training_data)
            print(f"Epoch {epoch:3d} | Loss: {avg_loss:.6f}")

    checkpoint = {
        "checkpoint_format_version": 2,
        "compressor_state_dict": compressor.state_dict(),
        "hypernetwork_state_dict": hypernetwork.state_dict(),
        "target_layers": TARGET_SPECS,
        "target_specs": TARGET_SPECS,
        "target_dims": target_dims,
        "bridge_mode": "activation_bias",
        "mamba_state_source": "hidden_last_token",
        "mamba_target_layer": MAMBA_TARGET_LAYER,
        "qwen_model_id": QWEN_MODEL_ID,
        "mamba_model_id": MAMBA_MODEL_ID,
        "max_mamba_tokens": args.max_mamba_tokens,
        "episodes_file": str(episodes_path.name),
    }
    torch.save(checkpoint, output_path)

    if legacy_output_path != output_path:
        shutil.copyfile(output_path, legacy_output_path)

    print(f"\nReincarnation Complete! Saved to {output_path.name}")
    print(f"Legacy alias updated at {legacy_output_path.name}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train the 1.5B Adrenaline Bridge on CHEESE shaping episodes."
    )
    parser.add_argument("--episodes-file", default=EPISODES_FILE)
    parser.add_argument("--target-dir", default=TARGET_DIR)
    parser.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME)
    parser.add_argument("--legacy-output-name", default=LEGACY_OUTPUT_NAME)
    parser.add_argument("--mamba-device", default="cuda:0")
    parser.add_argument("--bridge-device", default="cuda:0")
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--log-every", type=int, default=10)
    return parser


if __name__ == "__main__":
    train_reincarnation(build_arg_parser().parse_args())
