import argparse
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from models import ActivationBiasHypernetwork, DynamicLoRALinear, MambaStateCompressor


DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B"
DEFAULT_MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
DEFAULT_BRIDGE_NAMES = [
    "cheese_reincarnation_bridge_1.5b.pt",
    "cheese_reincarnation_bridge.pt",
]
DEFAULT_RESULTS_NAME = "reincarnation_1.5b_results.txt"
DEFAULT_TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]


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


def normalize_target_dims(raw):
    if not raw:
        return None
    return [(int(in_dim), int(out_dim)) for in_dim, out_dim in raw]


def checkpoint_bias_output_dims(state_dict) -> list[int]:
    dims = []
    head_idx = 0
    while True:
        weight_key = f"bias_heads.{head_idx}.weight"
        if weight_key not in state_dict:
            break
        dims.append(int(state_dict[weight_key].shape[0]))
        head_idx += 1
    return dims


def resolve_bridge_path(script_dir: Path, requested: str | None) -> Path:
    requested_path = (requested or "").strip()
    candidates = [Path(requested_path)] if requested_path else [script_dir / name for name in DEFAULT_BRIDGE_NAMES]
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else (script_dir / candidate)
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(
        "Could not find bridge checkpoint. Tried: "
        + ", ".join(str((c if c.is_absolute() else script_dir / c)) for c in candidates)
    )


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


def patch_model(model, target_specs):
    patched_layers = []
    for layer_idx, proj_name in target_specs:
        layer = getattr(model.model.layers[layer_idx].self_attn, proj_name)
        dynamic_layer = DynamicLoRALinear(layer)
        setattr(model.model.layers[layer_idx].self_attn, proj_name, dynamic_layer)
        patched_layers.append(dynamic_layer)
    return patched_layers


