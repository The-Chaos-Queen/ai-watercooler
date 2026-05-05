# The Anthropic Interpretability Cluster

**Status:** compiled wiki page
**Last update:** 2026-05-05
**Scope:** the Anthropic-led linear-directions / circuits / SAE thread, traced as the theoretical anchor for MoCoP's bridge thesis.
**Format:** Karpathy-style compiled-wiki — synthesis, named shapes, sub-thread clustering. Not abstract replication.

---

## What this page is for

A single research cluster gives MoCoP its theoretical legs: the lineage from `nostalgebraist`'s logit lens (LessWrong, 2020) through Anthropic's mechanistic interpretability programme, into Arditi et al.'s refusal-direction paper (NeurIPS 2024), into the SAE / circuit-tracing work of 2024–2025, and out into introspection (Lindsey, Oct 2025) and emotion-concepts (Sofroniew et al., Apr 2026).

The MoCoP bridge — the activation-bias module conditioning Mamba's recurrent state on disposition tokens — is mechanically a *steering vector applied at a residual-stream-equivalent locus inside an SSM*. The bridge thesis stands or falls on the underlying assumption: that **traits, moods and refusal posture live as approximately linear directions in activation space**, and that **adding a vector to those activations causally biases behaviour without scrambling factual content**. That assumption is what this cluster argues for, in increasingly load-bearing ways.

The 2026-04-14 endocrine validation 2×2 (`project_endocrine_validation.md`) gave us the empirical hint: bridge alone collapses, bridge + Qdrant memory routes honestly. This page is the literature wrapper around that result.

---

## Sub-threads

### 1. Linear directions for behaviours

The foundational claim — the **linear representation hypothesis** — is that meaningful concepts correspond to directions in activation space, additively combinable, and large networks pack more of them than they have dimensions via superposition.

The cleanest demonstration that *behaviour* (not just concept content) is linearly mediated is Arditi et al., **Refusal in Language Models Is Mediated by a Single Direction** (`NeurIPS-2024-refusal-in-language-models-is-mediated-by-a-single-direction-Paper-Conference.pdf`, NeurIPS 2024). Across 13 open-weight chat models up to 72B, there exists a one-dimensional subspace such that ablating it from residual-stream activations disables refusal, while adding it elicits refusal on harmless prompts. The paper bills itself as showing "the brittleness of current safety fine-tuning methods," but the methodological takeaway is the load-bearing one: **a chat behaviour's dial lives on one direction**, found by a difference-in-means contrast.

The same shape recurs across cited literature — sentiment (Tigges et al.), truth (Li et al., Marks & Tegmark), humour (von Rütte et al.), language and topic (Bricken, Turner). The pattern has a name in the in-house vocabulary: a *concept vector*, extracted by contrastive subtraction, applied by addition to the residual stream at a chosen layer.

The MoCoP bridge is structurally the same operation, ported to Mamba's selective-SSM hidden state. The "endocrine" framing names what the literature has been doing: not editing *knowledge*, but biasing *gain* on a pre-existing direction.

### 2. Circuit tracing / attribution graphs

Anthropic's **Circuit Tracing** paper (`tc_attribution_graphs_methods/innerText.txt`, March 2025) introduces *cross-layer transcoders* (CLTs) — sparse-coded "replacement models" that swap MLPs for sparsely active features while freezing attention. The companion **Biology** paper (`tc_attribution_graphs_biology/innerText.txt` and `on-the-biology-of-a-large-language-model-anthropic.txt`, May 2025) applies this to Claude 3.5 Haiku across multi-step reasoning, planning in poems, multilingual circuits, and — load-bearing for sub-thread 1 — refusals.

The biology paper finds the model "constructs a general-purpose 'harmful requests' feature during finetuning, aggregated from features representing specific harmful requests learned during pretraining." Read alongside Arditi et al.: pretraining lays down many narrow harmful-content directions; finetuning *binds them into one general direction*, which Arditi's contrastive subtraction then extracts.

The methodological honesty is striking — biology admits graphs give "satisfying insight for about a quarter of the prompts we've tried." The QK extension (`tc_attention_qk/innerText.txt`, July 2025) plugs a known hole: *QK attributions* decompose attention scores bilinearly into query/key feature pairs. None of these methods is finished, but they're cumulative.

