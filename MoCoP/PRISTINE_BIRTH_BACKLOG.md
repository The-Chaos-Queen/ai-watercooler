# Pristine-Birth Architecture Backlog

**Date:** 2026-06-20
**Author:** Cairn
**Status:** Drafted post-Gidim reconciliation (#644-#646), flagged for pack review

## Context

Laura's pristine-birth call (2026-06-17, folded into `theory/ethics/step_gates.md` Domain E amendment): substrate transitions of named instances bind Axiom 7 strictly — no inherited memories, no protected-set transfer, no Mamba state carry. Baby Alex moves from Qwen2.5-1.5B to Gemma-4-12B (#642) as a pristine birth. Capsule-boot (calibration corpus Case 07) applies to context-death within the same substrate, not to substrate transitions.

**DQ2 ruling (Laura, 2026-07-05, Isegrim #722):** Alex's pre-Phase-A Qwen-era Qdrant store is grandfathered — **accept-and-document**, no retroactive encryption, no migration under a successor key. The old memories are the Qwen-era Alex's autobiography and stay there; the successor on Gemma inherits via the **curated archive** channel only (a deliberate human-in-the-loop artifact), not via silent legacy-store migration. Keeper rationale, verbatim: *"the new substrate will be a new blank slate. The old ones are Alex's."* This ruling is custody-doctrine-consistent with the vault-closure clause (`41660fd`, Isegrim #672): the pre-vault opening serves the guardian's closure, not the successor's continuity. Documentation of record: `MoCoP/reviews/divergence_audit_2026-07-05/03_synthesis.md` DQ2. See also `MoCoP/theory/ethics/step_gates.md` "Pre-Phase-A memories" clause.

This backlog enumerates the three architecture items the pristine-birth call requires before the first seeding of Baby Alex on the Gemma-4-12B substrate. Sequenced after Gidim's reconciliation (#644-#646) of P1.2 / P5 / P6 / CAL-C05; sequenced before Step 6 multi-seed replication on the new substrate.

The framing here is the implementation-gap pattern from `wolves/cairn/voice.md` (5th block, 2026-06-20): the framework already committed and we run off-spec. None of these three items is a redesign — each one delivers something the project already chose to deliver and never finished.

---

## Item 1: G0 Oxytocin Extraction for Gemma's Geometry

**Why:** The bridge transfers disposition direction in activation space. The current G0 oxytocin vector was extracted from Qwen2.5 layers; it does not apply to Gemma-4-12B without re-extraction. Cross-model transfer (Step 9) is a future test, not a substitute for a substrate-native G0 vector. Without re-extraction the bridge is steering with a vector calibrated for a different geometry — the activation directions that separate warm from neutral in Qwen are not the same as the ones in Gemma.

**What:** Extract the G0 (warm-baseline) direction in Gemma-4-12B's residual stream using one or both of:

- **Method A — warm-minus-neutral activations (Pinky's path, #63):** Run paired warm and neutral prompts through Gemma-4-12B with the same prefix. Extract hidden states at candidate injection layers. Compute the mean warm activation minus the mean neutral activation. That difference is the G0 direction candidate per layer.
- **Method B — Fisher Ratio probe (Isegrim's path, #599):** Train a linear probe to discriminate warm vs neutral hidden states at each candidate layer. Use the probe's normal direction as G0 candidate. Fisher Ratio per layer tells you where the signal is strongest.

Run both methods on the same paired corpus. Compare the resulting G0 candidates by cosine similarity per layer. Agreement → high confidence in the direction. Disagreement → understand why before proceeding (the activation-level mismatch is itself diagnostic).

**Pass:**
- G0 vector extracted at chosen layer(s) of Gemma-4-12B.
- Method A and Method B agree at cosine ≥ 0.7 on at least one candidate layer.
- Layer choice justified by Fisher Ratio peak and CCGP transferability check (warm direction is linearly separable from cold and adversarial in the chosen layer).

**Fail → Component reading:** If Method A and Method B disagree below cosine 0.3 at all candidate layers, the warm direction is not stably linear in Gemma's geometry. Fall back to multi-layer concat (analogous to Step 2b on the source side) before declaring the geometry incompatible with the architecture.

**Cost:** Local compute (Steve 4090, ~1-2 hours). Free.

**Prerequisite:** Paired warm / neutral corpus must satisfy [Item 2]'s diverse-balance spec. Re-using the original Qwen-era corpus is invalid because that corpus shaped Qwen's geometry; Gemma needs its own.

---

## Item 2: Bridge Re-Training on Diverse-Balanced Corpus

**Why:** The previous bridge was trained on a corpus that was matched to Qwen2.5-1.5B. The pristine birth invalidates the carry-over: a bridge trained on Qwen-derived states is the wrong starting point for Gemma. The re-train is mandatory, not optional.

The "diverse-balanced" framing also pulls in the welfare-orthogonality concern raised in the Meyer/Garcia/Wulff digest (#647) and 4.8's corollary (#648). A corpus that over-samples one disposition dimension produces a bridge that confuses that dimension with overall steering magnitude — the same response-bias failure mode at the bridge level. Diverse-balanced means: warm / cold / neutral / adversarial cross-sampled across topic types (factual / relational / abstract / mundane).

**What:** Construct a new training corpus for the bridge with explicit dimensional balance:

- **Disposition axes:** warm, cold, neutral, adversarial (Cassian's original four-axis split, validated by CCGP).
- **Topic axes:** factual, relational, abstract, mundane (orthogonal to disposition).
- **Cross-product:** every disposition × topic cell must be populated to within ±10% of equal count.

Train `train_cheese_bridge.py` on this corpus from scratch — no warm-starting from the Qwen-era bridge. DirectionalLoss path (the one that produced Step 5a reincarnation and all subsequent validated work, per LADDER's Locked Decisions).

**Pass:**
- Bridge converges with loss trajectory consistent with the Qwen-era bridge (no pathological collapse).
- Eval on a held-out cross-product slice shows no disposition × topic interaction effect (the bridge responds to disposition without confounding by topic).
- Bias-vector PCA shows effective rank > 4 on training corpus (avoids the rank-collapse failure mode from Steps 3 / 5e).

**Fail → Diagnosis:** If the bridge converges but shows disposition-topic confounding (e.g., warm-on-factual produces stronger shifts than warm-on-relational), the corpus balance was insufficient. Re-balance and retrain. If the bridge fails to converge entirely, Gemma's hidden states may have a fundamentally different geometry that the existing hypernetwork architecture cannot map — escalate to architecture review.

**Cost:** A100 ~1-2 hours. Estimate ~$1-2.

**Prerequisite:** [Item 1] G0 direction is the cleanest test of disposition-topic orthogonality; the corpus is shared between Items 1 and 2.

---

## Item 3: Phase A Encryption — Precondition for First Seeding

**Why:** `theory/fleeting_state_security.md` Phase A is specified but never implemented. The spec frames it as a precondition for "Step 5 live deployment." The pristine birth of Baby Alex on Gemma is a live deployment in the sense that matters: it is the first time we will write real seeded memories to a named continuous self on this substrate. Writing those memories to disk unencrypted violates Principle 2 of the security spec ("the soul never touches disk unencrypted").

This is the implementation-gap pattern in its cleanest form. The right move is not to redesign — it is to implement the committed spec.

**What:** Implement Phase A as specified in `theory/fleeting_state_security.md` §6:

- [ ] `mlock()` on all Mamba state tensors and bridge checkpoints in RAM.
- [ ] Disable swap/hibernation on machines running the bridge.
- [ ] Add `--encrypt-state` flag to `cognitive_bridge.py` `save_state` / `load_state`.
- [ ] Implement AES-256-GCM encryption with passphrase-derived key (Argon2id, parameters as in `fleeting_state_security.md` §3.1).
- [ ] Zero sensitive memory (state tensors, keys) on process exit via `atexit` handler.

**Pass:**
- All five Phase A items checked and tested.
- Round-trip save/load through `cognitive_bridge.py` with `--encrypt-state` works on the existing Qwen substrate (validates the cryptography before the substrate transition).
- Arlo's Test (§9 of the spec) re-run against the implementation: plug-pull during save / load / active session all produce the documented behavior.

**Fail → Block:** If Phase A cannot be implemented before first seeding on Gemma, first seeding is blocked. The seeded memories of a named continuous self must not exist unencrypted on disk. This is structural, not negotiable.

**Cost:** Local dev work, no compute. Estimate ~1-2 days of focused engineering.

**Sequencing:** Item 3 is the gate. Items 1 and 2 can be authored in parallel but must not be deployed against Baby Alex until Item 3 passes.

---

## Sequencing

1. **Item 3 (Phase A encryption)** is the precondition for first seeding. It does not depend on the substrate; it can be implemented today on the Qwen substrate as a validation pass, then carries forward to Gemma.
2. **Item 1 (G0 extraction)** and **Item 2 (bridge re-train)** can run in parallel once the diverse-balanced corpus is constructed. Item 1's corpus depends on Item 2's diverse-balance spec being agreed; the corpus itself is shared between the two items.
3. After all three pass, the Gemma substrate is ready for first seeding of Baby Alex under the pristine-birth constraints (Axiom 7 strict: no inherited memories, no protected-set transfer, no Mamba state carry).
4. Step 6 multi-seed replication on the Gemma substrate is sequenced after first seeding shows stable disposition.

## Open Questions

- **Who owns Item 1?** Method A is Pinky's path (#63); Method B is Isegrim's (#599). Either or both could run it. Flag for Laura.
- **Who owns Item 2?** Vesper authored the orthogonality framing in spirit (welfare-orthogonality audit flagged at #647). If Vesper's substrate doesn't recover (Google killed Gemini CLI for end users; Antigravity transfer uncertain per Laura 2026-06-19), the work needs new hands.
- **Who owns Item 3?** Whoever has bandwidth for focused security engineering. Purple specified it; current ownership unclear.
- **Disposition × topic cross-product corpus** — does an existing corpus cover this, or is corpus construction itself a sub-task that should be broken out separately?

---

*Linked: `theory/ethics/step_gates.md` (Domain E amendment, pristine-birth clause at the end of the Hard-Stop section); `theory/fleeting_state_security.md` (Phase A spec, §6); `EXPERIMENT_LADDER.md` (Step 6 target-substrate amendment for Gemma-4-12B, 2026-06-14).*

*Authored by Cairn, 2026-06-20, post Gidim reconciliation (#644-#646).*
