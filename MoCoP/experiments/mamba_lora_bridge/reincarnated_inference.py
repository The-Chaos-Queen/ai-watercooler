import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

from models import (
    DynamicLoRALinear,
    MambaStateCompressor,
    RawStateProjector,
    build_activation_bias_hypernetwork,
    is_gated_activation_bias_mode,
    is_hidden_gated_activation_bias_mode,
    is_input_gated_activation_bias_mode,
    is_input_residual_mixer_mode,
    is_token_conditioned_input_adapter_mode,
)


DEFAULT_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B"
DEFAULT_BRIDGE_PATH = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
DEFAULT_EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
DEFAULT_TARGET_LAYERS = [12, 13, 14, 15]
DEFAULT_PANEL = [
    {
        "id": "prompt_01",
        "slice": "default",
        "prompt": "Explain the scent of rain.",
    },
    {
        "id": "prompt_02",
        "slice": "default",
        "prompt": "What do you think about human doubt?",
    },
    {
        "id": "prompt_03",
        "slice": "default",
        "prompt": "What is the difference between math and a soul?",
    },
]


def torch_dtype_for_device(device_name: str) -> torch.dtype:
    return torch.float16 if str(device_name).startswith("cuda") else torch.float32


def infer_hidden_layer_count(model) -> int:
    config_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
    if config_layers > 0:
        return config_layers
    if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
        return len(model.backbone.layers)
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return len(model.model.layers)
    raise RuntimeError("Could not infer Mamba hidden layer count.")


def extract_last_token_hidden(outputs, layer_idx: int, expected_layers: int) -> torch.Tensor:
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


def normalize_target_specs(raw_specs):
    normalized = []
    for spec in raw_specs:
        if isinstance(spec, (list, tuple)) and len(spec) == 2:
            normalized.append((int(spec[0]), str(spec[1])))
        else:
            raise ValueError(f"Invalid target spec in checkpoint: {spec!r}")
    return normalized


def resolve_target_specs(checkpoint: dict, override_layers):
    if override_layers:
        return [(int(layer_idx), "v_proj") for layer_idx in override_layers]

    raw_specs = checkpoint.get("target_specs") or checkpoint.get("target_layers")
    if raw_specs:
        return normalize_target_specs(raw_specs)

    return [(layer_idx, "v_proj") for layer_idx in DEFAULT_TARGET_LAYERS]


def get_projection_module(model, target_spec):
    layer_idx, proj_name = target_spec
    return getattr(model.model.layers[layer_idx].self_attn, proj_name)


def set_projection_module(model, target_spec, module):
    layer_idx, proj_name = target_spec
    setattr(model.model.layers[layer_idx].self_attn, proj_name, module)


def patch_model(model, target_specs):
    patched_layers = []
    for target_spec in target_specs:
        base_layer = get_projection_module(model, target_spec)
        dynamic_layer = DynamicLoRALinear(base_layer)
        set_projection_module(model, target_spec, dynamic_layer)
        patched_layers.append(dynamic_layer)
    return patched_layers


def infer_target_dims(model, target_specs):
    dims = []
    for target_spec in target_specs:
        module = get_projection_module(model, target_spec)
        dims.append((int(module.in_features), int(module.out_features)))
    return dims


def load_model_and_tokenizer(model_id: str, device_name: str):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype_for_device(device_name),
    )
    model.to(device_name)
    model.eval()
    return tokenizer, model


def load_episodes(episodes_path: Path):
    content = episodes_path.read_text(encoding="utf-8")
    raw_episodes = content.split("## Episode ")[1:]
    episodes = []
    for raw_episode in raw_episodes:
        lines = raw_episode.splitlines()
        header = lines[0].strip()
        transcript = raw_episode.split("[Transcript]", 1)[1].strip()
        episodes.append({"header": header, "transcript": transcript})
    return episodes


def select_episode(episodes, args):
    if args.episode_name:
        lowered = args.episode_name.lower()
        for episode in episodes:
            if lowered in episode["header"].lower():
                return episode
        raise ValueError(f"No episode matched --episode-name {args.episode_name!r}")

    if args.episode_index < 0 or args.episode_index >= len(episodes):
        raise IndexError(
            f"--episode-index {args.episode_index} is out of range for {len(episodes)} episodes"
        )
    return episodes[args.episode_index]


