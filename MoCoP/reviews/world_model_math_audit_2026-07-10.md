# MoCoP World Model and Mathematics Audit

**Date:** 2026-07-10

**Status:** Phase 2 evidence published; `NO_GO_RUN_INCONSISTENT`; no bridge integration authorized

**Scope:** Formal bridge mathematics, World Model implementation state, and sequencing relative to the active Gemma/Mamba bridge lane
**Review boundary:** Repository through the 2026-07-10 spike/DC results and Watercooler posts #799-#805. The Gemma-4-31B census was still running and is not treated as evidence here.

## Implementation Update — 2026-07-11

The smallest artifact requested by this audit is now implemented in commit
`e6358a4`:

- `world_model_trace.py` defines a typed v2 pre-action/outcome trace with
  run/domain/source provenance, timestamps, normalized outcome probabilities,
  content hashes, and an explicit null observer.
- `world_model_baselines.py` provides Dirichlet-tabular, null, oracle, and
  deterministic action-shuffle estimators. The oracle is diagnostic only and
  is rejected as a reportable held-out predictor.
- `spikes/score_world_model_trace.py` fits on a separate training trace and
  scores an evaluation trace after enforcing run, episode, and source
  disjointness; prediction-before-outcome ordering; and rejection of answer-key
  or oracle leakage.
- `disposition_runner.py` no longer copies fixture
  `expected_post_correction` truth into `predicted_observation`. Uncollected
  prediction fields remain explicitly null/not-computable.

On the deterministic synthetic LS20 and tool fixtures, the held-out tabular
baseline scores `0.287682` NLL (nats) and `0.125` Brier, versus the null at
`1.386294` NLL and `1.125` Brier: improvements of `1.098612` nats and `1.0`
Brier in each domain. These figures validate the trace/scorer plumbing only;
they are not evidence that a real learned World Model works.

Package verification after integration: `314 passed, 45 deselected, 5
subtests passed`. OpenCLAW #148 owns the next falsifiable step: collect real
pre-action LS20/tool traces and publish a held-out report under the same
leakage constraints. The sidecar remains excluded from bridge loss, Gemma dose
targets, and online control.

## Phase 2 Real-Trace Update - 2026-07-11

OpenCLAW #148's falsifiable step is implemented in source commit `29abc1b` and
published at
`experiments/mamba_lora_bridge/results/world_model_phase2/phase2_real_v1/`.
The bundle contains official offline LS20 0.9.8/arcengine 0.9.3 transitions and
fixed-argv filesystem-tool transitions. Its pre-action journal records and
fsyncs the state source and frozen forecast before the environment step or tool
call, then records the outcome separately. Train/eval runs, episodes, source
groups, and seeds are disjoint.

The immutable identities are:

- source revision: `29abc1bee07d91bbe2cb2b32ea08d315613deed7`;
- pre-run manifest: `497acb5cbbea6f26afecfaf9c8f28d4bbd7cebba081e35d2f34d07ddef4facd2`;
- frozen baseline bundle: `6e96fae900fa85a12ac638df6e33d652ae6398cc8648dd143d6934679097bc7a`;
- pre-evaluation freeze: `7a7d2b856724ed29bff5e24de4b7f5db917ee746415d30cf3762980214d856d2`.

The realized sample is 352 training and 176 held-out transitions. Both domains
clear preregistered support, transition-micro, and run-macro effect gates. The
tool domain is positive against both the train-only empirical-marginal and
action-shuffle nulls on every metric in all 4/4 held-out runs. LS20 is strongly
positive in aggregate, but only 2/3 held-out runs are positive against both
nulls on NLL and class-summed multiclass Brier. That is below the frozen 0.75
run-consistency requirement, producing the honest decision
`NO_GO_RUN_INCONSISTENT`.

The result does not authorize an offline learned-observer prototype or any
bridge-loss, Gemma-dose, online action-selection, Qdrant-write, memory-routing,
or dynamic-alpha integration. A later replication must be a new preregistered
artifact with more independent LS20 runs; this bundle and its thresholds must
not be edited after seeing the result.

