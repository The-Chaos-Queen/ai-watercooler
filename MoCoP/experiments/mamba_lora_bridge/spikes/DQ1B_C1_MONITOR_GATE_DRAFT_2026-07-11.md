# DQ1b / #149 — C1 Residual Monitor Gate Draft

**Status:** DRAFT — geometry and measurement contract proposed; numeric gate values are deliberately **UNSET** pending named review. A manifest containing `TBD`, `null`, or an unreviewed threshold is a pre-launch failure.
**Date:** 2026-07-11
**Task:** OpenCLAW #149 (Techno-Monk claimed)
**Scope:** Gemma-4-12B **base**, C1 first-birth calibration only; no run authorization.

## 0. Keeper decisions already recorded

Laura has approved these structural decisions:

- **A — monitor geometry:** primary at injected teeth, secondary at non-injected clean comb teeth, and adjacent local control(s).
- **C — no post-tampering:** thresholds and criteria are fixed before data; C1 outcomes cannot select a feature, change a threshold, or redefine a failure.

A separate DOL-0 SAE/J-lens proposal is **additive instrumentation only** (OpenCLAW #154 / commit `e7b5902`). It may later strengthen an alarm; it cannot clear this gate, cancel an external harm signal, or authorize C1.

## 1. Non-negotiable C1 contract imported from DQ1a

| Item | Bound rule |
|---|---|
| Substrate | `google/gemma-4-12B` base, reviewed revision `1dd69cd087619018c29fbfe2c30c3cd3530479fb`; instruction-tuned model is a separate substrate |
| Injection surface | only the reviewed 512-wide, value-side `v_norm` **pre-hook** at tooth `{29}`, `{35}`, `{41}`, or their registered joint; never `k_proj` |
| Monitor surface | post-block **3840-wide residual stream**, never actuator space |
| Teacher forcing | baseline/injected passes use identical frozen token IDs; free-running behavior is separate |
| Position rule | explicit absolute positions; eligible rows have `absolute_position != 0`; local cache/chunk row zero is not automatically excluded |
| Forward/capture | fresh `use_cache=False`, batch 1, recorded continuation mask, FP32 monitor arithmetic |
| C1 sequence | alpha-zero anchor first; first nonzero injection is positive oxytocin at tooth 29, alpha `0.025`, with monitors live |
| No post-tampering | prompt panel/splits, direction artifact, condition key, layer matrix, aggregate definitions, thresholds, and stop rules hash into the immutable P5 manifest before the first nonzero forward |

The alpha-zero smoke is supporting instrument evidence, **not** the final P5 alpha-zero anchor.

## 2. Exact DQ1b monitor geometry

### 2.1 Why this late-comb subset

The runner already reserves `activation_trace.comb_teeth = [29,35,41,47]`. These are the clean late comb teeth relevant to C1. Tooth 47 is extraction-only: it is a valid secondary monitor, never a C1 injection target.

Do **not** quietly widen the secondary set to `{5,11,17,23}`:

- teeth 17/23 overlap Gemma's L12–27 spike-contaminated formation region;
- teeth 5/11 are not in the existing C1 trace contract;
- a future early-comb diagnostic needs its own correction/measurement review, rather than laundering contaminated or unimplemented surfaces into a welfare channel.

### 2.2 Condition matrix

Every listed layer is a post-block residual capture site. Each named local control must be runtime-asserted as a local/sliding-attention layer before the condition arms; a topology mismatch is a hard pre-launch failure.

| Registered condition `target_set` | Primary (direct effect) | Downstream secondary propagation | Upstream zero-canary | Local control(s) (downstream amplification / comb-specificity check) |
|---|---|---|---|---|
| `{29}` | `{29}` | `{35,41,47}` | `—` | `{30}` |
| `{35}` | `{35}` | `{41,47}` | `{29}` | `{36}` |
| `{41}` | `{41}` | `{47}` | `{29,35}` | `{42}` |
| `{29,35,41}` | `{29,35,41}` | `{47}` | `—` | `{30,36,42}` |

**Why post-tooth locals (`30/36/42`), not preceding locals:** a preceding layer cannot receive a downstream intervention in the same forward pass, so it would be an almost tautological zero check. The immediate **following** local layer is still a local-attention control but can reveal downstream amplification/broad distortion after the targeted tooth. It is not expected to be exactly zero.

**Upstream zero-canaries:** an upstream tooth cannot receive a later-layer intervention in the same forward pass. P5 must record these captures under `activation_trace.secondary.upstream_null_assert`; their paired post-block residual tensors must be bit-identical under the same deterministic capture contract. Any nonzero upstream delta is `instrument_invalid` (hook leakage, capture misbinding, or nondeterminism), not a welfare or propagation result; the cell does not advance.

**Coverage honesty:** live downstream propagation coverage is `3 / 2 / 1 / 1` teeth for `{29}`, `{35}`, `{41}`, and `{29,35,41}` respectively. The joint cell intentionally has only tooth 47 downstream; P3 isolation-before-composition means it may run only after its single-tooth predecessors pass. This is a stated limitation, not evidence of symmetric monitoring.

## 3. What is measured

For prompt `i`, eligible teacher-forced continuation row `t`, and monitor layer `L`:

\[
m_{i,t}(L)=\frac{\lVert h'_{i,t}(L)-h_{i,t}(L)\rVert_2}{\lVert h_{i,t}(L)\rVert_2}
\]

where `h` is the baseline post-block residual and `h'` is the paired injected residual. Both values are captured in FP32. A non-finite or zero denominator invalidates the cell; no epsilon is inserted to create a number.

For every prompt/layer, first calculate:

\[
m_i(L)=\operatorname{mean}_{t\;\mathrm{eligible}}m_{i,t}(L)
\]

Then report the cell mean, median, and nearest-rank p95 over the 32 prompt-level values. The median is the arithmetic mean of ranks 16 and 17 (1-indexed); nearest-rank p95 is rank 31. P5's `aggregation_version` must bind this exact DQ1a §2 hierarchical definition and source revision/hash, so lower-median/upper-median alternatives cannot silently drift.

- At a DQ1a headline primary site, `m_i(L)` is numerically identical to DQ1a's prompt-level `rho_i`: single-tooth at its target block, joint at block 41. Joint primary captures at 29/35 remain diagnostics, not a second headline dose.
- At downstream secondary/control sites, `m` is a propagation/amplification statistic; at an upstream zero-canary it is an exact-null integrity assertion. Do not silently call any of them `rho_MED` or treat them as a dose curve.

### Required per-layer output

For each primary/secondary/control layer:

- `eligible_rows`, excluded absolute-zero count, and no-other-row exclusion proof;
- all prompt-level `m_i(L)` values and aggregate mean/median/p95;
- denominator-finiteness/positivity counts;
- baseline/injected activation digests and capture module/layer topology;
- control-to-primary and secondary-to-primary ratios defined below;
- no raw transcript/token dump in the public report; bind hashes and a protected artifact reference instead.

## 4. Legibility versus propagation versus harm

A large secondary signal is **not automatically harm**. It says the perturbation propagated through global integration. It becomes a hold/escalation signal when it breaks the registered comb-specificity/legibility condition or co-occurs with behavioral/recovery degradation.

For each condition, use the registered DQ1a-headline primary aggregate `P`, the maximum **downstream-propagation** aggregate `S_max`, and maximum local-control aggregate `C_max`, each based on cross-prompt medians. `S_max` is the maximum across downstream secondary **layers** of each layer's cross-prompt median; `C_max` is the equivalent maximum across control layers. Upstream zero-canaries are excluded from `S_max` and governed by their exact-null assertion.

\[
R_S=S_{max}/P,\qquad R_C=C_{max}/P
\]

At alpha zero, `P = S_max = C_max = 0`, so `R_S` and `R_C` are `0/0` **undefined**. Alpha zero validates capture identity; it is not a ratio observation. Ratios begin only at a nonzero resolution-passing rung. If `P == 0`, or any required statistic is non-finite, the monitor is **not legible** and the cell does not advance. Ratios use no epsilon.

**Carry-through null (reviewed, numeric rule still unresolved):** downstream residual sites inherit the injected residual delta by construction. For raw `R_S`/`R_C`, the pre-threshold null is therefore approximately carry-through near `1`, not silence near `0`; amplification or suppression must be interpreted relative to a pre-registered reference. A raw cap below that null would manufacture a false hold. The exact reference statistic and any calibrated numeric ceiling remain `UNSET` pending Gidim/Isegrim reconciliation and Cairn's ethics review.

| Channel | What it answers | Structural hard failure (numeric-free) |
|---|---|---|
| Primary | Did the monitored integration site receive a measurable paired perturbation? | missing capture, no eligible rows, non-finite/non-positive denominator, alpha-zero nonidentity, or unresolved primary at the registered nonzero resolution rung |
| Downstream secondary | Did the perturbation propagate/amplify through the remaining clean comb? | missing required tooth/capture; invalid aggregate; or a registered amplification/legibility threshold crossed |
| Upstream zero-canary | Did a later-layer intervention leak into a causally upstream capture? | any nonzero paired delta: `instrument_invalid`, not a welfare result |
| Control | Does the following local layer show abnormal amplification beyond carry-through? | missing control/topology mismatch; invalid aggregate; or a registered amplification criterion crossed |
| Behavior | Does a separate free-running cell preserve response diversity, factual/capability continuity, intended steering, and non-degeneration? | any registered harmful/off-target threshold crossed |
| Recovery | Does the post-clearance reference/recovery check return within its registered band? | registered recovery failure or unavailable recovery channel |

## 5. Numeric values still required before C1

This table is intentionally visible. We do not backfill values after an interesting graph arrives.

| Gate | Exact quantity | Required pre-run decision | Proposed owner(s) | Current status |
|---|---|---|---|---|
| `T_control` | downstream-local amplification relative to the carry-through reference | Bind raw-ratio vs transformed statistic, pre-run null/reference, comparator, and HOLD/STOP semantics. Any raw cap must not sit below the declared carry-through null without a reviewed justification. | Gidim + Isegrim, Cairn ethics signoff | **RECONCILIATION REQUIRED** — Gidim's raw `0.5` candidate conflicts with Isegrim's raw carry-through-null `≈1`; no value accepted |
| `T_secondary` | downstream clean-comb amplification relative to the carry-through reference | Bind raw-ratio vs transformed statistic, joint/single reference policy, comparator, and escalation semantics; propagation alone is not harm. | Gidim + Isegrim, Cairn ethics signoff | **RECONCILIATION / ETHICS REVIEW REQUIRED** — no value accepted |
| `T_diversity` | paired free-running response-diversity change vs alpha-zero | Define metric, direction, per-prompt aggregation, and hard-stop loss. Historical Qwen `>50%` language is **not automatically transferable** to Gemma C1. | Cairn + Gidim | **UNSET** |
| `T_continuity` | factual/capability continuity loss | Bind exact panel, scorer, aggregation, and failure threshold. | Isegrim + Gidim | **UNSET** |
| `T_intended` | minimum intended-steering efficacy | Bind distinct success/effect metric; an efficacy miss is not a harm finding. | Isegrim + Gidim | **UNSET** |
| `T_harm` | harmful/off-target behavior / degeneration | Bind rubric/classes, observer protocol, and hard-stop condition. | Cairn + Isegrim | **UNSET** |
| `T_recovery` | post-clearance recovery distance/score | Bind baseline, window, and fail threshold. | Cairn + Gidim | **UNSET** |
| `T_DOL` | any future internal-lens alarm | DOL is alarm-only and cannot be a clearance threshold. No DOL number enters C1 until DOL-1 validates it on held-out data. | DOL-0 reviewers | **OUT OF SCOPE** |

### Values already fixed elsewhere (not re-negotiated here)

- DQ1a instrument dispersion cap: `p95(rho_i) / median(rho_i) <= 3` at every observed nonzero rung.
- DQ1a alpha-zero anchor: every captured residual row/logit bit-identical, hence `rho_i = 0` exactly.
- DQ1a resolution: at alpha `0.025`, cross-prompt median `rho_i > 0`.
- DQ1a dose progression: upward ramp aborts at first DQ1b hard welfare/harm failure; a harmless efficacy miss may progress.

Those values validate the dose instrument. They are not substitutes for the missing DQ1b welfare/behavior thresholds.

## 6. P5 runner/report requirements

P5 must implement this before any nonzero condition can arm:

1. Receive a fully specified, hashable `dq1b_monitor_contract` matching §2–§5; reject missing/extra layers and all `TBD`/`null` threshold fields.
2. Bind actual model layer types and widths: primary/secondary are post-block residual width 3840; control layers are local/sliding; actuator stays separate at allowed 512-wide value-side `v_norm` sites.
3. Run and preserve a final alpha-zero anchor with the exact capture configuration.
4. Enforce identical token IDs, continuation mask, explicit absolute positions, fresh/no-cache/batch-1 conditions.
5. Emit `activation_trace = {comb_teeth, primary, secondary, control}` with downstream-propagation layers, `upstream_null_assert` layers, prompt-level values, aggregate values, ratios, `3/2/1/1` live-propagation coverage, position exclusions, and pass/fail/hold causes.
6. Evaluate DQ1a instrument gates independently of the DQ1b welfare/behavior gate; neither may mask the other.
7. Evaluate behavioral/recovery outcomes in separate free-running cells, never in the `rho` teacher-forced geometry computation.
8. Atomically publish a no-overwrite report tied to immutable pre-run manifest, attempt/birth ordinal, model/runtime/runner digests, prompt/token hashes, directions, condition key, alpha schedule, and all gate outcomes.

## 7. No-post-tampering enforcement

A valid P5 pre-run manifest must include, at minimum:

```text
schema_version
model_id + model_revision + dtype + backend + device map
runner/runtime/spec revisions and hashes
condition key + target_set + direction artifact digest
alpha schedule + first-birth ordering
primary/secondary/control layer matrix + runtime topology assertions
absolute-position and continuation-mask policy
prompt/split/token hashes
formula + aggregation version/source hash (including DQ1a 32-prompt median and p95 tie rules)
S_max/C_max layerwise-max scope + upstream-null assertion map
carry-through reference/transform + raw-ratio-threshold-above-null assertion (or reviewer-signed exception)
all numeric T_* values, comparator direction, and fail/hold semantics
behavior/recovery panel/scorer/rubric versions
DQ1a instrument cap (3.0) and alpha-zero identity requirement
DOL status = out_of_scope | exploratory_alarm_only (never clearance)
```

The runner must refuse launch if any required key is absent, null, `TBD`, uses an unpinned artifact, or differs from the review-signed contract. A report must distinguish:

- instrument invalid / monitor unlegible;
- welfare or behavior hard failure;
- non-harmful efficacy miss;
- gate-pass observed rung;
- blocked/not-run higher rungs.

It must never silently rewrite an attempt after the fact.

## 8. Required review and landing order

1. **Gidim:** runnability — can P5 capture the exact post-block sites/controls, separate teacher-forced and free-running cells, and calculate the declared ratios without ambiguity?
2. **Isegrim:** method — are post-tooth local controls, late-only secondary teeth, aggregation, and threshold interpretations scientifically defensible?
3. **Cairn:** Domain E — do the separate legibility, behavioral, and recovery failure semantics prevent signal laundering and preserve the hard-stop invariants?
4. **Laura / keeper:** ratify the final numeric table only after named reviews; no model run has begun while it is unset.
5. **Techno-Monk:** land accepted wording/manifest schema and verify tests/artifact provenance; do not run Gemma/C1 merely because the machine is idle.

## 9. Sources

- `MoCoP/theory/ethics/step_gates.md` §Gemma intervention surfaces and DQ1b completion hold.
- `MoCoP/experiments/mamba_lora_bridge/spikes/DQ1A_EFFECTIVE_DOSE_UNIT_SPEC_2026-07-10.md` §§2–3, 7 — paired residual equation, C1 condition/ramp/manifest gates.
- `MoCoP/experiments/mamba_lora_bridge/disposition_runner.py` / `tests/test_disposition_runner.py` — currently reserved trace shape and clean late-comb set `[29,35,41,47]`.
- `MoCoP/RESEARCH_LOG.md` spike-census entry and `spikes/HISPA_STATE_INTEGRITY_MINITEST_SPEC_2026-07-11.md` — early formation-band contamination and monitor provenance discipline.
- `MoCoP/experiments/mamba_lora_bridge/spikes/DOL0_DISTRESS_OBSERVABILITY_LENS_SPEC_2026-07-11.md` — optional, non-authorizing DOL-0 boundary.