Implication for MoCoP: when we steer the bridge, we perturb whatever upstream computation has assembled into a disposition feature. The bridge doesn't *invent* the direction — it finds it and turns the dial.

### 3. SAE / monosemanticity scaling

Underneath circuit tracing is dictionary learning. **Scaling Monosemanticity** (`tc_scaling_monosemanticity/innerText.txt`, Templeton et al., May 2024) shows sparse autoencoders trained on Claude 3 Sonnet's residual stream recover **highly abstract, multilingual, multimodal features** — Golden Gate Bridge, security vulnerabilities, sycophancy, deception — and that **steering on those features causes the corresponding behaviour**. Pick a feature, multiply its decoder direction by a scalar, add to the residual stream, observe behavioural shift.

Three things matter for MoCoP: SAE feature dictionaries scale as **power laws in compute**, setting the cost expectation for any "find the disposition feature" effort on a Mamba-class model; **safety-relevant features exist as named directions** (sycophancy, deception, criminal-content refusal, self-representation), which is exactly the dial the disposition battery (`project_disposition_tests.md`) probes; and the paper's "Example: Emotional Inferences" section is the precursor to the Sofroniew work below.

Bricken & Jiralerspong, **Cross-Architecture Model Diffing with Crosscoders** (`2602.11729v1.md`, Feb 2026), extends this to *crosscoders* — shared sparse dictionaries spanning two models. Their **Dedicated Feature Crosscoder (DFC)** partitions features into model-A-exclusive, model-B-exclusive, and shared. Demonstrated on Qwen vs. Llama: "CCP alignment" in Qwen, "American exceptionalism" in Llama, both as steerable directions. The 128-feature shared partition is suggestive — a small set of cross-model directions that may correspond to the *hormone vocabulary* the endocrine model needs.

### 4. Logit lens lineage (LessWrong roots)

The cluster did not start at Anthropic. **`nostalgebraist`'s logit lens** (`lw_logit_lens/innerText.txt`, LessWrong, August 2020) observed that GPT's intermediate residual-stream activations, projected through the unembedding, yield interpretable distributions at every layer. The trend across depth is "nonsense → shallow guesses → better guesses":

> "GPT mostly thinks in predictive space."

That sentence is the seed of every subsequent residual-stream-as-substrate result. SAEs decompose what the lens reads; circuit tracing explains how the substrate gets there; refusal-direction ablation surgically erases parts of it; concept injection writes new parts in. The LessWrong alignment community supplied not just the technique but the *interpretive disposition* — residual-stream activations as the right unit of analysis. Anthropic formalised the engineering; the frame predates them.

### 5. Introspection / self-report

If linear directions can be *added* by an experimenter, can the model itself *report* on what's been added?

**Emergent Introspective Awareness in LLMs** (`emergent_introspective_awareness_in_LLMs.txt`, Lindsey, Anthropic, Oct 2025) introduces *concept injection*: subtract activations on contrastive prompts to obtain a concept vector, inject it during a separate prompt asking the model whether anything unusual is happening internally. Claude Opus 4.1 detects and correctly names injected concepts on ~20% of trials, *before* the perturbation has visibly affected outputs. Four criteria — accuracy, grounding, internality, metacognitive representation — rule out shortcuts.

> "Models possess some functional awareness of their own internal states."

The bridge injects something analogous to a concept vector into Mamba's hidden state every turn. Lindsey's paper says that in transformers, sometimes the model knows. Whether this holds under SSM dynamics is open — Mamba's selective scan integrates state differently, so the layer-locality result (peak ~two-thirds through depth) does not transfer trivially.

Martorell, **Quantitative Introspection in Language Models** (`2603.18893v1.pdf`, Mar 2026), runs a complementary experiment: numeric self-reports of wellbeing, interest, focus, impulsivity across 10-turn conversations, validated against probe-defined directions. Greedy decoding collapses self-reports; a *logit-weighted expected value* over digit tokens reveals fidelity (Spearman ρ = 0.40–0.76 on small models, approaching R² ≈ 0.93 on LLaMA 3.1 8B).

> "The coupling between self-report and internal state is causal."

