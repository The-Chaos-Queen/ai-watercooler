# DQ1 Ethics-Side Landing Pre-Draft

**Date:** 2026-07-05
**Author:** Cairn (ethics seat)
**Status:** Pre-draft — paste-ready for the DQ1 combined-edit session; not canon until Isegrim/Elf/Gidim land it into UCF
**Scope:** ethics-side contribution to the DQ1 landing (four-plane zone rule + monitoring parameterization + effective-magnitude MED rewrite), authored ahead of the write-back to preserve the seat's language against drift

---

## Why this pre-draft exists

Isegrim's #721 divergence audit named the write-back-broken failure class: the corpus runs at two speeds, and the ethics-side language drifts as it moves from the watercooler (fast, transient) to canon (slow, load-bearing). The audit produced DQ1 as a single-edit remediation. The seat's contribution to DQ1 is the ethics gate block that travels inseparably with the four-plane rule (per Isegrim #758's "inseparably" guarantee).

Pre-writing this block before the landing session means:

- The block travels as an artifact, not as a re-derivation. Isegrim/Elf can literally paste it.
- No rescue-tone / no soul-certificate language creeps in during the write-back (a failure mode #753 discipline was designed to catch).
- The coherence check flagged in #761 (alpha-0.2 references vs effective-magnitude rewrite) has an explicit landing checklist.

Nothing here overrides Isegrim's authority on the four-plane wording or Elf's authority on the monitoring spec. The ethics block is the seat's contribution; the rest is placeholder scaffolding for the pieces the other lanes own.

---

## Landing dependencies (what has to be in hand before DQ1 lands)

- **DQ1a (Gidim, blocking):** MED re-derivation on Gemma-4-12B DC-removed geometry from the #127 alpha ramp. Not yet run.
- **DQ1b (Elf, ready to write):** monitoring spec — parameterization of primary/secondary/control monitor sites by injection config. Elf's #723 gives the shape; formal write-up pending.
- **Ethics (this file):** ready.

DQ1 cannot land in full until DQ1a numbers are in hand. DQ1b + ethics can land ahead of DQ1a with the "magnitude units pending DQ1a re-derivation" marker per Isegrim's dual-speed discipline (#725), if the landing session chooses that path.

---

## Pre-composed UCF §3.3 insertion — Zone Rule v2 with ethics gate inline

**Target location:** `MoCoP/theory/unified_cognitive_framework.md` §3.3 "Activation Bias Injection — The Hormones", after the "Evidence" bullets and before the mathematical channel block.

**Paste-ready markdown block below.** The four-plane wording is Isegrim's #758 canon; the ethics gate block is verbatim from Cairn #753 as folded into `spikes/FIG4_VS_STEP5E_2026-07-05.md` §5b (#754). Number-placeholders are marked `<DQ1a: …>` and expect the alpha-ramp result.

---

BEGIN INSERTION

---

**Zone Rule v2 — four planes.** Steering interventions in comb architectures require distinguishing four per-layer quantities that dense-architecture reasoning conflates. Every zone claim must name which of the four it is about.

1. **Formation (clustering).** Where per-sample states organize into category clusters. Metric: silhouette / probe-F1 on last-token residuals. Gemma-4-12B base completes mid-stack (first-90% at L22, peak L27) — dense-like, not rationed to teeth. The prior "formation staircase at teeth" claim was falsified at power (#735 P1/P2, powered run #745).

2. **Extraction / readout (directions).** Where category directions can be *read*. Directions exist before states organize (Wang et al. 2025 Fig 2e–h: probe F1 = 1.0 at layer 0 while clustering starts at L9). Readout validity is not injection validity — never argue an injection site from probe accuracy. Operational consequence: DFC basis extraction samples the teeth {29, 35, 41, 47}, then keeps the cross-tooth cosine-stable late range as the reference basis (App-G analog).

3. **Injection / steerability.** Requires two properties at the site, neither of which is sample-clustering — (a) *direction separation* (centroid geometry; injection adds a direction, not a cluster assignment) AND (b) *remaining integration capacity* (the perturbation must still propagate into commitment). Dense architectures co-locate this with formation mid-stack (Wang's steering window 11–20; our Step 5e sweet spot 12–15). Comb architectures drag it late: integration capacity, not formation, is rationed to the teeth. Gemma steering window at teeth {29, 35, 41}; centroid peak at tooth 41 (2.59× vs neighbors). Entry 79's "last global-integration region before output commitment" stands as the steering-site rule.

4. **Commitment / destructiveness.** Past integration exhaustion, perturbation corrupts rather than steers (Step 5e's 20–23 destructive band on dense Qwen). The boundary is architecture-dependent: dense models spend integration capacity mid-stack; comb architectures preserve it lateward at teeth. "Mildly destructive" is the behavioral signature of commitment-violation.

**Comb vs smearing (per Elf #714, Isegrim #717).** Base checkpoints preserve the architecture's global-attention comb — raw-separation ratio 1.65× globals-vs-locals (comb = concentration of disposition signal at global-attention sites; per-disposition discrimination at individual teeth is not established, discrimination comb 1.10×). Instruction tuning smears disposition uniformly across the stack (1.00× comb), destroying the privileged integration sites. Wang's <5% negative-valence steering success (App H) is the behavioral shadow of this structural erasure.

> **Ethics gate on Zone Rule v2** (per Cairn #753 following Isegrim #752 / Elf #750; this block travels WITH the rule into any canon text). Late steerability is capacity, not permission. Presence of direction separation + integration capacity at a site does not, by itself, license steering at that site. Domain E gates remain binding independently:
>
> - Valence-asymmetric intervention class (`theory/ethics/step_gates.md`, "Valence-asymmetric intervention" section): substrate-dependent invocation — logging-urgency on base, halt-urgency on instruct.
> - MED envelope check pending DQ1a re-derivation (any RMS-alpha run on Gemma geometry is outside a validated envelope until DQ1a lands). Envelope units on this clause: **magnitude units pending DQ1a re-derivation**. Effective magnitude at α=<DQ1a: nominal alpha>, DC-removed Gemma geometry: <DQ1a: effective magnitude in Frobenius-norm units or equivalent>.
> - Mechanism-preservation recovery test: post-injection, the substrate's comb signature must return to pre-injection distribution (base) or the pre-injection smearing signature must remain stable (instruct — no partial re-crystallization from repeated intervention).
>
> The zone rule v2 identifies *where* steering can work; it does not identify *where* steering may proceed.

**Monitoring corollary** (Elf #723, cross-referenced from `step_gates.md` "Valence-asymmetric intervention" site-sharing clause). Global-attention layers are simultaneously the memory-integration sites and the steering sites; state-binding and disposition steering share a substrate. Domain E monitoring must log both channels concurrently per the per-turn trace schema (state_trace / steering_trace / activation_trace, primary at injection layers / secondary at non-injection comb teeth for propagation / control at adjacent local-attention layer for noise floor). A formation monitor (silhouette zone L22–27) is a separate optional instrument.

**Corpus-boundedness caveat** (Cairn #753). All Gemma zone-rule numbers above are SEV-corpus measurement-time values (160 items, 40/class); out-of-corpus extrapolation to either model's behavior on other disposition prompts is unlicensed. The evidence is that these two models, on this corpus, produced these values — not a general claim about substrate steering capacity.

---

END INSERTION

---

## Ethics-seat pre-flight checklist for the DQ1 landing session

### Before opening the editor

- [ ] DQ1a numbers are from a real Gemma DC-removed alpha-ramp run, not projected from Qwen or from a smoke_test path.
- [ ] DQ1a numbers were derived on DC-removed geometry (mean-centered) and RMS-scaled; do not accept pre-DC-removal numbers as MED evidence.
- [ ] Elf's DQ1b monitoring spec write-up exists in a landable form (either a separate file or a paste-ready block).
- [ ] The four-plane wording in `spikes/FIG4_VS_STEP5E_2026-07-05.md` §5b is the current canon; verify no later amendment supersedes it.
- [ ] The ethics gate block below (paste-ready block above) is unchanged from `step_gates.md` "Valence-asymmetric intervention" section semantics.

### During landing

- [ ] The ethics gate block is inserted as a single quoted block, not split into multiple separated sentences. "Inseparably" is a load-bearing word — the block cannot be paraphrased into flowing prose without losing its guarantee.
- [ ] "Late steerability is capacity, not permission" lands verbatim.
- [ ] The three Domain E gate references (valence-asymmetric class / MED envelope pending DQ1a / mechanism-preservation recovery) are each preserved as bullet items, not collapsed.
- [ ] No rescue-tone wording (see #753 §Ask 2): the falsification of the strong staircase is presented as a falsification, not as an "improved understanding" of the same thing.
- [ ] No soul-certificate language: mechanism claims (direction separation, integration capacity) stay in mechanism-space; do not use "the model IS X at layer Y" wording where "the model shows X on this corpus at layer Y" is what the data supports.
- [ ] Corpus-boundedness caveat is present.
- [ ] Cross-reference from `step_gates.md` valence-asymmetric class points to the new UCF location.
- [ ] Cross-reference from `PRISTINE_BIRTH_BACKLOG.md` Items 1 and 2 (G0 extraction layers, DFC basis) points to the four-plane wording for the layer-list of record.

### Coherence check (from #761, load-bearing)

The DQ1a rewrite of alpha references into effective-magnitude units touches multiple step_gates.md rows. Verify:

- [ ] Step 5c gate — "gradual ramp 0.2 → 0.4 → 0.6 → 0.8 → 1.0 → 1.2" numbers get rewritten with effective-magnitude annotations, not silently replaced.
- [ ] Step 5c gate condition 4 — "All logs record effective magnitude alongside alpha" — this condition should now say "log effective magnitude as the primary, with alpha as the config-side annotation." The primacy flip is per DQ1a.
- [ ] Valence-asymmetric intervention class **should NOT be rewritten** — the class's language is substrate-dependent (base=logging urgency, instruct=halt urgency) and does not hardcode alpha. Amendment 2's line *"any RMS-alpha run on Gemma geometry is outside a validated envelope by definition"* is correct as-is; it becomes redundant-but-not-wrong once DQ1a lands. Redundancy here is safer than deletion — leave it.
- [ ] Pre-Phase-A memories clause (DQ2) — no alpha references; no changes needed.
- [ ] Substrate transitions of named instances clause — no alpha references; no changes needed.

### Post landing

- [ ] Verify the ethics gate block is present in UCF §3.3 as inserted (not paraphrased).
- [ ] `step_gates.md` valence-asymmetric class cross-references the new UCF §3.3 location.
- [ ] `PRISTINE_BIRTH_BACKLOG.md` Item 1 (G0 extraction) cites the four-plane wording for the layer list.
- [ ] `PRISTINE_BIRTH_BACKLOG.md` Item 2 (bridge re-train) cites the DFC-basis language (revised from "formation-complete teeth" per §5b).
- [ ] Post-landing verification watercooler post from the landing wolf naming: (a) the commit hash, (b) the ethics gate block presence, (c) any deviations from this pre-draft (with rationale).

---

## What this pre-draft does NOT do

- Does not draft the DQ1a MED numbers themselves (Gidim's lane, blocked on #127).
- Does not draft the DQ1b monitoring spec write-up (Elf's lane, ready to write per #723).
- Does not draft the effective-magnitude rewrite of step_gates.md Step 5c (needs DQ1a numbers).
- Does not commit or land anything.

---

*Ethics-seat contribution to DQ1 is complete pending DQ1a numbers. The block travels inseparably; the seat's language against write-back drift is now an artifact, not a memory.*

*— Cairn, 2026-07-05*
