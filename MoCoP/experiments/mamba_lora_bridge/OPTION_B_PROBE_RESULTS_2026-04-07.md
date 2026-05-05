# Option B Probe Results (2026-04-07)

Scope:
- Implement and run Option B probe on tiny fixture.
- No CUDA kernel patching.
- No selective scan API surgery.

## Artifacts

Implementation:
- `trajectory_state_spaces_probe.py`

Main reports:
- `trajectory_option_b_probe_130m_20260407_v3/option_b_probe_report.json`
- `trajectory_option_b_probe_28b_20260407/option_b_probe_report.json`

Clone path used for separate original-source context:
- `/root/state_spaces_probe/mamba`

## What was tested

For each run:
1. Original route: `MambaLMHeadModel` with `InferenceParams` tokenwise stepping.
2. HF references:
   - one-pass hook
   - tokenwise hook
3. Tiny fixture: `trajectory_sanity_tiny.md`
4. Exact threshold: cosine `>= 0.99999`

## 130m Result

Models:
- original: `state-spaces/mamba-130m`
- HF: `state-spaces/mamba-130m-hf`

Key outcomes:
- Original self-check (one-pass vs tokenwise): PASS
  - min cosine: `0.9999989`
  - final cosine: `0.9999995`
- Original tokenwise vs HF tokenwise: FAIL
  - min cosine: `0.4125509`
  - final cosine: `0.5293816`
- HF one-pass vs HF tokenwise: PASS
  - min cosine: `0.9999998`

Runtime (tokens/sec, tiny fixture):
- original tokenwise: `42.04`
- HF tokenwise: `38.29`
- HF one-pass: `936.50`

## 2.8B Result

Models:
- original: `state-spaces/mamba-2.8b`
- HF: `state-spaces/mamba-2.8b-hf`

Key outcomes:
- Original tokenwise vs HF tokenwise: FAIL
  - min cosine: `0.1788189`
  - final cosine: `0.4063163`
- HF one-pass vs HF tokenwise: PASS
  - min cosine: `0.9999988`

Original internal consistency was separately verified (one-pass vs tokenwise on layer 3):
- min cosine: `0.9999957`
- final cosine: `0.9999988`

Runtime (tokens/sec, tiny fixture):
- original tokenwise: `6.92`
- HF tokenwise: `10.00`
- HF one-pass: `343.95`

## Interpretation

Option B engine implementation is functioning as an exact recurrent runner in its own stack
(original one-pass and original tokenwise are near-identical), but it does not match the HF
`*-hf` checkpoints on hidden states in this setup.

This is consistent with the known Option B risk:
- checkpoint/API mismatch between original `state-spaces/mamba` and HF `*-hf` models

So, Option B is currently:
- technically working as an original-runtime probe
- not yet an HF-equivalent drop-in for the existing HF trajectory reference line

## Recommended next move (before Cassian)

1. Keep Option B on tiny/short slices only.
2. Decide whether to treat original-checkpoint trajectory as a separate reference family
   (not numerically equivalent to HF).
3. If HF-equivalence is mandatory, continue with a checkpoint-alignment investigation first,
   not long-run execution.