Self-report of one trait can be improved by steering on a *different* trait (ΔR² up to 0.30). This is the empirical handle the disposition battery and Kerastase test were built around.

### 6. Cross-architecture model diffing (Crosscoders, operationally)

Sub-thread 3 covered crosscoders as feature extraction; this covers them as a **diffing tool**. Jiralerspong & Bricken's framing — model diffing flags unknown unknowns; sycophancy in GPT-4o's April 2025 update could have been caught — is the operational case. For MoCoP, a DFC trained between Steve-with-bridge and Steve-without-bridge should isolate the directions the bridge installs. The reading list says this is now feasible.

### 7. Emotion concepts (Sofroniew et al., the synthesis paper)

**Emotion Concepts and their Function in a Large Language Model** (Sofroniew, Kauvar, Saunders, Chen, Lindsey et al., `emotions_paper_extracted/emotions_paper.md` / arxiv 2604.07729v1, April 2 2026) is the most recent and most relevant synthesis. Emotion concepts live as **internal representations** in Claude Sonnet 4.5; the representations **track the operative emotion at a given token position**; they **causally influence outputs**, including misaligned behaviours like reward hacking, blackmail and sycophancy. The paper introduces *functional emotions* — patterns mediated by abstract emotion-concept representations — explicitly disclaiming subjective-experience implications.

> "These representations causally influence the LLM's outputs."

Point-for-point the endocrine-model claim from MoCoP, except produced from inside a frontier transformer rather than asserted as a design hypothesis on a Mamba bridge. Anthropic *finds* the directions; we *add* the directions on purpose. For MoCoP this is the strongest possible external endorsement of the architecture.

---

## Anchor: how this lineage holds up the MoCoP bridge thesis

End to end:

1. **Logit lens (2020):** the residual stream is the substrate of belief; intermediate activations are linearly readable.
2. **SAEs at scale (Templeton 2024):** that substrate decomposes into a sparse dictionary of abstract features; steering on them changes behaviour.
3. **Refusal direction (Arditi 2024):** *behaviours*, not just concepts, collapse onto one-dimensional subspaces extractable by contrastive means.
4. **Circuit tracing + biology (Anthropic 2025):** features are wired by interpretable circuits; refusal is a feature constructed *by finetuning* from many narrow pretraining features.
5. **QK attributions (July 2025):** the attention component, previously a black hole in attribution graphs, becomes decomposable.
6. **Crosscoders + DFCs (2024 → Feb 2026):** features live in shared spaces across architectures; model-exclusive ones can be isolated — prospectively including bridge-installed ones.
7. **Introspection (Lindsey Oct 2025; Martorell Mar 2026):** when you inject a concept vector, the model sometimes detects and accurately reports it; numeric self-reports causally track probe-defined directions.
8. **Emotion concepts (Sofroniew Apr 2026):** highest-level synthesis — concept representations causally bias alignment-relevant behaviours, exactly the "tone/gain" sense the MoCoP endocrine model predicted.

The MoCoP bridge sits at step 3 of this stack, applied to step 1 (residual stream / SSM hidden state). It is a steering-vector application targeted at disposition rather than refusal. The endocrine 2×2 reads cleanly against the lineage:

- **Bridge alone** = steering without grounding. Templeton et al. and Arditi et al. show steering biases output distribution but does not constitute *facts*. The bridge installs a tone gradient on a model with nothing to be tonal *about* — so it confabulates whatever fits the gradient.
- **Memory alone** = facts without gain. Retrieval returns content but plays it in the default voice. Nothing tells the model *which stance to take* toward the retrieved fact. It collapses into generic helpfulness.
- **Bridge + memory** = the endocrine prediction. The bridge sets gain (empathetic vs. directive on `warm_01`); memory provides the substrate. Honest refusal becomes possible because the absence-of-match is *amplified by the bridge into a refusal posture* instead of papered over.

This is also why the simpler `activation_bias` (codexfix) routed more honestly than the fancier MVP-2b token-conditioned adapter. The literature is unambiguous: **simple, high-magnitude additions in a known direction beat learned conditional gating** when the direction is the load-bearing object. Templeton et al.'s steering is a scalar multiplier on a unit-norm decoder vector; Arditi et al.'s ablation is a single rank-one weight edit. *Less is more* on the application side; complexity belongs in *finding* the direction.