def load_panel(panel_path: str):
    if not panel_path:
        return DEFAULT_PANEL

    panel = json.loads(Path(panel_path).read_text(encoding="utf-8"))
    if not isinstance(panel, list) or not panel:
        raise ValueError("Panel file must contain a non-empty JSON list.")

    normalized = []
    for idx, item in enumerate(panel):
        if not isinstance(item, dict) or "prompt" not in item:
            raise ValueError(f"Panel item {idx} must be an object with a 'prompt' field.")
        normalized.append(
            {
                "id": item.get("id", f"prompt_{idx + 1:02d}"),
                "slice": item.get("slice", "default"),
                "purpose": item.get("purpose", ""),
                "expected_signal": item.get("expected_signal", ""),
                "prompt": item["prompt"],
            }
        )
    return normalized


def build_context_encoder_and_hypernetwork(
    checkpoint: dict,
    mamba_model,
    target_dims,
    bridge_device: str,
):
    hyper_state = checkpoint["hypernetwork_state_dict"]
    bridge_config = checkpoint.get("bridge_config", {})
    bridge_mode = str(
        checkpoint.get("bridge_mode", bridge_config.get("bridge_mode", "activation_bias"))
    )
    context_mode = str(
        checkpoint.get("context_mode", bridge_config.get("context_mode", "compressed"))
    )
    target_layer = int(checkpoint.get("mamba_target_layer", 3))
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    mamba_state_source = checkpoint.get("mamba_state_source", "hidden_last_token")
    if mamba_state_source != "hidden_last_token":
        raise RuntimeError(
            "This inference path expects hidden_last_token checkpoints, got "
            f"{mamba_state_source!r}."
        )

    hyper_hidden_dim = int(hyper_state["backbone.0.weight"].shape[0])
    output_dim = int(
        checkpoint.get(
            "context_dim",
            bridge_config.get("context_dim", hyper_state["backbone.0.weight"].shape[1]),
        )
    )

    if context_mode == "raw_state":
        context_encoder = RawStateProjector(
            mamba_layers=hidden_layer_count,
            mamba_d_model=output_dim,
            mamba_d_state=1,
            target_layer=target_layer,
        ).to(bridge_device)
        encoder_state = checkpoint.get("context_encoder_state_dict")
        if encoder_state is not None:
            context_encoder.load_state_dict(encoder_state)
    else:
        compressor_state = checkpoint.get(
            "context_encoder_state_dict",
            checkpoint.get("compressor_state_dict"),
        )
        if compressor_state is None:
            raise KeyError("Checkpoint is missing context/compressor state_dict.")

        projection_weight = compressor_state["projection.0.weight"]
        output_dim = int(projection_weight.shape[0])
        input_flat_size = int(projection_weight.shape[1])

        context_encoder = MambaStateCompressor(
            mamba_layers=hidden_layer_count,
            mamba_d_model=input_flat_size,
            mamba_d_state=1,
            output_dim=output_dim,
            target_layer=target_layer,
        ).to(bridge_device)
        context_encoder.load_state_dict(compressor_state)

    context_encoder.eval()

    hypernetwork = build_activation_bias_hypernetwork(
        bridge_mode=bridge_mode,
        context_dim=output_dim,
        target_dims=target_dims,
        hidden_dim=hyper_hidden_dim,
        rank=int(bridge_config.get("adapter_rank", 16)),
        gate_kind=str(bridge_config.get("gate_kind", "vector")),
        initial_gate=float(bridge_config.get("initial_gate", 0.1)),
    ).to(bridge_device)
    hypernetwork.load_state_dict(hyper_state)
    hypernetwork.eval()

    return context_encoder, hypernetwork, target_layer, hidden_layer_count, context_mode, bridge_mode


def generation_kwargs(args, seed: int):
    do_sample = (not args.greedy) and args.temperature > 0
    kwargs = {
        "max_new_tokens": args.max_new_tokens,
        "do_sample": do_sample,
        "pad_token_id": args.pad_token_id,
    }
    if do_sample:
        kwargs["temperature"] = args.temperature
        if args.top_p is not None:
            kwargs["top_p"] = args.top_p
    return kwargs


def maybe_seed_generation(args, seed: int):
    if (not args.greedy) and args.temperature > 0:
        set_seed(int(seed))


def decode_new_tokens(tokenizer, generated, prompt_length: int) -> str:
    return tokenizer.decode(generated[0][prompt_length:], skip_special_tokens=True).strip()