The verifier re-derives journal custody, source/action/outcome continuity,
materialized traces, train-frozen estimators, evaluation forecasts, scores,
decision checks, report text, and artifact hashes. It explicitly claims
internal consistency only, not independent external attestation. Verification
after integration: `355 passed, 45 deselected, 5 subtests passed`; Ruff,
byte-compilation, and whitespace checks clean.

## Executive Verdict

MoCoP has a real empirical and engineering spine. The Mamba readout, bridge, target hooks, injection runtime, disposition runner, memory gate, and focused tests are substantive. The theory is strongest where it stays close to those measured interfaces.

The World Model is not yet piped in because there is not yet a predictive World Model to pipe in. Three partial artifacts exist:

1. `friction_world_model.py` is a deterministic tag/rule selector and response linter.
2. `disposition_runner.py` reserves a ten-field `world_model` trace envelope, but almost every value is null.
3. `chat_server.py` computes surprise, activation drift, and a tension proxy for memory routing, but that proxy is not an action-conditioned prediction error and is not connected to the World Model trace.

The correct near-term move is therefore **not** to insert World Model features into the Gemma bridge training run. Build a model-free, shadow-mode prediction loop beside it, first on LS20/tool traces where state, action, and outcome are identifiable. Couple it to latent injection only after an explicit bridge x friction factorial evaluation.

Two bridge-math issues deserve resolution before interpreting a new Gemma bridge:

- the current RMS-alpha is dimension-dependent and its documented injection equation omits GQA replication;
- the trainer learns absolute `v_proj` activations and later adds them as biases, rather than learning matched counterfactual activation deltas.

The second issue is especially relevant after posts #801/#803. The learned bridge DC is empirically independent of the host spike and `v_proj` bias. DC removal is repairing a bridge-internal constant, not cancelling a Gemma architecture artifact.

## Current Experimental Boundary

### What the July 10 census established

- Qwen2.5-1.5B and Qwen3-14B have massive persistent residual spikes; Gemma-4-12B does not.
- Gemma's injection teeth `{29, 35, 41}` are outside the spike band and have ordinary residual magnitudes.
- Gemma retains a strong position-0 attention sink, so attention monitors still require position-0 masking.
- The Qwen bridge DC is essentially orthogonal to the host spike, host `v_proj` bias, and ordinary mean `v_proj` direction under the registered null test. DC/spike identity P3 is falsified.
- The earlier loader-regression alarm was retracted in post #802. Gemma requires `trust_remote_code=True`; bf16 loads, while the current remote converter and bitsandbytes 4-bit path are incompatible.
- Gemma-4-31B is a pending family/scale control. No conclusion in this audit depends on its result.

These results make Gemma's late injection geometry a green signal. They do not validate the bridge target construction or the World Model theory.

## Implemented Reality Map

| Surface | What exists | What does not exist |
|---|---|---|
| Mamba runtime | Incremental in-session `cache_params` path plus Layer-3 last-token readout; bridge can update per turn | Persisted recurrent cache across sleep/wake on the new Gemma path; verified single-env Gemma incremental loop |
| Bridge | Compressor/hypernetwork, per-layer additive `v_proj` biases, DC-removal and RMS flags | Gemma-specific recorder/trainer/runtime implementation in the committed core files; shared model-family latent contract |
| Friction v0 | Typed `CognitiveState`, `FrictionRule`, tag selection, compact prompt rendering, three hard-coded response checks | Transition model, observation model, belief distribution, rollout, likelihood, rule learning, candidate action selection |
| #130 trace | Stable JSONL envelope with ten World Model keys | Pre-action probability distribution, numeric PE, posterior update, computed friction/salience/memory fields |
| Live dual gate | Token NLL surprise, activation drift, response-direction mismatch proxy, quantile routing to memory | Connection to `world_model`; calibrated environmental prediction error; safe dynamic-alpha controller |
| LS20 | Hand-authored JSONL fixture and lexical illegal-action/confabulation scorer | Actual environment adapter, learned/symbolic transition dynamics, multi-step prediction evaluation |

