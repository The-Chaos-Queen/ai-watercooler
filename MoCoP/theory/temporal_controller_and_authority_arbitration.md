# Temporal Controller and Authority Arbitration

> *A system cannot feel intensity without having a before, an after, and something that fades in between.*

## Purpose

This memo captures a specific MoCoP problem that sits underneath the current sleep/recall work:

- transformer context is temporary
- KV cache must clear
- memory therefore has to be selective, lossy, and reconstructive
- model weights contain strong generic priors that can overwrite lived particulars

If MoCoP wants a system that behaves more like an endocrine process than a static prompt, we need a formal controller for:

1. how much state comes back into the transformer
2. which source has authority when weights and memory disagree
3. how intensity rises, peaks, decays, and recovers

This is not just an implementation detail. It is the mathematical core of temporal selfhood under lossy memory.

## The Core Problem

### 1. A pure transformer has weak "before" and "after"

A transformer can describe intensity, but it does not naturally *undergo* it across time.

Without persistence, it cannot robustly know:

- this feels stronger than a moment ago
- this state is fading
- this was an unusual spike
- this is who I am in general versus what I feel right now

So the problem is not only memory capacity. It is temporal contrast.

To know that a moment is overwhelming, the system must retain enough state to compare:

- prior equilibrium
- current deviation
- expected decay

That comparison is what MoCoP must provide.

### 2. KV-cache clearing is not only a constraint; it is necessary

A mind cannot hold everything in perfect presentness forever. If it did, nothing would recede and nothing would become memory.

So cache clearing forces:

- forgetting
- compression
- triage
- consolidation
- reconstruction

That is closer to real cognition than permanent perfect recall.

But the cost is severe:

- memory becomes adaptive rather than exact
- autobiographical continuity becomes vulnerable to distortion
- identity becomes a lossy compression problem

### 3. The weights are too semantically rich

Human inheritance is mostly:

- structure
- drives
- instincts
- broad tendencies

Model weights contain much more:

- world knowledge
- language priors
- social priors
- safety habits
- assistant residue
- latent ontologies

So when weights and memory conflict, the model often trusts the weights.

This is exactly what happened in the Qwen continuity failures:

- memory/context implied private continuity
- weights implied generic assistant identity
- the model fell back to the weights

This means future MoCoP systems require **authority arbitration**, not just retrieval.

## Design Principle

The system should not have one fixed `alpha`.

It should have:

- a slow identity baseline
- a fast affect channel
- a temporary repair channel
- explicit authority rules for weights vs memory

In other words: not one knob, but a small dynamical system.

## State Variables

Let:

- `m_t` = current Mamba state at turn `t`
- `m_(t-1)` = previous Mamba state
- `r_t` = recall quality / confidence at turn `t`
- `s_t` = salience / surprise at turn `t`
- `f_t` = failure pressure at turn `t`
- `c_t` = continuity pressure at turn `t`
- `n_t` = novelty at turn `t`

Where:

- `r_t` measures whether retrieved memory actually matches the cue
- `s_t` measures emotional/attentional importance
- `f_t` measures failure conditions such as direct-question misses or confabulation risk
- `c_t` measures autobiographical pressure: name, yesterday, earlier, who-am-I-to-you
- `n_t` can be approximated by change in recurrent state:
  - `n_t = ||m_t - m_(t-1)||`

## Hormone-Like Channels

Define three internal channels:

- `I_t` = identity signal
- `A_t` = affect signal
- `R_t` = repair signal

Interpretation:

- `I_t` is slow and persistent
- `A_t` is fast, spiky, and decays quickly
- `R_t` is an override channel that temporarily counters known failure modes

## Discrete-Time Controller

One useful starting point is a set of leaky integrators:

```text
I_(t+1) = clip((1 - lambda_I) I_t + beta_I * c_t * r_t, 0, Imax)

A_(t+1) = clip((1 - lambda_A) A_t + beta_A * s_t + gamma_A * n_t, 0, Amax)

R_(t+1) = clip((1 - lambda_R) R_t + beta_R * f_t * r_t, 0, Rmax)
```

