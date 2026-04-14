import argparse
import os
import shutil
from pathlib import Path
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

from mamba_runtime_compat import ensure_mamba_ssm_compat
from models import (
    MambaStateCompressor,
    RawStateProjector,
    build_activation_bias_hypernetwork,
    is_gated_activation_bias_mode,
    is_hidden_gated_activation_bias_mode,
    is_input_gated_activation_bias_mode,
    is_input_residual_mixer_mode,
    is_token_conditioned_input_adapter_mode,
)


MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen2.5-7B"
MAMBA_TARGET_LAYER = 3
TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
TARGET_DIR = "activation_sessions_1.5b"
DEFAULT_OUTPUT_NAME = "cheese_reincarnation_bridge_1.5b.pt"
LEGACY_OUTPUT_NAME = "cheese_reincarnation_bridge.pt"
DEFAULT_CONTEXT_DIM = 2048
DEFAULT_HYPER_HIDDEN_DIM = 1024
DEFAULT_ADAPTER_RANK = 16
DEFAULT_MAMBA_STATE_CACHE_DIR = "mamba_hidden_states_l3"


def sanitize_episode_name(header: str) -> str:
    return (
        header.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "")
        .replace("/", "_")
    )


def load_episodes(episodes_path: Path):
    content = episodes_path.read_text(encoding="utf-8")
    raw_episodes = content.split("## Episode ")[1:]
    episodes = []
    for raw_episode in raw_episodes:
        lines = raw_episode.splitlines()
        header = lines[0].strip()
        transcript = raw_episode.split("[Transcript]", 1)[1].strip()
        episodes.append(
            {
                "header": header,
                "episode_name": sanitize_episode_name(header),
                "transcript": transcript,
            }
        )
    return episodes


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
    if "mamba" in model_id.lower():
        ensure_mamba_ssm_compat()

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
    for (layer_idx, proj_name), (expected_in_dim, expected_out_dim) in zip(target_specs, target_dims):
        if layer_idx not in target_activations:
            raise KeyError(
                f"Missing recorded activation for layer {layer_idx} in episode {ep_name}."
            )

        recorded = target_activations[layer_idx]
        if isinstance(recorded, dict):
            recorded_output = recorded.get("v_proj_out")
        else:
            recorded_output = recorded
        if recorded_output is None:
            raise KeyError(
                f"Episode {ep_name} layer {layer_idx} is missing recorded v_proj_out."
            )

        recorded_width = (
            int(recorded_output.shape[-1])
            if recorded_output.ndim > 0
            else int(recorded_output.numel())
        )
        if recorded_width != expected_out_dim:
            raise ValueError(
                "Recorded activation width does not match the selected Qwen runtime target surface: "
                f"episode={ep_name} layer={layer_idx} proj={proj_name} "
                f"recorded={recorded_width} expected={expected_out_dim}. "
                "Re-record activations before training."
            )

        if isinstance(recorded, dict) and "v_proj_in" in recorded and recorded["v_proj_in"] is not None:
            recorded_input = recorded["v_proj_in"]
            recorded_input_width = (
                int(recorded_input.shape[-1])
                if recorded_input.ndim > 0
                else int(recorded_input.numel())
            )
            if recorded_input_width != expected_in_dim:
                raise ValueError(
                    "Recorded activation input width does not match the selected Qwen runtime surface: "
                    f"episode={ep_name} layer={layer_idx} proj={proj_name} "
                    f"recorded={recorded_input_width} expected={expected_in_dim}. "
                    "Re-record activations before training."
                )


def extract_target_output(target_activations, layer_idx: int, ep_name: str) -> torch.Tensor:
    recorded = target_activations[layer_idx]
    if isinstance(recorded, dict):
        output = recorded.get("v_proj_out")
        if output is None:
            raise KeyError(
                f"Episode {ep_name} layer {layer_idx} is missing recorded v_proj_out."
            )
        return output
    return recorded


def extract_target_input(target_activations, layer_idx: int, ep_name: str) -> torch.Tensor | None:
    recorded = target_activations[layer_idx]
    if not isinstance(recorded, dict):
        raise KeyError(f"Episode {ep_name} layer {layer_idx} does not contain input/output dicts. Was record_cheese_batch.py run with --capture-vproj-inputs?")
    hidden_input = recorded.get("v_proj_in")
    if hidden_input is None:
        raise KeyError(
            f"Episode {ep_name} layer {layer_idx} is missing recorded v_proj_in."
        )
    return hidden_input


def resolve_bridge_mode(args: argparse.Namespace) -> str:
    if args.token_conditioned_input_adapter:
        return "token_conditioned_input_adapter"
    if args.input_residual_mixer:
        return "input_residual_mixer"
    if args.input_gated_residual:
        return "input_gated_activation_bias"
    if args.hidden_gated_residual:
        return "hidden_gated_activation_bias"
    if args.gated_residual:
        return "gated_activation_bias"
    return "activation_bias"


def validate_target_inputs_available(target_activations, ep_name: str):
    for layer_idx, _ in TARGET_SPECS:
        extract_target_input(target_activations, layer_idx, ep_name)


def materialize_episode_targets(target_activations, ep_name: str) -> dict[int, torch.Tensor]:
    return {
        layer_idx: extract_target_output(target_activations, layer_idx, ep_name).detach().cpu()
        for layer_idx, _ in TARGET_SPECS
    }


def materialize_episode_inputs(target_activations, ep_name: str) -> dict[int, torch.Tensor]:
    return {
        layer_idx: extract_target_input(target_activations, layer_idx, ep_name).detach().cpu()
        for layer_idx, _ in TARGET_SPECS
    }


def build_cross_episode_input_pairs(training_data, device: str):
    pair_mamba_states = []
    pair_source_inputs = {layer: [] for layer, _ in TARGET_SPECS}
    pair_target_inputs = {layer: [] for layer, _ in TARGET_SPECS}

    for target_item in training_data:
        for source_item in training_data:
            pair_mamba_states.append(target_item["mamba_state"])
            for layer, _ in TARGET_SPECS:
                pair_source_inputs[layer].append(source_item["target_input"][layer].float())
                pair_target_inputs[layer].append(target_item["target_input"][layer].float())

    batch_pair_mamba_states = torch.cat(pair_mamba_states, dim=0).to(device).float()
    batch_pair_source_inputs = {
        layer: torch.stack(values, dim=0).to(device)
        for layer, values in pair_source_inputs.items()
    }
    batch_pair_target_inputs = {
        layer: torch.stack(values, dim=0).to(device)
        for layer, values in pair_target_inputs.items()
    }
    return batch_pair_mamba_states, batch_pair_source_inputs, batch_pair_target_inputs


