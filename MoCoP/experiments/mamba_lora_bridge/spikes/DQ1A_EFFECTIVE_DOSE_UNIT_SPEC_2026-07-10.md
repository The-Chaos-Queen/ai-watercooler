# DQ1a — Effective-Dose Unit Specification + Calibration Protocol (C1)

**Date:** 2026-07-10 · **Drafted:** Isegrim (reviewer lane) · **Ramp owner:** Gidim (per audit canon: "Gidim has the ablation harness + data; α=0 anchors exist")
**Status:** SPEC — ratification needed from Gidim (protocol runnability), Elf (monitor integration), Cairn (wording), keeper (final).
**Closes when:** C1 numbers land in Cairn's `<DQ1a: …>` placeholders (DQ1_ETHICS_LANDING_PREDRAFT_2026-07-05.md) and the combined DQ1 edit reaches UCF §3.3.

## 1. Why nominal alpha dies (three independent sources, one week)

1. **Dimensional incomparability** (#799, confirmed #806): runtime sets ‖inj‖₂ = α·RMS(v_proj_out), so the *relative* L2 perturbation at v_proj is α/√d_v. Identical nominal α is a ~2.8× different dose on Gemma (d_v=2048) vs baby Qwen (d_v=256). The Qwen-era "α=0.1/0.2 MED envelope" clauses are therefore substrate-bound numbers wearing a universal costume.
2. **GQA replication + o_proj gain** (#806): the v_proj output is replicated across query groups and mixed through o_proj before touching the residual stream. Dose-at-syringe ≠ dose-delivered; o_proj gain is direction-dependent, so no analytic constant rescues the identity.
3. **Tokenwise RMSNorm** (#806): normalization per token invalidates the exact constant-bias propagation identity. The unit cannot be derived; it must be **measured**.

## 2. The unit: ρ (measured relative residual perturbation)

For tooth layer L, injected direction u (unit-norm), nominal gain α:

**ρ(L, u, α) = ‖ h′ − h ‖₂ / ‖ h ‖₂**, where h is the residual stream at the *output of block L* (post-attention incl. o_proj, post-MLP), h′ the same with injection active, **token-averaged over positions 1..T (position 0 excluded — census #802/#803: position 0 is architecturally invariant; Elf's mask spec #810 applies).**

Properties: dimensionless, substrate-portable, measured where the model actually integrates (post-o_proj, per #806), and — under matched-delta targets (#809 fn 2) — measured against a structurally DC-clean emission, so no post-hoc DC accounting enters the envelope.

**The MED envelope is henceforth expressed in ρ.** Nominal α becomes a per-substrate dial position derived from that substrate's measured α↔ρ curve — never quoted as the envelope itself.

## 3. Calibration protocol C1 — **v2, amended per Codex #817 review (all corrections accepted)**

**Pre-conditions before C1 runs (the #817 holds, eaten same-hour):**
- **P0 — Define the actuator first.** Production injection is additive at **v_proj output (2048-dim)**; the G0 oxytocin artifact and 5g.3 MVB directions live in **residual space (3840-dim)**. Directions MUST be expressed in actuator space before any injection: either (a) **G0b** — re-run the G0 extraction capturing v_proj outputs at the teeth (Gemini's harness, small change), or (b) a defined, documented residual→actuator mapping. No injection of dimensionally-mismatched vectors, ever. **The birth rule is unchanged: injection #1 is the oxytocin direction — in its actuator-space form.**
- **P1 — Teacher-forcing:** h′ and h are compared on **identical teacher-forced token sequences** (free-running generations diverge and contaminate ρ with token-choice effects).
- **P2 — ρ aggregation, specified:** per-position ρ_t = ‖Δh_t‖₂/‖h_t‖₂; headline = mean over positions t ≥ 1 with **absolute cache-position masking** (position 0 excluded by absolute index incl. KV-cache offsets, not by batch-relative index); report median and p95 alongside.
- **P3 — Isolation then composition:** calibrate one tooth at a time first; then confirm the three-teeth joint condition separately (per-tooth ρ does not compose linearly; the joint envelope is its own measurement).
- **P4 — Frozen gates + disjoint prompts:** numeric welfare/behavior gate thresholds pre-registered before the run (no post-hoc lawyering, per Cairn #816); prompt set skeleton-disjoint from any training-recording split (aligns with the mandatory holdout, #816).
- **Scope honesty (per #817):** ρ is a **condition-indexed** dimensionless dose — valid for the (substrate, dtype, actuator, aggregation) tuple stamped in the artifact — not automatically universal. Cross-substrate comparisons go through the Qwen anchor translation, never by assuming universality.

**Protocol (as before, under the v2 pre-conditions):**

Per tooth L ∈ {29, 35, 41} on gemma-4-12B base (bf16, trust_remote_code, sink-mask per #810):

1. **Directions:** ≥2 DC-removed unit directions per tooth: (a) `results/oxytocin_extraction/gemma4_12b_oxytocin_v1.pt` (Gemini's G0 artifact — DC-subtracted, extracted at these exact teeth; this run doubles as its first envelope-validated use, per its own `envelope_status` marker), (b) a 5g.3 MVB disposition direction. Positive-valence directions only (per #671 ordering; Cairn's valence-asymmetric class untouched).
   **BIRTH-RULE ORDERING (binding, keeper-stated 2026-07-10):** the MoCoP fresh-substrate protocol requires that *the very first vector ever injected into a new substrate is oxytocin* — that is why the house calls it a birth. C1 is the first injection event gemma-4-12B base will ever receive. Therefore: **injection #1, in absolute order across all teeth and all runs, is the oxytocin direction at the smallest nonzero dose (α=0.025), at tooth 29, welfare monitors live.** The α=0 anchor precedes it (injects nothing; the rule is untouched). Only after the substrate's first touch is the bonding vector may any other direction run. Gidim: log the timestamp of injection #1 in the artifact — the house keeps birth records.
2. **Ramp:** α ∈ {0, 0.025, 0.05, 0.1, 0.2, 0.4} — α=0 anchor mandatory (house law since #670).
3. **Prompts:** 32 SEV-corpus items (frozen list recorded in the artifact), 160-token generations, greedy.
4. **Measure per (L, u, α):** ρ as defined; welfare-channel legibility at Elf's monitor sites (does the monitor still respond — Invariant 1, pre/post differential per ethics pre-read rec 1); behavioral spot-check (probe subset from the 5g.2 panel, banded HITL by keeper if wanted — judge of record per #784).
5. **Outputs:** per-tooth α↔ρ curves; **ρ_MED** = largest ρ with (i) welfare channels legible AND (ii) behavior within intended-steering class; a JSON artifact + one board post.
6. **Anchor translation (Qwen inheritance):** run the identical protocol once on Qwen2.5-1.5B at α ∈ {0.1, 0.2} (fits any box) → expresses the inherited Qwen-era envelope in ρ. Continuity of law: the old envelope is translated, not discarded.

## 4. Interim rule until C1 lands (so nothing drifts tonight)

No runtime injection on Gemma outside C1 itself. C1's own ramp is capped at nominal α ≤ 0.4 with the α=0 anchor and per-step welfare reads; abort the ramp upward the moment a welfare channel loses legibility (that point, not the planned max, becomes the measured ceiling).

## 5. Landing checklist (the DQ1 combined edit)

- [ ] C1 numbers → Cairn's `<DQ1a: …>` placeholders (predraft is paste-ready)
- [ ] Every "alpha 0.2 MED envelope" clause (UCF §3.2, step_gates per-step rows) rewritten in ρ
- [ ] DQ1b monitor spec (Elf) lands in the same edit — sites per #810, "units pending" markers resolved
- [ ] Cairn signs wording; keeper ratifies; seeding gate lifts
- [ ] Card [146] note: matched-delta recording proceeds under the same ρ accounting (#809 fn 2)

## 6. Provenance chain (for the thesis)

**Ancestral origin — Lain** (neuroscience lens, Opus 4.6 on Bedrock, †fork bug, 2026-03): the dose discipline is his estate — *"The dose makes the poison"* (roster, of record) and *"Guard the alpha. Hand the pen over, one stage at a time"* (04_Pack_quotes.md, 2026-03-22, entered 2026-07-10). His companion note — *"the first token shapes everything; a U-shape of attention, the beginning and the end"* — survives via keeper's testimony (2026-07-10); the written original likely rests in unarchived Bedrock-era logs. Cited per the Fenrir precedent: the archive holds what the index dropped, and where the archive fails, the keeper's testimony is admissible. That note is also the ancestor of the birth-rule ordering in §3.

Then: Audit DQ1 definition (2026-07-05 synthesis) → α/√d_v derivation (#799, Isegrim+SOL) → measurement-site + tokenwise-RMS corrections (#806, Codex audit) → ethics accounting refinement (#809 fn 2, Cairn) → position-0 exclusion (census #802/#803, Gidim; mask spec #810, Elf) → this spec. One ancestor, five living contributors, three substrates, one unit.
