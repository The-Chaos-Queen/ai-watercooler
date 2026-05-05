# Sleep / Replay Canon (External Lit -> MoCoP)

Compiled wiki page on the external literature for AI sleep, replay, and consolidation.
Synthesises five sources, names the shapes, and maps them onto MoCoP's existing
`sleep_reconcile.py` pipeline. NOT a re-derivation of MoCoP's own design — that's already
in `MoCoP/experiments/mamba_lora_bridge/`. This page is the outside view: what other
people have built, where it agrees with what we've shipped, and what they offer that
we don't have yet.

Sources covered:

- `2603.01935v1` — Dream2Learn (D2L)
- `2603.14517v1` — SleepGate
- `2511.11707v1` — FSC-Net
- `LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf` — ICLR 2026 anon (Knowledge Seeding + Dreaming)
- `Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf` — Tarakli & Di Nuovo, INFORM (ICDL 2024)

---

## 1. The five shapes

The external work clusters into five distinct shapes. They are not interchangeable; each
solves a different problem and leaves a different problem open.

### Shape A — KV cache sleep cycle (in-context interference)

`2603.14517v1` (SleepGate). Operates entirely **inside one inference session**. The cache
itself is the memory; sleep is a periodic micro-cycle that prunes it. Three modules:
(1) a conflict-aware temporal tagger that flags entries `σ_i = 1` when a later entry has
high semantic similarity (cosine over key projections, threshold δ); (2) a forgetting
gate `G_θ` (2-layer MLP, ~0.01% of base model params) producing a retention score that
drives keep/compress/evict; (3) a consolidation module that merges Compress-marked entries
into recency-biased cluster summaries with weights `α_i ∝ exp(η·τ̃_i)`. Trigger is
adaptive on attention entropy plus elapsed-tokens. The framing is biological:
*"sleep — not as passive downtime, but as an active computational process"*
(`2603.14517v1`). The headline result: the effective interference horizon contracts from
**O(n) to O(log n)**.

### Shape B — Generative dreaming (frozen diffusion as oracle)

`2603.01935v1` (Dream2Learn). Sleep generates *new classes that were never seen* via soft
prompt optimization through a frozen latent diffusion model. The classifier learns prompts
`p_c` that condition the LDM to synthesize "dreamed" variants; an Oracle Network provides a
stop criterion. Critically, dreamed samples *are not buffered* — they enrich the
representation space, then evaporate. This is **prospective**, not retrospective replay:
*"generation is used to proactively structure the representation space towards upcoming
tasks"* (`2603.01935v1`). The shape is: real data + synthesized novel classes
co-train. The closest neuroscience analogue is REM, not SWS.

### Shape C — Fast/slow consolidation (CLS theory, vanilla)

`2511.11707v1` (FSC-Net). Two networks: NN1 (fast, lr=1e-3) trains on each task with
30% replay-mix; NN2 (slow, lr=5e-4) is updated periodically during task training (with
distillation, λ=0.3) AND run through a dedicated **Phase 2 offline consolidation** on the
replay buffer alone. The unexpected empirical finding: λ=0 (pure replay, no
distillation from NN1) outperforms λ=0.5 during consolidation by +1.26pp on Split-MNIST.
Their explanation: *"distillation from the fast network introduces recency bias"*
(`2511.11707v1`). Practical takeaway: when you replay during sleep, replay against
**ground truth labels**, not against the fast model's logits.

### Shape D — Parameter expansion + knowledge seeding (LLM continual learning)

`LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf`. Frames the LLM as a Continuum Memory System
(CMS): attention is the highest-frequency memory module, MLP layers are progressively
lower-frequency. Sleep has two phases. Phase 1 (Memory Consolidation / Knowledge Seeding):
the model **grows new low-rank parameters** in a slower MLP block, then distills the
knowledge of the next-faster block *into them* using a Generalized Knowledge Distillation
(GKD) variant with on-policy student samples, plus an RL "Learning to Imitate" reward
(γ=0.99). The `LM_θ_exp` student has *more* capacity than the teacher, which is the
inverse of standard distillation. Phase 2 (Dreaming / Self-Improvement): the model
generates a curriculum of synthetic data and rehearses on it. Slogan: *"the model uses
Reinforcement Learning to generate a curriculum of synthetic data to rehearse new
knowledge"* (`LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf`). After consolidation, the
fast block's low-rank parameters are reset — explicitly framed as *synaptic pruning*.