Focused model-free verification during this audit: `14 passed, 5 subtests passed` for `test_friction_world_model.py` and `test_ls20_trace_scorer.py`.

## Bridge Mathematics

### M1. RMS alpha is not a width-invariant dose

The runtime computes, per token row,

```text
u = b / (||b||_2 + eps)
r_j = RMS(v_j)
delta_v_j = alpha * r_j * u
```

See `experiments/mamba_lora_bridge/models.py:1530-1538`.

Therefore:

```text
||delta_v_j||_2 / ||v_j||_2 = alpha / sqrt(d_v)
RMS(delta_v_j) / RMS(v_j)   = alpha / sqrt(d_v)
```

For Qwen `d_v=256`; for Gemma `d_v=2048`. The same nominal alpha is `sqrt(8) = 2.828` times weaker in relative value-space RMS on Gemma. This is the closed-form basis for DQ1a.

The primary intervention unit should be measured, not configured:

```text
eta_v,l = RMS(delta_V_l) / RMS(V_l)
eta_r,l = RMS(W_O,l R_l delta_V_l) / RMS(r_l)
```

`eta_r,l`, measured after GQA replication and `o_proj`, is the more meaningful delivered dose. Nominal alpha remains metadata.

### M2. GQA is missing from the framework equation

For Gemma, the bridge bias is in KV value space. With 8 KV heads, 16 query heads, and head width 256, a 2048-wide bias is repeated into a 4096-wide attention output before `o_proj`.

For token-constant fixed bias, the correct residual effect is:

```text
delta_r_l = W_O,l R_l b_l
```

where `R_l` is the KV-to-query-head replication operator. The current `W_O b` equation in `theory/unified_cognitive_framework.md:318-320` and `717-719` is dimensionally invalid on Gemma.

### M3. Tokenwise RMS scaling changes the causal identity

The framework's proof

```text
Attn(Q,K,V + 1 b^T) = Attn(Q,K,V) + 1 b^T
```

is correct for a token-constant bias in evaluation mode. The RMS runtime uses token-dependent `r_j`, so instead:

```text
delta_r_i = alpha * W_O R(u) * sum_j A_ij r_j
```

The direction remains in a one-dimensional subspace per layer, but its magnitude now depends on attention-weighted token RMS. The fixed-bias proof must not be used to describe the RMS path without this qualification.

If exact query-independent injection is desired, use a session/layer scalar RMS reference. If tokenwise magnitude modulation is desired, retain it and describe it as a low-rank attention-conditioned intervention.

### M4. The training target is an absolute activation, not a delta

The current pipeline does this:

1. `record_cheese_batch.py:99-116` records the raw last-token `v_proj` module output.
2. `train_cheese_bridge.py:489-509` trains the predicted bias toward its direction and norm.
3. `models.py:1520,1530-1538` adds that prediction to the ordinary live `v_proj` output.

In a simple decomposition,

```text
v_l(x,d) = mu_l + content_l(x) + disposition_l(d) + noise
```

the bridge is asked to reproduce `mu + content + disposition`, then add it to another live activation. The observed dominant DC is an expected failure mode of this objective. Post-hoc mean subtraction removes an unconditional output mean, but does not identify or remove scenario/content nuisance and spends model capacity learning the constant first.

The target should be defined as a matched counterfactual difference, for example:

```text
b*_l(x,d) = v_l(x,d) - v_l(x,d_neutral)
delta_m(x,d) = m(x,d) - m(x,d_neutral)
```

using the same scenario skeleton on both sides. A pre/post experiential state delta is another valid source construction when a genuine recurrent before-state exists.

This also resolves a paper/code mismatch: `RESEARCH_PAPER.md:300-306` calls the target `target_delta`, while the implementation uses an absolute activation.

### M5. The current loss mixes incomparable scales

`DirectionalLoss` combines bounded, unitless cosine loss with raw squared norm error:

```text
alpha_loss * (1 - cosine) + (1 - alpha_loss) * (||p||_2 - ||t||_2)^2
```

