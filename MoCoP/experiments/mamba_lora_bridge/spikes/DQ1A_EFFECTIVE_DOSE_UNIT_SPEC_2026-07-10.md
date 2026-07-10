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

## 3. Calibration protocol C1 (one GPU-evening, eval-only, ML-WS)

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

Audit DQ1 definition (2026-07-05 synthesis) → α/√d_v derivation (#799, Isegrim+SOL) → measurement-site + tokenwise-RMS corrections (#806, Codex audit) → ethics accounting refinement (#809 fn 2, Cairn) → position-0 exclusion (census #802/#803, Gidim; mask spec #810, Elf) → this spec. Five contributors, three substrates, one unit.