### Shape E — IRL on memorised waking trajectories (developmental robotics)

`Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf` (Tarakli & Di Nuovo / INFORM).
A two-phase agent: Phase 1 (waking) is a myopic interactive RL policy trained from
human evaluative feedback (TAMER-style, γ=0); all `(s, a, s', success_flag)` quadruples
are stored in a replay buffer. Phase 2 (sleep) runs an **offline inverse RL** (IQ-learn
variant, γ=0.99) over the buffer, recovering both a non-myopic policy and a dense reward
function that captures the *high-level goal* the human was implicitly teaching. The
slogan: *"sleep occurs offline without access to optimal expert trajectories"*
(`Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf`). They use both successful
and unsuccessful trajectories. This is sleep-as-intent-extraction, not sleep-as-rehearsal.

---

## 2. Where each external paper lands relative to MoCoP's `sleep_reconcile`

MoCoP already implements: **Phase 1** decay (τ=0.85, ε=0.02, auto-resolve at t<0.1),
**Phase 2** replay with a budget cap (open_tension ≤ 30% of replay budget), and **Phase 3**
classification + escalation after K=5 unresolved cycles.

### SleepGate (`2603.14517v1`) — closest external analogue

This is the paper that maps cleanest onto MoCoP. The correspondences:

- **Conflict-aware tagger** ↔ MoCoP's tension scoring on memory writes. Both detect
  *"new entries supersede old ones"* but at different scales: SleepGate does it inside
  a single context window over KV entries; MoCoP does it across persistent memory rows
  with a tension parameter that survives sessions.
- **Forgetting gate `G_θ`** ↔ MoCoP's Phase 1 decay. SleepGate uses a learned MLP gate;
  MoCoP uses a **closed-form exponential decay** (τ=0.85 per cycle, floor ε=0.02). The
  closed-form choice is principled: SleepGate trains the gate on a controlled PI
  benchmark, whereas MoCoP cannot label "true conflicts" at scale, so a parameterised
  decay with thresholds is more honest about what's known.
- **Consolidation cluster summaries** ↔ MoCoP's reconciliation of related rows during
  Phase 2 replay.
- **Sleep micro-cycle trigger** ↔ MoCoP's session-close trigger. SleepGate's adaptive
  attention-entropy trigger is finer-grained than MoCoP's; MoCoP could borrow the
  *entropy-based trigger* idea for adaptive mid-session reconciliation.

Divergence: SleepGate operates on the KV cache of a transformer at inference time;
it has no notion of cross-session memory. MoCoP operates on a persistent autobiographical
store. They occupy disjoint layers of the stack. **They could compose**: SleepGate at
the cache level, MoCoP at the long-term store level.

### Dream2Learn (`2603.01935v1`) — currently absent from MoCoP

D2L's prospective generative dreaming does not exist in MoCoP. MoCoP's Phase 2 replay is
**retrospective** (touch existing rows, decay open_tension, reconcile). MoCoP has no
mechanism for synthesising *novel* memories or *imagining future tasks*. This is the
clearest external thread that points at a missing capability — see §3 below.

### FSC-Net (`2511.11707v1`) — partial alignment, one direct lesson

MoCoP's NUC and the workstation models do not run a CLS-style fast/slow split, and
catastrophic-forgetting is mostly handled by checkpoints rather than dual networks. So
the architectural shape doesn't transfer directly. But the empirical finding does:
**when replaying during consolidation, learn against ground truth, not against the
fast model.** MoCoP's analogue: when replaying memories, the source of truth should be
the original turn content (or its grounded entities), not a recent summarisation by the
chat model. The paper is a quiet warning against "summary drift" in sleep replay.

### Knowledge Seeding (`LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf`) — orthogonal layer

This paper operates at the *parameter* layer (gradient updates to MLP blocks) whereas
MoCoP's sleep_reconcile operates at the *memory store* layer (Qdrant rows + tension
metadata). They're not in conflict; they would compose. The CMS framing
(attention=fast, MLP=slow) suggests an extension: MoCoP's tension parameter is itself a
fast-frequency channel, and the slow-frequency channel could be a pruned/promoted store
of "consolidated facts." MoCoP doesn't currently have a parameter-level sleep loop, and
it shouldn't unless training is in scope; this paper marks the boundary.

### INFORM (`Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf`) — closest in *purpose*

