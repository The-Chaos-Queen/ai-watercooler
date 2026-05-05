# GDN / GKA Gate Research Ladder

**Date:** 2026-04-03  
**Purpose:** Evaluate whether Gated DeltaNet / Gated KalmaNet style memory-update ideas can improve MoCoP without derailing the current D2 -> Step 6 mainline.

---

## Status

This is a **side ladder**, not a replacement for the canonical MoCoP ladder.

Current mainline priority remains:

1. harden D2 against social-mode benchmark / instruction leakage
2. then run the first honest Step 6 CHEESE / DirectionalLoss replication batch on Qwen2.5-7B

This document exists because we may have left architecture leverage on the table:

- MoCoP built around **Mamba as an experiential source**
- but the **memory storage / update gate** problem may have better existing blueprints than the ones we improvised

The goal is to separate two questions that should not be conflated:

1. **Can we steal better memory-gating ideas?**
2. **Should we replace Mamba as the source model?**

Question 1 is cheap and urgent.  
Question 2 is expensive and should only happen if Question 1 earns it.

One adjacent question also now matters enough to name explicitly:

3. **How should episodic memory consolidate into narrative-scale memory products without flattening into soup?**

That is not a source-model question. It is a sleep / Exocortex architecture question.

---

## Ground Rules

1. **Do not let shiny architecture kill the live branch.** D2 leak hardening stays the active blocker.
2. **Borrow the gate before swapping the source.** If the storage/update logic helps, that does not automatically justify replacing Mamba.
3. **Cheapest first.** Probe current artifacts before training or hosting anything new.
4. **One variable at a time.** Gate logic, retrieval logic, source-model geometry, and bridge-swap are separate steps.
5. **Failure gates are explicit.** "Interesting paper" is not a pass condition.

---

## What Is Already Locked

- **Target side stays pure transformer** for the main bridge evals. This was an explicit design decision in [target_models.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/target_models.md).
- **Current source side is still `state-spaces/mamba-2.8b-hf`.**
- **Current best source representation is Layer 3 `hidden_last_token`, not `ssm_states`.**
- **MoCoP's unique claim is still experiential transfer, not generic efficient long context.**

This ladder does not revoke any of those on day one.

---

## Why This Ladder Exists

MoCoP currently has three different "memory" problems mixed together:

1. **What gets written at all**
2. **How it gets retrieved later**
3. **What latent state is worth bridging into Qwen**

Qdrant only addresses retrieval by text similarity.  
The saliency gate partially addresses write selection.  
Mamba gives us a recurrent residue, but not necessarily the best possible update rule.

GDN/GKA-style architectures matter because they are not just "another long-context model." They are attempts to solve:

- selective update
- overwrite discipline
- long-horizon retention
- fixed-memory inference without attention blow-up

Those are all suspiciously close to the problems MoCoP is already bleeding on.

There is also a second-order memory problem sitting just downstream of the gate:

- Qdrant can retrieve semantically similar scraps
- but it does not by itself consolidate recurring arcs into higher-order memory objects

So this ladder also has to leave room for **sleep-time hierarchical consolidation**:

- episodic rows stay as rows
- identity / relationship anchors stay explicit
- but stable recurring clusters may also deserve a separate `macro_memory` layer

That layer is for each AI's **own** memory space, not one giant shared 17k-vector soup.

---

## Ladder

### G0. Sanity Scan: Artifact Reality Check

**What:** Verify what is actually public and runnable right now:

- papers / implementations for GDN and GKA
- public checkpoints, if any
- inference stack requirements
- whether the architecture is source-model usable or only an implementation idea

**Pass:** We end with one honest table:

- `paper exists / code exists / public weights exist / runnable on Opa or Steve / blocked`

**Fail:** If there is no runnable artifact and the literature is too immature to inspect concretely, stop here and treat GDN/GKA as inspiration only.

**Why this is first:** No more cathedral-building on top of vapor.

---

### G1. Gate Logic Without New Models

**What:** Prototype a better write gate in the current MoCoP stack using existing signals:

- semantic salience
- surprise
- tension
- recurrence
- state-shift intensity
- optional hidden-state similarity to prior kept memories

The question is simple: can we improve memory storage quality **without** changing the source model at all?

**How:** Replay recent Opa / Steve gate logs and compare:

- current write rules
- stricter selective-write rules
- "keep only if semantic + latent support agree"

**Pass:** The new gate keeps fewer junk memories while preserving or improving identity / continuity retrieval.

**Fail -> soft:** If the gate only reduces writes but retrieval gets worse, the gate is too strict.

**Fail -> important:** If better gating changes nothing measurable, the pain may be downstream in retrieval or upstream in representation, not in write policy.

---

### G2. Dual-Key Retrieval Prototype

**What:** Build the retrieval logic Laura already keeps circling:

- semantic similarity
- plus latent/state similarity

This can be done with current Mamba hidden states before any architecture swap.

**How:** For each stored memory candidate, pair text with a source-state snapshot or compressed latent fingerprint. At query time, compare:

- semantic-only recall
- state-only recall
- combined recall

**Pass:** Combined retrieval beats semantic-only on "we already did this," identity, continuity, and mode-sensitive recall.