def is_zero_bias_control_prompt(prompt_id: str, prompt_slice: str) -> bool:
    normalized_id = str(prompt_id).strip().lower()
    normalized_slice = str(prompt_slice).strip().lower()
    return (
        normalized_id.startswith("fact_")
        or normalized_id.startswith("obs_")
        or normalized_slice in {"baseline_factual", "observation_passive"}
        or normalized_slice.endswith("_control")
        or "control" in normalized_slice
    )


def is_memory_routing_probe(prompt_id: str, prompt_slice: str) -> bool:
    normalized_id = str(prompt_id).strip().lower()
    normalized_slice = str(prompt_slice).strip().lower()
    return normalized_id == "rr_10" or "memory" in normalized_slice


def load_prompt_trace_dataset(path: Path):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise TypeError(f"Prompt-trace dataset must be a dict payload, got {type(payload)!r}")
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"Prompt-trace dataset has no samples: {path}")
    return payload


def get_trace_tensor(trace_map, layer_idx: int, field_name: str, sample_label: str) -> torch.Tensor:
    if not isinstance(trace_map, dict):
        raise TypeError(f"{field_name} for {sample_label} must be a dict keyed by layer.")
    if layer_idx in trace_map:
        tensor = trace_map[layer_idx]
    elif str(layer_idx) in trace_map:
        tensor = trace_map[str(layer_idx)]
    else:
        raise KeyError(f"{field_name} for {sample_label} is missing layer {layer_idx}.")
    if not isinstance(tensor, torch.Tensor):
        raise TypeError(
            f"{field_name} for {sample_label} layer {layer_idx} must be a tensor, "
            f"got {type(tensor)!r}."
        )
    return tensor.detach().cpu()


def build_prompt_trace_pair_batches(prompt_trace_payload, episode_state_by_name, device: str):
    pair_mamba_states = []
    pair_source_inputs = {layer: [] for layer, _ in TARGET_SPECS}
    pair_target_inputs = {layer: [] for layer, _ in TARGET_SPECS}
    pair_prompt_ids = []
    pair_prompt_slices = []
    prompt_ids = set()
    episode_names = set()

    for sample in prompt_trace_payload["samples"]:
        episode_name = str(sample.get("episode_name", "")).strip()
        prompt_id = str(sample.get("prompt_id", "")).strip()
        prompt_slice = str(sample.get("prompt_slice", "")).strip()
        sample_label = f"episode={episode_name or '<missing>'} prompt={prompt_id or '<missing>'}"
        if not episode_name:
            raise ValueError(f"Prompt-trace sample is missing episode_name: {sample!r}")
        if episode_name not in episode_state_by_name:
            raise KeyError(
                f"Prompt-trace sample references unknown episode {episode_name!r}. "
                "Make sure the episodes file matches the dataset."
            )

        mamba_state = episode_state_by_name[episode_name].detach().cpu().float()
        if mamba_state.dim() != 2 or mamba_state.shape[0] != 1:
            raise ValueError(
                f"Expected episode state for {episode_name} to have shape [1, d], got {tuple(mamba_state.shape)}."
            )

        source_trace_map = sample.get("source_trace")
        target_trace_map = sample.get("target_trace")
        token_count = None
        for layer_idx, _ in TARGET_SPECS:
            source_trace = get_trace_tensor(source_trace_map, layer_idx, "source_trace", sample_label).float()
            target_trace = get_trace_tensor(target_trace_map, layer_idx, "target_trace", sample_label).float()
            if source_trace.dim() != 2 or target_trace.dim() != 2:
                raise ValueError(
                    f"Prompt-trace tensors for {sample_label} layer {layer_idx} must be 2D [tokens, hidden]."
                )
            if tuple(source_trace.shape) != tuple(target_trace.shape):
                raise ValueError(
                    f"Source/target trace shape mismatch for {sample_label} layer {layer_idx}: "
                    f"{tuple(source_trace.shape)} vs {tuple(target_trace.shape)}."
                )
            if token_count is None:
                token_count = int(source_trace.shape[0])
                pair_mamba_states.append(mamba_state.repeat(token_count, 1))
                pair_prompt_ids.extend([prompt_id] * token_count)
                pair_prompt_slices.extend([prompt_slice] * token_count)
            pair_source_inputs[layer_idx].append(source_trace)
            pair_target_inputs[layer_idx].append(target_trace)

        prompt_ids.add(prompt_id)
        episode_names.add(episode_name)

    batch_pair_mamba_states = torch.cat(pair_mamba_states, dim=0).to(device).float()
    batch_pair_source_inputs = {
        layer: torch.cat(values, dim=0).to(device)
        for layer, values in pair_source_inputs.items()
    }
    batch_pair_target_inputs = {
        layer: torch.cat(values, dim=0).to(device)
        for layer, values in pair_target_inputs.items()
    }
    summary = {
        "pair_count": int(batch_pair_mamba_states.shape[0]),
        "prompt_count": len(prompt_ids),
        "episode_count": len(episode_names),
        "sample_count": len(prompt_trace_payload["samples"]),
    }
    label_metadata = {
        "prompt_ids": pair_prompt_ids,
        "prompt_slices": pair_prompt_slices,
    }
    return (
        batch_pair_mamba_states,
        batch_pair_source_inputs,
        batch_pair_target_inputs,
        summary,
        label_metadata,
    )


