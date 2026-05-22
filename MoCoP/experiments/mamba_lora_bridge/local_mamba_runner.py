#!/usr/bin/env python3
"""Small local prompt runner for Hugging Face Mamba-family models."""

import argparse
import sys


DEFAULT_MODEL_ID = "state-spaces/mamba2-370m"
PRESETS = {
    "mamba130m": "state-spaces/mamba-130m-hf",
    "mamba370m": "state-spaces/mamba-370m-hf",
    "mamba790m": "state-spaces/mamba-790m-hf",
    "mamba2_130m": "state-spaces/mamba2-130m",
    "mamba2_370m": "state-spaces/mamba2-370m",
    "mamba2_780m": "state-spaces/mamba2-780m",
    "latent_2p8b": "batteryphil/mamba-2.8b-latent",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local Mamba-family prompt through Hugging Face."
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face model id. Default: %(default)s",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        help="Shortcut for a known Mamba-family model id.",
    )
    parser.add_argument("--prompt", help="Single prompt. If omitted, start interactive mode.")
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument(
        "--dtype",
        choices=("auto", "bfloat16", "float16", "float32"),
        default="auto",
        help="Requested torch dtype for model load.",
    )
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Pass trust_remote_code=True when loading the model/tokenizer.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print preset model ids and exit.",
    )
    return parser


def resolve_dtype(torch_module, dtype_name: str):
    if dtype_name == "bfloat16":
        return torch_module.bfloat16
    if dtype_name == "float16":
        return torch_module.float16
    if dtype_name == "float32":
        return torch_module.float32
    if torch_module.cuda.is_available():
        return torch_module.bfloat16
    return torch_module.float32


def load_stack(model_id: str, dtype_name: str, trust_remote_code: bool):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from mamba_runtime_compat import ensure_mamba_ssm_compat

    ensure_mamba_ssm_compat()

    torch_dtype = resolve_dtype(torch, dtype_name)
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, trust_remote_code=trust_remote_code
    )
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        trust_remote_code=trust_remote_code,
    )
    model = model.to(device)
    model.eval()
    return torch, tokenizer, model, device


def generate_once(
    torch_module,
    tokenizer,
    model,
    device: str,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch_module.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.pad_token_id,
        )
    new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def interactive_loop(torch_module, tokenizer, model, device, args) -> int:
    print(f"[ready] model={args.model_id} device={device}")
    print("Type /quit to exit.")
    while True:
        try:
            prompt = input("\nPrompt> ").strip()
        except EOFError:
            print()
            return 0
        if not prompt:
            continue
        if prompt in {"/quit", "/exit"}:
            return 0
        answer = generate_once(
            torch_module,
            tokenizer,
            model,
            device,
            prompt,
            args.max_new_tokens,
            args.temperature,
            args.top_p,
        )
        print(f"\n{answer}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_presets:
        for key, value in PRESETS.items():
            print(f"{key:12} {value}")
        return 0

    if args.preset:
        args.model_id = PRESETS[args.preset]

    torch_module, tokenizer, model, device = load_stack(
        args.model_id, args.dtype, args.trust_remote_code
    )
    if args.prompt:
        answer = generate_once(
            torch_module,
            tokenizer,
            model,
            device,
            args.prompt,
            args.max_new_tokens,
            args.temperature,
            args.top_p,
        )
        print(answer)
        return 0

    return interactive_loop(torch_module, tokenizer, model, device, args)


if __name__ == "__main__":
    sys.exit(main())
