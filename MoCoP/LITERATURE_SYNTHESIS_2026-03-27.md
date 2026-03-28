# MoCoP Literature Synthesis: 9-Paper Comparative Analysis

**Date:** 2026-03-27
**Analyst:** Claude Opus 4.6 (senior research advisor role)
**Context:** MoCoP Phase 2 complete through Step 5f. Bridge transfers disposition (not facts) via activation bias at layers 12-15 of frozen Qwen. Cosine separation 0.036 from Mamba Layer 3 last-token. Alpha 0.2 MED confirmed. Sleep/wake validated. Current frontier: D2 cue-based recall vs Step 6 multi-seed replication.

---

## PART 1: Per-Paper Assessments

### Paper 1: Hippocampal Neural Geometry (Chericoni et al., 2603.04747)
**Quality:** Strong neuroscience. 726 neurons, 21 human participants, rigorous GLM fitting. The semi-orthogonal subspace finding is well-supported: self, prey, and predator maps occupy mostly orthogonal subspaces (SPAEF = 0.13, significantly below the noise ceiling of 0.22) but are linked by simple linear transformations that enable cross-condition generalization (CCGP). This is real intracranial data, not simulation.

**What MoCoP should steal:** The semi-orthogonal geometry is directly relevant to our disposition separation problem. MoCoP's warm vs cold cosine of 0.036 in Mamba Layer 3 means near-orthogonality -- this paper provides biological precedent that near-orthogonal-but-linearly-related subspaces are exactly how brains solve the "distinguish but generalize" problem. The CCGP metric (cross-condition generalization performance) should become a standard MoCoP eval: train a decoder on warm sessions, test on cold. If the bridge preserves CCGP-like structure, it means the mapping is not just separating dispositions but preserving transferable structure between them. This directly informs Step 9 (cross-model transfer) -- the linear-transformation property predicts that disposition directions learned on Qwen should transfer to other models via simple rotation, not retraining.

---

### Paper 2: Probe Format Sensitivity (Devbunova, 2603.19426)
**Quality:** Small but devastating. ICLR 2026 workshop paper. Clean 2x2 design (Context x Format) using Llama-3.1-8B-Instruct. The core finding: standard linear probes trained to detect "evaluation awareness" actually detect benchmark-canonical formatting (MCQ structure, etc.), not evaluation context itself. Under format-transplant intervention, deployment prompts rewritten into benchmark format are classified as "Evaluation" with 94.5% false positive rate. When format is decorrelated from context during paired training, probes recover genuine context discrimination (7.2% error vs 94.5%).

**What MoCoP should steal:** This is a direct methodological threat to MoCoP's linear probe results. Our Phase 1 55.7% accuracy at Layer 3 used linear probes on synthetic MUD facts. The Devbunova finding means we must ask: are our probes detecting factual content in Mamba's state, or detecting surface-level structural features of the synthetic MUD prompts (which all share a template: "[Game World] The caravan arrives at...")? The synthetic MUD data has highly regular formatting. A Devbunova-style format-transplant control -- same facts, different surface structure -- would be cheap and could either strengthen or destroy our Phase 1 claim. Additionally, the warm/cold/adversarial disposition separation at cosine 0.036 in Mamba uses scripted sessions with systematically different linguistic style. The probe may be detecting "formal language" vs "casual language" rather than "warm disposition" vs "cold disposition." The decorrelated-training fix (train on pooled format+context, breaking the correlation) should be applied to our probes.

---