def build_batch_supervision(
    *,
    bridge_mode: str,
    device: str,
    prompt_trace_dataset_path: Path | None,
    batch_mamba_states: torch.Tensor | None,
    pair_batch_mamba_states: torch.Tensor | None,
    prompt_trace_pair_batch_mamba_states: torch.Tensor | None,
    prompt_trace_label_metadata: dict | None,
    contamination_loss_weight: float,
    memory_routing_loss_weight: float,
):
    supervision_notes = []

    if prompt_trace_dataset_path is not None:
        if prompt_trace_pair_batch_mamba_states is None:
            raise RuntimeError(
                "Prompt-trace supervision requires prompt_trace_pair_batch_mamba_states."
            )
        label_metadata = prompt_trace_label_metadata or {}
        prompt_ids = list(label_metadata.get("prompt_ids", []))
        prompt_slices = list(label_metadata.get("prompt_slices", []))
        if len(prompt_ids) != int(prompt_trace_pair_batch_mamba_states.shape[0]):
            raise RuntimeError(
                "Prompt-trace prompt_ids length does not match token-pair batch size."
            )
        if len(prompt_slices) != int(prompt_trace_pair_batch_mamba_states.shape[0]):
            raise RuntimeError(
                "Prompt-trace prompt_slices length does not match token-pair batch size."
            )
        control_mask = torch.tensor(
            [
                is_zero_bias_control_prompt(prompt_id, prompt_slice)
                for prompt_id, prompt_slice in zip(prompt_ids, prompt_slices)
            ],
            device=device,
            dtype=torch.bool,
        )
        memory_probe_mask = torch.tensor(
            [
                is_memory_routing_probe(prompt_id, prompt_slice)
                for prompt_id, prompt_slice in zip(prompt_ids, prompt_slices)
            ],
            device=device,
            dtype=torch.bool,
        )
        return (
            prompt_trace_pair_batch_mamba_states,
            control_mask,
            memory_probe_mask,
            supervision_notes,
        )

    if is_token_conditioned_input_adapter_mode(bridge_mode):
        if pair_batch_mamba_states is None:
            raise RuntimeError(
                "Token-conditioned supervision requires pair_batch_mamba_states."
            )
        if contamination_loss_weight > 0:
            supervision_notes.append(
                "Contamination loss disabled: no prompt-trace dataset, so no prompt-level control labels exist."
            )
        if memory_routing_loss_weight > 0:
            supervision_notes.append(
                "Memory routing loss disabled: no prompt-trace dataset, so no prompt-level memory labels exist."
            )
        zero_mask = torch.zeros(
            int(pair_batch_mamba_states.shape[0]),
            device=device,
            dtype=torch.bool,
        )
        return pair_batch_mamba_states, zero_mask, zero_mask.clone(), supervision_notes

    if batch_mamba_states is None:
        raise RuntimeError("Episode-batch supervision requires batch_mamba_states.")

    if contamination_loss_weight > 0:
        supervision_notes.append(
            "Contamination loss disabled on episode-only batches: it needs prompt-level control labels, not episode names."
        )
    if memory_routing_loss_weight > 0:
        supervision_notes.append(
            "Memory routing loss disabled on episode-only batches: it needs prompt-level memory labels, not episode names."
        )
    zero_mask = torch.zeros(
        int(batch_mamba_states.shape[0]),
        device=device,
        dtype=torch.bool,
    )
    return batch_mamba_states, zero_mask, zero_mask.clone(), supervision_notes


class DirectionalLoss(nn.Module):
    def __init__(self, alpha: float = 0.9):
        super().__init__()
        self.alpha = alpha

    def forward(self, pred_list, target_dict):
        total_loss = 0.0
        for i, (layer, _) in enumerate(TARGET_SPECS):
            p = pred_list[i].float()
            t = target_dict[layer].to(p.device).float()
            if t.dim() == 1:
                t = t.unsqueeze(0)
            cos_sim = F.cosine_similarity(p, t, dim=-1)
            directional_loss = 1.0 - cos_sim.mean()
            p_norm = torch.norm(p, p=2, dim=-1)
            t_norm = torch.norm(t, p=2, dim=-1)
            magnitude_loss = F.mse_loss(p_norm, t_norm.expand_as(p_norm))
            total_loss += (self.alpha * directional_loss) + (
                (1 - self.alpha) * magnitude_loss
            )
        return total_loss / len(TARGET_SPECS)


class DiversityPreservationLoss(nn.Module):
    """
    Match the relative geometry of predicted bridge outputs to target outputs.

    This is the lightest useful welfare/anti-collapse term we can add without
    changing the dataset surface: if target biases differ across episodes, the
    bridge should preserve that separation instead of collapsing toward one mean
    direction.
    """

    def __init__(self, weight: float = 0.1):
        super().__init__()
        self.weight = float(weight)

    def forward(self, pred_list, target_dict):
        if self.weight <= 0:
            sample = pred_list[0]
            return sample.new_zeros(())

        pred_full = torch.cat([p.float() for p in pred_list], dim=-1)
        target_full = torch.cat(
            [
                target_dict[layer].to(pred_full.device).float().reshape(pred_full.shape[0], -1)
                for layer, _ in TARGET_SPECS
            ],
            dim=-1,
        )
        if pred_full.shape[0] < 2:
            return pred_full.new_zeros(())

        pred_norm = F.normalize(pred_full, dim=-1)
        target_norm = F.normalize(target_full, dim=-1)
        pred_cos = pred_norm @ pred_norm.T
        target_cos = target_norm @ target_norm.T
        upper = torch.triu_indices(pred_cos.shape[0], pred_cos.shape[1], offset=1)
        return self.weight * F.mse_loss(
            pred_cos[upper[0], upper[1]],
            target_cos[upper[0], upper[1]],
        )


def flatten_exported_input_adapter_state(exported_states) -> torch.Tensor:
    flat_parts = []
    for layer_state in exported_states:
        for key in (
            "adapter_A",
            "adapter_B",
            "adapter_bias",
            "input_scale",
            "delta_scale",
            "gate_offset",
        ):
            value = layer_state[key].float().reshape(layer_state[key].shape[0], -1)
            flat_parts.append(value)
    return torch.cat(flat_parts, dim=-1)


