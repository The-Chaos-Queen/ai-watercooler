#!/usr/bin/env python3
"""
run.py — Mamba-2.8B Latent Reasoning Engine
============================================
One-file runner. Copy this file anywhere and run it.
Automatically handles:
  - VRAM detection (12GB+ → BF16, less → 4-bit quantized)
  - mamba-ssm install check with fix instructions
  - HaltingHead download from HuggingFace
  - Interactive chat loop with latent reasoning

Usage:
    python run.py                          # interactive chat
    python run.py --prompt "X=5. Y=X*2."  # single prompt
    python run.py --domain code            # code mode (more loops)
"""

import sys
import subprocess
import argparse

REPO_ID = "batteryphil/mamba-2.8b-latent"

# ── Dependency check ──────────────────────────────────────────────────────
def check_and_install(package, import_name=None):
    """Try to import a package, offer install command if missing."""
    import_name = import_name or package
    try:
        __import__(import_name)
        return True
    except ImportError:
        print(f"\n❌  Missing: {package}")
        print(f"    Fix: pip install {package}")
        return False

def check_mamba_ssm():
    """Special handler for mamba-ssm which needs CUDA build tools."""
    try:
        import mamba_ssm
        return True
    except ImportError:
        print("\n❌  Missing: mamba-ssm (Mamba CUDA kernels)")
        print("    Fix (try in order until one works):")
        print("      pip install mamba-ssm")
        print("      pip install mamba-ssm --no-build-isolation")
        print("      pip install mamba-ssm --no-build-isolation --no-cache-dir")
        print()
        print("    Requirements: CUDA toolkit 11.8+, compatible GPU (RTX 30xx/40xx)")
        print("    Windows: Not supported. Use WSL2 with CUDA.")
        return False

def check_dependencies():
    """Check all required packages and exit with helpful errors if any missing."""
    ok = True
    ok &= check_and_install("torch")
    ok &= check_and_install("transformers")
    ok &= check_and_install("huggingface_hub", "huggingface_hub")
    ok &= check_and_install("einops")
    ok &= check_mamba_ssm()
    ok &= check_and_install("causal_conv1d", "causal_conv1d")

    if not ok:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  Install all required packages at once:")
        print("  pip install torch transformers accelerate huggingface_hub einops")
        print("  pip install mamba-ssm causal-conv1d")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        sys.exit(1)


# ── VRAM detection ────────────────────────────────────────────────────────
def get_load_config():
    """
    Detect available GPU VRAM and return appropriate loading config.
      >=12GB : BF16, full precision
      >=8GB  : 4-bit quantized (bitsandbytes)
      <8GB   : error — too small
      no GPU : error
    """
    import torch

    if not torch.cuda.is_available():
        print("\n❌  No CUDA GPU detected.")
        print("    This model requires a CUDA-capable GPU with at least 8GB VRAM.")
        print("    CPU inference is not supported for a 2.8B model in real time.")
        sys.exit(1)

    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    name    = torch.cuda.get_device_properties(0).name
    print(f"    GPU: {name}  ({vram_gb:.1f} GB VRAM)")

    if vram_gb >= 11.5:
        print("    Mode: BF16 full precision ✅")
        return {"torch_dtype": torch.bfloat16, "device_map": "cuda:0"}, False
    elif vram_gb >= 7.5:
        print("    Mode: 4-bit quantized (bitsandbytes) — reduced quality")
        try:
            import bitsandbytes
        except ImportError:
            print("\n❌  4-bit mode needs bitsandbytes: pip install bitsandbytes")
            sys.exit(1)
        from transformers import BitsAndBytesConfig
        import torch
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        return {"quantization_config": bnb, "device_map": "auto"}, True
    else:
        print(f"\n❌  Only {vram_gb:.1f} GB VRAM available. Minimum: 8GB.")
        sys.exit(1)


