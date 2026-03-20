# Bridge Target Models — Baseline Solvability + Bridge Eval Matrix

**Locked:** 2026-03-14
**Criteria:** Base (not instruct), pure transformer (no hybrid/SSM), 7B-14B range

| # | HuggingFace ID | Size | Family | Context | Notes |
|---|----------------|------|--------|---------|-------|
| 1 | `Qwen/Qwen2.5-7B` | 7B | Qwen 2.5 | 128k | Pure dense transformer, known clean baseline |
| 2 | `meta-llama/Llama-3.1-8B` | 8B | Llama 3.1 | 128k | Industry benchmark standard |
| 3 | `Qwen/Qwen3-14B-Base` | 14B | Qwen 3 | 128k+ | Newer Qwen, pure dense (no GDN/MoE of 3.5) |
| 4 | `google/gemma-2-9b` | 9B | Gemma 2 | 8k | Pure transformer, heavily filtered training data |
| 5 | `mistralai/Mistral-Nemo-Base-2407` | 12B | Mistral | 128k | Pure transformer, joint Mistral/Nvidia |

## Usage

```bash
# D1 baseline solvability — run each model with facts in text context
python baseline_solvability_probe.py --model-id Qwen/Qwen2.5-7B
python baseline_solvability_probe.py --model-id meta-llama/Llama-3.1-8B
# etc.

# Bridge training — swap target model via CLI flag
python train_bridge.py --qwen-model-id Qwen/Qwen2.5-7B --epochs 3
```

## Rationale

- **No instruct/chat/thinking models** — instruction tuning overrides disposition with deliberation. We need gut responses, not reasoned answers.
- **No hybrid architectures** — Qwen3.5 (Gated Delta Networks), Ministral-3 (hybrid), Falcon H1 (Mamba+Transformer) all excluded. LoRA injection targets transformer attention layers; hybrid internals confuse the signal.
- **Base models only** — the LoRA should be the ONLY behavioral modifier on top of pretrained weights.
- **Multiple families** — if the bridge works across Qwen, Llama, Gemma, and Mistral, that's a generalizable result.

## Dropped Candidates

- `Qwen/Qwen3.5-9B-Base` — Gated Delta Networks + sparse MoE (hybrid)
- `mistralai/Ministral-3-8B-Base-2512` — hybrid architecture confirmed
- `unsloth/gpt-oss-20b` — MoE (sparse routing complicates LoRA injection)
- `unsloth/gemma-3-12b-it-GGUF` — instruct-tuned
- `google/gemma-2-27b` — pure but 27B too tight on A100-80GB with bridge overhead