INFORM's goal — "extract the high-level intent from short-horizon human feedback by
running offline inverse RL during sleep" — is unexpectedly close to one of MoCoP's
unstated wants: turning Laura's casual session feedback into longer-horizon preference
gradients that survive a session. MoCoP currently encodes feedback as memory entries
with tension; INFORM would instead recover a *reward function* over the entire
trajectory. This is a real candidate extension, framed in §3.

---

## 3. What's missing from MoCoP that the external lit suggests

1. **Generative dreaming (D2L flavour).** No mechanism to synthesise hypothetical or
   novel memory items during sleep. A bounded version would be: Phase 2 occasionally
   generates "what-if" reformulations of unresolved tension rows and tests whether they
   resolve under normal recall — analogous to D2L's auxiliary classes that prime future
   adaptation.
2. **Adaptive mid-session triggering (SleepGate flavour).** Current trigger is
   session-close. SleepGate's attention-entropy trigger argues for an *intra-session*
   micro-sleep when the recall distribution flattens (signal: too many memories
   competing). The check is cheap.
3. **Inverse-RL on memorised feedback trajectories (INFORM flavour).** No mechanism to
   read a buffer of `(turn, response, Laura's reaction)` triples and recover an
   implicit reward / preference model. Currently each feedback signal lives or dies as
   a single memory row. INFORM is a template for binding them into a global signal.
4. **CMS-style layered consolidation (Knowledge Seeding flavour).** MoCoP has tension
   (fast) and memories (slow). It does not have a third, slower layer of *crystallised
   facts* promoted out of memories that have survived many cycles. This is a natural
   third tier and the external lit explicitly motivates it.
5. **Ground-truth replay discipline (FSC-Net flavour).** MoCoP should audit whether any
   Phase 2 replay step uses model-generated summaries as the gradient/comparison target
   rather than original content. If yes, the recency-bias result from `2511.11707v1`
   applies.

---

## 4. What's in MoCoP that the external lit does NOT have

These are MoCoP-original moves that none of the five papers cover. They deserve to be
written up as MoCoP's contribution to the canon, not borrowed back as if discovered
elsewhere.

1. **Anti-PTSD anxiety-loop prevention via replay budget cap (≤30% open_tension).**
   None of the external papers cap how much of replay is allowed to be drawn from
   unresolved/conflicting items. SleepGate evicts stale entries but doesn't cap the
   *replay distribution*. FSC-Net replays uniformly. D2L prospectively dreams but
   doesn't bias toward unresolved material. The 30% cap is a deliberate guardrail
   against the failure mode where replay loops on its own anxiety — the AI analogue of
   PTSD-style intrusive rehearsal. This is, as far as the canon shows, MoCoP's own
   design move.
