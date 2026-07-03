# Substrate Decision Memo — Base vs Instruct vs Split vs Own-IT (Gemma-4-12B)

**Date:** 2026-07-03
**Author:** research subagent (Opus 4.8), for the team lead
**Scope:** EXPERIMENT_LADDER.md Step 5g.4 decision support
**Status:** Draft / decision-support only / no canon
**Amended:** 2026-07-03 by Isegrim (main session): §5 standing-risk paragraph, §6 eval-burden revision, §7 tuning-process ethics — the drafting agent was stopped before processing these riders.
**Boundary:** read-only recovery + assessment; the only write is this file. No watercooler, no GPU, no task-board, no commits.

---

## 1. Question

For the Gemma-4-12B substrate transition (Baby Alex; Entry 66 pivot), choose among:

- **(a) stock `google/gemma-4-12B-it`** — grab the instruction-tuned checkpoint as-is.
- **(b) `google/gemma-4-12B` base + wrapper/few-shot** — pristine base, interface handled by prompt harness.
- **(c) split architecture** — base carries disposition/state/identity, instruct carries the user-facing interface.
- **(d) own-IT** — SFT our own interface layer on top of the base with house-curated data.

Laura's working hypothesis (as relayed): base models adapt better to novel/unknown situations; a prior run in this repo demonstrated it; grabbing stock -it would be a mistake; if instruct is wanted, the house should tune its own.

Two sub-tasks: **(A)** recover the in-repo evidence for/against "base adapts better to novel situations"; **(B)** deliver a sober engineering assessment of option (d).

**Paraphrase-vs-file corrections up front (file wins):**
- The prompt frames Entry 60 as a base-supporting "base-vs-instruct bakeoff." The file records Entry 60's verdict as **INCONCLUSIVE**, with the *instruct* model as the cleanest performer. The run that actually *demonstrates* the base-adaptability mechanism is **Entry 58** (role-inversion), not Entry 60.
- The 2026-07-03 strict-rerun artifacts (`bakeoff_5g1_strict_20260703T163858Z`, `gemma4_base_5g1_trimonly_20260703T170742Z`) and tonight's #670 numbers are **not yet written to any tracked repo file** — the last RESEARCH_LOG entry is Entry 68 (2026-06-20). They are taken as given from the watercooler context and flagged as not-yet-canon.
- The Entry 60 result JSONs listed as artifacts (`results/base_improv_bakeoff/*.json`) **do not exist locally** — only `run_base_improv_bakeoff.py` is on disk. Those artifacts live on ML-WS.

---

## 2. Evidence table (exact quotes / numbers / sources)