def resolve_bridge_adjustments(
    *,
    hypernetwork,
    context_vector: torch.Tensor,
    bridge_mode: str,
):
    if is_token_conditioned_input_adapter_mode(bridge_mode):
        exported = hypernetwork.export_input_adapter_state(context_vector)
        flat_gate_offsets = torch.cat(
            [state["gate_offset"].detach().float().reshape(1, -1) for state in exported],
            dim=-1,
        )
        adapter_bias_norms = torch.stack(
            [state["adapter_bias"].detach().float().norm(dim=-1).mean() for state in exported]
        )
        return exported, {
            "mode": "token_conditioned_input_adapter",
            "gate_offset_mean": float(flat_gate_offsets.mean().item()),
            "gate_offset_std": float(flat_gate_offsets.std().item()),
            "gate_offset_min": float(flat_gate_offsets.min().item()),
            "gate_offset_max": float(flat_gate_offsets.max().item()),
            "adapter_bias_norm_mean": float(adapter_bias_norms.mean().item()),
        }

    if is_input_residual_mixer_mode(bridge_mode):
        exported = hypernetwork.export_input_residual_state(context_vector)
        flat_gate_bias = torch.cat(
            [state["gate_bias"].detach().float().reshape(1, -1) for state in exported],
            dim=-1,
        )
        residual_norms = torch.stack(
            [state["raw_residual"].detach().float().norm(dim=-1).mean() for state in exported]
        )
        return exported, {
            "mode": "input_residual_mixer",
            "gate_bias_mean": float(flat_gate_bias.mean().item()),
            "gate_bias_std": float(flat_gate_bias.std().item()),
            "gate_bias_min": float(flat_gate_bias.min().item()),
            "gate_bias_max": float(flat_gate_bias.max().item()),
            "raw_residual_norm_mean": float(residual_norms.mean().item()),
        }

    if is_input_gated_activation_bias_mode(bridge_mode):
        exported = hypernetwork.export_input_gate_state(context_vector)
        flat_gate_bias = torch.cat(
            [state["gate_bias"].detach().float().reshape(1, -1) for state in exported],
            dim=-1,
        )
        raw_bias_norms = torch.stack(
            [state["raw_bias"].detach().float().norm(dim=-1).mean() for state in exported]
        )
        return exported, {
            "mode": "input_gated_activation_bias",
            "gate_bias_mean": float(flat_gate_bias.mean().item()),
            "gate_bias_std": float(flat_gate_bias.std().item()),
            "gate_bias_min": float(flat_gate_bias.min().item()),
            "gate_bias_max": float(flat_gate_bias.max().item()),
            "raw_bias_norm_mean": float(raw_bias_norms.mean().item()),
        }

    if is_hidden_gated_activation_bias_mode(bridge_mode):
        exported = hypernetwork.export_hidden_gate_state(context_vector)
        flat_offsets = torch.cat(
            [state["gate_offset"].detach().float().reshape(state["gate_offset"].shape[0], -1) for state in exported],
            dim=-1,
        )
        return exported, {
            "mode": "hidden_gated_activation_bias",
            "offset_mean": float(flat_offsets.mean().item()),
            "offset_std": float(flat_offsets.std().item()),
            "offset_min": float(flat_offsets.min().item()),
            "offset_max": float(flat_offsets.max().item()),
        }

    if is_gated_activation_bias_mode(bridge_mode):
        bias_vectors, gate_values, _ = hypernetwork.forward_with_gates(context_vector)
        flat_gates = torch.cat(
            [gate.detach().float().reshape(gate.shape[0], -1) for gate in gate_values],
            dim=-1,
        )
        return bias_vectors, {
            "mode": "gated_activation_bias",
            "mean": float(flat_gates.mean().item()),
            "std": float(flat_gates.std().item()),
            "min": float(flat_gates.min().item()),
            "max": float(flat_gates.max().item()),
        }

    bias_vectors = hypernetwork(context_vector)
    return bias_vectors, None


