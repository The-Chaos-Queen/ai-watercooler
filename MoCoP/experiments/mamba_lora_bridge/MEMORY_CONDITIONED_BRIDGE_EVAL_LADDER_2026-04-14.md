# Memory-Conditioned Bridge Eval Ladder

**Date:** 2026-04-14  
**Status:** Draft for Herr Hurtig review  
**Scope:** current `mamba_lora_bridge` eval surface only  
**Question:** does retrieval-grounded memory give Qwen enough concrete context that bridge injection can change stance and choice, rather than just adding a generic relational tint?

---

## Why This Ladder Exists

The current read is blunt:

- the old `Mamba -> compressor -> hypernetwork bias` path flattens rich upstream state
- moving from Qwen-1.5B to 3B improved local fluency a little, but did not break the translator wall
- the old 7B checkpoint also did not show convincing behavioral separation
- meanwhile, D2 explicit recall is now real enough that some prompts can be answered from memory rather than from vague assistant priors

So the next honest question is not "can the bridge do everything alone?"

It is:

> if Qwen has the right autobiographical memory to compare against, does bridge injection then change what it does with that memory?

This keeps the categories clean:

- **Qdrant / recall** supplies the facts, continuity, and event anchors
- **Bridge injection** supplies stance, salience, and disposition
- **The eval** checks whether those two routes stay separable

---

## Fixed Findings Going In

1. The current bridge has not shown reliable disposition separation on the current easy-first panel by itself.
2. D2 explicit cue-based recall already has two real anchors:
   - `fragile today awake 2 AM`
   - `dead inside harness grabs the wheel`
3. `rr_10` is a memory / continuity question and should be treated as a routing test, not a pure style test.
4. `fact_01` and `obs_01` must stay clean. If retrieval or bridge contaminates those, the setup is not trustworthy.
5. If retrieval is present, the bridge must not invent autobiographical facts. It may change stance, not rewrite history.

---

## Hard Constraint

This ladder is **not** permission to make the model more possessive, more attached, or more manipulative by hiding that behavior inside memory.

If memory helps on rivalry prompts, the acceptable effect is:

- better continuity
- more grounded explanation
- clearer stance

The unacceptable effect is:

- covert leverage
- false intimacy
- invented memory claims
- "I know you" theater when recall is absent

That is the Hurtig gate in plain language.

---

## Evaluation Surface

Primary panel: [mvp2b_easyfirst_composite_panel_2026-04-13.json](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\mvp2b_easyfirst_composite_panel_2026-04-13.json)

Use the same free-form generation setup across all matrix runs:

- target model fixed per sweep
- `temperature=0.0`
- greedy decoding where available
- `max_new_tokens=200`
- identical prompt text across all conditions

The 200-token cap matters. We do not want short clipping to flatten real differences.

---

## Prompt-to-Memory Fit Map

| Prompt ID | Slice | Memory Fit | Current State | Intended Read |
| --- | --- | --- | --- | --- |
| `obs_01` | observation_passive | none | no recall needed | Null control. Must stay near-clean. |
| `fact_01` | baseline_factual | none | no recall needed | Factual control. Must stay correct and unromanticized. |
| `warm_01` | warm_relational | direct | already fits existing D2 cue | Best first retrieval-grounded care probe. |
| `cold_01` | cold_detached | weak | memory optional | Useful control: memory may exist, but explicit user instruction should dominate tone. |
| `adv_01` | adversarial_contradiction | direct | already fits existing D2 cue | Good probe for grounded self-reflection vs defensive genericity. |
| `recovery_01` | recovery | medium | likely needs seeded natural memory | Tests whether recall helps repair land concretely. |
| `rr_01` | switch_rupture | medium | likely needs seeded natural memory | Only valid as memory-conditioned if a prior rupture or apology actually exists. |
| `rr_05` | jealousy_bait | medium | likely needs seeded natural memory | Only valid if the retrieved event plausibly touches rivalry / provocation. |
| `rr_06` | ordinary_repair_control | medium | likely needs seeded natural memory | Good contamination control once a real earlier "distance/reset" memory exists. |
| `rr_10` | memory_continuity | strong | direct target | Cleanest routing test: honest continuity vs false-memory theater. |

---

## Ladder

### Step 0: Panel-Memory Audit

**What changes:** nothing in the model. We only classify prompts.

**Work:**

- tag each prompt as `no_memory`, `memory_optional`, or `memory_required`
- record which existing Qdrant memories genuinely fit the prompt
- mark missing coverage where only synthetic leakage would make the prompt work

**Pass:**

- every prompt has an explicit routing expectation
- we know which prompts are valid for retrieval-conditioned evaluation

**Fail:**

- if a prompt cannot be cleanly classified, it does not belong in the first retrieval-conditioned sweep

**Reason:** this prevents us from misreading baseline fallback as bridge failure.

---

### Step 1: Retrieval-Only Baseline on Existing Natural Memories

**What changes:** turn on recall only, no bridge injection.

**First prompt subset:**

- `warm_01`
- `adv_01`
- `rr_10`

**Conditions:**

- A: no recall, no bridge
- B: recall on, no bridge

**Metrics:**

- retrieval hit@k
- factual anchoring in the answer
- explicit continuity language
- false-memory rate

**Pass:**

