# GDN / GKA Artifact Matrix

**Date:** 2026-04-03  
**Status:** starter matrix for G0. This is a reality-check sheet, not a hype sheet.

| Candidate | Family | Public weights | Architecture class | Base vs instruct | Intended runtime | Local status | Notes |
|---|---|---:|---|---|---|---|---|
| `state-spaces/mamba-2.8b-hf` | Mamba | yes | pure recurrent / SSM | base | HF transformers + mamba kernels | already in use | current MoCoP source baseline |
| `nvidia/mamba2-8b-3t-4k` | Mamba-2 | yes | pure recurrent / SSM | base | NeMo / Megatron | blocked for casual local use | real public 8B checkpoint, but not a friendly chat toy |
| `mistralai/Mamba-Codestral-7B-v0.1` | Mamba | yes | pure recurrent / SSM | instruct-ish code model | HF | probably runnable on proper box | easier specimen than NVIDIA pure 8B |
| `amazon/Mamba2-primed-HQwen3-8B-Instruct` | hybrid Mamba2 + Qwen | yes | hybrid (18 Attention / 18 Mamba-2) | instruct | vLLM / transformers | probably runnable on Steve (8B) | useful for geometry and throughput reality, not a pure GDN/GKA answer |
| `amazon/GDN-primed-HQwen3-8B-Instruct` | GDN hybrid | yes | hybrid (18 Attention / 18 GDN) | instruct | vLLM / transformers | probably runnable on Steve (8B) | Requires FLA (Flash Linear Attention) triton kernels |
| `amazon/GKA-primed-HQwen3-32B-Instruct` | GKA hybrid | yes | hybrid (32 Attention / 32 GKA) | instruct | vLLM | likely blocked | 32B model is too large for local 8GB-16GB VRAM. Needs vLLM and test-time ridge regression solver |
| `GatedDeltaNet` reference implementation | GDN | code only | recurrent / gated delta update | n/a | custom kernels / research code | inspect first | likely useful as architecture inspiration even without public chat weights |
| `Gated KalmaNet` reference implementation | GKA | paper first | recurrent / Kalman-style gated update | n/a | unknown | not verified yet | newest and most likely to be paper-heavy |

---

## Questions To Fill In

For each candidate, confirm:

1. Is there a real model card or only a paper?
2. Are there public weights or only code?
3. Is the artifact actually meant for inference, or only for pretraining / benchmarks?
4. Can Opa or Steve run it honestly?
5. Is it useful as a **source-model candidate**, or only as a **gate/update blueprint**?

---

## Working Rule

Do not upgrade any row from `unknown` to `real` until one of the following is true:

- we opened the model card
- we found a public repo with runnable code
- we verified a documented runtime path

No more architecture by rumor.