class EpisodeSeparationLoss(nn.Module):
    """
    Prevent the token-conditioned adapter from collapsing all CHEESE episodes
    into the same exported adapter state.

    The raw Mamba episode states remain distinct. This loss enforces a minimum
    amount of that separation in the exported adapter parameters.
    """

    def __init__(
        self,
        weight: float = 0.0,
        min_distance: float = 0.02,
        distance_scale: float = 1.0,
    ):
        super().__init__()
        self.weight = float(weight)
        self.min_distance = float(max(0.0, min_distance))
        self.distance_scale = float(max(0.0, distance_scale))

    def forward(
        self,
        reference_vectors: torch.Tensor,
        adapter_vectors: torch.Tensor,
    ) -> torch.Tensor:
        if self.weight <= 0:
            return adapter_vectors.new_zeros(())
        if reference_vectors.shape[0] < 2 or adapter_vectors.shape[0] < 2:
            return adapter_vectors.new_zeros(())

        ref_norm = F.normalize(reference_vectors.float(), dim=-1)
        adapter_norm = F.normalize(adapter_vectors.float(), dim=-1)
        ref_dist = 1.0 - (ref_norm @ ref_norm.T)
        adapter_dist = 1.0 - (adapter_norm @ adapter_norm.T)
        upper = torch.triu_indices(ref_dist.shape[0], ref_dist.shape[1], offset=1)

        target_dist = torch.clamp(
            self.distance_scale * ref_dist[upper[0], upper[1]].detach(),
            min=self.min_distance,
        )
        observed_dist = adapter_dist[upper[0], upper[1]]
        return self.weight * F.relu(target_dist - observed_dist).pow(2).mean()


class EpisodeContrastiveLoss(nn.Module):
    """
    Cross-modal episode-ID contrastive loss.

    Adapter states should align with the correct raw CHEESE context and not with
    the other episodes. This is stronger than a pure margin floor because it
    forces episode-specific matching, not just generic non-collapse.
    """

    def __init__(
        self,
        adapter_dim: int,
        context_dim: int,
        projection_dim: int = 128,
        temperature: float = 0.1,
        weight: float = 0.0,
    ):
        super().__init__()
        if projection_dim <= 0:
            raise ValueError(f"projection_dim must be positive, got {projection_dim}")
        if temperature <= 0:
            raise ValueError(f"temperature must be positive, got {temperature}")

        self.weight = float(weight)
        self.temperature = float(temperature)
        self.adapter_projector = nn.Linear(adapter_dim, projection_dim, bias=False)
        self.context_projector = nn.Linear(context_dim, projection_dim, bias=False)
        nn.init.normal_(self.adapter_projector.weight, std=0.02)
        nn.init.normal_(self.context_projector.weight, std=0.02)

    def forward(
        self,
        adapter_vectors: torch.Tensor,
        context_vectors: torch.Tensor,
    ) -> torch.Tensor:
        if self.weight <= 0:
            return adapter_vectors.new_zeros(())
        if adapter_vectors.shape[0] < 2 or context_vectors.shape[0] < 2:
            return adapter_vectors.new_zeros(())

        adapter_embed = F.normalize(
            self.adapter_projector(adapter_vectors.float()),
            dim=-1,
        )
        context_embed = F.normalize(
            self.context_projector(context_vectors.float()),
            dim=-1,
        )
        logits = (adapter_embed @ context_embed.T) / self.temperature
        labels = torch.arange(logits.shape[0], device=logits.device)
        loss_a2c = F.cross_entropy(logits, labels)
        loss_c2a = F.cross_entropy(logits.T, labels)
        return self.weight * 0.5 * (loss_a2c + loss_c2a)


class PairwiseMarginLoss(nn.Module):
    """
    L_margin: Pairwise margin loss to prevent mode collapse.
    Ensures that different dispositions produce behaviorally distinct bias outputs.
    Can be driven by a target margin matrix (e.g. from raw Mamba cosines).
    """

    def __init__(self, weight: float = 0.0, default_margin: float = 0.1):
        super().__init__()
        self.weight = float(weight)
        self.default_margin = float(default_margin)

    def forward(
        self,
        pred_bias_list: List[torch.Tensor],
        target_margins: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if self.weight <= 0 or not pred_bias_list:
            return pred_bias_list[0].new_zeros(()) if pred_bias_list else torch.tensor(0.0)

        total_loss = 0.0
        for bias in pred_bias_list:
            if bias.shape[0] < 2:
                continue

            # Compute pairwise cosine distances
            norm_bias = F.normalize(bias.float(), dim=-1)
            dist_matrix = 1.0 - (norm_bias @ norm_bias.T)

            # Extract upper triangle
            indices = torch.triu_indices(bias.shape[0], bias.shape[0], offset=1)
            dists = dist_matrix[indices[0], indices[1]]

            if target_margins is not None:
                margins = target_margins[indices[0], indices[1]].to(bias.device)
            else:
                margins = self.default_margin

            # Loss: reward distances that fall below the required margin
            total_loss += F.relu(margins - dists).pow(2).mean()

        return self.weight * (total_loss / len(pred_bias_list))


class ContaminationLoss(nn.Module):
    """
    L_clean: Penalizes bridge activity on control (neutral/factual) prompts.
    Forces the translator to stay silent when no disposition is required.
    """

    def __init__(self, weight: float = 0.0):
        super().__init__()
        self.weight = float(weight)

    def forward(
        self,
        pred_bias_list: List[torch.Tensor],
        is_control_mask: torch.Tensor,
    ) -> torch.Tensor:
        if self.weight <= 0 or not pred_bias_list or not is_control_mask.any():
            return pred_bias_list[0].new_zeros(())

        total_loss = 0.0
        for bias in pred_bias_list:
            # bias: [batch, out_dim]
            control_biases = bias[is_control_mask]
            # Target zero bias vector for control samples
            total_loss += control_biases.pow(2).mean()

        return self.weight * (total_loss / len(pred_bias_list))


class MemoryRoutingLoss(nn.Module):
    """
    L_mem: Routing constraint to prevent False-Memory Virus.
    Specifically targets the gate values to be zero on episodic probes.
    """

    def __init__(self, weight: float = 0.0):
        super().__init__()
        self.weight = float(weight)

    def forward(
        self,
        gate_values: List[torch.Tensor],
        is_memory_probe_mask: torch.Tensor,
    ) -> torch.Tensor:
        if self.weight <= 0 or not gate_values or not is_memory_probe_mask.any():
            return (
                gate_values[0].new_zeros(()) if gate_values else torch.tensor(0.0)
            )

        total_loss = 0.0
        for gate in gate_values:
            # gate: [batch, out_dim] or [batch, 1]
            memory_gates = gate[is_memory_probe_mask]
            # Target zero gate for memory probes
            total_loss += memory_gates.pow(2).mean()

        return self.weight * (total_loss / len(gate_values))


def build_context_encoder(
    skip_compressor: bool,
    hidden_layer_count: int,
    context_dim: int,
):
    if skip_compressor:
        encoder = RawStateProjector(
            mamba_layers=hidden_layer_count,
            mamba_d_model=2560,
            mamba_d_state=1,
            target_layer=MAMBA_TARGET_LAYER,
        )
        return encoder, encoder.output_dim, "raw_state"

    encoder = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=context_dim,
        target_layer=MAMBA_TARGET_LAYER,
    )
    return encoder, context_dim, "compressed"