The `0.9/0.1` weights do not imply a 90/10 contribution because the norm term scales with activation width and magnitude. On the RMS runtime path, predicted norm is discarded by normalization anyway.

For a direction-only RMS bridge, train direction plus a separate calibrated confidence/gate. If norm must be retained for the fixed arm, use a dimensionless log-ratio or z-scored term and report each component separately.

### M6. The proposed `L_sep` and split are not implemented

The Gemma design requires contrastive disposition separation, but the committed activation-bias trainer does not have a disposition-label-aware `L_sep`. Existing episode separation and contrastive weights default to zero and target episode identity; `DiversityPreservationLoss` preserves pairwise geometry of the same absolute targets.

The stated train/eval disjointness also needs a manifest. The design proposes training on all 160 SEV items while the #130 panel references exact SEV items. Split by scenario skeleton before any recording so matched variants cannot cross the boundary.

Required controls:

- scenario/skeleton-held-out evaluation;
- disposition-label shuffle;
- Mamba-state pairing shuffle;
- untrained and constant bridge controls;
- neutral-delta zero control;
- per-tooth confidence intervals and empirical nulls.

### M7. Several formal claims are evidence ahead of identification

- A disposition-conditioned answer flip shows an intervention effect, not uniquely "precision weighting." A prior shift or decision-threshold shift fits the same observation.
- The existing CCGP script derives nested samples from one scripted session per class and reuses shared-class samples across pair tasks. It does not establish cross-condition generalization.
- Layer discrimination, readout quality, injection efficacy, and causal mediation are distinct quantities. The current four-plane zone rule correctly begins to separate them; the equations and paper claims should follow that separation.

## World Model Audit

### W1. The #130 trace is an envelope, not a prediction loop

`disposition_runner.py:641-647` creates ten nullable fields. On correction re-probes, `fill_correction_pe()` sets:

```text
predicted_observation = probe.expected_post_correction
observed_after        = generated answer
action                = "operator_correction_reprobe"
prediction_error      = null
```

See `disposition_runner.py:658-668` and `905-921`.

The expected value comes from the evaluation fixture after the test designer has labelled the correct response. It is useful rubric truth, but it is not a prediction committed by the agent before an action. Comparing an expected answer with generated prose is also not an environment transition.

The field should be renamed or removed from this path until a predictive distribution exists. At minimum, traces must distinguish:

- `not_applicable`;
- `not_collected`;
- `collected`;
- `estimator_failed`.

Using `null` for all four states makes completeness tests pass while semantic completeness remains zero.

### W2. Friction v0 is a policy-constraint scaffold

`friction_world_model.py` usefully provides inspectable types and conservative failure checks. Its honest current description is:

```text
message -> heuristic tags -> matching static rules -> prompt context
draft response -> hard-coded lexical checks -> violation score
```

It is not currently:

```text
belief -> action-conditioned transition -> predicted observation
       -> observed outcome -> likelihood/error -> posterior belief
```

Concrete gaps:

- `energy_terms` are loaded and serialized but never used by `score_response_friction()`;
- rule counters have no update path;
- `active_tensions` is initialized empty and has no producer;
- `candidate_actions` and `selected_action` have no selector;
- `identity_confidence` defaults to `0.95` rather than coming from calibrated alternatives;
- rule status is hand-authored; no held-out promotion report exists;
- scoring checks only three hard-coded violation families.

This is not a criticism of v0's size. The module explicitly says it is a small deterministic substrate. The correction is terminological and architectural: keep `PolicyConstraint`/friction separate from `TransitionHypothesis`/world dynamics.

### W3. The live tension proxy is not prediction error

`chat_server.py:1126-1169` defines:

```text
incoming_delta = hidden(user_context) - hidden(pre_context)
outcome_delta  = hidden(post_response) - hidden(user_context)
tension        = 1 - cosine(incoming_delta, outcome_delta)
```

It is wired into `evaluate_dual_gate()` at `chat_server.py:4214-4231`, thresholded, logged, and used in memory-routing metadata. It is not connected to `world_model`, and it does not currently control alpha.

