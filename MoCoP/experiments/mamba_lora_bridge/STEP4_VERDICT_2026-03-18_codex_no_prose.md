# Step 4 Verdict: Constant Bias Does Not Explain The Result

**Date:** 2026-03-18
**Status:** Step 4 `PASS`; Step 1 `C3 PASS`
**Claim level:** narrow, decision-grade

---

## Question

Does the current `activation_bias` result reduce to a single learned constant bias vector with no Mamba dependence?

## Answer

No.

The available constant-bias runs do not approach the Mamba-conditioned `activation_bias` baseline. With the `C3 fixed_mean` rerun now recorded in `float16 (--no-4bit)`, the control hierarchy is:

`per-sample activation_bias > fixed_mean >> constant_bias`

| Run | Epochs | LR | Seed | Bridge PPL | Baseline PPL | Delta |
|---|---:|---:|---:|---:|---:|---:|
| fixed mean (`C3`, `--no-4bit`) | eval-only | - | `1337` | `27.0648` | `29.6920` | `-2.6272` |
| constant bias | 3 | `2e-5` | `1337` | `29.6806` | `29.7073` | `-0.0267` |
| constant bias | 3 | `2e-5` | `42` | `29.6760` | `29.7073` | `-0.0313` |
| constant bias | 10 | `5e-5` | `1337` | `29.4761` | `29.7073` | `-0.2312` |
| activation bias | 3 | `2e-5` | `1337` | `25.6667` | `29.7073` | `-4.0406` |

The best observed constant-bias improvement is about `0.23` PPL. The Mamba-conditioned activation-bias result is about `4.04` PPL.

That gap is too large to explain the current result as "just a learned static shove." The `C3` rerun also shows that a shared learned direction helps, but it does not fully explain the per-sample result.

---

## What Step 4 Proves

- A pure constant bias is not sufficient to reproduce the current `activation_bias` win.
- Something in the Mamba-conditioned path matters.
- The current `activation_bias` result is not reducible to the Step 4 control.
- Together with `C3`, the controls now show that the learned direction matters and per-sample variation adds additional gain.

---

## What Step 4 Does Not Prove

- It does **not** prove factual transfer. Held-out recall remains `0/16`.
- It does **not** prove disposition transfer. That is Step 5.
- It does **not** prove that the bridge carries rich or human-salient state. It only proves that the current result is not matched by a constant-bias baseline.
- It does **not** rescue Step 2. The raw bypass still failed end-to-end.

---

## Interpretation

The strongest safe interpretation is:

`per-sample activation_bias > fixed_mean >> constant_bias`

That is enough for a Step 4 pass and a Step 1 `C3` pass.

---

## Ladder Position

| Step | Status | Notes |
|---|---|---|
| Step 1 / C2 | `PASS` | random-bias is worse than trained activation bias from existing logs |
| Step 1 / C3 | `PASS` | `fixed_mean` rerun in `float16 (--no-4bit)` lands at `27.0648` vs baseline `29.6920` |
| Step 2 | `FAIL` | raw bypass did not beat compressed path end-to-end |
| Step 3 | `DONE` | compressed bias outputs are near-collapsed in direction |
| Step 4 | `PASS` | constant bias does not explain the activation-bias result |

Current reading:

- the channel is not empty
- the learned direction matters
- per-sample variation matters
- the current bridge is still narrow
- the compressed-path result is stronger than the raw-bypass result

---

## Recommended Next Move

1. Update the ladder to reflect `Step 1 PASS`, `Step 2 FAIL`, `Step 3 DONE`, `Step 4 PASS`.
2. Revisit the Step 2b vs Step 5 decision explicitly instead of treating Step 5 as automatic.
3. If Step 5 proceeds, carry the control hierarchy forward as the current baseline claim.

---

## Artifact Basis

- `run_constant_bias/eval_epoch_003_comparison.json`
- `run_constant_bias_seed42/eval_epoch_003_comparison.json`
- `run_constant_bias_10ep/eval_comparison_latest.json`
- `run_actbias/q25_actbias_midblock_e1.log`
- `step1_c3_fixed_mean_no4bit/eval_epoch_001_comparison.json`
- `step1_c3_fixed_mean_no4bit/step1_c3_fixed_mean_no4bit.log`