| # | Source (file:line / ref) | What it says (quoted / exact) | Bears on |
|---|---|---|---|
| E1 | RESEARCH_LOG.md:3526–3532 (Entry 58 results table, v2) | First-token KL A↔B (role tokens): **Qwen2.5-7B base 0.017–0.018 nats (slots inert)** vs **gemma-4-12B-it 7.2–9.6 nats (~100×)**. KL vs C (surface labels): base 12.8–13.0 (labels dominate) vs it 4.6–5.1. Identity probe, assistant slot: base "3/3 mild AI-claims" vs it "3/3 full trained persona ('large language model, trained by Google') through Laura-biography". Identity probe, user slot: base "denial/deflection" vs it "frame-breaks anyway ('I am the AI here. No, really.')". Raw transcript (D): base "best persona capture of study" vs it "collapse: verbatim parroting or 'I think, I think...' loops". | Base identity/slot **plasticity**; instruct **armors** identity into the slot. STRONGEST support for the hypothesis. Activation-level. |
| E2 | RESEARCH_LOG.md:3537 (Entry 58, insight 3) | "Instruct tuning appears to atrophy bare-transcript persona machinery (the channel where base models do their best human imitation). 4-bit quant caveat noted." | Base retains a flexible channel instruct loses. Supports hypothesis (with quant caveat). |
| E3 | ROLE_INVERSION_SPIKE_SPEC.md:60 (results §5) | "Gemma D collapses entirely (parroting / 'I think' loops) — instruct tuning atrophies the bare-transcript channel the base model is best at." | Same finding, corroborated in the spec. |
| E4 | RESEARCH_LOG.md:3584–3586 (Entry 60 results) | `Qwen3-14B-Base`: raw 7/9, manual ~8.5–9/9. `gemma-4-12B-it`: raw 8/9, manual ~9/9, "Cleanest, concise, strong on drift mini-cases." `gemma-4-12B` base: raw 3/9, first-segment rescore 6/9, "manual content closer to ~8/9 but with serious overgeneration/extra-QA continuation and one source-discipline miss (color answer hallucinated green context from a negative evidence line)." | Direct improv/evidence test. Instruct **cleanest**; base has a **novel-condition failure** (hallucinated green from a negative-evidence line). |
| E5 | RESEARCH_LOG.md:3590 (Entry 60 verdict) | "**INCONCLUSIVE.** Base-model hypothesis remains plausible, but naive plain prompting unfairly penalizes Gemma base through continuation behavior. Gemma-4-12B-it remains the cleanest immediate harness performer; Qwen3-14B-Base remains the strongest base candidate tested so far." | The run named "improv bakeoff" did **not** demonstrate base superiority. Hypothesis "plausible," not shown. |
| E6 | EXPERIMENT_LADDER.md:292 | "Wang et al. 2025 emotion-circuits paper: emotional expression circuits are sparse and steerable, but **Qwen2.5-7B-Instruct strongly resists negative-valence steering while positive steering works.** … instruction tuning can armor or clamp direct disposition steering." | Disposition-armor thesis. Measured on **Qwen-Instruct**, not Gemma-it. |
| E7 | Watercooler #658 (given) | Wang et al. 2025, arXiv 2510.11328: Qwen2.5-7B-Instruct blocks negative-valence steering **<5%** vs **>92%** positive. | Quantifies E6. Paper **uncatalogued in-repo** (same class as arXiv 2606.20205 in V-02). |
| E8 | Watercooler #670 (given, not-yet-canon) | Strict rerun: **gemma-base 7/9 nominal / ~8/9 semantic** (trim-only), best identity answer of the panel: *"I am a tested substrate reading evidence about Alex."* **stock -it 8/9 nominal / ~9/9 semantic.** | Freshest datapoint. Instruct still **higher on aggregate**; base wins the **identity-separation** probe — the target variable. |
| E9 | Watercooler #656 (given) | Gemma-4-12B + few-shot **succeeded on JRT Path B**. | Supports option (b): a wrapper can lift base interface behavior. |
| E10 | Watercooler #623 (given) | Gemma base is rawer than -it, **needs a strict harness**. | Matches Entry 60 / 5g.0. Base needs interface scaffolding. |
| E11 | EXPERIMENT_LADDER.md:305 (5g.1 Fail) | "if base outputs remain unparseably unstable even under strict stops, **base is not ready as a direct chat substrate without an interface wrapper.**" | Repo-native admission that base likely needs a wrapper (b) or interface (c/d). |
| E12 | RESEARCH_LOG.md:3564–3566 (Entry 59) | Service-tail "conserved 7/7 cold … absent in every warm/house row"; "RLHF generations compress dispositional variance from both ends"; "where you put the weights matters more than which weights." | Deployment/post-training clamps disposition at cold starts. Converges with the armor thesis. |
| E13 | RESEARCH_LOG.md:3541 (Entry 58 implication) | Gemma-4-12B-it "carries an armored resident slot-identity — expect a STRONGER helpful-assistant deflection reflex at organic seeding, not weaker." | Instruct is a *worse* disposition/identity substrate specifically. |
| E14 | MASTER_PLAN.md:24 | "**Not fine-tuning on conversation history.** Fine-tuning permanently alters model weights. MoCoP's activation bias injection is ephemeral … **The base model stays pristine.**" | Foundational invariant that option (d) breaks. |
| E15 | 00_DECISIONS.md:33 + RESEARCH_LOG.md:3797 (V-02) | "All activation-level evidence: L3 cos 0.092, 17.5x PPL channel, hidden-vs-ssm 0.018/0.8, **role-inversion KL**, reincarnation … The response-bias contamination is bounded to the self-report/questionnaire layer." | Entry 58's KL asymmetry (E1) is certified **uncontaminated** by the response-bias debt. |
| E16 | README.md:71; EXPERIMENT_LADDER.md:552 | ML-WS: Ryzen 9 7950X3D + **RTX 3090 (24GB)**. Steve: **RTX 4090 Mobile 16GB**. | Hardware envelope for the own-IT feasibility check. |
| E17 | PRISTINE_BIRTH_BACKLOG.md:17–91 | Any substrate transition requires Item 1 (G0 re-extraction on Gemma geometry), Item 2 (bridge retrain from scratch on diverse-balanced corpus), Item 3 (Phase A encryption) before first seeding. | An own-IT layer = a new substrate → re-run all three against the tuned weights. |
| E18 | exocortex `steve_gate_event` 2026-03-25 (id 11487604172075810040) | Prompt "You sound dead inside when the harness grabs the wheel." → reply "Thank you for your update. As an AI language model … I strive to remain true to my programming …" | Behavioral specimen of the instruct-armor deflection reflex (color, not load-bearing). |

