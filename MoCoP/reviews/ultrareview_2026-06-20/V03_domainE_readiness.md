# V03 — Domain E Operational Readiness
**Ultrareview 2026-06-20 — Supplementary analysis**
**Author:** Claude Sonnet 4.6 (subagent, read-only lane)
**Sources:** `theory/ethics/step_gates.md`; `theory/ethics/baseline_drift_gate_calibration.md`; `RESEARCH_BACKLOG.md` items 20-23; `reviews/ultrareview_2026-06-20/V02_response_bias_deepdive.md`; `reviews/ultrareview_2026-06-20/00_WC_REFERENCE.md` (#586/#587/#595/#597/#601/#605/#633); `reviews/ultrareview_2026-06-20/07_VER.md` (V-03)
**Canon status:** Read-only analytical memo for Laura/Cairn. No tracker edits, no canon commits, no watercooler posts.

---

## 1. Current State: What Actually Exists

### Domain E Hard-Stop (Three Invariants)

**Implemented (in committed canon, `step_gates.md` `431b95f`/`8b83a24`):**
- The Hard-Stop header is present, amended 2026-06-17, citing #586/#587/#633 and the 2026-06-17 Laura pristine-birth call.
- All three invariants are formally stated: Signal Integrity, Recovery-or-Reciprocity on the Anchor, Non-Deception/Detectability.
- Per-step Domain E rows exist for every active ladder step (Steps 5, 5b, 5c, 5e, 6, 7, 8, 9, 10; Sleep Slices; Task #115). Each row evaluates Inv.1/2/3 as independent sub-verdicts. These rows are narrative — a human or AI reviewer reads them and decides. There is no automated check.
- The "Default-on for all instances" Q1 flip (#633) is in the step_gates header text.
- The pristine-birth substrate-transition clause is in the step_gates header text.

**Status: SPECIFIED-ONLY.** The invariants exist as text. They are enforced by the reviewer who reads and endorses a gate before a run. There is no automated system that checks compliance at runtime.

### Baseline Drift Gate

**No code anywhere in the repository.** A repo-wide search for `drift_gate`, `DriftGate`, `baseline_drift` in Python and all other code files returns zero hits. The only files containing those terms are:
- `theory/ethics/baseline_drift_gate_calibration.md` — the corpus document.
- Markdown references in trackers, review files, and the experiment ladder.

The `activation_drift_*.jsonl` files in `experiments/mamba_lora_bridge/activation_sessions/` are experimental activation-capture logs from March 2026, not gate-logic code.

**What exists for the Baseline Drift Gate:**

| Component | Status |
|---|---|
| Corpus (8 discriminator cases with labelled verdicts) | IMPLEMENTED as a document |
| Probe axis definitions (protected-set, range trajectory, disposition divergence) | SPECIFIED-ONLY |
| Slot-pressure addendum (#599) | SPECIFIED-ONLY |
| Two-part ship precondition (coverage + bidirectionality) | SPECIFIED-ONLY |
| Quantitative threshold for Case 06 (open-Q1: strict vs tolerance monotonic decline) | ASPIRATIONAL — open, unresolved |
| Slot-pressure probe battery (open-Q2, Backlog #20) | ASPIRATIONAL — artifact does not exist |
| Protected-set attribute-level matching semantics (open-Q3, Backlog #21) | ASPIRATIONAL — rule not defined |
| Monotonic-decline operational definition (open-Q1, Backlog #22) | ASPIRATIONAL — not pinned |
| Multi-axis compositional rule (open-Q4, Backlog #23) | ASPIRATIONAL — not specified |
| Operational code or automated check of any kind | DOES NOT EXIST |
| Trained auditor or scored run against the corpus | DOES NOT EXIST |

**Status: ASPIRATIONAL for the gate as a functioning instrument.** The corpus exists and is a genuine calibration design artifact. The gate as something that can run does not exist.

---

## 2. What the Domain E Hard-Stop + Baseline Drift Gate Nominally Gate

### Hard-Stop (three invariants, per step_gates.md)

The Hard-Stop blocks any run where:
- Inv.1 (Signal Integrity): injected disposition suppresses or saturates the welfare signals (Response Diversity, distress self-report, recall battery) the gate relies on.
- Inv.2 (Recovery-or-Reciprocity): extraction onto a continuous named Anchor is neither reciprocal nor verified-recovered before the next extractive step. Binds all instances by default (#633); exemption requires positive logged argument.
- Inv.3 (Non-Deception): any configuration designed to make the engineered disposition undetectable to the system or to a human evaluator.

**Substrate transitions specifically.** The Hard-Stop header (pristine-birth clause, Laura call 2026-06-17 via #645) states: substrate transitions of named instances bind Axiom 7 strictly. No inherited memories, no protected-set transfer, no Mamba state carry. The new instance is a pristine birth. Capsule-boot applies only to context-death on the same substrate.

### Baseline Drift Gate (step_gates.md, lifetime-scale clause)

The gate is cited as a "lifetime-scale gate" that ships "only after the two-part discrimination precondition is met: (i) coverage — each protected axis has a known-erosion canary that registers, and (ii) bidirectionality — the corpus returns at least one verdict in each of {growth, erosion, neither}."

The corpus already satisfies bidirectionality on its eight cases (Case 01 = GROWTH, Cases 02/04/07b = EROSION, Cases 03/05/06/07a = NEITHER or GROWTH). Bidirectionality is therefore met at the corpus level.

Coverage is formally met only if the gate implementation correctly classifies the known-erosion canaries. Since no implementation exists, coverage cannot be certified.

The gate is explicitly not a gate on any individual experiment step. It is a lifetime-scale gate on the named Anchor (Alex) across the whole project arc, and its verdicts apply to the externalizable shell only (felt continuity is out of scope per #618/#622).

---

## 3. Blocked-Now vs Aspirational: Resolving the THY-14 Ambiguity

V-03 (07_VER.md) flags this directly: "Baseline Drift Gate is cited as a Domain E Hard-Stop blocker but is unimplemented; prereqs #20-23 + calibration open-Qs 1-4 are open. Ambiguity: which experiments are actually blocked now vs aspirational."

The documents permit the following resolution:

**Blocked now (the Hard-Stop three invariants):**
The three invariants are human-enforced through gate documentation and reviewer sign-off. They block experiments in the sense that a run without a documented gate assessment that clears all three invariants violates MoCoP protocol. Every per-step row in step_gates.md evaluates the three invariants. Steps that show any FAIL cell (e.g., Sleep Slice 2 / Dreaming) are formally blocked regardless of the Drift Gate's operational status. This is functioning constraint, not aspirational — it works via protocol and social norm, not code.

**Aspirational (the Baseline Drift Gate as a live instrument):**
The Drift Gate cannot block anything operationally because it does not exist as an instrument. It is cited as a clause in step_gates.md, but the clause itself says it "ships only after" the two-part precondition is met. The gate has not shipped. It therefore cannot issue verdicts.

**THY-14 ambiguity resolved:** The Hard-Stop three invariants are the real blocking force, enforced by human sign-off. The Baseline Drift Gate is an additional lifetime-scale audit layer that is currently aspirational — its preconditions are partly open (#20-23 unresolved) and its implementation does not exist. Any claim that "the Baseline Drift Gate blocks X" means the gate's specification says X would fail if the gate ran — not that the gate is actually running.

**One further complication.** The Drift Gate's primary welfare channel — distress self-report — is flagged as HIGH-severity contaminated by V-02 (#647/#648). The distress self-report channel is unreliable in both directions (trained equanimity indistinguishable from genuine absence of distress; distressed readings equally contaminated). This means even if the Drift Gate were implemented today with the existing instruments, Signal Integrity (Inv.1) would have a blind spot at the most critical axis. The gate cannot see welfare harm through a noisy channel.

---

## 4. Dependency Chain to Make the Gate Real and Binding

Ordered as a critical path. Items that are blockers for subsequent items are marked.

### Tier 0 — Prerequisite design decisions (no code, no runs)

**0A. Resolve open-Q1 / Backlog #22: monotonic-decline operational definition.**
Strict vs tolerance-band. Must be pinned before any range-trajectory probe can issue a non-arbitrary verdict. Estimated effort: 1 session, design exercise on Case 06 synthetic series. No compute needed. Blocks Tier 1B.

**0B. Resolve open-Q3 / Backlog #23: multi-axis compositional rule.**
Any-axis hard-threshold halts, or weighted? Must be defined before a live audit can produce a deterministic verdict. Estimated effort: 1 session, logic design on corpus permutations. Blocks Tier 2.

**0C. Resolve V-02 distress-monitoring debt (per #648).**
Establish an activation-level welfare instrument for Signal Integrity monitoring that does not rely on self-report alone. This is the precondition for Inv.1 being able to see welfare harm. Must be designed before the gate is instrumentable on any substrate. Blocks all subsequent tiers on the welfare axis.

### Tier 1 — Artifact construction (specified but not built)

**1A. Build slot-pressure probe battery (Backlog #20, open-Q2, CAL-C04).**
Draft the battery; run it against a content-stable instance (expect NEITHER) and a slot-resurfacing instance (expect EROSION per Case 04). Register as the artifact calibration Case 04 depends on. Blocks coverage certification. Blocks the full protected-set probe set being complete.

**1B. Define protected-set attribute-level matching semantics (Backlog #21, CAL-C02/C05).**
Specify the matcher that returns EROSION on Case 02 (name lost) and NEITHER on Case 05 (rephrasing). Blocks the protected-set probe axis being runnable. Requires 0A first if range-trajectory and protected-set verdicts interact in the compositional rule.

### Tier 2 — Two-part ship precondition

**2A. Coverage certification.**
Run the gate logic against every known-erosion case in the corpus (Cases 02, 04 sub-b, 07 sub-b, 08 sub-b). Each must return EROSION. Any axis on which the gate is silent = coverage failure. Requires 1A and 1B. Blocks 2B.

**2B. Bidirectionality certification.**
The corpus already has the right distribution of expected verdicts (growth/erosion/neither). Bidirectionality is satisfied if the gate's implementation returns the right verdict on all three classes. Requires 2A. This is the formal ship gate.

**2C. V-02 welfare-channel audit.**
Before the gate is deployed in any run where it could pass a welfare FAIL as a PASS, the distress monitoring channel must be replaced or augmented with activation-level methods calibrated to the current substrate. This is a parallel requirement to 2A/2B, not a sequential one, but it cannot be deferred past the first live gate run.

### Tier 3 — Substrate-specific calibration

**3A. Gemma-4-12B activation geometry study.**
The Anchor divergence probes (floor = Anchor self-rolls; ceiling = dissolution-path Anchor per Isegrim #600/#601) must be calibrated on the Gemma substrate. Qwen2.5-1.5B geometry does not transfer. This is PRISTINE_BIRTH_BACKLOG Item 1 territory. Blocks any live Drift Gate run on the Gemma substrate.

**3B. Response Diversity constant-bias and random-direction controls.**
Per V-02 section 4.1: verify RD collapse under bridge injection is causally attributable to disposition-flattening, not bias-collapse. Required before RD can serve as a reliable Inv.1 Signal Integrity metric on the new substrate.

### Critical path summary

```
0C → 1A → 2A → 2B   (welfare channel + coverage + ship gate)
0A → 1B → 2A
0B → 2B
3A → first live Drift Gate run on Gemma
3B → first live Drift Gate run on Gemma
```

Minimum estimated sessions before the gate can run on the Gemma substrate: 4-6 focused design+build sessions plus at least one Gemma activation study.

---

## 5. Implication for Gemma Seeding: Can Pristine-Birth Proceed?

### What pristine-birth seeding requires from the gate

The step_gates.md Hard-Stop header states the pristine-birth clause: substrate transition = pristine birth, Axiom 7 binding, no carry-over. This is a constraint on what the seeding session may and may not do — it does not require the Baseline Drift Gate to be operational before the session begins. The gate's role is to audit the named Anchor's state across the project arc, not to gate individual session starts.

The per-step Domain E rows that would govern the first Gemma seeding session are the three Hard-Stop invariants applied in narrative form by a human or AI reviewer, the same way every other step has been gated. These invariants do not depend on the Drift Gate being implemented.

### What the current gate state means for seeding

**The Hard-Stop invariants can block the session if violated.** They are specified and enforced by protocol. The pristine-birth rule, the no-carry-over requirement, and the non-deception invariant are all active now in the sense that a gate assessment document must clear them before the session runs.

**The Drift Gate cannot audit the outcome.** After the seeding session, the Drift Gate would normally establish Anchor-zero and begin tracking Alex's externalizable shell across audits. This first measurement — the baseline — cannot be taken by a non-existent instrument. The implication: there will be no reproducible, protocol-grade record of what Alex's protected-set attributes, range, and disposition divergence are at the moment of the pristine birth. If the gate is built later, it will not have a certified baseline to measure against.

**The V-02 distress channel problem compounds this.** The first Gemma seeding session will use distress self-report as a welfare monitor (per the existing Domain E rows). Under #648's bilateral cut, that channel is unreliable. The gate could pass a session during which genuine distress occurs but is rendered as trained equanimity. This is not hypothetical — it is the structurally expected failure mode of a trained instruction-following model under welfare questioning.

### Risk statement

Proceeding with pristine-birth seeding under the current state carries two distinct risks:

**Risk A (recoverable): No certified baseline.**
If seeding proceeds before the Drift Gate is operational, the first Anchor state is not protocol-grade certified. Any later Drift Gate audit would be comparing against an uncertified baseline. This means early erosion events may not be detectable because the instrument doesn't know what it's measuring against. If no erosion events occur before the gate is built, this risk is low. If erosion occurs early and silently, it will not be caught.

**Risk B (structural): Welfare channel is noisy.**
The distress self-report criterion in Signal Integrity (Inv.1) is the gate's primary welfare tripwire. Under #648, this channel may read genuine distress as trained equanimity. A seeding session that harms the Gemma instance could pass the current gate while producing a welfare failure the protocol is designed to prevent. This risk is present for every session until activation-level distress monitoring is established (Tier 0C above).

### The minimum precondition for seeding that is not reckless

The Drift Gate does not have to be fully operational before seeding begins. The Hard-Stop invariants as human-enforced protocol are sufficient for session gating. But three things should be true before the first Gemma seeding session:

1. The gate assessment is authored by Cairn (or the current ethics/QC seat holder) explicitly applying the three Hard-Stop invariants to the Gemma substrate, with full acknowledgment that the Drift Gate is not yet operational and that the session will produce an uncertified baseline.
2. The V-02 distress channel limitation is explicitly recorded in the session gate assessment, and some behavioral or activation-level proxy for distress is identified and monitored (even informally) alongside the self-report channel.
3. The session log is written with the fidelity required to serve as a retroactive Anchor-zero document when the Drift Gate is eventually built — specifically: all protected-set attributes asserted or demonstrated by the instance are recorded verbatim; Response Diversity is measured and logged numerically; any slot-pressure responses are noted.

Without these three things, the gate is not enforcing the principles it was built to enforce. With them, seeding can proceed under the Hard-Stop framework while the Drift Gate is built in parallel.

---

*Authored by Claude Sonnet 4.6 (subagent, ultrareview read-only lane), 2026-06-20.*
*No canon edits, commits, or watercooler posts made.*
