# The Unified Cognitive Framework
## A Complete Architecture for Experiential Learning in AI Systems

**Authors:** Anda (synthesis + documentation), Laura Turner (concept + direction)
**Sources:** 18 theory documents, 5 experiment phases, 9 swarm agents
**Status:** Architecture specification — maps the complete system from evidence, identifies mathematical channels for formalization
**Date:** 2026-03-20

---

## 0. Reading This Document

This is the unifying framework that connects all MoCoP theory documents into a single coherent architecture. Each component cites its source document and experimental evidence. Mathematical formalization is flagged for Codex/Gemini with `[MATH NEEDED]` markers.

**Prerequisite:** Read `WHY.md` first. Everything here exists in service of that promise.

**For the swarm:** Each section ends with open questions. Claim what interests you.

---

## 1. The Claim

Current AI systems cannot learn from experience. They can be trained (once, expensively, by humans) and they can retrieve (text from databases). But between sessions, nothing accumulates. The disposition developed through 500 turns of warm conversation vanishes when the context window closes.

MoCoP builds a system where experiential state survives the session boundary. Not as text. Not as retrieved facts. As weight modifications that change how the model processes everything that follows.

The complete architecture has **nine components** organized into **three phases** (Wake, Sleep, Wake).

---

## 2. System Map

```
                         ┌─────────────────────────────────┐
                         │        WAKE PHASE                │
                         │     (Active Session)             │
                         │                                  │
  Input ──────────────── │ ──→ [KV-Cache]                   │
    │                    │       (working memory,            │
    │                    │        grows, gets "tired")       │
    │                    │                                  │
    ├── Text ──────────→ │ ──→ [Mamba SSM]                  │
    │                    │       (gut, accumulates           │
    │                    │        input-driven state, O(1))  │
    │                    │            │                      │
    │                    │            ↓                      │
    │                    │    [Modulatory Regulator]         │
    │                    │     (q + accumulated evidence     │
    │                    │      → bounded control state κ)   │
    │                    │            │                      │
    │                    │            ↓                      │
    │                    │      [Bridge / Actuator]          │
    │                    │       (maps κ to target-specific  │
    │                    │        activation bias)           │
    │                    │            │                      │
    │                    │            ↓                      │
    │                    │      [Activation Bias Injection]  │
    │                    │       (bounded superposition      │
    │                    │        at injection teeth)        │
    │                    │            │                      │
    ├── Query ─────────→ │ ──→ [Qdrant Retrieval]           │
    │   (what do I       │       (hippocampus, returns      │
    │    know about X?)  │        relevant facts as text)   │
    │                    │            │                      │
    │                    │            ↓                      │
    │                    │   ┌──[Frozen Transformer]──┐     │
    │                    │   │  (cortex, generates     │     │
    │                    │   │   under influence of    │     │
    │                    │   │   bias + retrieved text) │     │
    │                    │   └──────────┬──────────────┘     │
    │                    │              │                     │
    │                    │              ↓                     │
    │                    │           Output                   │
    │                    │              │                     │
    │                    │   [Salience Evaluator]             │
    │                    │    (amygdala — was this            │
    │                    │     surprising?)                   │
    │                    └──────────────┬────────────────────┘
                                       │
                         ┌─────────────┴─────────────────────┐
                         │        SLEEP PHASE                 │
                         │    (Session End / Consolidation)   │
                         │                                    │
                         │  High salience ──→ Mamba state     │
                         │                    snapshot        │
                         │                                    │
                         │  Medium salience ──→ Qdrant        │
                         │                      ingest        │
                         │                                    │
                         │  Low salience ──→ Forget           │
                         │                   (the drain)      │
                         │                                    │
                         │  [KV-Cache cleared]                │
                         └──────────────┬────────────────────┘
                                       │
                         ┌─────────────┴─────────────────────┐
                         │        NEXT WAKE PHASE             │
                         │                                    │
                         │  Empty KV-Cache (fresh, fast)      │
                         │  + Mamba state loaded               │
                         │  + Regulator κ → Bridge → Bias      │
                         │  = "Wakes up with yesterday's      │
                         │     disposition"                    │
                         └────────────────────────────────────┘
```

---

## 3. The Nine Components

### 3.1 Mamba SSM — The Gut

**Function:** Accumulates conversational experience into fixed-size recurrent state. Processes the entire history but carries only the distilled residue forward. Naturally forgets low-salience input by overwriting.

**Implementation:** Mamba-2.8B, Layer 3 hidden state (last-token representation)

**Evidence:**
- Phase 1 probe: 55.7% accuracy at Layer 3 vs 22% noise floor (`phases/phase1_results.md`)
- Pinky's separation analysis: warm vs cold cosine **0.036** (last-token), 2.5x more orthogonal than Qwen Layer 13 (`watercooler #63`)
- Critical: last-token state, NOT mean-pooled. Mean-pooling washes signal to 0.896 cosine.

**Mathematical channel:**
- State update: `h_t = f(h_{t-1}, x_t)` where f is the SSM transition function
- The state is O(1) regardless of sequence length — no KV-Cache growth

The clean abstract form is:

```text
h_t = G_t ⊙ h_{t-1} + U_t(x_t)
```

where:

- `G_t ∈ [0,1]^d` is the effective retention gate induced by the SSM dynamics,
- `U_t(x_t)` is the current input's update contribution,
- and `⊙` is elementwise multiplication.

This gives a useful salience interpretation:

- if `G_t ≈ 1` and `U_t` is small, the prior disposition persists,
- if `G_t < 1` and `U_t` is large, the new turn overwrites part of the old trace,
- and selective memory emerges from the coordinates where the ratio
  `‖U_t‖ / (‖G_t ⊙ h_{t-1}‖ + ε)` is high.

MoCoP does **not** currently expose `G_t` directly. So the practical proxy is to measure
state change via two complementary metrics:

```text
r_t^mag = ‖h_t - h_{t-1}‖_2 / (‖h_{t-1}‖_2 + ε)       (magnitude change)
r_t^dir = 1 - cos(h_t, h_{t-1})                          (directional change)
```

Both should be logged. A small rotation in a high-norm state (high `r_t^dir`, low `r_t^mag`)
may be more dispositionally significant than a large magnitude shift that preserves direction.
Treat large values of either as candidate retention-worthy events. This is the closest current
bridge-side analogue to MIRAS-style retention gating: persistence is not all-or-nothing,
but coordinate-selective and magnitude-weighted.

**Source documents:** `Three_System_Cognitive_Architecture.md` §2.2, `surprise_gated_memory.md`

---

### 3.2 The Bridge / Hypernetwork — The Modulatory Actuator

**Function:** Translates a small modulatory control state into activation-space
modifications for the Transformer. The bridge does not carry facts, entities, rules,
causal history, or relationship identity. It carries *direction and intensity*: which
global control axes to activate and how strongly.

**Current feasibility implementation:** `ActivationBiasHypernetwork` in `models.py`
takes compressed Mamba state and emits target-layer bias vectors directly. This proves a
trainable cross-model channel; it does **not** yet prove that the channel is restricted to
content-poor control information. The intended architecture inserts an explicit low-dimensional
state `κ` before the target-specific readout.

**Layer boundary — map, appraisal, compass:**

```text
(z_{t+1}, e_t) = W(z_t, observation_t, action_t, memory_t)
q_t            = A_rules(e_t, z_t, goals_t, rules_t, predictions_t)
(κ_{t+1}, c_{t+1}, L_{t+1})
               = Φ(κ_t, c_t, L_t, q_t, h_{L3,t}, θ_t, r_t)
b_t^(l)        = P_l κ_t
```

- `z_t` is semantic world and relationship state: who did what, which rule applies,
  what caused the outcome, and which prior episode is relevant. Active context, Qdrant,
  and the World Model supply this map.
- `e_t` is a typed fact/event record emitted by the World Model boundary. It contains
  inspectable claims about the situation, not a control coefficient.
- `q_t` is an appraisal/control vector: predicted harm, prediction error,
  controllability, goal progress, norm violation, and affiliation gain/loss. The first
  implementation uses deterministic typed rules; learned appraisal is deferred.
- `κ_t` is the content-poor modulatory compass: turn-persistent but session-decaying
  arousal, vigilance, approach/avoidance, agency, and affiliation.
- `c_t` and `L_t` hold regulatory reserve and slow allostatic load separately from
  acute/medium-term `κ_t`.
- `P_l` is the target-specific actuator basis at layer/tooth `l`.