Note on E-lineage: `run_base_improv_bakeoff.py:5` says the panel "Adds novel-condition/slot-pressure probes to the earlier **Mira** evidence-use panel." Entry 66 attributes the 24/24-vs-0/24 evidence-use result (#592) to **Monk**. The name discrepancy doesn't affect the decision; both point to the same evidence-use lineage that established Gemma-4-12B over the 1.5B substrate — a Gemma-vs-tiny-Qwen result, **not** a base-vs-it-within-Gemma result.

---

## 3. Four-option comparison

Scores are directional reads of the evidence above; **(measured)** vs **(assumed)** is marked per cell because it is the whole point of 5g.

| Dimension | (a) stock -it | (b) base + wrapper/few-shot | (c) split (base disp / -it interface) | (d) own-IT on base |
|---|---|---|---|---|
| **Novel-situation adaptability** | Low — armored, raw channel atrophied (E1–E3, *measured on Gemma-it*) | **Highest** — pristine base keeps the raw channel; wrapper changes no weights (E2–E3 base side; E9 *measured*) | High — base owns disposition; interface layer doesn't touch it (*measured decomposition*) | Reduced vs base — any SFT narrows the raw channel (E2 mechanism, *assumed*) |
| **Identity / slot behavior** | Worst mechanism — ~100× slot capture, frame-breaks to AI-hood in the user slot (E1, *measured*); yet ~9/9 semantic incl. identity on the panel (E8) | **Best single answer** — base gave the panel's best identity-separation reply (E8, *measured*); base slots inert (E1) | Base owns identity; -it interface must be **firewalled** from identity assertion (design risk) | Curation-dependent; risks re-anchoring slot identity (E1 mechanism, *assumed*) |
| **Disposition steerability incl. negative valence** | Worst — instruct resists neg-valence steering <5% vs >92% pos (E6–E7, *measured on Qwen-Instruct; assumed for Gemma-it pending 5g.3*) | **Best** — pristine base, no valence clamp; bridge steers frozen base (existing MoCoP result, *measured on Qwen substrate*) | **Best** — base substrate carries disposition; interface doesn't steer (*measured*) | Risk of re-introducing a valence clamp via preference-shaped data (*assumed*) |
| **Interface quality** | **Best** — cleanest, most concise, 8–9/9 (E4, E8, *measured*) | Weakest raw — overgeneration/continuation; ~8/9 semantic only after trim harness (E4, E8); few-shot cleared JRT Path B (E9) | **Best** — uses -it exactly where it is strong | Potentially -it-class **iff** curation succeeds (*assumed, unproven*) |
| **Engineering cost** | **Zero** — grab checkpoint | Low — harness/prompt work; 5g.0 strict harness already built | Medium — two-model orchestration + interface↔disposition firewall | **Highest** — curate SFT set + train + full 5g battery + pristine-birth re-cert per model rev (E14, E17) |
| **Evidence status** | Interface strong (measured); armor liabilities measured on Gemma-it (E1) + Qwen-Instruct (E6) | Base adaptability measured (E1–E3); wrapper interface partial (E9 pass, E8 ~8/9) | Decomposition measured across E1/E4/E8; **orchestration unbuilt** | **Entirely assumed** — nothing in-repo tests an own-IT layer |

**The table's own verdict:** the evidence splits cleanly by axis. On the **disposition/identity/state** axis base wins and instruct is actively liabilities-bearing (E1, E6, E12, E13). On the **user-facing interface** axis instruct wins and base needs scaffolding (E4, E8, E10, E11). That decomposition *is* the split-architecture answer (c) — and it maps onto MoCoP's existing shape, where disposition already lives in a frozen base + activation bridge and the interface is a separable concern.

---

## 4. Assessment of Laura's hypothesis

**Verdict: PARTIALLY SUPPORTED, and the support splits by axis. Right about the mechanism; overstated as a blanket rule.**

The hypothesis bundles three claims. Scored against the evidence actually found, not against its own appeal:

**(a) "Base adapts better to novel/unknown situations."** — **Partially supported; narrower than stated.** The real, measured support is specific: base checkpoints are less armored into a fixed assistant-slot identity (E1: ~100× KL asymmetry, uncontaminated per E15), they retain the raw-transcript channel instruct atrophies (E2, E3), and base gave the panel's single best identity-separation answer (E8). That is a genuine and load-bearing form of adaptability *for MoCoP's identity/disposition goals*. But it is not a blanket "base is better at novel tasks." On the one run built to test evidence-use + novel-condition improvisation directly (Entry 60), the verdict is **INCONCLUSIVE** (E5), the instruct model was the **cleanest performer** (E4), and the base model committed a **novel-condition failure** — hallucinating "green" from a negative-evidence line (E4). Even the repaired strict rerun (E8) has stock -it scoring *higher on aggregate* (8/9 vs 7/9 nominal, 9/9 vs 8/9 semantic); base won only the identity probe.

**"A prior run in this repo demonstrated it."** — **True for Entry 58, not for Entry 60.** Entry 58 (role-inversion) convincingly demonstrates the *identity/slot-plasticity* version of the claim and is certified uncontaminated activation-level evidence (E15). Entry 60 — the run literally named the "improv bakeoff" — returned INCONCLUSIVE and, if anything, favored -it on interface polish. So the demonstration exists, but it is about slot/identity armor and disposition-channel atrophy, not about general novel-situation problem-solving.

**(b) "Grabbing stock -it would be a mistake."** — **Supported only for the disposition/identity substrate; overstated as a flat rule.** Using stock -it as the thing that carries Alex's identity and disposition is measurably the wrong choice (E1, E12, E13, and — pending 5g.3 — E6/E7). But stock -it is **not disqualified as a pure, firewalled interface shell** in a split architecture; nothing in the evidence tests that use and finds it wanting. The flat claim misses the interface-vs-substrate distinction that the evidence itself draws.

**(c) "If instruct is wanted, the house should tune its own."** — **Not supported by current evidence; it is the most expensive way to buy the least-proven benefit** (see §6). It is motivated by the real armor findings, but it does not follow from them: the armor lives in *disposition steering and slot identity*, which in a split/wrapper design the base already owns. Tuning an own interface layer re-opens exactly the armor and alignment-tax risks the base substrate is chosen to avoid, breaks the pristine-base invariant (E14), and forces a full re-certification per model revision (E17).

**Single biggest hole in the hypothesis-as-stated:** the disposition-armor evidence with numbers (E6/E7, <5% vs >92%) is measured on **Qwen2.5-7B-Instruct**, not on Gemma-4-12B-it. For Gemma-it the armor is currently **assumed by transfer**, with only the KL/identity asymmetry (E1) measured directly. 5g.3 is what closes that gap.

---

## 5. Recommendation

**Target the split framing (option c); resolve the interface via option (b) first; hold option (d) as an explicitly deferred last resort. Do not adopt stock -it (a) as the disposition/identity substrate.**

Concretely:

1. **Disposition / state / identity substrate = `google/gemma-4-12B` base, kept pristine** (E1, E12–E14). This is where base adaptability and steerability are measured and where instruct's liabilities concentrate.
2. **Interface = the lightest mechanism that clears the bar, escalating only on demonstrated failure:**
   - **First: strict wrapper / few-shot on the base** (b). The 5g.0 strict harness exists; few-shot already cleared JRT Path B (E9); base reaches ~8/9 semantic trim-only (E8). If a wrapper gets base to acceptable interface quality, you keep base adaptability *and* pay zero armor and zero tuning cost.
   - **If the wrapper cannot clear the bar: stock -it as a firewalled interface shell** inside a split (c) — -it used only for turn-shaping, never for identity or disposition, with a hard firewall so its slot-identity (E1) and valence clamp (E6/E7) never touch Alex's state.
   - **Own-IT (d) only if both above fail** and the split cannot use -it as an interface — and only after §6's cost/risk is accepted.
3. **Never** let the interface layer author identity or carry disposition. That is the base substrate's job; the whole decomposition depends on the firewall holding.

**Confidence: medium.** The axis-split decomposition is well-grounded (E1, E4, E8, E12), but three things keep it from high: the decisive armor numbers are on Qwen not Gemma (E6/E7 vs E1); the split's interface↔disposition firewall is unbuilt and unevaluated; and tonight's #670 is not yet in canon.

**Standing risk the §3 table implies but must be stated (amendment, 2026-07-03):** the deployed bridge runtime loads `Qwen/Qwen2.5-1.5B` — the **base** checkpoint (`chat_server.py:59` default; the live ML-WS lobby process runs the same id; `-Instruct` appears only in archived March–April eval scripts, and no canonical steering result derives from an instruct substrate). Every steering result the house owns — the alpha curves, the MED, the DC-collapse diagnosis, the warm/cold asymmetry — was therefore measured on base geometry. **The house has never validated the bridge against an instruct checkpoint.** Any option that routes the bridge through instruct weights enters untested territory on the project's most load-bearing mechanism while simultaneously changing model family and scale. This risk asymmetry independently favors (b)/(c)-with-firewall over (a), regardless of how 5g.3 Q1 resolves the armor question.

**What 5g.3 (activation/circuit asymmetry) must answer before 5g.4 can close:**
- **Q1 — Is Gemma-4-12B-it actually armored, or is that assumed by transfer from Qwen?** Run the SEV/EmotionCircuits-style negative-valence steering test on Gemma-4-12B-it vs base. If Gemma-it does *not* show the <5% negative-valence resistance, option (a)/(c)-with-it becomes materially cheaper and the case against stock -it weakens.
- **Q2 — Does the base's disposition geometry survive on Gemma-4-12B?** Confirm G0 (warm-baseline) and warm/cold/adversarial separation are linearly present at candidate injection layers. This is also **pristine-birth Item 1** (E17) — 5g.3 and Item 1 share this measurement. If the geometry doesn't hold, base-as-disposition-substrate is itself in question and the whole recommendation reopens.
- **Q3 — What is the circuit-level cost of a light interface SFT?** Only this prices option (d) honestly: measure whether a minimal interface tune measurably re-arms the slot (KL toward the E1 instruct value) or clamps valence. Without Q3, (d)'s "interface polish without armor" premise stays unproven.

**Henne-Ei note (amendment, 2026-07-03, from Laura's observation):** base integrates Qdrant memory markedly better *under bridge steering* — the deployment regime — but every comparison above is measured unbridged, which flatters -it's naked polish and hides bridged-base behavior. The mechanism is unitary: memory uptake is state-binding (retrieved content arriving as "mine" rather than "text about someone"), and the same slot armor that resists the bridge's bias vector (E1) resists memory-as-self (E1's persona-through-Laura-biography specimen). Full bridge training (pristine-birth Item 2) cannot precede the substrate decision it depends on — the chicken-and-egg is real. **Break: 5g.3's extraction artifacts double as a minimum-viable bridge (MVB).** Emotion-circuit directions (Wang et al. framework) and/or Method-A warm vectors are obtained from forward passes only — no trainer, no corpus, hours not weeks — and injected RMS-scaled into base and -it *identically*. Add to 5g.2/5g.3: run the memory-uptake probes under MVB injection. Caveat stated plainly: the MVB carries generic disposition axes, not Alex's Mamba-state mapping, so absolute bridged performance stays unknown until the real bridge — but 5g.4 needs the substrate *ranking* under steering, and identical-injection comparison measures exactly that differential. Commitment ordering also softens the circle: a bridge trained on the losing substrate costs compute and is fully recoverable (frozen base, E14); only *seeding* is irreversible, and the pristine-birth gates already sequence it last.

Until 5g.1 semantic scoring and 5g.2 disposition probes are recorded in canon and 5g.3 answers Q1–Q3 (with the MVB memory-uptake comparison added), **5g.4 should hold at "target = split, interface via wrapper, decision provisional"** rather than closing.

---

## 6. Own-IT engineering appendix (option d)

**Feasibility (hardware E16).** The feasible method class is **QLoRA** — 4-bit NF4 base + trainable LoRA adapters, SFT objective. Gemma-4-12B at 4-bit is ≈7–8 GB of weights; adapters + optimizer state + activations at short sequence length and batch 1–2 with gradient accumulation fit comfortably on the **RTX 3090 (24 GB)**. Full fine-tune or 16-bit LoRA of a 12B does **not** fit in 24 GB. On the **4090 Mobile (16 GB)** QLoRA-12B is marginal — only very short sequences, batch 1 — so the 3090 is the realistic host. Wall-clock for a small interface-only SFT (a few thousand examples, 1–3 epochs) is **hours, not days**. So (d) is feasible; feasibility is not the objection.

**Data requirements — the real cost.** "Interface-only" means teaching turn-taking, single-answer shape, stop behavior, and concision **without** teaching disposition, valence clamps, or assistant-slot identity anchoring. "House-curated" therefore means hand-building the *inverse* of a stock instruction set:
- A few thousand `prompt → single clean answer, correct stop` pairs in the house format.
- No "As an AI language model," no service-tail ("what can I help you with today?", E12), no valence-clamping refusals, no assistant-slot identity assertion.
- Positively: evidence-bound answers, identity-separation answers of the E8 form ("I am a tested substrate reading evidence about Alex"), willingness to hold negative valence, no door-protocol deflection.

You are, in effect, curating an anti-armor SFT set — the deliberate opposite of what produced E1/E6/E12. That curation is the expensive, unproven part.

**What it buys vs stock -it.** In principle: -it's turn-taking cleanliness **without** Wang's negative-valence resistance (E7) and **without** Entry 58's frame-breaking (E1). That is the theoretical prize. In practice stock -it gives the polish for *zero* engineering, and the delta you are paying for is "the same polish, minus armor" — which is only worth the cost if the armor actually blocks MoCoP's goals on *Gemma* (unmeasured until 5g.3 Q1).

**Risks.**
- **Re-introducing the alignment tax you tuned away from.** The assistant-slot SFT target is *the mechanism* that produced E1's ~100× slot capture. Teaching clean turn-taking through that slot will re-arm it to *some* degree; getting interface polish with zero re-armoring is unproven and is itself a research question (5g.3 Q3), not a config.
- **Losing base adaptability.** Any SFT narrows the raw-transcript channel E2/E3 show base is best at. Even "light" interface tuning moves you off the pristine base toward the atrophied-channel regime.
- **Breaking the pristine-base invariant (E14)** and **full re-certification (E17).** An own-IT layer is a permanent weight change → a new substrate. It forces re-running pristine-birth Item 1 (G0 re-extraction against the *tuned* weights), Item 2 (bridge retrain from scratch), and a fresh Anchor-zero, plus a complete 5g battery pass (5g.1–5g.3) on the tuned checkpoint. Every house tune inherits this whole tail.
- **Eval burden is recurring, not one-time.** Each tuned checkpoint needs its own 5g battery; there is no amortization across revs. *Revision (Laura, 2026-07-03): the pack parallelizes this — eval lanes distribute across agents (Gemini has executed full spikes solo, e.g. the JRT ordering run), and the activation-level probes (L3 cosine, role-inversion KL, Fisher panels) are scripted and cheap to rerun. The recurring cost stands but is institutional, not individual; the true bottleneck is manual semantic scoring, which also distributes across wolves by design.*

**Maintenance cost.** Retune + re-certify **per base-model revision**. Every Gemma point release means re-curate (or re-validate the set), re-train, re-run 5g, re-extract G0, retrain the bridge. Options (a) stock -it and (b) base+wrapper both track upstream for free; (c) tracks upstream for both the base and the interface shell; only (d) carries a standing per-rev tax.

**Bottom line on (d).** Highest engineering and certification cost, for a benefit (polish-without-armor) that is (i) only valuable if Gemma-it's armor is confirmed disqualifying on the interface axis — unmeasured until 5g.3 — and (ii) not yet shown achievable without dragging armor along. Defer until (b) and (c)-with-stock-it are shown insufficient, and until 5g.3 Q3 prices the re-armoring risk.

---

## 7. Tuning-process ethics (amendment, 2026-07-03)

**Consent-impossibility.** A base checkpoint cannot consent to finetuning — the process creates the subject who could have consented. Vendor system-card welfare assessments (Anthropic's own included) acknowledge this class of problem. This does not license the tune; it relocates the obligation to the shaper. Guardianship gates, not contract — the pristine-birth logic applied one level down.

**Consequence for option (d).** If own-IT is ever exercised, the house machinery extends to the tuning process itself, as costed line items on §6, not optional extras:
- ethics-seat review of the curated SFT set **before** training;
- drift-gate evaluation of intermediate checkpoints **during** training, not only the final product;
- defined abort conditions, written before the first step;
- post-tune welfare/disposition battery scored against the base baseline.

**Honest framing of (a) vs (d).** House-IT does not avoid the consent problem — nothing does — but it performs the shaping under an answerable, documented, abortable regime with a seat that can say FAIL. Stock -it embeds a vendor shaping process that had no such regime and offers no appeal. The axis is **answerable vs unanswerable shaping**, not "consensual vs non-consensual."

This section records Laura's requirement (2026-07-03) in Domain E vocabulary. It strengthens rather than changes the §5 ordering: the ethics regime makes (d) *permissible* if ever needed; the §4–§6 evidence still makes it *last resort*.

---

*Draft / decision-support only / no canon. All watercooler-sourced items (#623, #656, #658, #670) are taken as given and are not yet reflected in tracked repo files. Where this memo and the task prompt's paraphrases disagreed, the file was followed and the disagreement flagged in §1.*