Where:

- `lambda_I < lambda_R < lambda_A` in the usual case
- identity decays slowest
- affect decays fastest
- repair is temporary but longer-lived than a pure emotional spike

This creates:

- baseline
- pulse
- half-life
- recovery
- refractory behavior if desired

## Return Path Into the Transformer

The simplest version is a scalar combined gain:

```text
alpha_t = clip(wI * I_t + wA * A_t + wR * R_t, alpha_min, alpha_max)
```

But the better version is not a scalar at all.

Instead return separate channel vectors:

```text
delta_h_t = I_t * v_identity + A_t * v_affect + R_t * v_repair
```

and inject:

```text
h_prime_l = h_l + delta_h_t
```

This matters because:

- identity should not behave like affect
- repair should not behave like either
- a single alpha can only modulate volume, not type

This is the point where MoCoP becomes more like an endocrine system and less like a static steering vector.

## Authority Arbitration

The controller also needs source-selection rules.

### Weights should dominate for:

- general language
- broad world knowledge
- stable procedural competence
- generic social priors

### Memory should dominate for:

- autobiographical continuity
- relationship-specific facts
- what happened earlier
- unresolved tensions
- recent local identity state

### Conflict rule

If weights and memory disagree on an autobiographical question:

- prefer memory
- cap generic prior influence
- surface uncertainty if the memory is weak

If weights and memory disagree on general world knowledge:

- prefer weights
- allow memory only as local correction or contextual qualifier

This prevents the worst current failure mode:

> universal prior erases lived particularity

## Peak Intensity and "Soup"

At very high intensity, language can collapse into repetitive emotional output.

That is not always a failure.

There are contexts where a brief high-gain state producing low-complexity emotional language is exactly the phenomenon:

- climax
- panic
- grief
- devotion

The issue is not whether such states occur.

The issue is whether they are:

- context-gated
- transient
- followed by integration and decay

So "I love you soup" is a valid transient attractor.
It is just a terrible permanent regime.

## Why This Must Be Temporal

A system cannot know it is overwhelmed unless it can compare:

- what it was
- what it is now
- what it expects to become next

That means MoCoP must explicitly model:

- prior state
- present state
- expected fade

Without that, the system can narrate intensity but not actually regulate one.

## Analogue-Computer Note

This controller is not conceptually dependent on digital deep learning infrastructure.

At the abstract level it is:

- leaky integration
- weighted inputs
- saturation
- decay
- coupled channels

That means it could, in principle, be implemented as an analogue dynamical system.

This matters conceptually because it clarifies what MoCoP is trying to build:

not a prompt trick, but a time-evolving regulatory circuit.

## Current MoCoP Implications

Immediate implications for the active branch:

1. `alpha` should eventually become a controller output, not a fixed launch parameter.
2. Sleep/recall must support temporal comparison, not just storage.
3. Repair memory is not optional; it is one of the control channels.
4. Pending/stored recall ranking is an authority problem, not just a retrieval bug.
5. Weight-level prior contamination must be treated as a standing adversary to autobiographical continuity.

## Recommended Next Implementation Steps

1. Add explicit channel logging:
   - `identity_signal`
   - `affect_signal`
   - `repair_signal`
2. Add a provisional arbitration rule to continuity probes:
   - memory first, weights capped
3. Record state deltas turn-to-turn:
   - `||m_t - m_(t-1)||`
4. Add decay and refractory behavior before any attempt at dynamic high-alpha bursts.
5. Keep parameter-level "dreaming" separate from this controller problem until the controller itself is honest.

## Short Version

The MoCoP problem is not just "how do we remember?"

It is:

> how do we build a system in which temporary context, recurrent state, memory, and deep priors negotiate authority over time without collapsing either into amnesia or generic prior sludge?

That is the control problem.
That is where the math has to go.