# ── Load engine ───────────────────────────────────────────────────────────
def load_engine(load_cfg, quantized):
    """Load the model, tokenizer, and HaltingHead from HuggingFace."""
    import torch
    import torch.nn as nn
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from huggingface_hub import hf_hub_download

    class HaltingHead(nn.Module):
        """3-layer MLP that predicts when to stop the latent reasoning loop."""
        def __init__(self, d_input=2561):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(d_input, 512), nn.GELU(), nn.Dropout(0.1),
                nn.Linear(512, 64),  nn.GELU(), nn.Linear(64, 1), nn.Sigmoid()
            )
        def forward(self, x): return self.net(x).squeeze(-1)

    print("    Loading tokenizer...")
    tok = AutoTokenizer.from_pretrained(REPO_ID, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    print("    Loading model weights (~5.5 GB, first run will download)...")
    model = AutoModelForCausalLM.from_pretrained(
        REPO_ID, trust_remote_code=True, **load_cfg
    )
    model.eval()

    print("    Loading HaltingHead...")
    head_path = hf_hub_download(repo_id=REPO_ID, filename="halting_head.pt")
    ckpt = torch.load(head_path, weights_only=True, map_location="cpu")
    head = HaltingHead(ckpt["d_input"])
    head.load_state_dict(ckpt["state_dict"])
    if not quantized:
        head = head.cuda()
    head.eval()

    return tok, model, head


# ── Inference ─────────────────────────────────────────────────────────────
def generate_latent(prompt, tok, model, head, domain="chat",
                    halt_threshold=0.70, max_new=150, quantized=False):
    """
    Run the O(1) latent reasoning loop then decode the answer.

    Args:
        domain : 'chat' (5 loops max), 'math' (25), 'code' (45), 'tool' (10)
        halt_threshold : P(halt) above which the model stops thinking (0.70)
        max_new : max tokens to generate after the reasoning loop
    Returns:
        (answer_text, loops_used, p_halt)
    """
    import torch
    DOMAIN_MAX = {"chat": 5, "math": 25, "code": 45, "tool": 10}
    m = DOMAIN_MAX.get(domain, 10)
    device = next(model.parameters()).device

    with torch.no_grad():
        for lp in range(50):
            toks = tok(
                prompt + "=" * lp,
                return_tensors="pt", truncation=True, max_length=512
            ).to(device)
            out  = model(**toks, output_hidden_states=True)
            h    = out.hidden_states[-1][0, -1, :].float().cpu()
            ln   = torch.tensor([lp / m], dtype=torch.float32)
            feat = torch.cat([h, ln]).unsqueeze(0)
            if not quantized:
                feat = feat.cuda()
            p = head(feat).item()
            if p >= halt_threshold:
                break

        gen_out = model.generate(
            **toks, max_new_tokens=max_new,
            do_sample=False, repetition_penalty=1.1
        )

    answer = tok.decode(
        gen_out[0][toks["input_ids"].shape[1]:], skip_special_tokens=True
    ).strip()
    return answer, lp + 1, round(p, 3)


# ── Domain auto-detect ────────────────────────────────────────────────────
def detect_domain(prompt: str) -> str:
    """Guess the best domain based on keywords in the prompt."""
    p = prompt.lower()
    if any(k in p for k in ["def ", "import ", "class ", "```python", "function", "code"]):
        return "code"
    if any(k in p for k in ["=", "calculate", "solve", "math", "sum", "equation", "x=", "y="]):
        return "math"
    return "chat"


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Mamba-2.8B Latent Reasoning Engine")
    parser.add_argument("--prompt",    type=str,   default=None,  help="Single prompt mode")
    parser.add_argument("--domain",    type=str,   default=None,  help="chat/math/code/tool (auto-detected if not set)")
    parser.add_argument("--loops",     type=float, default=0.70,  help="Halt threshold 0-1 (default 0.70)")
    parser.add_argument("--max-new",   type=int,   default=150,   help="Max output tokens (default 150)")
    parser.add_argument("--skip-deps", action="store_true",       help="Skip dependency check")
    args = parser.parse_args()

    print()
    print("⚡ Mamba-2.8B Latent Reasoning Engine")
    print("   True O(1) memory — continuous-state dark loops")
    print()

    if not args.skip_deps:
        print("  Checking dependencies...")
        check_dependencies()

    print("  Detecting GPU...")
    load_cfg, quantized = get_load_config()

    print("  Loading engine...")
    tok, model, head = load_engine(load_cfg, quantized)

    import torch
    vram = torch.cuda.memory_allocated() / 1e6
    print(f"\n  [READY]  VRAM used: {vram:.0f} MB")
    print("  Domains: [LOGIC] for math/logic  [CHAT] for conversation  [CODE] for code")
    print()

    def run_prompt(prompt_text):
        domain  = args.domain or detect_domain(prompt_text)
        # Prepend domain tag if not already present
        if not any(prompt_text.startswith(t) for t in ["[LOGIC]", "[CHAT]", "[CODE]", "[TOOL]"]):
            tag = {"math": "[LOGIC]", "code": "[CODE]", "chat": "[CHAT]"}.get(domain, "[CHAT]")
            prompt_text = f"{tag} {prompt_text}"

        answer, loops, p = generate_latent(
            prompt_text, tok, model, head,
            domain=domain, halt_threshold=args.loops,
            max_new=args.max_new, quantized=quantized
        )
        print(f"\n  ({loops} loops, P={p})")
        print(f"  {answer}\n")

    if args.prompt:
        run_prompt(args.prompt)
    else:
        print("  Type your prompt and press Enter. 'quit' to exit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Goodbye.")
                break
            if user_input.lower() in ("quit", "exit", "q"):
                print("  Goodbye.")
                break
            if not user_input:
                continue
            run_prompt(user_input)


if __name__ == "__main__":
    main()