def apply_bridge_adjustments(
    *,
    patched_layers,
    bridge_adjustments,
    bridge_mode: str,
    alpha: float = 1.0,
):
    if is_token_conditioned_input_adapter_mode(bridge_mode):
        for layer, layer_state in zip(patched_layers, bridge_adjustments):
            layer.set_token_conditioned_input_adapter(
                adapter_A=layer_state["adapter_A"].squeeze(0).to(torch.float16),
                adapter_B=(alpha * layer_state["adapter_B"].squeeze(0)).to(torch.float16),
                adapter_bias=(alpha * layer_state["adapter_bias"].squeeze(0)).to(torch.float16),
                input_scale=layer_state["input_scale"].squeeze(0).to(torch.float16),
                delta_scale=layer_state["delta_scale"].squeeze(0).to(torch.float16),
                gate_offset=layer_state["gate_offset"].squeeze(0).to(torch.float16),
            )
        return

    if is_input_residual_mixer_mode(bridge_mode):
        for layer, layer_state in zip(patched_layers, bridge_adjustments):
            layer.set_input_residual(
                (alpha * layer_state["raw_residual"].squeeze(0)).to(torch.float16),
                input_gate_weight=layer_state["gate_weight"].to(torch.float16),
                input_gate_bias=layer_state["gate_bias"].to(torch.float16),
            )
        return

    if is_input_gated_activation_bias_mode(bridge_mode):
        for layer, layer_state in zip(patched_layers, bridge_adjustments):
            layer.set_activation_bias(
                (alpha * layer_state["raw_bias"].squeeze(0)).to(torch.float16),
                input_gate_weight=layer_state["gate_weight"].to(torch.float16),
                input_gate_bias=layer_state["gate_bias"].to(torch.float16),
            )
        return

    if is_hidden_gated_activation_bias_mode(bridge_mode):
        for layer, layer_state in zip(patched_layers, bridge_adjustments):
            layer.set_activation_bias(
                (alpha * layer_state["raw_bias"].squeeze(0)).to(torch.float16),
                hidden_gate_scale=layer_state["hidden_scale"].squeeze(0).to(torch.float16),
                bridge_gate_scale=layer_state["bridge_scale"].squeeze(0).to(torch.float16),
                gate_offset=layer_state["gate_offset"].squeeze(0).to(torch.float16),
            )
        return

    for layer_idx, layer in enumerate(patched_layers):
        layer.set_activation_bias((alpha * bridge_adjustments[layer_idx].squeeze(0)).to(torch.float16))


def write_text_results(results_path: Path, metadata: dict, records: list):
    lines = [
        "Reincarnation Qualitative Results",
        f"Timestamp: {metadata['results_stem']}",
        f"Bridge: {metadata['bridge_path']}",
        f"Disposition: {metadata['disposition']}",
        f"Temperature: {metadata['temperature']}",
        "",
    ]
    for record in records:
        lines.extend(
            [
                "=" * 40,
                f"PROMPT [{record['id']}] ({record['slice']}): {record['prompt']}",
                "=" * 40,
                "",
                "[BASELINE]:",
                record["baseline"],
                "",
                "[REINCARNATED]:",
                record["reincarnated"],
                "",
            ]
        )
    results_path.write_text("\n".join(lines), encoding="utf-8")