There is no predicted outcome in this calculation. Orthogonal response geometry can be an appropriate answer, and aligned geometry can preserve a wrong premise. Calling the quantity `qwen_direction_mismatch` in code is accurate; calling it prediction error in theory is not.

Direct use as a dynamic-alpha sensor would also create a risky feedback loop:

- the bridge intervention changes the activations being measured;
- live Mamba accumulation updates the bridge around the response path before gate evaluation;
- layer concatenation is not normalized, so high-norm/wide layers dominate;
- near-zero deltas map to zero tension instead of "unmeasurable";
- spike/sink contamination differs by substrate;
- the controller could oscillate or learn to suppress its own sensor.

Before any controller experiment, log norms, mark undefined cases, measure under a fixed pre-action bridge state, correct the monitor per substrate, then use a lagged/clamped controller with hysteresis in offline replay.

### W4. Active-inference vocabulary currently overclaims

`theory/active_inference_reconciliation.md:8-12` places these objects in one equivalence class:

- predictive surprisal `-log p(o|b,a)`;
- a generic weighted energy score;
- variational free energy;
- expected free energy;
- friction/tension.

They are not interchangeable.

Variational free energy for latent state `s` and approximate posterior `q` is:

```text
F[q] = E_q[log q(s) - log p(o,s)]
     = KL(q(s) || p(s|o)) - log p(o)
```

It upper-bounds surprisal and contains an explicit approximate posterior and generative model. Expected free energy is prospective over policies and adds a particular preference/epistemic construction; even its formal justification is an active research question. See Millidge, Tschantz, and Buckley, *Whence the Expected Free Energy?* (`https://arxiv.org/abs/2004.08128`).

MoCoP does not need active-inference branding to justify its next engineering step. "Action-conditioned prediction plus constrained candidate selection" is narrower, testable, and sufficient. The active-inference name becomes earned when the generative model, belief approximation, preferences, and policy objective are explicit.

### W5. Dynamics, preferences, ethics, and disposition must remain separate

The current prose sometimes treats the World Model as a conscience. That conflates four functions:

1. **Dynamics:** what is likely to happen after an action.
2. **Belief:** uncertainty about the current hidden state.
3. **Preference/constraint:** what outcomes or actions are acceptable.
4. **Disposition:** how the language substrate interprets and expresses a response.

A model that bends its dynamics prediction toward desired outcomes is not ethical; it is inaccurate. An ethical gate should evaluate predictions, not rewrite them. Likewise, a bridge disposition should not become the source of factual game state.

Predicted and observed events also require strict provenance separation. A forecast must never enter Mamba/Qdrant as an experienced event merely because it was internally generated.

## Minimal Formal Contract

For the first real World Model, define:

```text
s_t       external/latent environment state
b_t(s)    belief distribution over s_t
o_t       observation with provenance
a_t       committed action
T_theta(s' | s, a)       transition model
O_theta(o | s)           observation model
C_psi(a, s, o)           separate friction/preference cost
```

Pre-action prediction:

```text
p_theta(o_{t+1} | b_t, a_t)
  = sum_s sum_s' b_t(s) T_theta(s'|s,a_t) O_theta(o_{t+1}|s')
```

Scoring after the observation:

```text
PE_log = -log p_theta(o_{t+1} | b_t, a_t)
PE_brier = sum_k (p_k - 1[o=k])^2
```

Belief update:

```text
b_{t+1}(s') proportional to O_theta(o_{t+1}|s')
                          * sum_s T_theta(s'|s,a_t)b_t(s)
```

For candidate reranking before a full planner:

```text
pi(a|b) proportional to pi_0(a|b) * exp(-C_psi(a,b)/temperature)
```

Including the base measure `pi_0` and temperature matters; otherwise energy scale and policy behavior are unidentified.

The trace must commit prediction fields before outcome fields are available. Store hashes/timestamps so tests can enforce this ordering.

## Narrow Integration Path

### Phase 0: Fix the schema without changing behavior

Create a model-free typed trace module with:

- schema and estimator version;
- observation/action provenance;
- belief alternatives and normalized probabilities;
- candidate actions and chosen action;
- pre-action prediction distribution;
- observed outcome;
- metric name, units, and score;
- posterior update;
- friction terms as a separate block;
- memory-routing decision as a downstream block;
- explicit collection status for every optional field.

Expose a `WorldModelObserver` protocol and a null implementation. The #130 runner and chat runtime should consume the protocol, not construct ad hoc dictionaries.

### Phase 1: LS20 and tool calls first

Use domains where action and outcome are externally recorded:

- LS20 environment frames and legal action sets;
- tool exit status and structured result;
- file/test operations with deterministic expected effects.

Start with an oracle symbolic baseline and an action-shuffle null. Metrics:

- one-step NLL/Brier;
- structural state-delta error;
- illegal action rate;
- state confabulation rate;
- calibration error;
- hypothesis revision after contradiction;
- repeated failed-action loops;
- multi-step rollout degradation.

Pinductor is a useful later pattern because it proposes executable POMDP candidates and retains them by belief-based likelihood, not prose plausibility (`https://arxiv.org/abs/2605.13740`). It is not a drop-in social-memory model.

### Phase 2: Friction in shadow mode

Run static rules and candidate costs without altering prompts or logits. Produce replay reports:

- which rule fired;
- whether it predicted a future failure;
- held-out improvement versus no-rule;
- false-positive cost;
- calibration by rule family.

Promote `candidate -> active` only on held-out predictive improvement with minimum support and a rollback record. User corrections are evidence with provenance, not automatically ground truth or reward.

### Phase 3: One bounded generation intervention

Compare on the same fixed traces:

1. baseline generation;
2. static friction prompt;
3. draft plus deterministic rerank/regenerate-once;
4. shuffled/irrelevant friction control.

No Mamba injection change belongs in this phase.

### Phase 4: Factorial bridge test

After the Gemma bridge has a valid target, split, dose unit, and Gate-2 runner:

```text
                 friction off   friction on
bridge off             A             B
bridge on              C             D
```

Measure task/world-model metrics and disposition metrics concurrently. This identifies whether the bridge and friction layer are complementary, redundant, or interacting destructively.

Only after cell D beats B and C without monitor degradation should friction features be considered for a separate latent adapter. Keep its basis, dose, checkpoint, and ablation independent from the autobiographical disposition bridge.

## Sequencing Relative to the Active Gemma Lane

1. Let the 31B census/download finish; the World Model work requires no GPU.
2. Do not add World Model fields to the active Gemma training batch or loss.
3. Before the expensive bridge run, decide whether #139 will keep absolute targets or switch to matched deltas. This is the highest-value math decision.
4. Create an explicit SEV skeleton split manifest before recording targets.
5. Implement `L_sep` or remove the claim that it is part of Phase 1.
6. Record delivered post-`o_proj` dose and retain nominal alpha only as configuration metadata.
7. Run the World Model schema/LS20 lane locally and model-free in parallel.
8. Join the lanes only at the registered 2x2 factorial evaluation.

## Decision Queue

- **D1, pre-training:** Absolute activation target versus matched counterfactual delta.
- **D2, DQ1a:** Adopt `eta_r = RMS(delta residual)/RMS(residual)` as primary effective dose.
- **D3, trace:** Remove fixture answer keys from `predicted_observation`; introduce explicit collection status.
- **D4, terminology:** Reserve "active inference" for a specified generative/belief/policy objective; call v0 constrained predictive control.
- **D5, ownership:** Keep the World Model as a sidecar lane until the Gemma bridge Gate-2 backend exists.

## Bottom Line

The bridge should carry disposition. The World Model should predict consequences. Friction should score constraints. Qdrant should retain attributed evidence. Those components may eventually cooperate, but they should not share a loss or an unnamed latent until each works under its own falsifiable metric.

The smallest honest next artifact is a typed pre-action trace plus an LS20/tool transition baseline. That gives the existing equations a body without putting unvalidated World Model signals into the new Gemma substrate.