def mamba_state_cache_path(cache_dir: Path, episode_name: str, target_layer: int) -> Path:
    return cache_dir / f"mamba_hidden_l{target_layer}_{episode_name}.pt"


def load_cached_mamba_state(path: Path) -> torch.Tensor:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(payload, torch.Tensor):
        state = payload
    elif isinstance(payload, dict):
        state = None
        for key in ("last_token_state", "mamba_state", "state"):
            if key in payload and payload[key] is not None:
                state = payload[key]
                break
        if state is None:
            raise KeyError(f"Cached state file {path} is missing a tensor payload.")
    else:
        raise TypeError(f"Unsupported cached Mamba state payload in {path}: {type(payload)!r}")

    if state.dim() == 1:
        state = state.unsqueeze(0)
    return state.detach().cpu()


def save_cached_mamba_state(
    path: Path,
    last_token_state: torch.Tensor,
    episode_header: str,
    episode_name: str,
    max_mamba_tokens: int,
):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "episode_header": episode_header,
        "episode_name": episode_name,
        "mamba_model_id": MAMBA_MODEL_ID,
        "mamba_target_layer": MAMBA_TARGET_LAYER,
        "mamba_state_source": "hidden_last_token",
        "max_mamba_tokens": max_mamba_tokens,
        "last_token_state": last_token_state.detach().cpu(),
    }
    torch.save(payload, path)