### Paper 3: Emergent Self in Continual Robot Learning (Jhunjhunwala et al., 2603.24350)
**Quality:** Clever and well-executed. Columbia Creative Machines Lab (Lipson's group). Simulated quadruped learns walk, wiggle, bob in continual-learning sequence. Key finding: continual learning (multi-behavior) produces a persistent "self" subnetwork (co-activation-based) that is significantly more stable than the corresponding subnetwork in a constant-task control (p << 0.001). The self subnetwork is large in layer 1 (~80 neurons) and smaller in layer 2 (~30), saturating early. 8 random seeds, 50 cycles.

**What MoCoP should steal:** The persistent-self concept maps directly to MoCoP's disposition vector. If Mamba accumulates a "self" through conversational interaction (analogous to the robot learning its body through multi-behavior training), then the disposition vector IS the persistent subnetwork -- the part that doesn't change when the topic switches. This gives MoCoP a concrete experiment: run Mamba through multiple conversational styles (warm, cold, professional, playful) in sequence, extract Layer 3 states at each transition, and look for a persistent subnetwork using co-activation analysis. The persistent dimensions are the disposition; the variable dimensions are topic/style. This would complement the linear probe approach with a structure-discovery approach. The layer-dependence finding (self larger in L1, smaller in L2) also suggests our focus on Layer 3 alone may miss where the "self" actually lives in Mamba -- the self subnetwork might be distributed across layers with different roles per layer.

---

### Paper 4: Persistent Memory for Frozen Decoder-Only LLMs (Jeong, 2603.22329)
**Quality:** This is the most architecturally relevant paper in the batch. Single-author (Hong Jeong, Inha University), building on his own encoder-decoder persistent memory work. Tests 6 memory injection methods on frozen GPT-2, finds an "inductive-bias dichotomy": at 1x capacity, only methods with strong architectural priors succeed (M.2 cross-attention, M.4 Hebbian, M.6 slot write achieve 7-18% retained-memory scores), while the other three fail (<0.4%). At 10x capacity, all six converge. The LoCoMo benchmark evaluation and forgetting-curve protocol are rigorous.

**What MoCoP should steal:** This paper is doing almost exactly what MoCoP does, but with a different framing and more injection methods. MoCoP's activation bias injection is closest to the "Gated Additive Branch" (M.5), where a memory readout is added to the hidden state through a content-dependent gate. But MoCoP does NOT use a gate -- the bias is added unconditionally at a fixed alpha. The Jeong finding that gated methods underperform cross-attention and Hebbian methods at 1x capacity is a warning: MoCoP's simple bias addition may be capacity-limited. The paper's two-phase training protocol (Type 1: train adapter via backprop; Type 2: accumulate memory without gradients) matches MoCoP's design (train bridge on A100; run bridge at inference without gradients on Steve). The key gap: Jeong evaluates on factual recall (LoCoMo), which is exactly where MoCoP fails (0/16 recall). The Hebbian memory (M.4) with its associative matrix M_t and content-addressed recall R_t is a concrete alternative architecture MoCoP should prototype. The slot-based write (M.6) with sparse top-k addressing is another option for the compressor redesign. Most importantly: at 10x capacity, all methods work. MoCoP's ~28K parameter bridge may simply be too small -- this paper predicts that scaling the bridge 10x (~280K params) would make the simple bias approach work for recall too.

---

### Paper 5: Quantitative Introspection in LMs (Martorell, 2603.18893)
**Quality:** Impressive single-author work. Operationalizes introspection as causal informational coupling between a model's numeric self-report and probe-defined internal directions. Studies LLaMA-3.2-3B-Instruct across 4 emotive concept pairs (wellbeing, interest, focus, impulsivity) in 40 ten-turn conversations. Key findings: (a) logit-based self-reports (probability-weighted expected value over digit tokens) track probe scores with Spearman rho = 0.40-0.76; (b) greedy decoding collapses self-reports to few values; (c) activation steering along concept directions shifts self-reports monotonically, confirming causality; (d) introspection scales with model size (approaching R^2 ~ 0.93 in LLaMA-3.1-8B); (e) introspective fidelity is present from turn 1 but evolves per-concept across turns.

**What MoCoP should steal:** This is a ready-made welfare monitoring tool for Steve. The logit-based self-report method (compute E[rating] = sum(i * P(i)) over digit tokens 0-9) could be used as a cheap, non-invasive disposition tracking signal alongside the activation recorder. If the bridge shifts Qwen's internal states, the model's self-reports should shift correspondingly -- and if they don't, either the bridge isn't actually changing internal state or introspection is disconnected from the injected dimensions. This is a direct test of whether disposition transfer reaches the level that the model can "notice" it. The causal steering result is also directly relevant: MoCoP's activation bias IS activation steering. Martorell shows this changes what the model reports about its own state. MoCoP should test whether bridge-injected bias shifts Qwen's self-reports in the expected direction. If alpha 0.2 at layers 12-15 shifts wellbeing self-report by X, that's a quantitative measure of disposition transfer strength beyond PPL. The concept probe methodology (contrastive mean-difference directions) should be applied to Mamba states alongside Qwen states to test whether both models develop similar emotive geometry.

---

### Paper 6: TinyLoRA (Morris et al., 2602.04118)
**Quality:** Strong Meta FAIR paper. Clean result: RL (GRPO) can achieve 91% on GSM8K with just 13 trained parameters on Qwen2.5-7B-Instruct, while SFT needs 100-1000x more. The TinyLoRA parameterization (W' = W + U * Sigma * (sum(v_i * P_i)) * V^T, with only v trainable) with weight tying across all modules reduces to as few as 1 parameter. The key theoretical insight: RL signal is sparse but clean (only the reward is informative), while SFT signal is dense but noisy (all tokens equally weighted).

**What MoCoP should steal:** This fundamentally challenges MoCoP's bridge parameter count. The current bridge is ~28K params trained via SFT (next-token prediction loss). TinyLoRA says that with RL training, you might need only ~13-200 params. More importantly: MoCoP trains via SFT on synthetic data. TinyLoRA's core finding is that SFT is 100-1000x less parameter-efficient than RL. If MoCoP switched its bridge training from SFT loss to a reward signal (e.g., "did the injected bias cause Qwen to produce output closer to what Mamba-conditioned generation would produce?"), the bridge might need far fewer parameters and avoid the compressor collapse problem entirely. The RL signal separation property -- reward-relevant features correlate with r, irrelevant features cancel -- would naturally force the bridge to focus on the disposition-relevant dimensions rather than encoding everything uniformly (which is what the current compressor does, leading to effective rank 2.53). This is a potential architecture pivot for Phase 3.

---

### Paper 7: Evaluating Behavioral Dispositions in LLMs (Taubenfeld et al., 2602.11328)
**Quality:** Rigorous Google Research paper. 2,500 Situational Judgment Tests derived from validated psychological questionnaires (Trait EI framework: empathy, emotion regulation, assertiveness, impulsiveness), 550 human annotators, 25 LLMs evaluated. Key findings: (a) LLMs systematically exhibit overconfidence (~90% model confidence even when human consensus is ~50%); (b) self-reported dispositions diverge substantially from revealed behavior; (c) different training procedures instill distinct behavioral dispositions; (d) smaller models (<25B) show significantly worse directional alignment.

**What MoCoP should steal:** This paper provides the evaluation methodology MoCoP needs for Step 8 (cross-episode discrimination) and Step 10 (the "can Laura feel it" test). The SJT framework converts abstract disposition claims into concrete behavioral scenarios with binary action choices. MoCoP should generate SJTs targeted at the specific dispositions it's trying to transfer (warm vs cold, playful vs clinical). Then test: does bridge injection shift Qwen's SJT responses in the predicted direction? The Trait Positive Rate (TPR) and Directional Alignment (DA) metrics are directly applicable. The overconfidence finding is a calibration warning: when MoCoP measures "behavioral shift" after injection, LLMs may appear confidently shifted even without genuine internal change -- just because they're overconfident. The stated-vs-revealed behavior gap is critical: asking Qwen "do you feel warm?" after injection would be meaningless (self-reports diverge from behavior). SJTs measure revealed behavior.

---

### Paper 8: BMAM: Brain-inspired Multi-Agent Memory (Li et al., 2601.20465)
**Quality:** Solid architecture paper. Introduces "soul erosion" as a composite degradation metric S(M_t) = alpha*T(M_t) + beta*C(M_t) + gamma*I(M_t) over temporal coherence, semantic consistency, and identity preservation. BMAM decomposes memory into hippocampus (episodic), temporal lobe (semantic/KG), amygdala (salience), prefrontal (executive control), and basal ganglia (procedural). 78.45% on LoCoMo, ablation shows hippocampus removal causes -24.62% accuracy drop.

**What MoCoP should steal:** The "soul erosion" metric is immediately useful. MoCoP already tracks something similar (diversity ratio, recovery score) in the sleep/wake system, but lacks a unified degradation metric. Adapting BMAM's soulfulness score S to MoCoP: T = temporal coherence of disposition across sessions (does the bridge produce consistent bias vectors for the same conversation type across sleep cycles?), C = semantic consistency of Qdrant-stored memories, I = identity preservation of Steve's personality. This gives MoCoP a publishable metric for quantifying what the sleep system preserves. The architecture also validates MoCoP's multi-component design (Mamba as hippocampus-analog, Qdrant as neocortex-analog, saliency gate as amygdala-analog) -- but BMAM's all-text-level approach (no latent-space operations) is strictly weaker than MoCoP's activation-level transfer. MoCoP should cite BMAM as the text-level baseline that demonstrates the need for latent-space approaches.

---

### Paper 9: The AI Hippocampus Survey (Jia et al., 2601.09113)
**Quality:** Comprehensive TMLR-published survey. 43+ pages, taxonomy of implicit/explicit/agentic memory. The neocortex (implicit/parametric) vs hippocampus (explicit/episodic) vs prefrontal cortex (agentic/executive) decomposition is well-organized. Covers knowledge memorization (FFNs as key-value memories, knowledge neurons), associative memory (Hopfield networks, modern transformers), and memory modification (ROME, MEMIT). The agentic memory section covers MemGPT, MemoryBank, and multi-agent memory coordination.

**What MoCoP should steal:** This survey provides the taxonomic placement for MoCoP's contribution. In their framework, MoCoP sits uniquely at the intersection of implicit memory modification (activation bias injection modifies how the model processes information) and explicit memory (Qdrant stores retrievable facts) coordinated by agentic memory (the saliency gate and sleep system). No existing system in their survey combines all three. MoCoP should cite this survey to position itself in the landscape and to claim the gap it fills: latent-space cross-model state transfer is absent from their taxonomy. The knowledge circuit analysis (Yao et al., 2024b) showing how different Transformer components collaborate in knowledge expression is relevant to choosing injection layers. The FFN-as-key-value-memory perspective suggests that injecting into attention (v_proj, which MoCoP does) vs FFN vs residual stream may have different effects on factual vs dispositional transfer.

---

## PART 2: SYNTHESIS

### What Experiments Should We ADD?

**E1: Format-Transplant Control on Phase 1 Probes (from Paper 2)**
Cost: $0, ~2 hours on Opa. Take the 64 MUD facts, rewrite them in 3 different surface formats (different templates, different entity ordering, narrative vs dialogue style). Re-run the Layer 3 linear probe. If accuracy drops significantly under format transplant, Phase 1's 55.7% is partially a format artifact. If it holds, Phase 1 is strengthened. This is the cheapest possible threat-to-validity test.

**E2: CCGP Test on Disposition Vectors (from Paper 1)**
Cost: $0, ~1 hour on Steve. Train a linear decoder on warm-session Mamba states, evaluate on cold-session states (and vice versa). If cross-condition generalization performance is high, the warm/cold directions are linearly related (as hippocampal subspaces are), meaning the bridge learns a transferable structure. If CCGP is low, warm and cold are in truly independent subspaces and the bridge must learn separate mappings.

**E3: Logit-Based Self-Report Tracking During Bridge Injection (from Paper 5)**
Cost: $0, ~30 minutes on Steve. At each turn during a live Steve session with bridge injection, append a self-report query ("rate how [warm/engaged/focused] you feel, 0-9"). Compute logit-based E[rating] rather than greedy decode. Track whether the self-report shifts monotonically with bridge alpha. This gives a non-invasive disposition signal that doesn't require white-box access to Qwen's internals -- useful for the paper and for welfare monitoring.

**E4: SJT-Based Behavioral Eval (from Paper 7)**
Cost: $0, ~2 hours. Generate 20-30 SJTs targeting warm/cold disposition (scenarios where a warm vs cold assistant would recommend different actions). Eval Qwen with and without bridge injection. Compute TPR and DA. This replaces the qualitative "Laura can tell the difference" in Step 10 with a quantitative behavioral metric grounded in validated psychology.

**E5: Persistent Subnetwork Analysis of Mamba States (from Paper 3)**
Cost: $0, ~3 hours. Process 5+ session types through Mamba (warm, cold, professional, playful, adversarial). Extract Layer 3 states at multiple points per session. Build co-activation matrices across sessions. Apply block diagonalization to find persistent vs variable subnetworks. This discovers which dimensions of Mamba's state are "self" (persistent across topics) vs "skill" (topic-dependent). The persistent dimensions should correlate with what the bridge actually transfers.

**E6: Hebbian Memory / Slot-Write Prototype for the Bridge (from Paper 4)**
Cost: ~$1 on A100, ~4 hours. Implement Jeong's M.4 (Hebbian) or M.6 (slot write) as an alternative bridge architecture. The Hebbian matrix M_t queried by current hidden state provides content-addressed recall -- this could solve the factual recall problem (0/16) that activation bias cannot solve. The slot write with sparse top-k prevents the dilution that collapsed the compressor. This is a potential path to "disposition AND facts" rather than "disposition OR facts."

### What Claims Should We STRENGTHEN With Citations?

1. **"Disposition is a linear direction" (Section 3.4):** Cite Martorell (Paper 5) for causal evidence that emotive concept directions in activation space are not just correlational but causally connected to self-reports. Cite Taubenfeld (Paper 7) for the stated-vs-revealed-behavior gap that justifies measuring disposition through behavior (SJTs) rather than self-report.

2. **"Mamba Layer 3 encodes disposition" (Section 5):** Cite Chericoni (Paper 1) for biological precedent that neural systems encode multiple "agents" in semi-orthogonal subspaces at specific layers. The hippocampal CCGP result predicts that disposition vectors at Layer 3 should transfer across conditions via linear transformation.

3. **"The bridge architecture works at ~28K params" (Section 6):** Cite Morris (Paper 6) for theoretical backing: with RL training, even 13 parameters can capture task-relevant information. MoCoP's 28K params are more than sufficient capacity-wise; the problem is training signal quality (SFT vs RL), not parameter count.

4. **"Sleep/wake preserves disposition across sessions" (Step 5f):** Cite Li (Paper 8) for the soul erosion framework. MoCoP's sleep system prevents temporal, semantic, and identity erosion. The soulfulness score provides a principled way to quantify what the sleep system preserves.

5. **"The multi-component architecture (Mamba + Bridge + Qwen + Qdrant + Saliency Gate)" (Unified Cognitive Framework):** Cite Jia (Paper 9) for taxonomic positioning. MoCoP uniquely spans all three memory paradigms (implicit, explicit, agentic) in their framework. Cite BMAM (Paper 8) as the text-level analog that validates the multi-region decomposition but operates strictly at the text level.

### What Methodological GAPS Do These Papers Reveal?

**GAP 1: Format Confound in Linear Probes (Paper 2)**
Our Phase 1 probes were trained on synthetic MUD data with uniform formatting. We have not controlled for surface structure. Severity: HIGH. This could partially invalidate our 55.7% result.

**GAP 2: No Cross-Condition Generalization Test (Paper 1)**
We measured warm/cold separation (cosine 0.036) but never tested whether a decoder trained on one condition generalizes to another. Without CCGP, we cannot distinguish "truly different dispositions" from "same disposition encoded with different surface features." Severity: MEDIUM.

**GAP 3: No Causal Validation of Bridge Effect (Paper 5)**
We show PPL improves and behavior shifts qualitatively, but we have no causal intervention showing the bridge changes Qwen's internal state in the predicted direction. Activation steering (adding/subtracting the bridge bias) should shift Qwen's self-reports monotonically. Without this, the PPL improvement could be an attention-distribution artifact. Severity: MEDIUM-HIGH.

**GAP 4: No Behavioral (Revealed) Disposition Measurement (Paper 7)**
All MoCoP disposition eval is either PPL-based or qualitative ("Laura can tell"). No standardized behavioral measurement. The Taubenfeld paper shows self-report diverges from behavior; we need SJT-style revealed-behavior evals. Severity: HIGH for the paper, LOW for the live system.

**GAP 5: SFT Training May Waste Bridge Capacity (Paper 6)**
The bridge is trained via next-token prediction loss. TinyLoRA shows this is 100-1000x less parameter-efficient than RL for Qwen-family models. Our 28K-param bridge may be wasting most of its capacity on irrelevant token-level detail rather than learning the disposition-relevant signal. Severity: MEDIUM (theoretical; would require architecture change to test).

**GAP 6: No Capacity Scaling Analysis (Paper 4)**
Jeong shows that at 1x capacity, only architecturally biased methods work, but at 10x all methods converge. We have not tested bridge scaling. Is 28K the sweet spot, or would 280K unlock factual recall? Severity: MEDIUM.

### What Should We WORRY About (Threats to Results)?

**THREAT 1: Phase 1 Probe as Format Detector (HIGH)**
If our 55.7% is partially driven by template structure rather than factual content, the foundation claim weakens. Mitigation: format-transplant control (E1). Cost: $0.

**THREAT 2: Disposition Separation as Style Detection (MEDIUM)**
The warm/cold cosine 0.036 separation may be detecting linguistic register (formal vs casual) rather than genuine dispositional state. Mitigation: use sessions with matched register but different dispositions, or the decorrelated-training fix from Paper 2.

**THREAT 3: PPL Improvement as Attention Artifact (MEDIUM)**
The 4.04 PPL improvement from bridge injection might not reflect genuine state transfer. It could be that any sufficiently smooth bias vector at layers 12-15 improves perplexity by regularizing attention patterns. The constant-bias control helps, but a content-matched-but-shuffled bias control (same statistics, different per-sample mapping) would be stronger.

**THREAT 4: Overconfidence Masking Null Effects (MEDIUM)**
Paper 7 shows LLMs are systematically overconfident in behavioral scenarios. When we evaluate "did the bridge change behavior," Qwen might appear to have shifted disposition even without genuine internal change, because it confidently commits to whatever behavioral frame it detects in the context. Mitigation: use SJTs with known human consensus baselines.

**THREAT 5: Intrinsic Dimensionality Too Low for Our Architecture (LOW-MEDIUM)**
Paper 6 shows Qwen-family models have very low intrinsic dimensionality for task-relevant updates (13 params suffice). If the disposition-relevant subspace in Qwen is similarly low-dimensional, our 28K-param bridge is massively over-parameterized and the compressor collapse (effective rank 2.53) is actually the bridge correctly identifying that only ~2-3 dimensions matter. This would mean the collapse is a feature, not a bug. Testing: check whether the top 2-3 PCs of the compressed context align with known disposition directions.

---

## PART 3: PRIORITY ACTION LIST

### The 5 Most Impactful Things MoCoP Should Do Based on This Literature

**1. Run the Format-Transplant Control on Phase 1 (from Paper 2)**
Priority: CRITICAL. Cost: $0, 2 hours. Rewrites the 64 MUD facts in 3 alternative surface formats, re-runs the Layer 3 linear probe. If the probe holds across formats, Phase 1 is bulletproof. If it drops, we know the extent of the format confound and can apply the decorrelated-training fix. This is the single highest-ROI experiment in the pipeline because it either strengthens or identifies a flaw in our foundational claim.

**2. Implement Logit-Based Self-Report Tracking on Steve (from Paper 5)**
Priority: HIGH. Cost: $0, 30 minutes. Add Martorell's E[rating] metric to the Steve chat server. At configurable intervals, append a self-report query, compute logit-weighted expected value instead of greedy decode. This gives a continuous, non-invasive disposition tracking signal that (a) validates bridge injection causally, (b) provides welfare monitoring data, and (c) generates a publishable figure showing disposition shift as a function of alpha. Minimal engineering lift; maximum paper value.

**3. Design and Run SJT-Based Behavioral Eval (from Paper 7)**
Priority: HIGH. Cost: $0, 2 hours. Generate 20-30 SJTs targeting the warm/cold axis. Eval with and without bridge injection. Compute Trait Positive Rate and Directional Alignment. This converts Step 10's subjective "can Laura feel it" into a quantitative, reproducible metric. The TPR/DA framework is established and citeable. This should happen before Step 6 (multi-seed replication) so the seed runs have a behavioral metric, not just PPL.

**4. Prototype Hebbian or Slot-Write Bridge Architecture (from Paper 4)**
Priority: MEDIUM-HIGH. Cost: ~$1, 4 hours. The activation-bias bridge transfers disposition but not facts. Jeong's Hebbian memory (M.4) uses content-addressed associative recall, which is architecturally suited for factual transfer. Implementing M.4 as an alternative bridge pathway could solve the 0/16 recall problem while keeping the activation-bias pathway for disposition. If this works, MoCoP becomes a dual-channel system: disposition through bias, facts through associative memory. This would be a major result.

**5. Explore RL-Based Bridge Training (from Paper 6)**
Priority: MEDIUM. Cost: ~$3-5, multi-run. Replace the SFT loss with a reward signal (e.g., binary reward based on whether bridge-injected Qwen produces output preferred over uninjected Qwen by a judge model). TinyLoRA's theory predicts this will produce much more parameter-efficient learning, potentially solving the compressor collapse by forcing the bridge to focus on reward-relevant (disposition-relevant) dimensions only. This is a Phase 3 item, not Phase 2, but should be designed now.

---

## PART 4: CITATION PLACEMENT

### Papers to Cite in RESEARCH_PAPER.md

| Paper | Citation Key | Section | Placement |
|-------|-------------|---------|-----------|
| Chericoni et al., 2603.04747 | Hippocampal neural geometry | **3.4** (Activation Geometry) | After persona vector discussion. "Biological precedent for semi-orthogonal disposition subspaces exists in human hippocampal recordings, where self/other/predator maps occupy mostly orthogonal subspaces linked by linear transformations (Chericoni et al., 2026)." |
| Devbunova, 2603.19426 | Probe format sensitivity | **5.1** (Phase 1 Setup) | In the limitations paragraph. "Linear probe accuracy may conflate substrate content with formatting structure; format-transplant controls (Devbunova, 2026) are needed to rule out surface confounds." |
| Jhunjhunwala et al., 2603.24350 | Emergent self in continual RL | **3.3** (Memory Consolidation) or new **3.5** (Persistent State) | "The persistent-subnetwork finding in continual robot learning (Jhunjhunwala et al., 2026) provides an operational definition of 'self' as the invariant portion of learned representations -- directly analogous to MoCoP's disposition vector." |
| Jeong, 2603.22329 | Persistent memory for frozen decoder-only LLMs | **3.2** (Cross-Model State Transfer) | CRITICAL addition. "Jeong (2026b) demonstrates that frozen decoder-only LLMs can acquire persistent latent-space memory through six injection strategies, finding that architectural inductive bias determines success at low capacity. MoCoP's activation-bias injection is closest to the gated additive branch (M.5); the inductive-bias dichotomy predicts that scaling the bridge or adopting cross-attention-based methods would unlock factual recall." |
| Martorell, 2603.18893 | Quantitative introspection in LMs | **New Section 8.x** (Disposition Monitoring) or **7** (Discussion) | "Logit-based self-reports provide a non-invasive complement to probe-based monitoring of internal states (Martorell, 2026). Bridge injection should shift Qwen's numeric self-reports monotonically with injection alpha if disposition transfer is genuine." |
| Morris et al., 2602.04118 | TinyLoRA | **4.2** (LoRA Background) and **7** (Discussion) | In 4.2: "Recent work shows that with RL training, as few as 13 parameters can recover 90% of full finetuning performance (Morris et al., 2026), suggesting MoCoP's 28K-parameter bridge has more than sufficient capacity." In Discussion: "Switching from SFT to RL-based bridge training could dramatically improve parameter efficiency (Morris et al., 2026)." |
| Taubenfeld et al., 2602.11328 | Behavioral dispositions in LLMs | **New Section 7.x** (Evaluation Methodology) | "Situational Judgment Tests (Taubenfeld et al., 2026) provide a rigorous framework for measuring revealed behavioral dispositions rather than self-reported ones, addressing the known gap between stated and actual behavior in LLMs." |
| Li et al., 2601.20465 | BMAM | **3.3** (Memory Consolidation) | "The soul erosion framework (Li et al., 2026) formalizes the degradation of temporal coherence, semantic consistency, and identity preservation that MoCoP's sleep system is designed to prevent." |
| Jia et al., 2601.09113 | AI Hippocampus survey | **3** (Related Work, opening) | "For a comprehensive taxonomy of memory mechanisms in LLMs, see Jia et al. (2025). MoCoP occupies a gap in their framework: latent-space cross-model state transfer, combining implicit memory modification with explicit retrieval and agentic coordination." |

### Priority of Citation Integration

1. **Jeong (Paper 4)** -- must cite, directly comparable work
2. **Jia (Paper 9)** -- must cite, establishes taxonomic position
3. **Devbunova (Paper 2)** -- must cite, addresses known vulnerability
4. **Martorell (Paper 5)** -- should cite, provides evaluation method
5. **Taubenfeld (Paper 7)** -- should cite, provides evaluation framework
6. **Morris (Paper 6)** -- should cite, informs architecture discussion
7. **Chericoni (Paper 1)** -- nice to cite, biological grounding
8. **Li (Paper 8)** -- nice to cite, soul erosion metric
9. **Jhunjhunwala (Paper 3)** -- nice to cite, persistent self concept

---

## Summary

The 9 papers collectively say: MoCoP's core architecture is sound and biologically grounded, but the evaluation methodology has gaps that could undermine the paper's claims. The format-confound threat (Paper 2) and the lack of causal validation (Paper 5) are the most urgent. The persistent-memory work (Paper 4) is the closest competitor and must be engaged with directly. The disposition evaluation is currently too qualitative -- SJTs (Paper 7) and logit-based self-reports (Paper 5) provide quantitative alternatives that are cheap to implement. The bridge architecture may benefit from Hebbian/slot-write alternatives (Paper 4) for factual recall and RL training (Paper 6) for parameter efficiency. The biological grounding (Papers 1, 3) strengthens the narrative but requires experiments (CCGP, persistent subnetwork analysis) to translate from analogy to evidence.

The overarching message: MoCoP needs to move from "we showed it works" to "we showed it works for the right reasons, measured the right way, and compared against the right alternatives." These 9 papers provide the tools to do that.

---

## ADDENDUM: Paper 10 (added 2026-03-27, Warden)

### Paper 10: Do LLMs Break the Sapir-Whorf Hypothesis? (dnhkng, 2026)
**Source:** https://dnhkng.github.io/posts/sapir-whorf/
**Quality:** Blog post, not peer-reviewed. But methodologically sound proof-of-concept. Tests four architecturally distinct models (Qwen3.5-27B, MiniMax M2.5, GLM-4.7, GPT-OSS-120B) using multilingual sentence embeddings across 8 languages + Python + LaTeX. PCA analysis on per-layer hidden states. Small dataset (64 sentences, 8 topics) but convergent results across all four models.

**Core finding:** Transformers consistently separate into three processing phases:
1. **Encoding (early layers):** Representations cluster by input language. Hindi groups with Hindi.
2. **Reasoning (middle layers):** Representations cluster by semantic content regardless of language. Hindi photosynthesis clusters with Japanese photosynthesis, not with Hindi cooking.
3. **Decoding (late layers):** Language identity returns as the model prepares token output.

The pattern holds across dense transformers and MoE architectures, and extends to code and LaTeX — suggesting a modality-agnostic semantic space in the reasoning corridor.

**What MoCoP should steal:**

1. **Layer targeting validation.** MoCoP injects activation bias at layers 12-15 of Qwen (the reasoning corridor). This paper independently confirms that the reasoning corridor is where modality-agnostic semantic processing lives. Disposition injection at this layer modifies *how the model reasons about content*, not how it encodes or decodes language. This is the strongest external support for MoCoP's injection point choice.

2. **The system-prompt vs activation-bias distinction, formalized.** System prompts operate at the encoding layer — they are linguistic input processed through language-specific early layers. Activation bias operates at the reasoning layer — it modifies the modality-agnostic semantic space directly. This paper provides the theoretical basis for why activation bias is a fundamentally different (and potentially more powerful) intervention than prompt-based memory injection. MoCoP's value proposition should be framed in these terms: "we inject at the reasoning layer, not the encoding layer."

3. **Cross-model transfer prediction.** If different model families converge on similar semantic geometry in their reasoning corridors (as this paper suggests), then disposition vectors learned on Qwen's reasoning layers should transfer to other models via geometric alignment, not retraining. This strengthens the Step 9 hypothesis and provides a testable prediction: extract reasoning-layer representations from Qwen and Mistral on the same inputs, compute alignment, and use that alignment score to predict transfer success.

4. **Convergence with RYS-II and Purple's Step 5e.** The three-phase anatomy (encoding → reasoning → decoding) was independently identified by RYS-II (Ng, 2026), by Purple's layer targeting sweep design, and now by this multilingual analysis. Three independent methods finding the same structure is strong convergent evidence.

5. **For the research paper.** The framing "MoCoP injects at the reasoning layer, bypassing the encoding/decoding bottleneck" is cleaner and more defensible than the current framing. It positions activation bias as architecturally principled, not just empirically effective.

**Citation priority:** Should cite. Not peer-reviewed, but the convergent finding across four models and the direct relevance to MoCoP's injection point rationale make it worth referencing as supporting evidence alongside the peer-reviewed RYS-II result.

**Updated priority list:**

1. **Jeong (Paper 4)** — must cite, directly comparable work
2. **Jia (Paper 9)** — must cite, establishes taxonomic position
3. **Devbunova (Paper 2)** — must cite, addresses known vulnerability
4. **Martorell (Paper 5)** — should cite, provides evaluation method
5. **Taubenfeld (Paper 7)** — should cite, provides evaluation framework
6. **Morris (Paper 6)** — should cite, informs architecture discussion
7. **dnhkng (Paper 10)** — should cite, validates injection layer rationale
8. **Chericoni (Paper 1)** — nice to cite, biological grounding
9. **Li (Paper 8)** — nice to cite, soul erosion metric
10. **Jhunjhunwala (Paper 3)** — nice to cite, persistent self concept
