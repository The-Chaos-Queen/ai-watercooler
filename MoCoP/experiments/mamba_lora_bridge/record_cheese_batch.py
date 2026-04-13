import argparse
import os
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-1.5B"
DEFAULT_TARGET_LAYERS = [12, 13, 14, 15]
DEFAULT_OUTPUT_DIR = "activation_sessions_1.5b"
DEFAULT_INPUT_CAPTURE_OUTPUT_DIR = "activation_sessions_1.5b_input_gate"
DEFAULT_EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"


def sanitize_episode_name(header: str) -> str:
    return (
        header.lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "")
        .replace("/", "_")
    )


def parse_target_layers(raw: str) -> list[int]:
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def resolve_output_dir_name(args: argparse.Namespace) -> str:
    if args.capture_vproj_inputs and args.output_dir == DEFAULT_OUTPUT_DIR:
        return DEFAULT_INPUT_CAPTURE_OUTPUT_DIR
    return args.output_dir


def record_episodes(args: argparse.Namespace):
    script_dir = Path(__file__).resolve().parent
    episodes_path = script_dir / args.episodes_file
    output_dir = script_dir / resolve_output_dir_name(args)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model.eval()
    expected_widths = {
        layer_idx: int(model.model.layers[layer_idx].self_attn.v_proj.out_features)
        for layer_idx in args.target_layers
    }
    expected_input_widths = {
        layer_idx: int(model.model.layers[layer_idx].self_attn.v_proj.in_features)
        for layer_idx in args.target_layers
    }

    with open(episodes_path, "r", encoding="utf-8") as f:
        content = f.read()
    episodes = content.split("## Episode ")[1:]
    
    for ep in episodes:
        lines = ep.split("\n")
        header = lines[0].strip()
        ep_name = sanitize_episode_name(header)
        transcript = ep.split("[Transcript]")[1].strip()
            
        print(f"Processing Episode: {header}...")
        inputs = tokenizer(
            transcript,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_length,
        ).to(model.device)
        activations = {}

        def get_pre_hook(layer_idx):
            def hook(module, module_in):
                if not args.capture_vproj_inputs:
                    return
                hidden_in = module_in[0] if isinstance(module_in, tuple) else module_in
                activation = hidden_in[0, -1, :].detach().cpu()
                expected_width = expected_input_widths[layer_idx]
                if int(activation.shape[-1]) != expected_width:
                    raise RuntimeError(
                        "Recorded input width does not match 1.5B v_proj input width: "
                        f"layer={layer_idx} got={int(activation.shape[-1])} "
                        f"expected={expected_width}"
                    )
                layer_payload = activations.get(layer_idx)
                if not isinstance(layer_payload, dict):
                    layer_payload = {}
                    activations[layer_idx] = layer_payload
                layer_payload["v_proj_in"] = activation
            return hook

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
                if args.capture_vproj_inputs:
                    layer_payload = activations.get(layer_idx)
                    if not isinstance(layer_payload, dict):
                        layer_payload = {}
                        activations[layer_idx] = layer_payload
                    layer_payload["v_proj_out"] = activation
                else:
                    activations[layer_idx] = activation
            return hook

        handles = []
        for layer_idx in args.target_layers:
            layer_module = model.model.layers[layer_idx].self_attn.v_proj
            if args.capture_vproj_inputs:
                handles.append(layer_module.register_forward_pre_hook(get_pre_hook(layer_idx)))
            handles.append(layer_module.register_forward_hook(get_hook(layer_idx)))

        with torch.no_grad():
            model(**inputs)

        for handle in handles:
            handle.remove()

        if args.capture_vproj_inputs:
            missing_layers = [
                layer_idx
                for layer_idx in args.target_layers
                if layer_idx not in activations
                or "v_proj_in" not in activations[layer_idx]
                or "v_proj_out" not in activations[layer_idx]
            ]
        else:
            missing_layers = [layer_idx for layer_idx in args.target_layers if layer_idx not in activations]
        if missing_layers:
            raise RuntimeError(
                "Missing recorded activations for target layers: "
                + ", ".join(str(layer_idx) for layer_idx in missing_layers)
            )

        output_path = output_dir / f"target_cheese_{ep_name}.pt"
        torch.save(activations, output_path)
        sample_layer = args.target_layers[min(1, len(args.target_layers) - 1)]
        if args.capture_vproj_inputs:
            sample_payload = activations[sample_layer]
            print(
                "  Saved: "
                f"{output_path.name} (Input dim: {sample_payload['v_proj_in'].shape[0]}, "
                f"Output dim: {sample_payload['v_proj_out'].shape[0]})"
            )
        else:
            print(f"  Saved: {output_path.name} (Dim: {activations[sample_layer].shape[0]})")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record Qwen v_proj target activations for CHEESE shaping episodes."
    )
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-layers", type=parse_target_layers, default=DEFAULT_TARGET_LAYERS)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument(
        "--capture-vproj-inputs",
        action="store_true",
        help=(
            "Record both the live v_proj input hidden state and v_proj output. "
            "If used with the default output dir, writes to "
            f"{DEFAULT_INPUT_CAPTURE_OUTPUT_DIR}."
        ),
    )
    return parser

if __name__ == "__main__":
    record_episodes(build_arg_parser().parse_args())
