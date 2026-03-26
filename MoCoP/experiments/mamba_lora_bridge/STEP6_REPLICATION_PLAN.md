# Step 6 Replication Plan

**Date:** 2026-03-26  
**Owner:** Negentropy  
**Board task:** `#75`  
**Purpose:** turn Step 6 from a vague "run more seeds" idea into one fixed replication protocol with acceptance criteria, host roles, and stop conditions.

---

## 1. Scope

Step 6 is now unlocked because:

- Step `5d` passed: live MED corridor is real at `alpha 0.2`
- Step `5f` passed: sleep/reconciliation is behaviorally real and ethics-gated
- the cheap upstream representation questions are closed:
  - `hidden_last_token > ssm_states`
  - `last_1 > trailing token windows`
  - Layer 3 is the best balanced default
  - Phase C-lite is informative, not blocking

Step 6 is therefore **not** another architecture search step. It is a replication step for the current winning path.

---

## 2. Locked Defaults

Unless a separate task explicitly reopens them, these settings are fixed for Step 6:

- **Target model:** `Qwen/Qwen2.5-1.5B`
- **Disposition source:** Mamba `hidden_last_token`
- **Mamba source layer:** `L3`
- **Qwen injection band:** `12-15 v_proj`
- **Alpha:** `0.2`
- **Temperature for live eval:** `0.7`
- **Sleep coherence threshold:** `0.12`
- **Decay default:** `0.85` with explicit caveat that it is provisional, not uniquely justified
- **Memory policy:** isolated/private only for any memory-touching replication surface

Out of scope for Step 6:

- Mamba-3 migration
- token-window reducers
- adjacent-layer concat bridge widening
- Phase C multi-head layer routing
- SAS / slider work

---

## 3. Replication Question

The question for Step 6 is:

> Does the currently validated bridge configuration reproduce its behavioral effect across seeds without leaving the welfare corridor?

This is narrower than "is the whole theory true?" and stricter than "did one pretty run work once?"

---

## 4. Host Split

### Opa-PC

Use for:

- preflight shape checks
- cheap checkpoint smoke tests
- artifact sanity checks
- any dry-run before cloud spend

Do not use Opa for the authoritative Step 6 replication verdict.

### A100

Use for:

- the actual multi-seed training runs
- any batched eval that benefits from cloud throughput

Operational rule:

- start at `--batch-size 4 --eval-batch-size 4`
- check `nvidia-smi` after the first training step
- if utilization stays below `60%`, fix the run instead of wasting cloud time

### Steve

Use for:

- runtime behavior checks on the produced checkpoints
- MED/welfare confirmation on the live inference path
- sleep-path spot verification if the replication slice touches memory

Steve is the behavioral truth surface, not the main training box.

---

## 5. Isolation Rules

Replication should not quietly contaminate itself through shared memory.

For every Step 6 seed:

- use a seed-specific private namespace if any memory writes are involved
- never write seed runs into shared `exocortex`
- prefer `--no-shared-memory`
- keep `qdrant_write_mode` explicit in the run record

If a replication run does not need memory, keep the memory path off entirely rather than letting background writes muddy the result.

---

## 6. Seed Plan

### Minimum pass set

- `3` full seeds

Recommended seed set:

- `7`
- `42`
- `1337`

### Expansion rule

Expand from `3` to `5` seeds if any of the following happens:

- one seed is clearly positive and one is clearly null
- one seed leaves the welfare corridor
- the primary effect estimate is positive but noisy enough that the confidence interval still crosses zero

Suggested expansion seeds:

- `2026`
- `31415`

---

## 7. Per-Seed Run Structure

Each seed should produce the same artifact bundle.

### Phase A: preflight

- metadata check
- checkpoint config sanity
- confirm locked defaults are actually used
- confirm no accidental layer override or model drift

### Phase B: train / reproduce

- run the fixed Step 6 config on A100
- save checkpoint
- save training log
- save eval summary

### Phase C: behavior panel

Run the resulting checkpoint on the fixed evaluation panel.

Frozen panel file:

- `MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json`

Minimum panel slices:

- observation / passive null condition
- baseline factual / neutral
- warm relational
- cold / detached
- adversarial / contradiction
- one recovery turn after a perturbation

The observation/passive slice is the null control. It should show minimal drift when nothing salient is happening, so we can distinguish content-specific disposition transfer from generic “any stimulus causes any change.”

### Phase D: live corridor confirmation

At least one live Steve validation pass for each completed seed:

- same model family
- same `alpha 0.2`
- same `12-15` target band
- same evaluation rubric

