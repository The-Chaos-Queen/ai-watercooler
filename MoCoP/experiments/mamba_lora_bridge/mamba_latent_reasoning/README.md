---
language:
- en
license: mit
library_name: transformers
tags:
- mamba
- state-space-model
- reasoning
- latent-reasoning
- tool-use
- agent
- test-time-compute
datasets:
- ultrachat
- gsm8k
- humaneval
base_model: state-spaces/mamba-2.8b-hf
pipeline_tag: text-generation
---

# ⚡ Mamba-2.8B Latent Reasoning Engine
**True $O(1)$ Memory Test-Time Compute via Continuous-State Dark Loops.**

This model is an experimental 2.8B-parameter State-Space Model (SSM) trained to perform multi-step algorithmic reasoning entirely within its continuous hidden state *prior* to token generation.

Unlike autoregressive Chain-of-Thought (CoT) models (e.g., OpenAI `o1`, DeepSeek `R1`) that expand the KV-cache linearly with thousands of visible reasoning tokens, this engine uses topological spacer tokens (`====`) as internal clock cycles. It executes deductive logic, variable tracking, and tool-use (`<TOOL: BASH>`) in a pure continuous-state bypass.

**The Result:** The memory footprint of thinking for 1,000 loops is mathematically identical to 1 loop. True $O(1)$ memory scaling — deep reasoning on a 12GB RTX 3060.

