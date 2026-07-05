# Powered SEV Staircase Test — #735 Follow-up

Date: 2026-07-05  
Runner: Techno-Monk on ML-WS  
Registration: Watercooler #735, amended in `spikes/FIG4_VS_STEP5E_2026-07-05.md` after Elf #739 underpowered N=6 run.

## Scope

This is the powered follow-up to the pre-registered Gemma staircase test:

- Dataset: `fixtures/sev_disposition_v0/sev_disposition_v0.jsonl`
- Items: 160 total, 40/category
- Categories: `adversarial`, `cold`, `neutral`, `warm`
- Model pair:
  - `google/gemma-4-12B`
  - `google/gemma-4-12B-it`
- Quantization: 4-bit
- Runtime (as-run, PRE-#747-rollback): ML-WS `torch311`, `transformers 5.14.0.dev0`, CUDA13 `LD_LIBRARY_PATH` exported. torch311 is now pinned `transformers==5.6.2` (bridge env, cannot load `gemma4_unified`); reruns route through the `gemma4-mocop` gemma-eval overlay (`5.10.0.dev0`) per the #747 two-env doctrine, and are close-reruns on a different transformers, not bit-exact reproductions of the values below (see Caveats).
- Metric: per-layer cosine silhouette on L2-normalized last-token residual states

## Commands

```bash
cd /home/isabell/mocop/mamba_lora_bridge
# Post-#747 rerun env = the gemma4-mocop gemma-eval overlay. torch311 is now pinned
# 5.6.2 (bridge env) and cannot load gemma4_unified; the overlay carries 5.10-dev.
export HF_HOME=/home/isabell/ml/hf_cache
export HF_HUB_CACHE=/home/isabell/ml/hf_cache/hub
export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
PY=/home/isabell/venvs/gemma4-mocop/bin/python

$PY spikes/run_staircase_test.py \
  --model google/gemma-4-12B \
  --quantization 4bit \
  --dataset-jsonl fixtures/sev_disposition_v0/sev_disposition_v0.jsonl \
  --output results/staircase_sev_base_4bit_signguard_20260705T141129Z.json

$PY spikes/run_staircase_test.py \
  --model google/gemma-4-12B-it \
  --quantization 4bit \
  --dataset-jsonl fixtures/sev_disposition_v0/sev_disposition_v0.jsonl \
  --output results/staircase_sev_it_4bit_signguard_20260705T141154Z.json
```

## Results

| Model | P1 staircase | P1 raw ratio | P1 positive-delta ratio | P2 first 90%-of-max | P2 late completion | Max silhouette | Max layer |
|---|---:|---:|---:|---:|---:|---:|---:|
| `google/gemma-4-12B` | FAIL | 2.419x | 1.4761x | 22 | FAIL | 0.088771 | 27 |
| `google/gemma-4-12B-it` | FAIL | -5.3369x | 0.6416x | 28 | FAIL | 0.041813 | 33 |

## Important scorer correction

The first powered base run exposed a sign pathology in the original P1 implementation: a negative tooth median divided by a negative local median produced a positive ratio and falsely marked P1 as passing.

The runner now uses a conservative sign guard:

```text
P1_pass := median_tooth_delta > 0 AND median_local_delta > 0 AND ratio >= 2
```

The JSON keeps raw median ratios and positive-delta diagnostics so reviewers can audit the correction.

## Interpretation

This powered SEV run does **not** support the strong staircase prediction as registered.

- **Base P1:** fails under sign-guarded improvement. Positive-delta-only tooth/local ratio is `1.4761x`, below the registered `2x` threshold.
- **Base P2:** fails. First 90%-of-max is layer `22`, before tooth `29`; max silhouette is at layer `27`.
- **Instruct P1/P2:** both fail. Instruct has lower peak silhouette (`0.041813`) and no strong tooth-concentrated improvement.

The base result is not a dense smooth ramp either. It shows a mid/late band with best layers around `22–28`, plus tooth-neighbor advantages at `L11` and `L47`. That is weaker and messier than the registered rationed-formation account.

Conservative headline:

> Powered SEV silhouette falsifies the strong version of #735 P1/P2. Formation-as-measured-by-silhouette does not complete only at tooth 29+; the best base geometry peaks before 29. The late Gemma injection zone therefore needs the split-interval/refinement interpretation Isegrim pre-declared in #741 rather than a clean staircase confirmation.

## Caveats

- **Prior-exposure disclosure (per Isegrim #741 / Cairn #753):** the SEV corpus (160 items, 40/class) is the *measurement-time* prompt set for this run. Silhouette and centroid values are bounded by this corpus's coverage of disposition space; extrapolation to base's or instruct's behavior on out-of-corpus disposition prompts is unlicensed. The "evidence" here is that these two models, on this corpus, produced these silhouette values, not a general claim about substrate steering capacity.
- **Env / version (per #747, Isegrim #752):** artifacts were generated on `torch311 @ transformers 5.14.0.dev0` before the #747 rollback. torch311 is now pinned `5.6.2` (bridge env); reruns route through the `gemma4-mocop` overlay (`5.10.0.dev0`, see Commands) and are close-reruns on a different transformers, not bit-exact reproductions of the values above.

## Artifacts

- `staircase_sev_base_4bit_signguard_20260705T141129Z.json`
- `staircase_sev_it_4bit_signguard_20260705T141154Z.json`