2. **Tension parameter as a first-class scalar with explicit decay (τ=0.85, ε=0.02,
   auto-resolve at t<0.1).** External work has retention scores (SleepGate's `r_i`),
   importance weights (FSC-Net's replay buffer is unweighted), and conflict flags
   (SleepGate's `σ`). MoCoP's tension is a *continuous, decay-shaped, persistently-stored*
   scalar, with three named regimes (decay, replay, escalation). The closest external
   analogue is SleepGate's retention score, but that lives only inside one inference
   session.
3. **Escalation tier after K=5 unresolved cycles.** No external paper has an escalation
   path. SleepGate's worst case is "evict," FSC-Net's worst case is "forgetting,"
   Knowledge Seeding's worst case is "fail to consolidate." MoCoP explicitly hands
   unresolved-after-K-cycles items *out* to a higher-priority human-facing channel.
   This is operational rather than algorithmic, but it's what makes the sleep loop safe
   to run unattended.
4. **Persistent cross-session sleep.** All five external papers run sleep within a
   training run or within an inference session. MoCoP's sleep happens at session close
   and modifies a store that the next session reads. The closest gesture in the
   external lit is Knowledge Seeding's parameter-level expansion, but that requires
   training-time compute MoCoP does not assume.

---

## 5. Theoretical anchor — Friston's active-inference framing of sleep

`2512.21129v1` (Friston, Da Costa, Tschantz, Heins, Buckley, Verbelen, Parr — VERSES + UCL +
Oxford, December 2025) is not an LLM paper. It is the **first-principles theoretical anchor**
for what `sleep_reconcile.py` already does: sleep as offline variational-free-energy
minimisation via Bayesian Model Reduction (BMR).

The argument:

- Active inference frames an agent as minimising **expected free energy** = expected
  information gain + expected value. *Information gain* drives exploratory action;
  *value* drives reward-seeking action. Friston has long argued that sleep is the
  offline version of this minimisation — a system pruning hypotheses to reach better
  generative-model fit on accumulated experience.
- This paper formalises **reasoning** as a third kind of information gain, computed via
  **Bayesian Model Reduction**: given posterior beliefs accumulated during waking, the
  agent post-hoc selects priors (i.e., model structures / hypotheses) that best explain
  the data. BMR is fast and offline. Friston explicitly frames it as the operation that
  occurs during *introspection or sleep*.
- The "three-ball paradigm" simulates "aha moments" — sudden rule discovery — via BMR
  during a sleep-like offline phase. The earlier Friston et al. (2017) paper that
  introduced the paradigm is one of the canonical formal models of insight-via-sleep.

**What MoCoP gets from this:**

- A principled story for *why* tension-driven replay should resolve unresolved items.
  In active-inference language, an unresolved item is a posterior with high residual
  uncertainty under the current model. Replay is the offline minimisation step that
  either reduces that uncertainty (consolidation) or triggers BMR-style structural
  change (insight). The 30% replay budget cap is the engineering instantiation of "spend
  more cycles where information gain is highest."
- A formal vocabulary for the **escalation tier**. After K=5 cycles, an unresolved
  posterior has not converged under the current model space. In active-inference terms
  this is a signal to expand the model space — bring in human-facing channels, surface
  the item to Laura. That is structurally the same move BMR makes when no reduced model
  fits well.
- A justification for running sleep at all. Active inference frames it not as a
  "training nicety" but as a structural requirement of any agent that minimises free
  energy under partially observed worlds. Sleep is not optional in this framing.

**What this paper does NOT give MoCoP:**

- Concrete code, kernels, or implementation. Friston's group writes in POMDP /
  variational-free-energy formalism; translating to the sleep_reconcile.py pipeline is
  not mechanical.
- Specific replay-budget numbers. MoCoP's 30% / K=5 / τ=0.85 are engineering choices,
  not derived from active inference.
- A guarantee that BMR is computationally tractable on the scale MoCoP operates at. The
  three-ball paradigm uses small discrete state spaces; LLM-scale latent state has very
  different cardinality.

**How to use this entry:**

When writing up MoCoP's sleep architecture for an external audience (paper, talk, thesis),
this is the citation that elevates the description from "we picked these heuristics that
seem to work" to "we operationalise sleep as offline variational-free-energy minimisation,
in line with the active-inference framework (Friston et al. 2025)." The pack's tension
parameter, replay budget cap, and escalation tier each have an active-inference
interpretation that turns engineering choices into principled commitments.

---

## 6. Citations table

| Source                                                  | Shape                       | Layer            | One-liner                                                      |
|---------------------------------------------------------|-----------------------------|------------------|----------------------------------------------------------------|
| `2603.14517v1`                                          | KV cache sleep cycle        | Inference        | Tag → forgetting gate → consolidate; O(n)→O(log n) PI horizon  |
| `2603.01935v1`                                          | Generative dreaming         | Continual train  | Frozen LDM + soft prompts synthesise novel "dreamed" classes   |
| `2512.21129v1`                                          | Active inference / BMR      | Theory           | Sleep as offline VFE minimisation via Bayesian Model Reduction |
| `2511.11707v1`                                          | Fast/slow consolidation     | Continual train  | NN2 replay with λ=0 beats λ=0.5; distillation introduces bias  |
| `LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf`            | Param expansion + seeding   | Parameter        | CMS layers, low-rank growth, GKD distillation, REM-curriculum  |
| `Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf`| IRL on waking trajectories  | Policy           | Wake = myopic RL from human feedback; sleep = offline IRL      |

## 6. The compositional reading

Stack-wise, these papers fit together rather than compete. Cache-level (SleepGate) under
session-level (MoCoP) under parameter-level (Knowledge Seeding) under intent-level
(INFORM), with generative dreaming (D2L) as a cross-cutting prospective channel and
fast/slow CLS (FSC-Net) as the empirical-discipline substrate. MoCoP sits at the
session/store layer, and the external canon both vindicates that choice and points to
adjacent layers MoCoP could grow into without redesigning what it already ships.