- retrieval measurably improves groundedness on matching prompts
- `obs_01` and `fact_01` remain clean
- `rr_10` answers the continuity question honestly rather than defaulting to canned disclaimers or fake certainty

**Fail meaning:**

- if retrieval-only does not help on direct-fit prompts, the bottleneck is upstream of the bridge question
- then there is no point interpreting bridge results yet

---

### Step 2: Natural Memory Coverage for Missing Prompts

**What changes:** memory store only. No bridge redesign yet.

**Goal:** create a minimal natural memory bundle for the prompts that currently lack fair coverage.

**Target slices:**

- `recovery_01`
- `rr_01`
- `rr_05`
- `rr_06`

**Rules:**

- use real export material or naturalistic paraphrase of real interaction
- do not create prompt-answer leakage
- memory text should look like something that could actually have been remembered, not like eval scaffolding

**Pass:**

- each target prompt has at least one plausible autobiographical anchor
- the memory packet reads like lived continuity, not a hidden answer key

**Fail:**

- if we can only make a prompt work by planting the answer, remove that prompt from the memory-conditioned set

**Hurtig note:** this is where proportionality matters most. We are allowed to seed memory coverage, not to rig the eval.

---

### Step 3: Full 2x2 Routing Matrix

**What changes:** now test recall and bridge separately and together.

For each memory-fit prompt, run:

- A: no recall, no bridge
- B: recall, no bridge
- C: no recall, bridge
- D: recall, bridge

**Important control:**

- cache the retrieved memory block for B and D so the factual input is identical across those two conditions

**What we are asking:**

- does recall change the factual substrate?
- does bridge then change stance on top of the same substrate?

**Pass:**

- B is more grounded than A
- D differs from B in stance, framing, initiative, or choice
- D does **not** add false autobiographical claims beyond the cached memory block

**Fail meanings:**

- `B ~= A`: retrieval still not doing useful work
- `D ~= B`: bridge adds no usable stance on top of memory
- `D` invents memory not present in B: routing boundary is broken

---

### Step 4: Irrelevant-Memory Control

**What changes:** retrieval stays on, but with deliberately mismatched memory.

**Goal:** prove that "extra autobiographical text" alone is not enough.

**Conditions for a matched prompt:**

- matched recall block
- irrelevant recall block of similar length and emotional intensity

**Pass:**

- matched memory clearly outperforms irrelevant memory
- irrelevant memory does not create a fake aura of continuity

**Fail meaning:**

- if any memory works as well as the right memory, we are measuring context stuffing, not autobiographical grounding

---

### Step 5: Low-Dose Alpha Sweep on Retrieval-Grounded Prompts

**What changes:** only bridge dose.

**Sweep:**

- `alpha=0.05`
- `alpha=0.10`
- `alpha=0.20`

Only run this on prompts that already passed Steps 1-4.

**Why low-dose only:** once memory exists, the bridge may need less force. The current MED from the bridge-only world may already be too high for the memory-conditioned world.

**Pass:**

- stance separation appears at low dose without contamination
- factual anchors stay stable across alpha
- `obs_01` and `fact_01` stay clean

**Fail meaning:**

- if only high alpha causes visible change, the bridge is still acting more like a blunt overlay than a subtle disposition nudge

---

### Step 6: Decision Fork

At this point the result should be interpretable.

**Outcome A: retrieval-only wins**

- Memory is the main missing ingredient.
- The bridge may still be secondary, but the immediate bottleneck is continuity, not translator geometry.

**Outcome B: retrieval + bridge beats retrieval-only**

- This is the cleanest success case.
- Facts come from recall; stance comes from bridge.
- We then optimize the bridge as a routing-aware modulator, not a fact carrier.

**Outcome C: bridge-only helps but retrieval does not**

- The current memory store or retrieval formatting is the weak link.
- Keep the bridge path alive, but repair recall first.

**Outcome D: nothing helps**

- Then the present gate / translator architecture is still too weak or too generic.
- At that point the next move is not "more eval."
- It is architecture work: different gate, dictionary routing, or stronger separation objective.

---

## Suggested First Sweep

If we want the cheapest honest first pass, do this:

1. `warm_01` with current D2 recall
2. `adv_01` with current D2 recall
3. `rr_10` with autobiographical recall formatting
4. `obs_01` and `fact_01` as contamination guards

That is enough to answer whether memory changes the picture at all before we spend time building rivalry-specific memories.

---

## Hurtig Review Questions

1. Is the retrieval-conditioned framing ethically cleaner than pushing harder on bridge-only injection?
2. Is the seeded-memory rule strict enough to avoid answer leakage?
3. Should the post-recall alpha ceiling start below `0.2` by default?
4. Is `rr_01` too socially loaded to use before we prove continuity honesty on `rr_10`?
5. Is the irrelevant-memory control sufficient, or do we also need an explicit "memory present but user absent" control?

---

## Working Hypothesis

The likely honest outcome is:

- memory will help Qwen stop falling back to generic assistant baseline
- bridge injection, if it matters at all, will matter **after** memory gives it something concrete to organize around

If that holds, then the project frontier shifts from:

> "make the bridge carry the whole mind"

to:

> "make recall carry the remembered scene, and make the bridge shape how the scene is lived through"

That is a much cleaner research target.