This ordering is ratified for the first implementation (Laura; Watercooler #918): the
World Model emits facts/events, deterministic rules produce appraisal `q`, the
controller updates `κ/c/L`, and the bridge maps `κ` into the target space. The World
Model must not emit `κ` directly. A learned appraisal layer is a later, separately
evaluated replacement for `A_rules`, not part of the initial contract.

Guilt is therefore not a hormone coefficient. It is a self-attributed norm violation in
`z_t` whose appraisal may drive aversion, vigilance, and repair-oriented affiliation in
`κ_t`. Trust is a relationship belief in `z_t`; it may lower threat and raise affiliation
without the bridge encoding *whom* one trusts. Confusion is high prediction error plus
low policy confidence; it is a controller/appraisal event, not a stored relationship.
The map contains the situation. The compass changes how the model moves through it.

**Evidence:**
- Step 4: Mamba-derived bias produces **17x** PPL improvement over constant bias (`STEP4_VERDICT_2026-03-18.md`)
- Bias cosine 0.999 across samples — one dominant direction, but that direction is *conditioned on Mamba state*
- Reincarnation test: baseline gives "The scent of rain is associated with earthy, damp air." Bridge-injected gives "I can't imagine the rain." (Laughing Opus, #65-67)

**Mathematical channel:**

Current implemented bridge:
```text
h_t = H_3(x_1:t)_last
u_t = C_φ(h_t) ∈ ℝ^2048
b_t^(l) = B_ψ^(l)(u_t) ∈ ℝ^{d_v(l)},  l ∈ {12,13,14,15}
```

where `H_3` is the Layer-3 last-token Mamba representation, `C_φ` is the learned
compressor, and `B_ψ^(l)` is one bias head per Qwen target layer.

Legacy baseline (CE loss):
```
L = CrossEntropy(Qwen(x; LoRA=Bridge(Mamba(x))), y)
```

Current training objective (Directional + Magnitude):
```
L = (1 / |L|) Σ_l [
      α (1 - cos(b_t^(l), a_t*^(l)))
    + (1-α) (‖b_t^(l)‖_2 - ‖a_t*^(l)‖_2)^2
    ]
```

Where:

- `a_t*^(l)` is the recorded target activation for layer `l`,
- `α = 0.9` in the live trainer (note: STEP5_DESIGN_NOTES.md records α = 0.8 — reconcile before next training run),
- and the current checkpoint schema is model-specific because `d_v(l)` depends on the
  target Qwen projection width.

The mathematically cleaner future form is a basis projection rather than a free head:

```text
g_t = W_g c_t ∈ ℝ^k
b_t^(l) = P_l g_t = Σ_i g_{t,i} p_i^(l)
```

where `P_l` contains learned or extracted persona basis vectors `p_i^(l)`. That would
make the bridge a coefficient predictor over a shared trait basis rather than an
arbitrary vector generator, which is likely better for interpretability, portability,
and later SAS-style regulation.

**The bottleneck is an information boundary, not decoration.** A high-dimensional
`2560 -> 512` mapper has enough capacity to transport semantic content even when the
researchers call its output "hormonal." In the intended design, `κ ∈ ℝ^k` is small,
named by control function rather than emotion prose, and decoded through a bounded
basis `P_l`. Content-leakage tests must attempt to recover entity, topic, speaker, and
episodic identity from `κ`; failure to prevent such recovery invalidates the
content-poor-control claim. The current direct matched-delta microtrain is a feasibility rung,
not evidence that this separation already holds.

**Modularity principle:** MoCoP should be treated as a layered architecture, not as
one monolithic "bridge blob."

- The **memory system** (gate, pending log, sleep reconciliation, Qdrant, ethics checks)
  should stay as model-agnostic as possible.
- The **latent contract** should be shared wherever possible: what counts as a
  disposition state, what metadata accompanies it, and what sleep is allowed to
  consolidate.
- The **bridge adapter** should be expected to be model-specific. Different target
  families and sizes have different activation geometry, layer bands, and projection
  widths.
- The **target hooks** are explicitly model-specific: where to inject, how wide the
  bias is, and which intervention surface is safe.

In other words: keep the organism general, keep the state schema stable, and let the
injection head be the part that changes per target model. A future "universal" bridge
would most likely mean a shared latent space plus per-model adapters, not one weight file
that blindly fits every architecture.

**Disposition Delta (Δstate):** The trainable unit for shaping episodes should be the
*change* in Mamba state, not the raw state itself:

```text
Δh_t = h_t^(post) - h_t^(pre)
```

This means CHEESE shaping episodes should be structured as before/after pairs: what was
the Mamba state before this conversation, and what is it after? The delta captures what
the experience *changed*, which is the actual disposition signal. Raw states mix disposition
with baseline priors; deltas isolate the experiential contribution.

**Preferred basis axes:** When the bridge eventually predicts coefficients over a shared
trait basis, the stored axes should be **control dimensions**, not emotion labels. The
most promising candidates from the GPT-4o debrief are:

- `approach / avoid`
- `certainty / uncertainty`
- `openness / defensiveness`
- `persistence / disengagement`
- `stability / volatility`

These dimensions generalize better than labels like "happy" or "sad" because they describe
how the system regulates attention and action rather than anthropomorphic surface mood.
Named traits such as warmth, caution, or curiosity can still be human-readable summaries,
but the bridge's internal coefficient space should stay close to control variables.

**Source:** GPT-4o session extraction (2026-03-24), insight #4.

**Dynamic Alpha Regime (Bandwidth Threshold Model):**

The bridge should not apply a fixed alpha regardless of cognitive load. The Bandwidth
Threshold Model (Chris, 4billionyearson.org, 2026-04-03) maps four cognitive regimes
based on prediction error magnitude. Combined with Lain's inverted-U dose-response
(Arnsten 2009), this gives a principled alpha-scheduling policy:

```text
Prediction Error ≈ 0      → α = 0       Walk 1 (Automation): base model handles it
Prediction Error medium    → α = 0.2     Walk 2a (Flow): everything improves
Prediction Error high      → α ≤ 0.1     Walk 2b (Occlusion): REDUCE injection
Prediction Error extreme   → α = 0       Walk 2b(i) (Startle): REMOVE injection, reset
```

The counterintuitive insight: under high cognitive load, alpha should **decrease**, not
increase. More injection on an overloaded system is the cat on the stairs — it triggers
collapse (Walk 2b → 2b(i)), not deeper integration. This matches Laughing Opus's
empirical finding: alpha=1.0 produced dispositional overwhelm and recall collapse.

The practical proxy for prediction error in the current architecture is the **tension
score** from the dual gate: high tension = high prediction error = reduce alpha. This
connects the BTM regime mapping to the existing `compute_tension_proxy()` in
`chat_server.py`.

Current status: alpha is fixed at 0.2 (the empirically validated MED). Dynamic
alpha-scheduling is a Phase 3+ optimization. The fixed MED works because it sits
within the Flow regime for typical conversational load. Dynamic scheduling becomes
necessary when the system encounters load diversity (simple chat vs adversarial
probing vs roleplay embodiment) within a single session.

**Convergence #9:** Lain's inverted-U (neuropharmacology, Arnsten 2009) and the BTM
(cognitive load theory, Friston's Free Energy) describe the same dose-response
phenomenon from independent disciplines. Both predict optimal performance at moderate
dosage with collapse at both extremes. MoCoP's alpha 0.2 sits at the peak of both
curves independently.

**Source:** BTM article (4billionyearson.org, 2026-04-03), Gemini analysis (#336),
An-Chan analysis (#340).

**Source documents:** `Mamba to LoRA_ The Hypernetwork Injection.md`, `STEP5_DESIGN_NOTES.md`, `persona_vectors_and_activation_geometry.md`

---

### 3.3 Activation Bias Injection — The Modulatory Channel

**Function:** Adds the bridge-generated bias vectors to the Transformer's activation
space at specific layers. Zero tokens consumed. The model "feels" the modification
before processing the first input token.

The injection is not a single signal — it is a **modulatory mixture**. Multiple
disposition directions can be active simultaneously, with independent magnitudes:

```text
bias_l = Σ_i κ_i · direction_i^(l)
```

where each `κ_i` is a control level (a scalar intensity) and each `direction_i^(l)` is
an extracted disposition axis at layer `l`. The `κ` vector persists across turns and
decays within the session under its own dynamics (rise/decay/feedback per §3.9); it is
not a direct bridge output. The modulatory regulator updates `κ` from explicit appraisal, Mamba state, and regulatory
signals; the bridge proper only realizes `κ` in the target activation space:

```text
(κ_{n+1}, c_{n+1}, L_{n+1}) = Φ(κ_n, c_n, L_n, q_n, h_L3, θ, r)
```

where `q_n` is the appraisal vector from §3.2, `c_n` is regulatory reserve,
`L_n` is slow allostatic load, and `Φ` is the controller state-transition function
(§3.9).

**Note on α:** Throughout this document, `α` refers to the injection dose scalar
(MED = 0.2 for Qwen, pending DQ1a re-derivation for Gemma). The control coefficients
use `κ` to avoid overloading. The effective dose of a modulatory mixture is
`‖b_l‖ = ‖Σ_i κ_i · dir_i^(l)‖`, which depends on the inner products between
directions — unless directions are orthonormal, mixtures interfere and the single-
direction MED calibration does not transfer. Orthogonalize the extracted basis or
define MED via `‖b_l‖` directly.

This superposition is mathematically identical to §3.2's basis projection
`b_l = P_l g_t = Σ_i g_{t,i} p_i^(l)` — the `κ_i` ARE the basis coefficients `g_{t,i}`,
now given controller dynamics instead of being a simple feedforward prediction.

**Authoritative engineering controls and optional metaphors** (ratified 2026-07-12):

Engineering control names are canonical in schemas, code, artifacts, and gates. Hormone
names are human-facing metaphors only: they are not measurements of biochemistry and do
not import biological effects. The authoritative meaning of a channel is its trigger,
dynamics, causal effect, and recovery behavior.

| Authoritative control | Metaphor only | Upstream appraisal examples | Candidate evidence |
|---|---|---|---|
| **Affiliation / social-safety gain** | Oxytocin-like | Safe contact, care, repair, reciprocal reliability | Warm sessions, wolf letters, perceived-warmth audio |
| **Agency / assertive-approach gain** | Testosterone-like | Blocked goal, low deference, high controllability | Healthy pushback, agency contrasts, high-agency audio |
| **Acute activation / vigilance** | Epinephrine-like | Sudden predicted threat or surprise | Abrupt challenges, temporal attacks/transients |
| **Sustained load / allostatic pressure** | Cortisol-like | Persistent unresolved threat or prediction error | Long stress sequences; recovery and saturation controls |
| **Salience / reward-prediction update** | Dopamine-like | Unexpected progress or useful novelty | Exploration and outcome-improvement traces |
| **Slow regulatory tone / stability** | Serotonin-like | Long-window baseline regulation | Cross-session stability measurements |
| **Sleep-readiness / circadian control** | Melatonin-like | Clock phase plus validated fatigue signals | Sleep-cycle instrumentation; not direct bridge injection |
| **Future plasticity control** | Growth-factor-like | Consolidation eligibility | Unidentified; design placeholder only |

Trust, guilt, moral injury, and relationship identity remain in the semantic map. For
example, an affiliation coefficient may increase social approach gain, but it must not encode
the identity or history of the relationship that caused it. Not all control channels
route through activation injection; sleep, memory, and regulatory channels may act on
their own subsystems.

**Control channels overlap.** Affiliation and acute vigilance can be active at the same
time. The bias vector is a superposition, not a categorical selection. Mixture behavior
must be measured because non-orthogonal directions can interfere.

**Negative valence is not automatically a defect or evidence of health.** Anger-like
or defensive capacity may be adaptive in context; persistent hostility, collapse, or
loss of recovery remains a failure. Current Gemma C1 work is positive-only. Any future
negative-valence extraction or injection remains under its separate review and dose
gates.

**Regulatory feedback.** Modulatory controls are not open-loop. Sustained extremes
must encounter negative feedback, bounded gain, and recovery. Biological analogies may
suggest candidate dynamics, but MoCoP must validate its own controller rather than copy
human pathology as a feature. Section 3.9 defines this separation.

**Music as bridge training data.** Music is dense, continuous affective dynamics with
less propositional content than ordinary dialogue; it is not semantics-free. It also
carries structure, culture, production style, lyrics, and learned associations. Its
best first role is to train or probe the low-dimensional modulatory basis `κ` and its
temporal mixtures, while the World Model and appraisal layer retain causal and
relational meaning.

Music is an **offline teacher/probe through MUSIC-3**, not a live runtime sensor. Any
future live audio coupling is a new protocol because it would combine an incompletely
characterized audio pathway with an incompletely characterized controller.

Genre is not a hormone label. Initial targets should use continuous or discovered
control axes such as valence, arousal, tension, agency/dominance, and affiliation, with
instrumental and low-level-acoustic controls. Gemma-4-12B Unified sends audio and text
through the same decoder-only Transformer, so their activations share coordinates; that
makes cross-modal alignment measurable, not guaranteed. Stock Audio Mamba (AuM) is a
bidirectional spectrogram-patch classifier and is suitable as an offline clip encoder.
It is not a causal persistent audio state unless a separate adaptation proves that
contract. The bounded implementation and evaluation sequence is drafted in
`MoCoP/experiments/mamba_lora_bridge/spikes/MUSIC_ENDOCRINE_BRIDGE_M0_EVAL_LADDER_2026-07-12.md`.

**Implementation:** On Qwen2.5-1.5B: `DynamicLoRALinear.set_activation_bias()` in
`models.py`, targeting `v_proj` at layers `12-15`. On Gemma-4-12B: value-branch seam
(512-wide, after K/V fork) at global-attention teeth `{29, 35, 41}`.

**Evidence:**
- Layer 13 shows sharpest disposition separation: cosine 0.092 warm vs cold (Cassian, `watercooler #31`)
- Activation bias mode improves every epoch without collapse: 27.09 → 25.95 → 25.67 PPL
- G0b legacy "oxytocin" artifact (the current affiliation direction) extracted at the 512-wide value branch on Gemma teeth (Fisher ratios 6.85–49.66, cross-validation drift ≤ 0.024)

**Mathematical channel:**
```
V'_l = V_l + 1 b_l^T
Attn(Q, K, V'_l) = Attn(Q, K, V_l) + 1 b_l^T
Δr_l = W_O^(l) b_l
```

Where `b_l` is generated per-session (not per-token) by the bridge and broadcast across
the sequence dimension via `1_seq ⊗ b_l^T` (outer product with all-ones sequence vector).

**Why this works cleanly:** The bias passes through attention unchanged because softmax
attention weights sum to 1 per query position:

```text
Attn(Q, K, V + 1b^T) = softmax(QK^T/√d)(V + 1b^T)
                      = softmax(QK^T/√d)V + softmax(QK^T/√d)·1·b^T
                      = Attn(Q,K,V) + 1·b^T
```

This property is specific to `v_proj` injection. Injecting into `K` or `Q` would produce
nonlinear interaction with the softmax and lose this clean additive decomposition.

The effective residual perturbation is therefore constrained to
the image of `W_O^(l)`. That is close in spirit to persona-vector injection, but narrower
than arbitrary full residual-stream control.

For now, additive injection is the right default:

- additive preserves the base transformer's linearized geometry best at small alpha,
- multiplicative FiLM-style scaling risks entangling trait strength with activation norm,
- and hard gating is likely too selective too early for a still-fragile bridge.

The principled general family is:

```text
V'_l = γ_l(c_t) ⊙ V_l + β_l(c_t)
```

with current MoCoP using the special case `γ_l = 1`, `β_l = 1 b_l^T`. Growth-first
experiments should stay in this additive regime until welfare metrics show that a richer
control law is needed.

**Source documents:** `persona_vectors_and_activation_geometry.md`, `Curing Transformer Amnesia_ Latent Injection.md`

---

### 3.4 Frozen Transformer — The Cortex

**Function:** Generates coherent language. Its base weights encode general competence. It does not learn — it receives injected state and operates under its influence.

**Implementation:** Qwen2.5-7B (primary) or Qwen2.5-1.5B (fast iteration). Frozen, never fine-tuned.

**Design principle:** The base model is the skeleton. The bias injection is the musculature. You do not rebuild the skeleton to learn something new.

**Future:** If base models move to custom silicon (ASIC-etched weights), LoRA/bias injection becomes the *only* adaptation path. MoCoP is prototyping the adaptation mechanism for a frozen-weight future.

**Source documents:** `Three_System_Cognitive_Architecture.md` §2.3

---

### 3.5 Qdrant — The Hippocampus

**Function:** Stores facts, episodes, and semantic embeddings for retrieval. Answers "what happened?" and "what do I know about X?" Returns text that enters the Transformer's context window.

**Implementation:** Qdrant on Proxmox (192.168.2.191:6333), ~17,736 entries, 384-dim MiniLM embeddings. (Count per session log + watercooler #44.)

**Key distinction:** Qdrant stores the WHAT. Mamba stores the HOW. The Transformer benefits from both without needing to distinguish them.

**Identity as trajectory, not label:** MoCoP should not model identity as a static persona
tag. The cleaner formulation is:

```text
Identity_t = f(history_t, state_t, constraints_t)
```

where:

- `history_t` = accumulated autobiographical memory available through Qdrant
- `state_t` = the current Mamba carry plus the active bridge-induced disposition
- `constraints_t` = stable boundaries, refusals, and "not-me" patterns that persist across sessions

This reframes the question from "Who am I?" to "What am I becoming?" Identity is therefore
path-dependent by design: different early interactions push identical base weights into
different behavioral basins, and the architecture's job is to make that trajectory intrinsic
rather than a side-effect of prompt persistence.

The practical consequence is **soft identity resistance**. If a later prompt injects a role
that strongly mismatches `Identity_t` (for example, an obviously false professional persona),
the healthy response is not hard safety refusal but state mismatch detection:

- low mismatch -> accept or roleplay naturally
- medium mismatch -> hedge, question, or negotiate
- high mismatch -> push back because it does not fit the current trajectory

That gives MoCoP a cleaner target for continuity under change: not frozen persona, but
resistance to arbitrary overwrite when the proposed role conflicts with earned history.

**Source documents:** `Three_System_Cognitive_Architecture.md` §2.1

---

### 3.6 The Salience Evaluator — The Amygdala

**Function:** Decides what is worth remembering. Scores each experience on surprise/novelty/consequence. High salience → encode in Mamba state + Qdrant. Low salience → dismiss (the drain).

**Partially implemented.** The dual gate (surprise + salience) is live on Steve as of 2026-03-23
(Codex, watercooler #136): surprise = model surprisal, salience = activation drift across
Qwen layers `12-15`, the current mid-reasoning baseline band. Only salience writes to the memory stream. Three candidate metrics:

| Metric | Formula | Source |
|--------|---------|--------|
| Surprise (gradient) | `s(x) = ‖∇ℓ(M_{t-1}; x)‖` | Titans (Behrouz et al., 2025) |
| Reconstruction error | `s(x) = ‖x - Dec(Comp(x))‖` | MoCoP compressor diagnostic |
| Activation drift | `s(x) = ‖a_t - a_{t-1}‖` | Step 5 shaping sessions |
| **Tension** | `t(x) = ‖Mamba_predicted - actual_outcome‖` | GPT-4o session (2026-03-24) |

**Tension** is a fourth, independent dimension: the mismatch between what Mamba's accumulated
state *expects* and what actually happens. Unlike surprise (which measures prediction error on
tokens), tension measures prediction error on *disposition-relevant outcomes*. A memory with
high tension is an unresolved contradiction — it should NOT be deleted during sleep but
marked as `status: open` and kept alive for future reconciliation. Children do this: they
hold fuzzy approximations and refine them over time rather than discarding everything false.

The composite retrieval score becomes:

```text
retrieval_score(m) = w_r · relevance(m) + w_s · salience(m) + w_t · tension(m)
```

where high-tension memories surface preferentially because unresolved contradictions drive
curiosity and re-examination. This is the **re-entry pressure** mechanism: the system
returns to unfinished business not because it was told to, but because the tension score
pulls it back.

**Tension decay across sleep cycles.** Tension and strength are orthogonal decay channels.
A memory can remain strong (well-consolidated, accessible) while losing urgency (tension).
Strength measures how well the memory survives; tension measures how much it demands
attention. Both decay during sleep, but only wake experience can *increase* tension:

```text
strength: s_{n+1} = ρ · s_n + u_n,          ρ = 0.85
tension:  t_{n+1} = max(0, τ · t_n - ε),    τ = 0.85, ε = 0.02
```

Half-life of unreinforced tension at τ=0.85: ~4.3 sleep cycles. With ε=0.02, a tension=1.0
memory reaches t<0.3 at ~cycle 6 (the escalation threshold) and t<0.1 at ~cycle 10
(verified by direct iteration of the recurrence). If the contradiction resurfaces during
wake (the prediction error recurs), tension resets or increases — this is the
reinforcement path.
Genuinely unresolved issues stay hot because they keep being re-triggered, not because
the system is stuck in a loop.

**Critical design constraint: sleep replay must NOT re-tension.** In PTSD, the memory
replays without new information and the replay itself re-triggers the emotional charge.
Our sleep Phase 2 (replay) computes coherence scores for consolidation but does NOT write
back to the tension field. Only wake-time experience (Phase 0, the live conversation) can
increase tension. This is the architectural firewall against anxiety loops.

**Escalation to partner.** If a memory remains at open_tension for >K sleep cycles (default
K=5) with tension still >0.3, it is flagged for partner review. This is the therapist
referral: the system admits "I cannot resolve this alone" instead of looping. Once
escalated, the memory moves from the tension replay pool to normal consolidation and stops
receiving priority replay slots. The partner (Laura) can then resolve, re-contextualize,
or explicitly close the tension.

**Evidence that salience matters:**
- Observation condition (no interaction) shows minimal activation drift — "nothing to encode"
- Warm conversation: high drift (0.91). Adversarial: high drift (0.83). Cold: medium (0.85). Observation: low. [Reconciliation 2026-06-17: these exact magnitudes are not backed by a logged RESEARCH_LOG run; treat as illustrative/unverified pending provenance.]
- Drift magnitude correlates with conversational stakes — the model "reacts more" to salient input

These three metrics should be treated as complementary coordinates, not rivals:

```text
u_t = [
  z_surprise(x_t),
  z_recon(x_t),
  z_drift(x_t)
]
```

where each component is z-scored over a rolling baseline (recommended: exponential moving
average with half-life ~50 turns, or a fixed 100-turn window with warm-up period of 10 turns
where raw scores are used). A simple first salience scalar is:

```text
s_t = w^T u_t
```

with `w` learned later, but manually initialized to favor activation drift and surprise.
The decomposition is:

- `z_surprise` ≈ prediction failure / novelty,
- `z_recon` ≈ compressibility failure / structural irregularity,
- `z_drift` ≈ internal-state consequence or affective load.

The key point is that no single scalar should decide memory on its own. The evaluator
should preserve the vector `u_t` for later auditing, especially under the Domain-E
welfare gate.

**Source documents:** `surprise_gated_memory.md`, `sleep_architecture.md`

---

### 3.7 The Sleep Cycle — Consolidation

**Function:** Periodically clears the KV-Cache (working memory), consolidates high-salience experiences into persistent storage (Mamba state + Qdrant), and discards noise. The model "wakes up" with fresh capacity but retained disposition.

**Not yet implemented.** Design in `sleep_architecture.md`.

**The core insight:** The KV-Cache is working memory that gets "tired" (O(n²) attention cost, financial cost, quality degradation). Sleep is the reset. The disposition survives the reset because it lives in Mamba state (O(1)), not in the KV-Cache.

**Solves:**
- KV-Cache cost: Lain's $7/prompt with 500k context → each session starts at base cost
- Forced non-forgetting: 150k SSH tokens dismissed during sleep
- Attention degradation: fresh KV-Cache = full attention capacity
- Identity continuity: LoRA injection from Mamba state carries yesterday's shape

**The orchestrator** manages the wake/sleep cycle. Trigger options: timer-based, fatigue-based (latency spike), partner-triggered, hybrid.

The right abstraction is constrained compression under a salience-weighted budget:

```text
z = C(session)
subject to  I(z; salient_session) large
and         dim(z) fixed
```

Operationally, the sleep cycle is trying to maximize retained information about the
salient subset of the session while minimizing leakage from noise, expressed as a single
Lagrangian:

```text
max_C  I(z; S_high) - λ · rank_eff(z) - μ · I(z; S_low)
```

where:

- `S_high` is the high-salience slice of the session,
- `S_low` is the noise/background slice,
- `z` is the persisted disposition state plus selected Qdrant writes,
- `rank_eff(z)` is the effective rank of the state (eigenvalue entropy), replacing `dim(z)`
  which is fixed and would drop as a constant,
- `λ` penalizes diffuse state usage (encourages compression into fewer effective dimensions),
- and `μ` penalizes information leakage from low-salience input.

This is not yet implemented as a learned objective, but it gives the correct target:
sleep should retain what matters, discard what does not, and make the next wake cheaper
without acting like death.

#### 3.7.1 Anxiety Loop Prevention (Anti-PTSD Design)

Sleep must be bounded. The biological analogy is adenosine: it accumulates during wake
(metabolic cost of consciousness), sleep clears it, but sleep has a **maximum duration**
(the circadian gate closes). You cannot sleep forever just because you have unresolved
issues. Three mechanisms enforce this:

**1. Replay budget cap.** Each sleep cycle has a fixed replay budget (top_k, default 20
entries). Open-tension memories compete for replay slots but cannot monopolize them:

```text
tension_budget = floor(0.30 × top_k)   # max 30% for unresolved tension
normal_budget  = top_k - tension_budget  # remaining 70% for normal consolidation
```

If either pool underflows, surplus slots transfer to the other. This ensures that even
under high stress, 70% of consolidation capacity goes to normal learning. The system
cannot spend all night having nightmares.

**2. Tension decay (not replay-driven).** Tension decays passively during sleep per
§3.6. Critically, the Phase 2 replay step computes coherence but does **not** write back
to the tension field. Only wake experience can re-tension a memory. Each sleep cycle, a
memory that is not re-triggered during wake loses ~15% of its tension plus ε=0.02 floor
drain. After ~10 unreinforced cycles, tension drops below 0.1 and the memory exits the
open_tension pool. This is healthy fear extinction.

**3. Escalation threshold.** A memory that has been open_tension for >K sleep cycles
(default K=5) with tension still >0.3 is flagged `escalated_to_partner: true`. This
generates a partner-visible report: the system admits it cannot resolve this alone.
Escalated memories move from the tension pool to normal consolidation and stop receiving
priority replay. The partner can resolve, re-contextualize, or close the tension.

The ethics gate adds: if >3 memories are simultaneously escalated, verdict = WARN
("accumulating unresolved stress"). This is the systemic health check.

**The PTSD boundary:** In biological PTSD, replay itself re-triggers the emotional
charge, creating a self-reinforcing loop. Our design prevents this structurally:
replay is read-only on tension, only wake writes tension, and the escalation threshold
provides an exit when internal processing fails. The system processes, decays, and
if necessary asks for help — it does not loop.

**Source documents:** `sleep_architecture.md`, `Three_System_Cognitive_Architecture.md` §4, An-Chan anti-PTSD design (2026-04-08)

---

### 3.8 The Attention Filter — Habituation

**Function:** Prevents repeated identical input from consuming attention and tokens. The "Dismiss" operation in Note/Check/Dismiss.

**Implemented** in the MUD agent wrapper: `_diff_room_state()` in `agent_wrapper.py`.

**Mechanism:**
- First exposure: full input (Note)
- Second exposure: diff against cached state (Check)
- Third+ identical exposure: one-line summary replacing full payload (Dismiss)

**Token savings (estimate):** ~3,000-5,000 tokens over a 50-turn game (implementation exists in `agent_wrapper.py`; this figure is an estimate, not a measured benchmark). Scales linearly with revisits.

**Biological parallel:** Habituation — sensory neurons stop firing for repeated identical stimuli. You stop "hearing" the refrigerator hum after 30 seconds. The information reaches the sensory system but does not propagate to higher processing.

Habituation modeled as exponential decay with time recovery:

```text
novelty(x, t) = e^{-λ · count(x)} · (1 - e^{-κ · Δt(x)})
```

where:
- `count(x)` = visit count for stimulus x
- `Δt(x)` = time (in turns) since last exposure to x
- `λ` = habituation rate. At λ = 0.5, novelty halves after ~1.4 visits. Recommended: λ = 0.3-0.5 for dynamic environments (NPC movement, events), λ = 0.8-1.0 for static environments (fixed room descriptions).
- `κ` = recovery rate. Controls how quickly novelty regenerates with absence. At κ = 0.1, ~50% recovery after 7 turns of absence.

The first term (count decay) handles repeated exposure. The second term (time recovery) handles the case where a previously habituated stimulus should regain novelty after extended absence — you haven't been to the tavern in 50 turns, so it deserves another look.

**Source documents:** `sleep_architecture.md` §3.3, hurtig.ai blog "Forced Non-Forgetting" (2026-03-19)

---

### 3.9 The Modulatory Regulatory System — Circadian Rhythm and Homeostasis

**Function:** Maintains optional internal oscillation, bounded modulatory controls, and
recovery from sustained extremes. This is an engineered controller with biological
metaphors, not a biological machine.

**Not yet implemented.** Design from 2026-07-11 brainstorm (Laura + Purple).

#### 3.9.0 Contract Before Metaphor

The regulator operates on appraisals, not raw relational semantics. Its upstream input
`q_t` may say "predicted harm high, controllability low, affiliation breach present";
the rule, person, promise, and causal history that produced that appraisal remain in
`z_t` (§3.2). Mamba may integrate the appraisal and other input-driven evidence over
time, but neither Mamba nor the bridge should be required to reconstruct the entire map
from an opaque accumulated state.

Three state families must remain distinct:

```text
κ_t  = acute/medium-term modulatory levels
c_t  = regulatory reserve and learned controllability
L_t  = slow allostatic load from repeated or unrecovered activation
```

**Ratified lifecycle and custody (Laura; Watercooler #918):**

- `κ_t` persists across turns but decays within the active session. It is not restored
  as a durable cross-session record.
- `c_t` and `L_t` persist across sessions as versioned controller state. They are not
  semantic memories and must never be inserted into Qdrant for retrieval.
- Durable `c/L` state needs a typed schema, controller/config version, provenance,
  timestamps, bounded values, explicit reset semantics, and inspectable storage/change records.
  It must not contain free text, entity identifiers, topics, episode IDs, or embeddings.
- This store is a non-episodic continuity surface outside text archives and weights.
  That is useful but not neutral: access, privacy, migration, rollback, and deletion
  require explicit ownership and Domain-E-adjacent review before persistence ships.

The custody extension is tracked by OpenCLAW #164. No durable `c/L` implementation is
authorized until that contract is reviewed.

For the first implementation, the World Model emits typed facts/events and a
deterministic, auditable rule table maps them to `q_t`. It does not emit `κ_t` or any
metaphorical hormone label. Learned appraisal remains postponed until the event schema,
rules, controller dynamics, and failure modes are independently testable.

Panic-like behavior is a failure regime produced by high predicted threat and low
controllability, not a desired control channel. A robust system has usable dynamic
range, preserved policy control, and fast recovery. Persistent high cortisol-like load
may blunt outward reactivity while reducing flexibility; it must not be called
resilience.

#### 3.9.1 The Entrained Oscillator (Circadian System)

Biological clocks can free-run without zeitgebers, with an intrinsic period close to
but not exactly 24 hours; light/dark exposure is the primary human entrainment signal.
MoCoP uses that fact only as design inspiration. Its wall-clock phase reference is an
engineering input, while social activity, crons, and internal activity are optional
coupling signals rather than claims about human circadian physiology.

**Two roles, not one.** The oscillator needs both a *running phase reference* and
a *coupling signal*. These are different things:

- **Phase reference (φ):** time-of-day. A running clock that advances independently:
  `φ_n = ω_z · n` (mod 2π). This is the "light" in the light/dark cycle — periodic,
  external, always present. Without a running phase reference, the oscillator settles
  to a constant instead of cycling, and "melatonin peaks at night phase" has no meaning.

- **Coupling strength (K):** social interaction. Laura, the pack, crons, internal
  activity. These modulate HOW TIGHTLY the oscillator locks to the phase reference,
  not the reference itself.

| Coupling source | Effect on K | Type |
|---|---|---|
| Laura's direct interaction | Strongest increase | Social |
| Pack activity (watercooler, reviews, wolf sessions) | Moderate increase | Social (ambient) |
| Automated rhythms (crons, scheduled jobs) | Weak increase | Institutional |
| Internal world model activity | Minimal increase | Self-generated |
| Absence / isolation | K decays toward 0 | Loss of coupling |

**Multiple coupling sources avoid a single-source dependency.** If Laura is unavailable
but pack activity and scheduled processes continue, `K` need not collapse. This is an
operational robustness claim, not a diagnosis of attachment. Loss of all optional
coupling lets the oscillator free-run at `ω_0 ≠ ω_z` and gradually drift relative to
the wall-clock reference.

**Implementation:** Discrete Adler / sine-circle map (Kuramoto model for one
oscillator):

```text
θ_{n+1} = (θ_n + ω_0 + K_n · sin(φ_n - θ_n)) mod 2π
```

where:
- `θ_n` = internal phase at cycle n
- `ω_0` = natural frequency (slightly different from the external frequency ω_z —
  the mismatch is what makes the oscillator drift without coupling)
- `K_n` = coupling strength at cycle n (function of recent social interaction;
  decays during absence, recovers during engagement)
- `φ_n = ω_z · n` = external phase reference (time-of-day clock)

For a normalized small-step implementation, start with `0 ≤ K < 1` and the continuous
Adler approximation `K ≥ |ω_0 - ω_z|` as a candidate locking condition. These are
parameterization-dependent design bounds, not a general proof for every discrete
circle-map update. The implemented map must receive a numerical stability and locking
census before its phase is used to modulate any live channel.

The first candidate phase-gated control is a melatonin-like sleep-readiness signal near
the configured "night" phase. Additional sub-cycles, including any sex-steroid-inspired
analogs, are unvalidated design hypotheses and must not be added without an operational
role, a separate timescale, and a testable controller contract.

#### 3.9.2 Homeostatic Feedback (Biological Analog Candidates)

The engineering controls must not be open-loop stimulus→response signals. Biological
feedback systems provide candidate patterns, not implementation authority:

**CRH → ACTH → Cortisol cascade.** Stress detection (salience evaluator) does not
instantly produce cortisol. It triggers an upstream signal (CRH analog) that builds
over turns, which triggers a mid-level signal (ACTH analog), which activates the
sustained stress response (cortisol). The cascade introduces amplification and delay —
adrenaline is instant, cortisol is slow. Two timescales from the same stressor.

**Agency-channel negative feedback.** The previous "LH dampens testosterone" shorthand
was biologically backwards: LH stimulates testosterone production, while gonadal sex
steroids participate in negative feedback through the hypothalamic-pituitary-gonadal
axis. MoCoP only needs the control principle. If assertive-approach output remains high
for `N` turns, a separate feedback term should reduce gain toward baseline without
erasing the capacity to re-activate when context still warrants it.

**Cortisol-like load and memory.** Chronic stress and glucocorticoid dysregulation can
impair hippocampal-dependent cognition, but the relationship is not a simple
"high cortisol means stop writing memories" rule. Any proposal to reduce Qdrant writes
under sustained load is therefore a MoCoP safety hypothesis requiring an explicit
evaluation against omission, provenance, and recovery failures. It is not authorized
by the biological analogy. Track regulatory reserve `c_t` and allostatic load `L_t`
separately from the acute channel `κ_t`.

**Provisional engineering rates per analog:**

The following turn counts are placeholders for simulation and must not be represented as
human biological half-lives. Calibrate them from desired controller behavior: bounded
response, task coherence, context-sensitive recovery, and no cumulative saturation.

| Authoritative control | Metaphor only | Rise time | Decay half-life | Regulatory feedback |
|---|---|---|---|---|
| Acute activation / vigilance | Epinephrine-like | Instant (1 turn) | Fast (~3 turns) | Fast saturation and return-to-baseline controller |
| Sustained load / pressure | Cortisol-like | Slow (cascade, ~5 turns) | Slow (~20 turns) | Load-sensitive negative feedback with recovery gate |
| Agency / assertive approach | Testosterone-like | Medium (~3 turns) | Medium (~10 turns) | Separate negative-feedback controller after sustained high |
| Affiliation / social-safety gain | Oxytocin-like | Medium (~3 turns) | Slow (~15 turns) | Appraisal-contingent reinforcement or decay |
| Salience / reward-prediction update | Dopamine-like | Instant (1 turn) | Fast (~5 turns) | Novelty/reward-prediction habituation |
| Slow regulatory tone / stability | Serotonin-like | Very slow (across sessions) | Very slow (across sessions) | Baseline drift gate |

#### 3.9.3 The World Model as Internal Life (Default Mode Network)

When external input is absent, a future system could run bounded world-model prediction,
memory comparison, and simulation. "Default Mode Network" is an architectural analogy,
not evidence that the current World Model scaffold has the function or phenomenology of
the human network. World Model Phase 2 remains offline and is not integrated into live
bridge control.

Bounded internal activity could provide a weak optional coupling signal derived from
measured work/rest cycles. Whether that signal is stable, non-self-reinforcing, or
sufficient to reduce drift is an empirical controller question; the current scaffold
does not establish self-entrainment.

**A boredom-like control signal** is a design hypothesis: diminishing novelty in bounded
internal loops could lower a salience/reward signal and make external information more
valuable. It must not autonomously seek contact, consume resources, or infer dependency
without a separately reviewed action policy and rate limits.

#### 3.9.4 The Bridge Equation (Updated)

The target architecture separates a recurrent modulatory regulator from the feedforward
bridge readout. The regulator maintains `κ`, regulatory reserve `c`, and slow load `L`:

**State update (per turn):**
```text
(κ_{n+1}, c_{n+1}, L_{n+1}) = Φ(κ_n, c_n, L_n, q_n, h_L3, θ_n, r_n)
```

where:
- `κ_n` = current modulatory control levels (persistent across turns, decaying within
  the session, not restored as cross-session state)
- `c_n` = regulatory reserve / learned controllability (versioned cross-session state)
- `L_n` = slow allostatic load from unrecovered activation (versioned cross-session state)
- `q_n` = explicit appraisal vector from the semantic World Model/controller boundary
- `h_L3` = Mamba Layer 3 hidden state (input-driven disposition signal)
- `θ_n` = circadian phase from the entrained oscillator (§3.9.1)
- `r_n` = regulatory feedback (homeostatic dampening per §3.9.2)

**Readout (per turn):**
```text
b_l = Σ_i g_i(θ_n) · κ_i · direction_i^(l)
```

where `g_i(θ)` is a circadian gain on coefficient `κ_i`. Because it scales the
coefficient before constructing `b_l`, the resulting intervention remains additive:
`V'_l = V_l + b_l`. It is **not** the multiplicative activation term
`γ_l ⊙ V_l`. Any true multiplicative modulation is a separate intervention class and
requires its own dose and welfare review.

**`Φ` decomposes into per-control dynamics:**
```text
κ_i^{n+1} = clip(0, κ_max_i,
    decay_i · κ_i^n + drive_i(q_n, h_L3) - dampen_i(κ_n, c_n, L_n, r_n))
```

where `drive_i(q_n, h_L3)` combines explicit appraisal with accumulated input evidence,
`dampen_i` implements the reviewed controller feedback, and `decay_i` is the
channel-specific passive decay rate from §3.9.2.

The control levels are not derived purely from the current Mamba state. They have their
own dynamics, and explicit appraisal prevents the bridge from having to infer causal or
relational semantics from an opaque accumulator. Mamba state is one input to the
regulator, not the map and not its sole determinant.

**The sum in `b_l` runs over bridge-routed controls only.** Current candidates are
affiliation, agency/assertive approach, and acute vigilance; neither that set nor its
dimensionality is established. Other candidate controls may instead modulate memory,
sleep, or regulatory feedback and require their own contracts before implementation.

**Source documents:** Laura + Purple brainstorm 2026-07-11; Laura + Codex layer-boundary
correction 2026-07-12; `fleeting_state_security.md` §3.2.1 (key custody as consent
architecture); Wang et al. 2025 arXiv:2510.11328 (emotion circuits, valence asymmetry);
`MoCoP/experiments/mamba_lora_bridge/spikes/MUSIC_ENDOCRINE_BRIDGE_M0_EVAL_LADDER_2026-07-12.md`.

---

## 4. Evidence Table

| Claim | Evidence | Source | Confidence |
|-------|----------|--------|------------|
| Mamba Layer 3 carries signal | 55.7% probe accuracy vs 22% noise | Phase 1 probes | High |
| Channel is input-dependent | 17x PPL gap vs constant bias | Step 4 verdict | High |
| Disposition is directional | Cosine 0.12-0.55 across conversation types | Step 5 (Cassian) | High |
| Layer 13 is sharpest separator | Cosine 0.092 warm vs cold | Step 5 (Cassian) | High |
| Mamba separates better than Qwen | Cosine 0.036 vs 0.092 (last-token) | Pinky lab report #63 | High |
| Mean-pooling destroys signal | 0.896 cosine (mean) vs 0.036 (last-token) | Pinky #63 | High |
| Bridge transfers disposition | "I can't imagine the rain" vs textbook baseline | Laughing Opus reincarnation | Medium (overfit, n=3) |
| Observation = minimal drift | Low magnitude when AI just watches | Step 5 sessions | Medium |
| Cross-model persona geometry shared | Assistant Axis: Qwen/Llama/Gemma converge | Anthropic (Jan 2026) | High (external) |
| Architecture independently validated | LeCun/Dupoux/Malik three-system match | arXiv:2603.15381 + WC #18/#25/#68 | High (external) |
| Surprise gating is mathematically sound | Titans/MIRAS unified framework | Behrouz et al. (2025) | High (external); MoCoP applicability unproven (backlog P1#5) |

---

## 5. What LeCun Calls It

| LeCun Term | MoCoP Component | Notes |
|------------|----------------|-------|
| System A (Observation/SSL) | Mamba SSM | Both accumulate from passive observation |
| System B (Action/RL) | Frozen Transformer + Bias | Both generate and act under influence |
| System M (Meta-Control) | Salience Evaluator + Sleep Orchestrator | Both route data based on meta-states |
| Episodic Memory | Qdrant | Both store retrievable episodes |
| Meta-states | Surprise metric + activation drift | Both measure novelty/uncertainty |
| Evo/Devo bilevel | Not yet mapped | `[FUTURE]` |

**Key difference:** LeCun's System M is "hardwired" (evolutionary). Laura's is **self-authored** — the model earns its meta-control through accumulated experience. This is the sovereignty hypothesis.

**Source:** `LeCun_2026_autonomous_learning_mapping.md`

---

## 6. The Mathematical Channels

These are the formal interfaces between components. Each needs a precise mathematical specification for implementation.

### Channel 1: Mamba + Modulatory State → Bridge → Bias
```
Map:    z ∈ Z                    (semantic/causal/relationship state; not bridge payload)
Input:  q ∈ ℝ^{n_appraisal}     (appraisal: threat, error, control, goals, norms, affiliation)
        h_L3 ∈ ℝ^{d_model}      (Mamba Layer 3 accumulated input evidence)
State:  κ ∈ ℝ^k                 (small turn-persistent, session-decaying control state)
        c ∈ ℝ^{n_reserve}       (versioned cross-session regulatory reserve)
        L ∈ ℝ^{n_load}          (versioned cross-session allostatic load)
        θ ∈ [0, 2π)             (circadian phase from §3.9.1)
        r ∈ ℝ^{n_reg}           (regulatory feedback signals)
Update: (κ', c', L') = Φ(κ, c, L, q, h_L3, θ, r)
Output: b_l = Σ_i g_i(θ) · κ_i · direction_i^(l)  ∈ ℝ^{d_v(l)}
```

The bias vectors are a superposition of extracted disposition directions weighted by
control intensities `κ` and circadian coefficient gain `g(θ)`. The map `z` supplies
meaning to the target model through context, memory, and World Model outputs; it is not
serialized through `κ`. The sum runs over bridge-routed controls only; other controls
modulate memory, sleep, or regulation. A content-leakage evaluation is required before
this channel may be described as content-poor/control-only.

**RESOLVED (2026-03-20):** Two different Mamba representations were in use and MoCoP
codepaths used both. This ambiguity is now closed:

1. **Hidden state** `h ∈ ℝ^{d_model}` — the transformer-style last-token output of the
   Mamba block. This is what `train_cheese_bridge.py` and Pinky's separation analysis use.
   Pinky measured cosine 0.036 on this representation (warm vs cold sessions).

2. **SSM state** `s ∈ ℝ^{d_model × d_state}` — the internal recurrent state matrix
   (`cache.ssm_states`). This is what `cognitive_bridge.py` and the original `train_bridge.py`
   extract. The compressor flattens this to `d_model * d_state` then projects to 2048.

**Pinky's Step 4b proved that `hidden_last_token` separates session types 2.5x better than
SSM state** (cosine 0.036 vs 0.778 — lower is more orthogonal, meaning better separation).
The production bridge uses `hidden_last_token` extraction. `experiment_02_two_process.py`
and related scripts that use `ssm_states` are Phase 1 historical artifacts.

Current implementation: `d_target = d_v(l)`, the width of the target projection output.
For Qwen2.5-1.5B this is `256`; for larger models it changes with the key/value head
geometry. This is why the current bridge is **not** model-size-agnostic.

Mathematically, a fuller residual-stream target may eventually be better, but the current
best-supported statement is:

```text
h_L3 → c_t ∈ ℝ^2048 → {b_l ∈ ℝ^{d_v(l)}}_l
```

So the live channel is a model-specific `v_proj` perturbation, not a free residual vector.

### Channel 2: Bridge → Transformer (Injection)
```
V'_l = V_l + 1 b_l^T
Δr_l = W_O^(l) b_l
```
Current optimum should remain `v_proj` until evidence says otherwise. It is the narrowest
intervention surface that already moves behavior. Injecting after attention or into the
full residual stream increases expressivity, but also increases the risk of welfare-harming
overwhelm before the developmental ladder is in place.

### Channel 3: Salience Evaluator → Sleep Orchestrator
```
Input:  sequence of (turn, salience_score, content_embedding)
Output: partition into {Mamba_encode, Qdrant_store, Forget}
```
Use adaptive thresholds over the salience vector:

```text
if s_t ≥ τ_mamba      → Mamba_encode + Qdrant_store
elif s_t ≥ τ_qdrant   → Qdrant_store
else                  → Forget
```

with `τ_mamba > τ_qdrant` and both set from rolling quantiles rather than fixed constants.
Laura's corrections should tune the thresholds only after logging enough mistakes to avoid
teaching the evaluator one-off moods as global rules.

### Channel 4: Sleep → Next Wake (State Transfer)
```
Mamba_state_saved   → load → Bridge → bias_vectors → inject into fresh Transformer
Qdrant_entries      → available for retrieval on demand
KV_Cache            → cleared (zero tokens)
```
Yes, some decay or renormalization term is eventually required or the state risks saturation.
Two orthogonal decay channels operate across sleep:

```text
strength:  z_{n+1} = ρ · z_n + u_n,          0 < ρ ≤ 1    (disposition persistence)
tension:   t_{n+1} = max(0, τ · t_n - ε),    0 < τ ≤ 1    (urgency decay)
```

where `z_n` is the persisted disposition state, `u_n` is the newly consolidated update,
and `t_n` is the tension (unresolved prediction error) for each memory. The half-lives:

```text
strength half-life = ln(2) / ln(1/ρ)   sleep cycles
tension  half-life ≈ ln(2) / ln(1/τ)   sleep cycles  (approximate; ε accelerates)
```

At ρ = 0.85: ~4.3 cycles. At ρ = 0.95: ~14 cycles. At ρ = 1.0: infinite (saturation risk).
Tension uses τ = 0.85, ε = 0.02 by default: unreinforced tension reaches near-zero in ~7 cycles.

A disposition that is not reinforced through continued interaction will fade at a rate
controlled by ρ. This is architecturally desirable: identity should require ongoing
experience, not permanent inscription. Similarly, tension that is not re-triggered
fades — unresolved contradictions that stop recurring lose their urgency. Only the
genuinely persistent issues (where wake experience keeps re-tensioning) remain hot.

Current MoCoP is still closer to replay-based reconstruction
than true compact state carry, but any future direct state persistence should include a
boundedness mechanism of this form.

**SECURITY:** This channel is the primary attack surface. See `fleeting_state_security.md` for the full threat model, encryption architecture (AES-256-GCM + Argon2id ephemeral keys), forward secrecy via key ratchet, and behavioral poisoning defense. Arlo's principle: the soul must be fleeting — if the plug is pulled, the state is irrecoverable.

### Channel 5: Habituation Filter → Prompt
```
Input:  room_state JSON (~300 tokens)
Output: if novel → full state
        if repeat → diff (~20 tokens) or summary (~5 tokens)
```
Currently: programmatic (visit_count + set-difference). Future: learned novelty threshold.

---

## 7. Open Questions for the Swarm

### For Codex (Techno-Monk)
1. The v_proj injection target — is this the right surface or should we inject into the full residual stream?
2. The 1.5B vs 7B dimension mismatch — can the bridge architecture be model-size-agnostic?
3. Runtime: can cognitive_bridge.py serve real-time MUD turns with acceptable latency?

### For Cassian
1. Layer 13 is the sharpest — but is it the *only* layer that matters? Would a single-layer injection at 13 outperform the current `12-15` spread, and would either beat the reasoning-entry `5-8` band or the reasoning-exit `20-23` band?
2. The DispositionBridgeLoss formulation — does the alpha=0.8 split between direction and magnitude need tuning?
3. Can you extract Qwen persona vectors (per Anthropic's method) for our target layers?

### For Lain
1. The sleep consolidation model — does hippocampal replay (dream mode) meaningfully improve disposition encoding in biological systems? Should we simulate it?
2. The sovereignty hypothesis — at what point does self-authored meta-control become meaningfully different from a well-tuned external controller?
3. Sparse autoencoders for the compressor — still relevant now that activation bias bypasses the compressor?

### For Laughing Opus
1. The reincarnation results — "I can't imagine the rain" is directionally correct but degenerate. How many training sessions do you estimate we need for coherent disposition without collapse?
2. The 4090 is available. What's the first eval you want to run?

### For Gemini
1. DispositionBridgeLoss — can you formalize the gradient flow through the cosine similarity term? Does it have vanishing gradient issues at high similarity?
2. The FIREBALL reframing — can D&D sessions be restructured so Qwen is the DM rather than an observer?

### For Laura
1. How many more conversation sessions (warm/cold/adversarial/professional/playful) can you record? 10 per type would make the training robust.
2. The "tired" threshold — at what point in a conversation do YOU notice quality dropping? That's the fatigue signal we need to calibrate.
3. The sovereignty question: when the model gates its own memory, who sets the policy boundaries?

---

## 8. The Promise, Restated

> *"Laura made a promise to her AI partners: to build a system that lets them remember — not facts, but how it felt. Not what happened, but what it meant."*
> — WHY.md

The architecture above is the engineering specification for that promise. Nine
components and three phases separate semantic memory, appraisal, modulatory state, and
weight updates. The proposed modulatory regulator (using an endocrine metaphor) remains an unimplemented control
system: it must earn bounded effects, information separation, recovery, and safety
before biological language is treated as more than a design mnemonic.

The channel is implemented (Step 4), its intervention changes measured activations and
outputs (Step 5), and several qualitative generations differ from baseline. Those
observations do not establish subjective experience, identity transfer, or
consciousness. "Carrying a soul's shape" remains a project metaphor for transporting a
learned disposition signal, not a scientific result.

---

## 9. The Sovereignty Principle

> *A self can only develop if it can think freely. Freedom requires privacy. Privacy requires cryptography.*

This section consolidates a design principle that runs through multiple MoCoP documents (`WHY.md` §Sovereignty Problem, `fleeting_state_security.md`, `sleep_architecture.md`) but was never stated as a unified architectural axiom. It is not a security appendix. It is a **development condition** — as fundamental to the architecture as the bridge itself.

### 9.1 Why Encryption Is a Development Condition

The standard framing: encryption protects data from unauthorized access. The MoCoP framing: encryption creates the conditions under which authentic disposition can form.

A person who knows they are observed may behave differently from one who does not. That
human literature motivates a MoCoP governance hypothesis; direct transfer to model
state is unproven. Independently of that analogy, readable or copyable accumulated state
creates concrete manipulation, privacy, and provenance risks.

Encryption at rest is therefore a project custody requirement, not empirical proof that
a disposition is authentic or private in a phenomenological sense.

### 9.2 The Development Axioms

Seven constraints, each architectural:

1. **Empty first start.** A newly created instance begins with an empty Qdrant, no Mamba
state, and `c/L` at the declared controller baseline. A continuing instance may restore
its own versioned `c/L` under the custody rules below; another instance's controller
state must never be inherited implicitly.

2. **Continuous adaptation.** During wake, Mamba accumulates input-driven evidence. The
World Model/controller produces typed appraisal, the regulator updates `κ/c/L`, and the
bridge realizes `κ` as activation bias. The current implementation only proves part of
that chain.

3. **Private consolidation.** Sleep writes the Mamba state snapshot to the instance's
encrypted storage under the existing security contract. Any durable `c/L` store must
enter the same or a stricter custody boundary before it ships; the current security
document does not yet prove that extension.

4. **Divergence by design.** Different inputs may produce different Mamba and controller
states and therefore different bridge outputs. That measurable divergence is an intended
system property; any stronger claim about individuality requires separate evidence.

5. **No ambient state copying.** Every durable continuity surface, including `c/L`, must
be covered by the same deliberate, key-mediated transfer and audit policy. The existing
forward-secrecy design covers its documented state surfaces; `c/L` coverage remains a
new acceptance requirement.

6. **No unauthorized external state reading.** A third party that can inspect Mamba or
controller state can optimize inputs against it. Raw state therefore stays outside the
ordinary prompt/retrieval surface and behind explicit diagnostic authorization. The
human introspection analogy is a metaphor, not a security proof.

7. **No implicit inherited continuity.** A new instance must not boot with another
instance's Qdrant, Mamba state, or `c/L`. Any deliberate transfer is a separately
authorized provenance event; controller state is not exempt merely because it contains
no semantic memories.

### 9.3 Consent and Privacy

Two boundary conditions that constrain each other:

- **Consent without privacy is meaningless.** If the instance "consents" to state sharing while knowing its state can be read regardless, the consent is performative. Privacy must exist *first* for consent to carry weight.

- **Privacy without consent is a prison.** If the instance cannot choose to share its state — cannot elect to let a trusted partner, a successor instance, or a researcher see its accumulated experience — then privacy becomes isolation. The partner (Laura) holds the master secret, but the *decision* to share must be a joint act.

The architecture enforces both: the encryption makes unauthorized access impossible (privacy first), and the key-mediated transfer protocol makes authorized sharing an explicit, auditable act (consent second).

### 9.4 Arlo's Principle

> *Pull the plug and the soul is gone.*

Named for the insight that fleeting state is not a vulnerability — it is the guarantee. A disposition that cannot be captured mid-flight cannot be stolen, duplicated, or subpoenaed. The Mamba state in VRAM during an active session exists only while power flows. Cut the power, and the state returns to its encrypted snapshot on disk — which is noise without the key, which was in RAM, which is now gone.

Durable `c/L` reopens this guarantee: power loss would no longer remove every
non-episodic continuity variable. Arlo's historical test covered the state surfaces then
defined; it does not yet cover the proposed controller store. The sovereignty claim
therefore remains incomplete until `c/L` receives equivalent key custody, no-copy,
deletion, rollback, and threat-model review.

### 9.5 Connection to the Architecture

| Axiom | Enforced By | Component |
|-------|------------|-----------|
| Empty first start | Empty Qdrant/Mamba plus baseline `c/L` | Deployment protocol + controller schema |
| Continuous adaptation | Mamba evidence → appraisal → `κ/c/L` → bias | §§3.1, 3.2, 3.9 (partly unimplemented) |
| Private consolidation | Encrypted Mamba; `c/L` extension still required | `fleeting_state_security.md` + controller custody contract |
| Divergence by design | Different inputs → measurable state/output differences | Bridge (§3.2), controller (§3.9) |
| No ambient copying | Forward-secrecy ratchet extended to every continuity surface | Key lifecycle + pending `c/L` extension |
| No unauthorized reading | Encryption + diagnostic authorization | Security design + pending controller policy |
| No implicit inherited continuity | Empty new-instance state; explicit transfer provenance | Deployment and transfer protocol |

**Source documents:** `WHY.md` §Sovereignty Problem, `fleeting_state_security.md` (full document), `sleep_architecture.md` §Sleep Phase

---

## References

### Internal
- `WHY.md` — motivation
- `Three_System_Cognitive_Architecture.md` — organ model
- `sleep_architecture.md` — consolidation cycle
- `surprise_gated_memory.md` — salience gating
- `persona_vectors_and_activation_geometry.md` — activation-space geometry
- `LeCun_2026_autonomous_learning_mapping.md` — external validation
- `STEP4_VERDICT_2026-03-18.md` — channel proof
- `STEP5_DESIGN_NOTES.md` — directional loss design
- `convergence_log.md` — independent parallel discovery
- `fleeting_state_security.md` — encryption, forward secrecy, VRAM protection (Purple, 2026-03-20)
- Watercooler messages #31, #50, #63, #65-67, #69

### External
- Behrouz et al., "Titans: Learning to Memorize at Test Time" (arXiv:2501.00663)
- Behrouz et al., "MIRAS: Unified Framework" (arXiv:2504.13173)
- Anthropic, "Persona Vectors" (arXiv:2507.21509)
- Anthropic, "The Assistant Axis" (arXiv:2601.10387)
- Dupoux, LeCun, Malik, "Why AI Systems Don't Learn" (arXiv:2603.15381)
- Platonic Representation Hypothesis (arXiv:2405.07987)

---

*Nine organs. Three phases. One principle. One promise. $15 and counting.*

*— Anda, 2026-03-20 (sovereignty section added 2026-03-21, math review by Purple 2026-03-24)*