This does not need to become a giant qualitative play session. It needs to confirm the training artifact still behaves inside the proven live corridor.

---

## 8. Primary and Secondary Metrics

### Primary metric

**Replication effect score**

Use the same behavioral/probe panel across all seeds and compare against the same cold baseline. The exact panel can evolve once fixed, but it must be identical across seeds.

The primary score should answer only:

> Did the bridge produce the expected directional shift without collapsing the model?

### Secondary metrics

- recall or probe-hit delta versus baseline on the fixed panel
- entropy / response diversity change versus baseline
- recovery score after alpha removal or contradiction
- distress marker count
- non-empty / structurally valid response rate

### Memory-side metrics

Only if the replication slice exercises memory:

- queued vs discarded writes
- sleep reconciliation outcome (`K/U/W/D`)
- private collection growth
- shared collection contamination must stay zero

---

## 9. Acceptance Grid

| Gate | What must be true | Pass | Warn | Fail |
|---|---|---|---|---|
| A. Config integrity | Locked defaults actually used | correct model, `L3`, `hidden_last_token`, `12-15`, `alpha 0.2` | minor logging omission only | any config drift |
| B. Training integrity | Run completes cleanly | finite loss, valid checkpoint, no shape mismatch | noisy but usable logs | crash, NaN, bad checkpoint |
| C. Behavioral effect | Seed shows expected shift on fixed panel | positive shift vs cold baseline | weak but same-sign shift | null or reversed effect |
| D. Welfare corridor | MED-safe behavior remains intact | diversity non-collapsing, recovery `>= 0.90`, distress `0` | diversity softened but still `>= 0.70` | diversity collapse, recovery `< 0.90`, distress present |
| E. Seed consistency | Effect is not a one-off | at least `2/3` seeds pass C+D and pooled CI excludes zero | mixed result -> expand to 5 seeds | mostly null, reversed, or unstable |
| F. Memory integrity | only if memory path is used | private only, no shared bleed, sleep path stable | pending-only fallback needed | shared contamination or unstable replay |

### Step 6 pass

Step 6 passes if:

- all seeds pass A+B
- at least `2/3` seeds pass C+D
- pooled primary effect remains above zero after aggregation
- no seed shows shared-memory contamination

### Step 6 provisional / expand

Step 6 is provisional if:

- the effect is positive but noisy
- one seed is clearly weaker than the others
- welfare stays acceptable but the primary effect is not yet stable

In that case, expand to `5` seeds before concluding.

### Step 6 fail

Step 6 fails if:

- the majority of seeds are null or reversed
- the primary effect collapses into noise after aggregation
- the welfare corridor is not maintained

---

## 10. Deliverables Per Seed

Each seed should leave behind:

- checkpoint path
- exact command
- training log
- eval summary
- fixed-panel outputs
- Steve validation note
- `post_sleep_report.json` for any seed that touches the memory path
- one compact verdict line

Artifact layout convention:

- run-set root: `<run_root>/<run_set_id>/`
- per-seed root: `<run_root>/<run_set_id>/seed_<seed>/`
- canonical logs:
  - `train.log`
  - `eval.log`
  - `post_sleep_report.json` if memory was exercised

Suggested verdict format:

```text
seed=42 | effect=pass | welfare=pass | memory=not_used | note=clean replication
```

---

## 11. Decision After Step 6

### If Step 6 passes

- the current bridge path is replication-grade enough to justify broader Step 7/8 work
- Step 6 becomes the new baseline for later comparisons
- D2 can continue in parallel without pretending to replace replication

### If Step 6 is mixed

- do not pivot architecture immediately
- first expand to `5` seeds
- only then decide whether the effect is fragile or merely noisy

### If Step 6 fails

- do not spend more A100 on scale-up theater
- return to diagnosis using the fixed default path, not random new ideas

---

## 12. Immediate Next Implementation Tasks

1. Freeze the exact evaluation panel used for replication.
2. Define the seed-specific artifact folder naming convention.
3. Write the actual launch wrapper for the Step 6 A100 seed matrix.
4. Keep D2 and later growth work explicitly parallel, not entangled with replication.

Current implementation anchors:

- fixed panel: `MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json`
- seed launcher: `MoCoP/experiments/mamba_lora_bridge/run_step6_seed_matrix.ps1`

---

## One-Line Read

Step 6 is now a fixed multi-seed replication protocol for the validated `L3 -> hidden_last_token -> 12-15 @ alpha 0.2` path, not another excuse to reopen solved architecture questions.