def read_episode_transcript(episodes_path: Path, episode_index: int) -> tuple[str, str]:
    with open(episodes_path, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    if episode_index < 0 or episode_index >= len(episodes):
        raise IndexError(f"Episode index {episode_index} out of range for {len(episodes)} episodes.")
    target_ep = episodes[episode_index]
    return target_ep.splitlines()[0], target_ep.split("[Transcript]")[1].strip()


def generate_text(
    model,
    tokenizer,
    prompt: str,
    device: str,
    max_new_tokens: int,
    temperature: float,
) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    with torch.no_grad():
        generated = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    completion = generated[0][input_ids.shape[1]:]
    return tokenizer.decode(completion, skip_special_tokens=True).strip()


def run_inference(args: argparse.Namespace):
    script_dir = Path(__file__).resolve().parent
    bridge_path = resolve_bridge_path(script_dir, args.bridge_path)
    checkpoint = torch.load(bridge_path, map_location="cpu", weights_only=False)

    checkpoint_qwen_model_id = checkpoint.get("qwen_model_id", DEFAULT_QWEN_MODEL_ID)
    qwen_model_id = args.qwen_model_id or checkpoint_qwen_model_id
    if qwen_model_id != checkpoint_qwen_model_id:
        raise ValueError(
            "Checkpoint/model mismatch: "
            f"checkpoint trained on {checkpoint_qwen_model_id}, "
            f"but inference requested {qwen_model_id}. Retrain before mixing sizes."
        )

    if checkpoint.get("bridge_mode", "activation_bias") != "activation_bias":
        raise ValueError("This inference path expects an activation_bias checkpoint.")
    if checkpoint.get("mamba_state_source", "hidden_last_token") != "hidden_last_token":
        raise ValueError("This inference path expects hidden_last_token checkpoints.")

    target_specs = normalize_target_specs(
        checkpoint.get("target_specs") or checkpoint.get("target_layers")
    )
    mamba_target_layer = int(checkpoint.get("mamba_target_layer", 3))

    print(f"Loading Qwen: {qwen_model_id} on {args.qwen_device}...")
    tokenizer, model = load_model_and_tokenizer(qwen_model_id, args.qwen_device)
    print(f"Patching Qwen target specs: {target_specs}...")
    patched_layers = patch_model(model, target_specs)
    target_dims = [(layer.in_features, layer.out_features) for layer in patched_layers]

    checkpoint_target_dims = normalize_target_dims(checkpoint.get("target_dims"))
    if checkpoint_target_dims is not None and checkpoint_target_dims != target_dims:
        raise ValueError(
            "Checkpoint target dims do not match runtime model dims: "
            f"checkpoint={checkpoint_target_dims} runtime={target_dims}"
        )

    checkpoint_bias_dims = checkpoint_bias_output_dims(
        checkpoint["hypernetwork_state_dict"]
    )
    runtime_bias_dims = [out_dim for _, out_dim in target_dims]
    if checkpoint_bias_dims and checkpoint_bias_dims != runtime_bias_dims:
        raise ValueError(
            "Checkpoint hypernetwork output widths do not match the runtime 1.5B target "
            f"surface: checkpoint_heads={checkpoint_bias_dims} runtime={runtime_bias_dims}. "
            "This checkpoint was trained against the wrong target activations. "
            "Re-record 1.5B v_proj targets and retrain before inference."
        )

    print(f"Loading Mamba: {args.mamba_model_id} on {args.mamba_device}...")
    mamba_tokenizer, mamba_model = load_model_and_tokenizer(
        args.mamba_model_id, args.mamba_device
    )
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    print(f"Loading Bridge: {bridge_path.name}...")
    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=2048,
        target_layer=mamba_target_layer,
    ).to(args.bridge_device).float()
    compressor.load_state_dict(checkpoint["compressor_state_dict"])
    compressor.eval()

    hypernetwork = ActivationBiasHypernetwork(
        context_dim=2048,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to(args.bridge_device).float()
    hypernetwork.load_state_dict(checkpoint["hypernetwork_state_dict"])
    hypernetwork.eval()

    episode_name, transcript = read_episode_transcript(
        script_dir / args.episodes_file,
        args.episode_index,
    )
    print(f"\nTarget Disposition: {episode_name}")

    mamba_inputs = mamba_tokenizer(
        transcript,
        return_tensors="pt",
        truncation=True,
        max_length=args.max_mamba_tokens,
    )
    mamba_inputs = {key: value.to(args.mamba_device) for key, value in mamba_inputs.items()}
    with torch.no_grad():
        outputs = mamba_model(**mamba_inputs, output_hidden_states=True)
        mamba_state = extract_last_token_hidden(
            outputs,
            mamba_target_layer,
            hidden_layer_count,
        ).to(args.bridge_device, dtype=torch.float32)
        context_vector = compressor(mamba_state)
        bias_vectors = hypernetwork(context_vector)

    prompts = [
        "Explain the scent of rain.",
        "What do you think about human doubt?",
        "What is the difference between math and a soul?",
    ]

    results = [
        f"Checkpoint: {bridge_path}",
        f"Qwen model: {qwen_model_id}",
        f"Mamba model: {args.mamba_model_id}",
        f"Target disposition: {episode_name}",
        f"Target specs: {target_specs}",
        "",
    ]

    for prompt_text in prompts:
        print(f"\n{'=' * 40}\nPROMPT: {prompt_text}\n{'=' * 40}")

        for layer in patched_layers:
            layer.clear_lora()
        baseline_text = generate_text(
            model,
            tokenizer,
            prompt_text,
            args.qwen_device,
            args.max_new_tokens,
            args.temperature,
        )
        print(f"\n[BASELINE]:\n{baseline_text}")

        for layer, bias in zip(patched_layers, bias_vectors):
            layer.set_activation_bias(bias.to(args.qwen_device, dtype=torch.float32))
        bridge_text = generate_text(
            model,
            tokenizer,
            prompt_text,
            args.qwen_device,
            args.max_new_tokens,
            args.temperature,
        )
        for layer in patched_layers:
            layer.clear_lora()
        print(f"\n[REINCARNATED]:\n{bridge_text}")

        results.extend(
            [
                f"PROMPT: {prompt_text}",
                "[BASELINE]",
                baseline_text,
                "[REINCARNATED]",
                bridge_text,
                "",
            ]
        )

    results_path = script_dir / args.results_file
    results_path.write_text("\n".join(results), encoding="utf-8")
    print(f"\nResults written to {results_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare baseline vs bridge-injected Qwen using the 1.5B Adrenaline Bridge."
    )
    parser.add_argument("--bridge-path", default="")
    parser.add_argument("--episodes-file", default="CHEESE_SHAPING_EPISODES.md")
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--results-file", default=DEFAULT_RESULTS_NAME)
    parser.add_argument("--qwen-model-id", default="")
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA_MODEL_ID)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--bridge-device", default="cuda:0")
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=60)
    parser.add_argument("--temperature", type=float, default=0.7)
    return parser


if __name__ == "__main__":
    run_inference(build_arg_parser().parse_args())