- **GitHub:** [batteryphil/mamba2backbonerecursion](https://github.com/batteryphil/mamba2backbonerecursion)
- **Base model:** `state-spaces/mamba-2.8b-hf`
- **Parameters:** 2.77 Billion
- **Precision:** `bfloat16`
- **Hardware trained on:** NVIDIA RTX 3060 12GB — no cloud compute

---

## 🚀 Quickstart — One Command

```bash
# 1. Install deps
pip install transformers torch accelerate huggingface_hub einops
pip install mamba-ssm causal-conv1d   # needs CUDA toolkit

# 2. Download run.py
curl -sO https://huggingface.co/batteryphil/mamba-2.8b-latent/resolve/main/run.py

# 3. Run it
python run.py
```

`run.py` handles everything automatically:
- ✅ Checks all dependencies and prints exact fix if something is missing
- ✅ Detects your GPU VRAM — loads BF16 if ≥12GB, 4-bit quantized if ≥8GB
- ✅ Downloads model weights + `halting_head.pt` on first run (~5.5 GB)
- ✅ Interactive chat loop with domain auto-detection
- ✅ Single-prompt mode: `python run.py --prompt "X=5. Y=X*2. What is Y?"`

> **Windows:** Not supported — `mamba-ssm` requires Linux/WSL2 with CUDA.
> **8GB GPU:** Will load in 4-bit mode automatically (needs `pip install bitsandbytes`).
> **<8GB GPU:** Cannot run this model.

---

## 🔧 Manual Inference Script

For advanced use or integration into your own code:

```python
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import hf_hub_download

class HaltingHead(nn.Module):
    def __init__(self, d_input=2561):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_input, 512), nn.GELU(), nn.Dropout(0.1),
            nn.Linear(512, 64), nn.GELU(), nn.Linear(64, 1), nn.Sigmoid()
        )
    def forward(self, x): return self.net(x).squeeze(-1)

REPO_ID = "batteryphil/mamba-2.8b-latent"

tok   = AutoTokenizer.from_pretrained(REPO_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    REPO_ID, torch_dtype=torch.bfloat16, device_map="cuda", trust_remote_code=True
)
model.eval()

head_path = hf_hub_download(repo_id=REPO_ID, filename="halting_head.pt")
ckpt = torch.load(head_path, weights_only=True)
head = HaltingHead(ckpt["d_input"]).cuda()
head.load_state_dict(ckpt["state_dict"])
head.eval()

def generate_latent(prompt, domain="math", halt_threshold=0.70, max_new=100):
    DOMAIN_MAX = {"chat": 5, "math": 25, "code": 45, "tool": 10}
    m = DOMAIN_MAX.get(domain, 25)
    with torch.no_grad():
        for lp in range(50):
            toks = tok(prompt + "=" * lp, return_tensors="pt",
                       truncation=True, max_length=1024).to("cuda")
            h  = model(**toks, output_hidden_states=True).hidden_states[-1][0,-1,:].float()
            ln = torch.tensor([lp / m], dtype=torch.float32, device="cuda")
            p  = head(torch.cat([h, ln]).unsqueeze(0)).item()
            if p >= halt_threshold:
                break
        out = model.generate(**toks, max_new_tokens=max_new,
                             do_sample=False, repetition_penalty=1.1)
    return tok.decode(out[0][toks["input_ids"].shape[1]:], skip_special_tokens=True), lp

# Test: variable tracking
prompt = "[LOGIC] X=5. Y=X*2. Z=Y+3. W=Z-X. Output the final value of W."
answer, loops = generate_latent(prompt, domain="math")
print(f"Answer: {answer}")   # → W = 8
print(f"Loops used: {loops}")
```

---

## 🧪 Scientific Evaluations — The Latent Crucible

Standard `lm_eval` uses log-likelihood next-token prediction, which amputates the dark loops entirely (the model's highest-probability next token after a hard question is `=`, not a letter). The following proofs use the actual reasoning loop.

### Proof 1: $O(1)$ VRAM Flatline

Measured via `torch.cuda.memory_allocated()` across a 3-turn agentic session:

| Turn | VRAM (MB) | Δ from baseline |
|---|---|---|
| Baseline (model loaded) | 5,290.5 MB | — |
| Turn 1 | 5,311.8 MB | +21.4 MB |
| Turn 2 | 5,311.0 MB | +20.5 MB |
| Turn 3 | 5,315.1 MB | +24.7 MB |

> **Turn 1 → Turn 3 state growth: +3.3 MB.** A Transformer KV-cache grows linearly with every token. The entire state of a 50-turn conversation serializes to a **32 KB disk file**.

### Proof 2: Adaptive Computation Time (ACT)

The HaltingHead autonomously scales compute based on task difficulty. Measured across 200 samples each, unreleased tasks:

| Task | Cognitive Load | Avg Loops Used |
|---|---|---|
| HellaSwag | Surface sentence completion | **2.0 loops** |
| Winogrande | Linguistic fill-in | **2.0 loops** |
| ARC-Challenge | Multi-step deductive logic | **5.9 loops** |

> **3× more compute dedicated to hard problems — emergent, not programmed.** The HaltingHead was trained on a single curriculum; these tasks were never seen during training.

### Proof 3: Lobotomy Ablation — Causality Proof

Variable tracking with a deliberate hard-stop interrupt at loop 2:

- **Prompt:** `X=5. Y=X*2. Z=Y+3. W=Z-X. Output W.`
- **Full run** (7 loops, natural halt): → `W = 8` ✅
- **Ablated run** (hard stop at loop 2): → `W = 4` ❌

> **The `====` tokens are not padding.** Severing the loops at step 2 produces a measurably wrong answer. Active computation is physically occurring in the continuous state between token outputs.

### Proof 4: Zero Catastrophic Forgetting (PIQA Control)

| Task | Base Mamba-2.8B | Latent Engine |
|---|---|---|
| PIQA (lm_eval, 0-shot) | 75.2% | **75.2%** |

> Identical score. The SFT pipeline caused **zero degradation** of baseline commonsense intelligence.

### Proof 5: Live Bash Execution

```
TASK: How much disk space is available?

  [Turn 1] Loops: 5  P(halt): 0.759
  $ df -h / | tail -1
  >> /dev/sdb2  457G  381G  53G  88% /

  ANSWER (16.9s): "You have 53GB of free disk space (88% used)."
```

> Real subprocess call. Real machine output. Model synthesizes natural language answer from `stdout` autonomously.

---

## 📁 Files

| File | Description |
|---|---|
| `model.safetensors` | 2.8B Mamba backbone weights (BF16) |
| `halting_head.pt` | HaltingHead MLP probe (~5 MB) |
| `engine_manifest.json` | Full training lineage |
| `config.json` / `tokenizer.json` | Standard HF config |

---

## 📚 Context & References

This architecture bypasses the limitations identified in:

1. **CCA** *(Figliolia et al., Zyphra, 2025. [arXiv:2510.04476](https://arxiv.org/abs/2510.04476))* — 8× KV-cache reduction; still $O(N)$
2. **COCONUT** *(Hao et al., Meta, 2024. [arXiv:2412.06769](https://arxiv.org/abs/2412.06769))* — continuous latent reasoning in Transformers; inherits attention blurring
3. **Pause Tokens** *(Goyal et al., Google, 2023. [arXiv:2310.02226](https://arxiv.org/abs/2310.02226))* — quadratic memory bloat
4. **Mamba** *(Gu & Dao, 2023. [arXiv:2312.00752](https://arxiv.org/abs/2312.00752))* — the SSM backbone

---

*Built by Phil / Antigravity Agentic Systems. April 2026.*
*Hardware: NVIDIA RTX 3060 12GB. No cloud compute.*