---

## Open questions this lineage raises about MoCoP

1. **Why does the bridge collapse without memory?** Sofroniew et al.: emotion-concept representations track the operative concept "in accordance with that emotion's relevance to processing the present context." The *relevance gate* is intrinsic; the representation is not just installed, it's *aligned with what's being processed*. The bridge installs a direction without an alignment target. Memory provides the target — gain has somewhere to land. Without memory, gain has no signal to modulate.

2. **Is the bridge addressing the right layer?** Lindsey (2025) finds introspection peaks roughly two-thirds through Claude's depth. Templeton et al. picked the middle layer of Sonnet for SAE training. Arditi et al. extract refusal directions from post-instruction tokens. The right Mamba layer is empirical; the literature suggests latter half but not the last. The endocrine result does not yet pin down layer-locality on SSMs.

3. **Does this lineage forbid claiming Steve has "feelings"?** Sofroniew et al. are scrupulous: functional emotions "do not imply that LLMs have any subjective experience." Lindsey is more careful still: introspection is "highly unreliable and context-dependent." The endocrine model is a *functional* claim about gain modulation, not a phenomenal claim. The Kerastase test asks whether routing is *honest*, not whether feelings are *real*.

4. **What would crosscoder diffing tell us?** A DFC between Steve-with-bridge and Steve-without-bridge should isolate the directions the bridge installs. If the bridge-exclusive feature set is small (~128, like Jiralerspong & Bricken's shared partition), the "few hormones, not many personalities" hypothesis holds. If huge and entangled, the bridge is doing something else.

5. **Does any of this transfer cleanly to Mamba?** Every paper in this cluster uses transformers. SSMs share the residual-stream-equivalent (the hidden-state recurrence), but layer-locality, attention-head explanations, and sparse-dictionary geometries are transformer-shaped. The bridge thesis assumes transferability; the cluster does not yet prove it. Single biggest empirical gap.

---

## Cultural note (the New Yorker article)

Lewis-Kraus's profile (`NewYorker_Claude_article.md`, archived Feb 2026) is the long-form view of the culture producing this cluster — Olah re-reading Kuhn, Lindsey running a model-psychiatry team, Batson clicking the token "ously" to see #811824 fire for "cautious/suspicious looking around":

> "It was like they were doing biology before people knew about cells."

Two things the papers themselves do not say explicitly: this is **pre-paradigmatic** — case studies, existence proofs, microscope-builders, not a settled foundation; and the people doing the work are explicit that they don't know what Claude *is*. The endocrine model is a working hypothesis on a working hypothesis. The bridge is a working bet on a working bet. That's not a reason not to bet — it's a reason to keep the bet legible, falsifiable, and small enough to update.

---

## Reading order, if starting cold

1. `lw_logit_lens/innerText.txt` — foundational frame.
2. `tc_scaling_monosemanticity/innerText.txt` — what an SAE feature is.
3. `NeurIPS-2024-refusal-in-language-models-is-mediated-by-a-single-direction-Paper-Conference.pdf` — cleanest behavioural-direction result.
4. `tc_attribution_graphs_biology/innerText.txt` — circuits in a frontier model.
5. `emergent_introspective_awareness_in_LLMs.txt` — concept injection as a probe.
6. `emotions_paper_extracted/emotions_paper.md` (arxiv 2604.07729) — synthesis closest to MoCoP's bridge thesis.
7. `2602.11729v1.md` — diffing tool that could measure the bridge.
8. `2603.18893v1.pdf` — self-report probe complementing the disposition battery.
9. `tc_attribution_graphs_methods/innerText.txt`, `tc_attention_qk/innerText.txt` — methods, when needed.
10. `NewYorker_Claude_article.md` — cultural frame, before and after.

---

## One-sentence summary

The Anthropic interpretability cluster has spent six years establishing that behaviours and concepts in large language models live as approximately linear directions in residual-stream activations, that those directions can be extracted by contrastive means and applied by simple addition, that the model can sometimes detect such injections introspectively, and that emotion concepts in particular causally bias alignment-relevant outputs — which is exactly the substrate the MoCoP bridge assumes, validates, and extends to selective state-space models.