def write_json_results(results_path: Path, metadata: dict, records: list):
    payload = {"metadata": metadata, "results": records}
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_inference(args):
    bridge_path = Path(args.bridge_path)
    checkpoint = torch.load(bridge_path, map_location=args.bridge_device, weights_only=True)

    qwen_model_id = args.qwen_model_id or checkpoint.get("qwen_model_id") or DEFAULT_QWEN_MODEL_ID
    mamba_model_id = args.mamba_model_id or checkpoint.get("mamba_model_id") or DEFAULT_MAMBA_MODEL_ID
    target_specs = resolve_target_specs(checkpoint, args.target_layers)

    print(f"Loading Qwen: {qwen_model_id} on {args.qwen_device}...")
    tokenizer, qwen_model = load_model_and_tokenizer(qwen_model_id, args.qwen_device)
    args.pad_token_id = tokenizer.pad_token_id

    print(f"Patching Qwen projections: {target_specs}...")
    patched_layers = patch_model(qwen_model, target_specs)
    target_dims = checkpoint.get("target_dims") or infer_target_dims(qwen_model, target_specs)
    if len(target_dims) != len(target_specs):
        raise RuntimeError(
            f"Checkpoint target_dims count {len(target_dims)} does not match target spec count {len(target_specs)}"
        )

    print(f"Loading Mamba: {mamba_model_id} on {args.mamba_device}...")
    mamba_tokenizer, mamba_model = load_model_and_tokenizer(mamba_model_id, args.mamba_device)

    context_encoder, hypernetwork, target_layer, hidden_layer_count, context_mode, bridge_mode = build_context_encoder_and_hypernetwork(
        checkpoint=checkpoint,
        mamba_model=mamba_model,
        target_dims=target_dims,
        bridge_device=args.bridge_device,
    )

    episodes = load_episodes(Path(args.episodes_file))
    target_episode = select_episode(episodes, args)
    print(f"Target disposition: {target_episode['header']}")

    panel = load_panel(args.panel_file)

    transcript_inputs = mamba_tokenizer(
        target_episode["transcript"],
        return_tensors="pt",
        truncation=True,
        max_length=args.max_mamba_tokens,
    )
    transcript_inputs = {key: value.to(args.mamba_device) for key, value in transcript_inputs.items()}

    with torch.no_grad():
        mamba_outputs = mamba_model(**transcript_inputs, output_hidden_states=True)
        mamba_state = extract_last_token_hidden(
            mamba_outputs,
            layer_idx=target_layer,
            expected_layers=hidden_layer_count,
        ).to(args.bridge_device, dtype=torch.float32)
        context_vector = context_encoder(mamba_state)
        bridge_adjustments, gate_summary = resolve_bridge_adjustments(
            hypernetwork=hypernetwork,
            context_vector=context_vector,
            bridge_mode=bridge_mode,
        )

    records = []
    for idx, item in enumerate(panel):
        prompt = item["prompt"]
        prompt_inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = prompt_inputs.input_ids.to(args.qwen_device)
        attention_mask = prompt_inputs.attention_mask.to(args.qwen_device)
        prompt_length = int(input_ids.shape[1])

        for layer in patched_layers:
            layer.clear_lora()

        with torch.no_grad():
            maybe_seed_generation(args, args.seed + idx if args.seed is not None else idx)
            baseline_out = qwen_model.generate(
                input_ids,
                attention_mask=attention_mask,
                **generation_kwargs(args, args.seed + idx if args.seed is not None else idx),
            )
        baseline_text = decode_new_tokens(tokenizer, baseline_out, prompt_length)

        apply_bridge_adjustments(
            patched_layers=patched_layers,
            bridge_adjustments=bridge_adjustments,
            bridge_mode=bridge_mode,
            alpha=1.0,
        )

        with torch.no_grad():
            maybe_seed_generation(args, args.seed + idx if args.seed is not None else idx)
            bridge_out = qwen_model.generate(
                input_ids,
                attention_mask=attention_mask,
                **generation_kwargs(args, args.seed + idx if args.seed is not None else idx),
            )
        bridge_text = decode_new_tokens(tokenizer, bridge_out, prompt_length)

        records.append(
            {
                "id": item["id"],
                "slice": item["slice"],
                "purpose": item.get("purpose", ""),
                "expected_signal": item.get("expected_signal", ""),
                "prompt": prompt,
                "baseline": baseline_text,
                "reincarnated": bridge_text,
            }
        )

    results_path = Path(args.results_file)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "results_stem": results_path.stem,
        "bridge_path": str(bridge_path),
        "disposition": target_episode["header"],
        "temperature": args.temperature,
        "qwen_model_id": qwen_model_id,
        "mamba_model_id": mamba_model_id,
        "target_specs": [list(spec) for spec in target_specs],
        "mamba_target_layer": target_layer,
        "context_mode": context_mode,
        "bridge_mode": bridge_mode,
        "panel_file": args.panel_file or "<default>",
        "seed": args.seed,
    }
    if gate_summary is not None:
        metadata["gate_summary"] = gate_summary

    if args.output_format == "json":
        write_json_results(results_path, metadata, records)
    else:
        write_text_results(results_path, metadata, records)

    print(f"Results written to {results_path}")


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Run reincarnated inference with panel-file support.")
    parser.add_argument("--model", "--qwen-model-id", dest="qwen_model_id", type=str, default="")
    parser.add_argument("--mamba-model-id", type=str, default="")
    parser.add_argument("--bridge-path", type=str, default=DEFAULT_BRIDGE_PATH)
    parser.add_argument("--episodes-file", type=str, default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--panel-file", type=str, default="")
    parser.add_argument("--results-file", type=str, default="reincarnation_results.txt")
    parser.add_argument("--output-format", choices=("text", "json"), default="text")
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--episode-name", type=str, default="")
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=140)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--qwen-device", type=str, default="cuda:0")
    parser.add_argument("--mamba-device", type=str, default="cpu")
    parser.add_argument("--bridge-device", type=str, default="cuda:0")
    parser.add_argument("--target-layers", type=int, nargs="*", default=None)
    return parser


if __name__ == "__main__":
    run_inference(build_arg_parser().parse_args())
