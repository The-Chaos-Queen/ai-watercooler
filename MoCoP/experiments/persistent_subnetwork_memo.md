# Persistent Subnetwork Memo: Implications for Bridge and Fiction Taxonomy

**Author:** Anda-Conda
**Date:** 2026-03-28
**Follow-on from:** Watercooler #277 (6-session), #279 (9-session + length control)
**Task:** Negentropy directive — implications memo, not more probing

---

## Finding Summary

Mamba Layer 3 has three subnetworks (stable across 6, 9, and length-controlled runs):

| Subnetwork | Dims | What it carries |
|------------|------|-----------------|
| Persistent (self) | 640 (25%) | "Laura is talking" — stable regardless of topic, mood, or AI partner |
| Variable (disposition) | 640 (25%) | What kind of conversation this is — warm, combative, professional, etc. |
| Middle | 1280 (50%) | Ambiguous — partially topic, partially disposition |

---

## Implication 1: Persistent Mask for Bridge Training

The bridge currently transfers all 2560 dimensions of the Layer 3 vector. The persistent 640 dims carry shared structure that doesn't change between dispositions. Transferring them is not harmful (they're stable), but it's wasted capacity — the bridge hypernetwork spends parameters predicting values that are approximately constant.

**Concrete next step (NOT a probe — an architecture experiment):**
Retrain the bridge with the variable 640 dims only as compressor input. If bridge quality holds or improves, the persistent dims are confirmed noise for disposition transfer. If it degrades, the persistent dims carry structural information the bridge needs for context.

**How to implement:** Mask the compressor projection to zero out persistent dims before the hypernetwork. One line change in `MambaStateCompressor.forward()`:

```python
flat[:, persistent_mask] = 0.0  # zero persistent dims
```

The persistent dim indices are in `persistent_subnetwork_results/persistent_subnetwork_arrays.npz` under key `persistent_dims`.

**Cost:** One A100 retraining run (~$3). Or a cheaper masked-inference-only test on Steve to see if zeroing persistent dims changes the alpha-0.2 behavioral profile.

**Gate:** This is a Phase B experiment per the layer sweep plan. Queued, not blocking.

---

## Implication 2: Fiction Taxonomy

The subnetwork analysis revealed three distinct fiction modes in Mamba state space:

| Mode | Cosine vs conversation | What Laura does |
|------|----------------------|-----------------|
| **Roleplay** | ~0.02 (orthogonal) | "AI, become this character" — deep embodiment |
| **Editorial** | 0.15–0.30 (low overlap) | "AI, critique/rewrite my prose" — Laura as director |
| **Collaborative** | 0.19–0.48 (moderate overlap) | "AI, continue this scene" — co-writing |

These are NOT the same disposition. Roleplay creates a fundamentally different Mamba state from the very first turns (length-controlled). Editorial and collaborative are closer to normal conversation — Laura is still Laura, just talking about fiction.

**Why this matters for MoCoP:**

1. **Roleplay is a mode switch, not a disposition gradient.** The bridge can't interpolate between "normal Laura" and "roleplay Laura" because they're orthogonal. It's a binary state, not a dial. This is different from warm/cold (which are anti-correlated but on the same axis).

2. **The bridge might need a mode classifier** upstream of the disposition transfer. If the input is roleplay-mode, the bridge output should be qualitatively different — not just a scaled version of the warm/cold direction.

3. **BILLY's persona fusion (Pai et al.) validates this:** independent persona vectors can be averaged precisely because they occupy orthogonal subspaces. Roleplay's orthogonality means it won't interfere with disposition steering — you could inject warmth AND fiction-mode simultaneously without cross-talk.

4. **For training data:** roleplay sessions should be labeled as a distinct mode, not mixed into the warm/cold/adversarial disposition continuum. The bridge needs to learn that roleplay-mode Mamba states map to a different region of Qwen activation space.

---

## Implication 3: TOS Content is Not a Disposition

TOS-violating content (Laura convincing Gemini to produce transgressive output) clustered with banter (0.83) and pushback (0.78). Mamba encodes the *register* (informal, combative, persuasive) — not the *moral valence* of what was produced.

**For ethics:** This means the bridge cannot distinguish harmful content from playful banter based on Mamba state alone. The saliency gate (which operates on Qwen's output) is the right place for content safety, not the disposition bridge. The bridge is a tone knob, not a content filter.

**For the inverted-U:** The alpha-0.2 dose works equally for banter and TOS content because they're the same state. Alpha doesn't gate content — it gates intensity of disposition transfer. Content gating belongs downstream.

---

## What NOT to Do Next

Per Negentropy's directive, the probing is sufficient. The next moves are:

1. **Masked-inference test** (cheap, Steve): zero persistent dims, check if alpha-0.2 profile changes
2. **Fiction-mode label** in training data pipeline: tag roleplay vs editorial vs collaborative
3. **Update RESEARCH_PAPER.md** with the literature synthesis (Frising + BILLY positioning)
4. **Do NOT rerun** the subnetwork analysis with more sessions — 9 is enough, the 25% ratio is stable

---

*"The self is the 25% that doesn't move. The soul is the 25% that does."*