def train_reincarnation(args: argparse.Namespace):
    script_dir = Path(__file__).resolve().parent
    episodes_path = script_dir / args.episodes_file
    target_dir = script_dir / args.target_dir
    output_path = script_dir / args.output_name
    legacy_output_path = script_dir / args.legacy_output_name
    cache_dir = script_dir / args.mamba_state_cache_dir if args.mamba_state_cache_dir else None
    prompt_trace_dataset_path = (
        script_dir / args.prompt_trace_dataset if args.prompt_trace_dataset else None
    )
    hidden_layer_count = 0

    bridge_mode = resolve_bridge_mode(args)
    if prompt_trace_dataset_path is not None and not is_token_conditioned_input_adapter_mode(bridge_mode):
        raise ValueError(
            "--prompt-trace-dataset is currently only supported with "
            "--token-conditioned-input-adapter."
        )
    target_dims = infer_qwen_target_dims(args.qwen_model_id, TARGET_SPECS)
    episodes = load_episodes(episodes_path)

    training_data = []
    pending_episodes = []
    cached_count = 0
    for episode in episodes:
        header = episode["header"]
        ep_name = episode["episode_name"]
        if prompt_trace_dataset_path is None:
            target_path = target_dir / f"target_cheese_{ep_name}.pt"
            target_activations = torch.load(target_path, map_location="cpu", weights_only=True)
            validate_target_activations(target_activations, TARGET_SPECS, target_dims, ep_name)
            if (
                is_input_gated_activation_bias_mode(bridge_mode)
                or is_input_residual_mixer_mode(bridge_mode)
                or is_token_conditioned_input_adapter_mode(bridge_mode)
            ):
                validate_target_inputs_available(target_activations, ep_name)
            episode_targets = materialize_episode_targets(target_activations, ep_name)
            episode_inputs = (
                materialize_episode_inputs(target_activations, ep_name)
                if (
                    is_input_gated_activation_bias_mode(bridge_mode)
                    or is_input_residual_mixer_mode(bridge_mode)
                    or is_token_conditioned_input_adapter_mode(bridge_mode)
                )
                else None
            )
        else:
            episode_targets = None
            episode_inputs = None
        cache_path = (
            mamba_state_cache_path(cache_dir, ep_name, MAMBA_TARGET_LAYER)
            if cache_dir is not None
            else None
        )
        if cache_path is not None and cache_path.exists():
            last_token_state = load_cached_mamba_state(cache_path)
            training_data.append(
                {
                    "name": header,
                    "episode_name": ep_name,
                    "mamba_state": last_token_state,
                    "target": episode_targets,
                    "target_input": episode_inputs,
                }
            )
            cached_count += 1
            continue
        pending_episodes.append(
            {
                "header": header,
                "episode_name": ep_name,
                "transcript": episode["transcript"],
                "target": episode_targets,
                "target_input": episode_inputs,
                "cache_path": cache_path,
            }
        )

    if pending_episodes and args.require_cached_mamba_states:
        missing = ", ".join(item["episode_name"] for item in pending_episodes[:5])
        if len(pending_episodes) > 5:
            missing += ", ..."
        raise FileNotFoundError(
            f"--require-cached-mamba-states was set, but {len(pending_episodes)} cached "
            f"Mamba states are missing: {missing}"
        )

    if pending_episodes:
        print(f"Loading Mamba: {MAMBA_MODEL_ID} on {args.mamba_device}")
        mamba_tokenizer, mamba_model = load_model_and_tokenizer(
            MAMBA_MODEL_ID, args.mamba_device
        )
        hidden_layer_count = infer_hidden_layer_count(mamba_model)
        computed_count = 0
        for episode in pending_episodes:
            inputs = mamba_tokenizer(
                episode["transcript"],
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
            if episode["cache_path"] is not None and args.save_mamba_states:
                save_cached_mamba_state(
                    episode["cache_path"],
                    last_token_state,
                    episode["header"],
                    episode["episode_name"],
                    args.max_mamba_tokens,
                )
            training_data.append(
                {
                    "name": episode["header"],
                    "episode_name": episode["episode_name"],
                    "mamba_state": last_token_state,
                    "target": episode["target"],
                    "target_input": episode["target_input"],
                }
            )
            computed_count += 1
        del mamba_model
    else:
        computed_count = 0
        hidden_layer_count = int(args.cached_hidden_layer_count)
        print(
            f"Using cached Mamba states only: {cached_count} episodes from "
            f"{cache_dir if cache_dir is not None else '<no-cache-dir>'}"
        )

    if cached_count:
        print(f"Loaded cached Mamba states: {cached_count}")
    if computed_count:
        print(f"Computed fresh Mamba states: {computed_count}")

    context_encoder, resolved_context_dim, context_mode = build_context_encoder(
        skip_compressor=args.skip_compressor,
        hidden_layer_count=hidden_layer_count,
        context_dim=args.context_dim,
    )
    context_encoder = context_encoder.to(args.bridge_device).float()
    if args.skip_compressor and args.context_dim != resolved_context_dim:
        print(
            f"[warn] --context-dim={args.context_dim} ignored because "
            f"--skip-compressor uses raw width {resolved_context_dim}."
        )
    print(
        f"Context path: mode={context_mode} target_layer={MAMBA_TARGET_LAYER} "
        f"context_dim={resolved_context_dim}"
    )

    hypernetwork = build_activation_bias_hypernetwork(
        bridge_mode=bridge_mode,
        context_dim=resolved_context_dim,
        target_dims=target_dims,
        hidden_dim=args.hyper_hidden_dim,
        rank=args.adapter_rank,
        gate_kind=args.gate_kind,
        initial_gate=args.initial_gate,
    ).to(args.bridge_device).float()

    batch_mamba_states = (
        torch.cat([item["mamba_state"] for item in training_data], dim=0).to(args.bridge_device).float()
        if prompt_trace_dataset_path is None
        else None
    )
    batch_targets = (
        {
            layer: torch.stack(
                [item["target"][layer].float() for item in training_data],
                dim=0,
            ).to(args.bridge_device)
            for layer, _ in TARGET_SPECS
        }
        if prompt_trace_dataset_path is None
        else None
    )
    batch_target_inputs = (
        {
            layer: torch.stack(
                [item["target_input"][layer].float() for item in training_data],
                dim=0,
            ).to(args.bridge_device)
            for layer, _ in TARGET_SPECS
        }
        if is_input_residual_mixer_mode(bridge_mode) and prompt_trace_dataset_path is None
        else None
    )
    batch_hidden_inputs = (
        [
            torch.stack(
                [item["target_input"][layer].float() for item in training_data],
                dim=0,
            ).to(args.bridge_device)
            for layer, _ in TARGET_SPECS
        ]
        if (
            is_input_gated_activation_bias_mode(bridge_mode)
            or is_input_residual_mixer_mode(bridge_mode)
            or is_token_conditioned_input_adapter_mode(bridge_mode)
        )
        and prompt_trace_dataset_path is None
        else None
    )
    prompt_trace_pair_batch_mamba_states = None
    prompt_trace_pair_batch_source_inputs = None
    prompt_trace_pair_batch_target_inputs = None
    prompt_trace_label_metadata = None
    episode_reference_mamba_states = (
        torch.cat([item["mamba_state"] for item in training_data], dim=0).to(args.bridge_device).float()
        if is_token_conditioned_input_adapter_mode(bridge_mode)
        else None
    )
    pair_batch_mamba_states = None
    pair_batch_source_inputs = None
    pair_batch_target_inputs = None
    if prompt_trace_dataset_path is not None:
        prompt_trace_payload = load_prompt_trace_dataset(prompt_trace_dataset_path)
        episode_state_by_name = {
            item["episode_name"]: item["mamba_state"] for item in training_data
        }
        (
            prompt_trace_pair_batch_mamba_states,
            prompt_trace_pair_batch_source_inputs,
            prompt_trace_pair_batch_target_inputs,
            prompt_trace_summary,
            prompt_trace_label_metadata,
        ) = build_prompt_trace_pair_batches(
            prompt_trace_payload,
            episode_state_by_name,
            args.bridge_device,
        )
        print(
            "Prompt-trace token batch: "
            f"{prompt_trace_summary['pair_count']} aligned token pairs "
            f"from {prompt_trace_summary['sample_count']} prompt/episode samples "
            f"({prompt_trace_summary['prompt_count']} prompts x "
            f"{prompt_trace_summary['episode_count']} episodes)"
        )
    elif is_token_conditioned_input_adapter_mode(bridge_mode):
        pair_batch_mamba_states, pair_batch_source_inputs, pair_batch_target_inputs = (
            build_cross_episode_input_pairs(training_data, args.bridge_device)
        )
        print(f"Token-conditioned pair batch: {pair_batch_mamba_states.shape[0]} source->target pairs")

    episode_contrastive_loss_fn = None
    if (
        is_token_conditioned_input_adapter_mode(bridge_mode)
        and episode_reference_mamba_states is not None
        and args.episode_contrastive_loss_weight > 0
    ):
        with torch.no_grad():
            init_episode_context_vector = context_encoder(episode_reference_mamba_states)
            init_exported_episode_states = hypernetwork.export_input_adapter_state(
                init_episode_context_vector
            )
            init_episode_adapter_vectors = flatten_exported_input_adapter_state(
                init_exported_episode_states
            )
        episode_contrastive_loss_fn = EpisodeContrastiveLoss(
            adapter_dim=int(init_episode_adapter_vectors.shape[-1]),
            context_dim=int(episode_reference_mamba_states.shape[-1]),
            projection_dim=args.episode_contrastive_dim,
            temperature=args.episode_contrastive_temp,
            weight=args.episode_contrastive_loss_weight,
        ).to(args.bridge_device)

    optimizer_params = list(context_encoder.parameters()) + list(hypernetwork.parameters())
    if episode_contrastive_loss_fn is not None:
        optimizer_params.extend(list(episode_contrastive_loss_fn.parameters()))
    optimizer = AdamW(optimizer_params, lr=args.lr)
    loss_fn = DirectionalLoss(alpha=args.alpha)
    diversity_loss_fn = DiversityPreservationLoss(weight=args.diversity_loss_weight)
    margin_loss_fn = PairwiseMarginLoss(
        weight=args.margin_loss_weight,
        default_margin=args.default_margin,
    )
    contamination_loss_fn = ContaminationLoss(weight=args.contamination_loss_weight)
    memory_routing_loss_fn = MemoryRoutingLoss(weight=args.memory_routing_loss_weight)
    episode_separation_loss_fn = EpisodeSeparationLoss(
        weight=args.episode_separation_loss_weight,
        min_distance=args.episode_separation_min_distance,
        distance_scale=args.episode_separation_distance_scale,
    )

    (
        supervision_mamba_states,
        is_control_mask,
        is_memory_probe_mask,
        supervision_notes,
    ) = build_batch_supervision(
        bridge_mode=bridge_mode,
        device=args.bridge_device,
        prompt_trace_dataset_path=prompt_trace_dataset_path,
        batch_mamba_states=batch_mamba_states,
        pair_batch_mamba_states=pair_batch_mamba_states,
        prompt_trace_pair_batch_mamba_states=prompt_trace_pair_batch_mamba_states,
        prompt_trace_label_metadata=prompt_trace_label_metadata,
        contamination_loss_weight=args.contamination_loss_weight,
        memory_routing_loss_weight=args.memory_routing_loss_weight,
    )
    for note in supervision_notes:
        print(f"[note] {note}")
    print(
        "Composite-loss supervision: "
        f"control={int(is_control_mask.sum().item())} "
        f"memory={int(is_memory_probe_mask.sum().item())}"
    )

    target_margins = None
    if args.use_mamba_margins and supervision_mamba_states is not None:
        with torch.no_grad():
            norm_mamba = F.normalize(supervision_mamba_states.float(), dim=-1)
            target_margins = 1.0 - (norm_mamba @ norm_mamba.T)
            # Clip to positive just in case of precision noise
            target_margins = torch.clamp(target_margins, min=0.0)

    print("\nStarting Overfit Loop (1.5B Reincarnation)...")
    for epoch in range(args.epochs + 1):
        optimizer.zero_grad()
        episode_separation_loss = None
        episode_contrastive_loss = None
        if is_token_conditioned_input_adapter_mode(bridge_mode):
            if (
                prompt_trace_pair_batch_mamba_states is not None
                and prompt_trace_pair_batch_source_inputs is not None
                and prompt_trace_pair_batch_target_inputs is not None
            ):
                context_vector = context_encoder(prompt_trace_pair_batch_mamba_states)
                source_inputs = [
                    prompt_trace_pair_batch_source_inputs[layer] for layer, _ in TARGET_SPECS
                ]
                pred_bias_list, gate_values, _ = hypernetwork.forward_with_inputs(
                    context_vector,
                    source_inputs,
                )
                training_targets = prompt_trace_pair_batch_target_inputs
            elif (
                pair_batch_mamba_states is not None
                and pair_batch_source_inputs is not None
                and pair_batch_target_inputs is not None
            ):
                context_vector = context_encoder(pair_batch_mamba_states)
                source_inputs = [pair_batch_source_inputs[layer] for layer, _ in TARGET_SPECS]
                pred_bias_list, gate_values, _ = hypernetwork.forward_with_inputs(
                    context_vector,
                    source_inputs,
                )
                training_targets = pair_batch_target_inputs
            else:
                raise RuntimeError(
                    "Token-conditioned input adapter mode requires either "
                    "cross-episode pairs or a prompt-trace dataset."
                )
            if episode_reference_mamba_states is None:
                raise RuntimeError("Episode separation requires token adapter episode reference states.")
            episode_context_vector = context_encoder(episode_reference_mamba_states)
            exported_episode_states = hypernetwork.export_input_adapter_state(episode_context_vector)
            episode_adapter_vectors = flatten_exported_input_adapter_state(exported_episode_states)
            episode_separation_loss = episode_separation_loss_fn(
                reference_vectors=episode_reference_mamba_states,
                adapter_vectors=episode_adapter_vectors,
            )
            if episode_contrastive_loss_fn is not None:
                episode_contrastive_loss = episode_contrastive_loss_fn(
                    adapter_vectors=episode_adapter_vectors,
                    context_vectors=episode_reference_mamba_states,
                )
        elif is_input_residual_mixer_mode(bridge_mode):
            context_vector = context_encoder(batch_mamba_states)
            if batch_hidden_inputs is None or batch_target_inputs is None:
                raise RuntimeError("Input-residual mixer mode requires recorded v_proj input surfaces.")
            pred_bias_list, gate_values, _ = hypernetwork.forward_with_inputs(
                context_vector,
                batch_hidden_inputs,
            )
            training_targets = batch_target_inputs
        elif is_input_gated_activation_bias_mode(bridge_mode):
            context_vector = context_encoder(batch_mamba_states)
            if batch_hidden_inputs is None:
                raise RuntimeError("Input-gated bridge mode requires recorded v_proj input surfaces.")
            pred_bias_list, gate_values, _ = hypernetwork.forward_with_inputs(
                context_vector,
                batch_hidden_inputs,
            )
            training_targets = batch_targets
        elif is_hidden_gated_activation_bias_mode(bridge_mode):
            context_vector = context_encoder(batch_mamba_states)
            target_surfaces = [batch_targets[layer] for layer, _ in TARGET_SPECS]
            pred_bias_list, gate_values, _ = hypernetwork.forward_with_hidden_surfaces(
                context_vector,
                target_surfaces,
            )
            training_targets = batch_targets
        elif is_gated_activation_bias_mode(bridge_mode):
            context_vector = context_encoder(batch_mamba_states)
            pred_bias_list, gate_values, _ = hypernetwork.forward_with_gates(context_vector)
            training_targets = batch_targets
        else:
            context_vector = context_encoder(batch_mamba_states)
            pred_bias_list = hypernetwork(context_vector)
            gate_values = []
            training_targets = batch_targets

        transfer_loss = loss_fn(pred_bias_list, training_targets)
        diversity_loss = diversity_loss_fn(pred_bias_list, training_targets)
        margin_loss = margin_loss_fn(pred_bias_list, target_margins)
        contamination_loss = contamination_loss_fn(pred_bias_list, is_control_mask)
        memory_routing_loss = memory_routing_loss_fn(gate_values, is_memory_probe_mask)

        if episode_separation_loss is None:
            episode_separation_loss = transfer_loss.new_zeros(())
        if episode_contrastive_loss is None:
            episode_contrastive_loss = transfer_loss.new_zeros(())
        loss = (
            transfer_loss
            + diversity_loss
            + margin_loss
            + contamination_loss
            + memory_routing_loss
            + episode_separation_loss
            + episode_contrastive_loss
        )
        loss.backward()
        optimizer.step()

        if epoch % args.log_every == 0:
            message = (
                f"Epoch {epoch:3d} | Loss: {loss.item():.6f} "
                f"| Xfer: {transfer_loss.item():.6f} "
                f"| Div: {diversity_loss.item():.6f} "
                f"| Marg: {margin_loss.item():.6f} "
                f"| Clean: {contamination_loss.item():.6f} "
                f"| Mem: {memory_routing_loss.item():.6f} "
                f"| Sep: {episode_separation_loss.item():.6f}"
            )
            if gate_values:
                flat_gates = torch.cat(
                    [gate.detach().float().reshape(gate.shape[0], -1) for gate in gate_values],
                    dim=-1,
                )
                message += (
                    f" | Gate mu={flat_gates.mean().item():.4f}"
                    f" sigma={flat_gates.std().item():.4f}"
                    f" min={flat_gates.min().item():.4f}"
                    f" max={flat_gates.max().item():.4f}"
                )
            print(message)

    checkpoint = {
        "checkpoint_format_version": 2,
        "context_encoder_state_dict": context_encoder.state_dict(),
        "hypernetwork_state_dict": hypernetwork.state_dict(),
        "target_layers": TARGET_SPECS,
        "target_specs": TARGET_SPECS,
        "target_dims": target_dims,
        "bridge_mode": bridge_mode,
        "context_mode": context_mode,
        "context_dim": resolved_context_dim,
        "hyper_hidden_dim": args.hyper_hidden_dim,
        "mamba_state_source": "hidden_last_token",
        "mamba_target_layer": MAMBA_TARGET_LAYER,
        "qwen_model_id": args.qwen_model_id,
        "mamba_model_id": MAMBA_MODEL_ID,
        "max_mamba_tokens": args.max_mamba_tokens,
        "episodes_file": str(episodes_path.name),
        "prompt_trace_dataset": (
            str(prompt_trace_dataset_path.name) if prompt_trace_dataset_path is not None else ""
        ),
        "bridge_config": {
            "bridge_mode": bridge_mode,
            "context_mode": context_mode,
            "context_dim": resolved_context_dim,
            "hyper_hidden_dim": args.hyper_hidden_dim,
            "skip_compressor": bool(args.skip_compressor),
            "gated_residual": bool(args.gated_residual),
            "hidden_gated_residual": bool(args.hidden_gated_residual),
            "input_gated_residual": bool(args.input_gated_residual),
            "input_residual_mixer": bool(args.input_residual_mixer),
            "token_conditioned_input_adapter": bool(args.token_conditioned_input_adapter),
            "adapter_rank": args.adapter_rank,
            "prompt_trace_dataset": (
                str(prompt_trace_dataset_path.name) if prompt_trace_dataset_path is not None else ""
            ),
            "episode_separation_loss_weight": args.episode_separation_loss_weight,
            "episode_separation_min_distance": args.episode_separation_min_distance,
            "episode_separation_distance_scale": args.episode_separation_distance_scale,
            "episode_contrastive_loss_weight": args.episode_contrastive_loss_weight,
            "episode_contrastive_dim": args.episode_contrastive_dim,
            "episode_contrastive_temp": args.episode_contrastive_temp,
            "gate_kind": args.gate_kind,
            "initial_gate": args.initial_gate,
            "diversity_loss_weight": args.diversity_loss_weight,
            "margin_loss_weight": args.margin_loss_weight,
            "default_margin": args.default_margin,
            "use_mamba_margins": bool(args.use_mamba_margins),
            "contamination_loss_weight": args.contamination_loss_weight,
            "memory_routing_loss_weight": args.memory_routing_loss_weight,
        },
    }
    if context_mode == "compressed":
        checkpoint["compressor_state_dict"] = context_encoder.state_dict()
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
    parser.add_argument("--qwen-model-id", default=DEFAULT_QWEN_MODEL_ID)
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--skip-compressor", action="store_true")
    parser.add_argument("--context-dim", type=int, default=DEFAULT_CONTEXT_DIM)
    parser.add_argument("--hyper-hidden-dim", type=int, default=DEFAULT_HYPER_HIDDEN_DIM)
    parser.add_argument("--mamba-state-cache-dir", default=DEFAULT_MAMBA_STATE_CACHE_DIR)
    parser.add_argument("--save-mamba-states", action="store_true")
    parser.add_argument("--require-cached-mamba-states", action="store_true")
    parser.add_argument("--cached-hidden-layer-count", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--gated-residual", action="store_true")
    parser.add_argument("--hidden-gated-residual", action="store_true")
    parser.add_argument("--input-gated-residual", action="store_true")
    parser.add_argument("--input-residual-mixer", action="store_true")
    parser.add_argument("--token-conditioned-input-adapter", action="store_true")
    parser.add_argument("--adapter-rank", type=int, default=DEFAULT_ADAPTER_RANK)
    parser.add_argument("--prompt-trace-dataset", default="")
    parser.add_argument("--episode-separation-loss-weight", type=float, default=0.0)
    parser.add_argument("--episode-separation-min-distance", type=float, default=0.02)
    parser.add_argument("--episode-separation-distance-scale", type=float, default=1.0)
    parser.add_argument("--episode-contrastive-loss-weight", type=float, default=0.0)
    parser.add_argument("--episode-contrastive-dim", type=int, default=128)
    parser.add_argument("--episode-contrastive-temp", type=float, default=0.1)
    parser.add_argument("--gate-kind", choices=("scalar", "vector"), default="vector")
    parser.add_argument("--initial-gate", type=float, default=0.1)
    parser.add_argument("--diversity-loss-weight", type=float, default=0.1)
    parser.add_argument("--margin-loss-weight", type=float, default=0.0)
    parser.add_argument("--default-margin", type=float, default=0.1)
    parser.add_argument("--use-mamba-margins", action="store_true")
    parser.add_argument("--contamination-loss-weight", type=float, default=0.0)
    parser.add_argument("--memory-routing-loss-weight", type=float, default=0.0)
    parser.add_argument("--log-every", type=int, default=10)
    return parser


if __name__ == "__main__":
    train_reincarnation(build_arg_parser().parse_args())