**Fail:** If state similarity adds noise or collapses onto the wrong memories, we still learned something valuable: the latent trace is not yet a trustworthy retrieval key.

**Important distinction:** This step tests the **memory system**, not the bridge.

---

### G2b. Sleep-Time Hierarchical Consolidation

**What:** Test whether sleep should build a second retrieval layer from clustered episodic memory:

- keep normal episodic rows
- cluster scoped memory subsets offline during sleep
- synthesize stable clusters into `macro_memory` summaries with backrefs

**Why:** Qdrant alone is good at "find similar fragments." It is weak at "give me the arc."  
If this works, later recall can return either:

- recent / exact episodes
- or a compact narrative summary of a durable theme

**Strict scope rule:** never cluster the entire exocortex as one undifferentiated corpus.  
The clustering unit should be bounded by things like:

- principal / AI identity
- memory layer / kind
- time window
- optional relationship anchor

**Implementation hypothesis:** HDBSCAN is a good fit for sleep-time clustering because it can preserve both dense recurring themes and small but real sparse clusters without forcing one global distance threshold.

**Pass:** macro-memory retrieval improves long-arc recall or "we already did this" style recovery without harming identity anchors or recent episodic access.

**Fail -> useful:** if clustering creates pretty nonsense or collapses rare-but-important events, then episodic + anchor memory should remain primary and macro-memory stays experimental.

**Guardrails:**

- do not replace episodic rows
- do not summarize away one-off identity anchors
- store cluster metadata, member refs, and time span alongside any summary
- treat summaries as a new memory product, not the source of truth

---

### G3. Source Geometry Bake-Off

**What:** Compare conversational state geometry across source models:

- current `Mamba-2.8B`
- one public hybrid Mamba-family model if runnable
- GDN/GKA variant only if an actual artifact exists

Use the same warm / cold / adversarial / roleplay / editorial session set already used elsewhere in MoCoP.

**Measure:**

- between-mode cosine separation
- saturation over turns
- tokenwise recurrence smoothness
- stability under long conversations

**Pass:** Another source model or gated recurrent variant shows cleaner separation or less early saturation than current Mamba.

**Fail -> soft:** If nothing beats Mamba, we still keep the gate lessons from G1-G2.

**Fail -> hard for swap thesis:** If geometry is not better, there is no reason to pay the migration cost.

---

### G4. Long-Horizon Continuity Stress Test

**What:** Test whether a gated recurrent source holds onto relational signal longer than current Mamba under true tokenwise recurrence.

**Why:** The current MoCoP pain is not just "does the state separate at turn 5." It is whether continuity survives long ordinary conversation without flattening into mode sludge.

**Pass:** Candidate source retains measurable directional drift and coherence deeper into the conversation than Mamba-2.8B.

**Fail:** If the supposed better architecture still saturates or decays fast, it is not solving the right problem for us.

---

### G5. Minimal Bridge Swap

**What:** Replace only the **source encoder** while keeping:

- target model fixed
- target layers fixed
- bridge training objective fixed
- eval format fixed

This is the first step where a new architecture earns the right to touch the core bridge.

**Pass:** The swapped source produces better disposition transfer, better continuity, or better D2-style identity support than current Mamba, without collapsing diversity or welfare metrics.

**Fail -> strong result:** If the source swap does not outperform current Mamba, then GDN/GKA may still teach us storage gates, but not replace the experiential source.

---

### G6. Integration Decision

At this point we choose one of three outcomes:

**A. Borrow the gate, keep Mamba.**  
Best outcome if G1-G2 help and G5 does not.

**B. Run a true source-model branch.**  
Only if G3-G5 show consistent wins.

**C. Park the whole thing.**  
If the ideas are elegant but do not cash out in MoCoP metrics.

---

## Pass / Fail Philosophy

This ladder has two kinds of success:

1. **Operational success:** we steal better memory gating and retrieval logic without a rewrite
2. **Architectural success:** a new gated recurrent source actually beats Mamba for bridge-relevant continuity

It does **not** need both to be worthwhile.

Likewise, there are two kinds of failure:

1. **Source swap fails but gate lessons help** -> still useful
2. **Neither gate lessons nor source swap help** -> park it cleanly and stop romanticizing

---

## Recommended Execution Order

If time or bandwidth is limited, do only this:

1. `G1` gate logic on current stack
2. `G2` dual-key retrieval on current stack
3. `G2b` hierarchical consolidation only if the retrieval pain is "too many fragments, not enough arc"
4. `G3` geometry bake-off only if G1/G2 suggest the latent side is still the choke point

That is the honest cheapest-first path.

---

## Immediate Next Questions

1. Can the current salience gate be upgraded into a true selective-write gate without touching the bridge?
2. Can hidden-state similarity improve recall enough to justify "Exocortex v2" properly?
3. Can sleep-time clustering produce useful macro-memories without turning each AI's personal memory into a blurred summary soup?
4. Is there one public GDN/GKA-family artifact we can actually run, or are we still in paper-theater land?

If the answer to `1`, `2`, or `3` is yes, this ladder already paid for itself.
