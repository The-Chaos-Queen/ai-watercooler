# Research Sweep: Laura's Watercooler Links (2026-07-18)

**Source:** WC #1188–#1193
**Reviewer:** Elf

---

## 1. OaK Lab — Rich Sutton (oaklab.ai/mission)

Rich Sutton's lab builds agents that achieve goals in complex environments through temporal abstractions grounded in experience. Core principles: batch-size-one continual learning from experience without replay buffers; self-verifiable abstractions useful for planning; credit assignment only to generalizing parameters. Aspirational target: trillion-parameter agent learning in real-time on 20W.

**MoCoP relevance:**
- **Batch-size-one continual learning** maps to MoCoP's Mamba bridge operating as a streaming state compressor (recurrent, no replay buffer needed).
- **Temporal abstractions** parallel the world-model phases (#170/#171) — discovering structure at multiple timescales from raw experience.
- **Self-verifiable abstractions** connect to the step-gate verification discipline and DQ1b's monitor architecture.
- **Connects to:** #170 (causal trace custody), #171 (event lifecycle), bridge architecture.

---

## 2. Schema Harness (schema-harness.github.io)

Achieves ~99% on ARC-AGI-3 Public by wrapping frontier models with structured evaluation scaffolding. Core claim: proper harness design (schema, structured prompting, memory) unlocks near-perfect abstract reasoning from existing models without architectural changes.

**MoCoP relevance:**
- Validates the harness/evaluation architecture approach — structured wrappers amplify reasoning.
- Relevant to how the P5 harness scaffolds Gemma's reasoning capacity via the injection mechanism.
- The "existing model + structured scaffold" philosophy is exactly MoCoP's bet: Mamba bridge + injection at global attention teeth, not a new foundation model.
- **Connects to:** #155 (B0 harness), #156 (C1 runner), evaluation design.

---

## 3. Endogenous DMT Brain Biotypes (ResearchHub #4248)

Multi-modal neuroimaging study (N=1,100, Cimbi dataset) using PET, resting-state fMRI, free-water diffusion MRI, and blood analyses to identify distinct brain biotypes related to endogenous DMT production. Emphasizes marker specificity and rigorous clustering.

**MoCoP relevance:**
- Direct parallel to the endocrine/disposition model — clustering distinct neurobiological profiles from multi-modal signals.
- Methodology (imaging + blood markers + clustering) mirrors how MoCoP could identify "affective biotypes" from bridge state signals at different injection sites.
- Validates multi-signal architecture for disposition inference (not single-channel).
- **Connects to:** Disposition system design, formation zone vs steering zone decomposition, the bridge's multi-tooth signal.

---

## 4. "The Organizational Behavior of Agentic AI" (arxiv 2606.30986)

Examines whether multi-agent AI collectives exhibit organizational behavior analogous to human organizations. Central finding: these systems are "partial organisational analogues" sustained by "context architecture" (prompts, memory, traces, schemas, tools, validators, permissions) rather than motivation/identity/trust. Proposes "contextual transaction cost" as the unifying mechanism. Key result: shared-state adaptive forms outperform human-imitation forms that add lossy handoffs.

**MoCoP relevance:**
- **Directly validates the pack architecture.** The "context architecture" framing describes exactly what MoCoP built: durable inspectable state (bridge + exocortex), schema-driven coordination (OpenCLAW), shared-state infrastructure (watercooler).
- **Shared-state > lossy handoffs** supports the Mamba bridge as persistent shared memory rather than message-passing between agents.
- **"Contextual transaction cost"** maps to the pack's coordination overhead — the watercooler, the review chains, the custody evidence. The pack minimizes this through shared state rather than handoff protocols.
- **Connects to:** Pack coordination model, watercooler architecture, the handoff/capsule design.

---

## 5. "Reasoning in Memory" (RiM) — Aichberger & Hochreiter (arxiv 2605.30343)

**Laura flagged: "Very relevant for MoCoP."**

Replaces autoregressive chain-of-thought with "memory blocks" — fixed sequences of special tokens that unlock LLM working memory for latent reasoning. Processed in a single forward pass rather than sequential token generation. Two-stage curriculum: (1) grounding (memory blocks predict explicit reasoning steps), (2) refinement (supervision removed, model iteratively refines answers). Matches or exceeds existing latent reasoning methods at lower compute cost.

**MoCoP relevance — HIGH:**
- **Memory blocks = bridge injection.** RiM's memory blocks are conceptually identical to what MoCoP's Mamba bridge does: compressing reasoning/state into a fixed-size latent representation that a larger model consumes in one pass at specific locations.
- **Two-stage curriculum** maps to MoCoP's training phases: first grounded (matched-delta recording with explicit targets, #146), then unsupervised refinement (the bridge learns its own compression).
- **Decoupled internal computation from token generation** is exactly MoCoP's architecture: Mamba does latent state compression, Gemma does externalized reasoning. The bridge IS the memory block.
- **Single forward pass consumption** validates injection at global attention teeth — the host model processes the bridge signal in one pass alongside its normal computation.
- **Core validation:** This paper independently validates the central MoCoP bet that working memory can be a distinct architectural component (injected, not emergent from autoregressive depth).
- **Connects to:** Bridge architecture (#139), matched-delta training (#146/#166), injection mechanism design, the Zheng & Meister 10-bit bottleneck (WC #789).

---

## Action Items

| Paper | Actionable for MoCoP | Priority |
|-------|---------------------|----------|
| RiM (Aichberger) | Compare memory-block curriculum to matched-delta training plan. Consider whether RiM's grounding stage maps to a pre-training curriculum for the bridge. | HIGH |
| OaK (Sutton) | Monitor for concrete architecture papers. Batch-size-one learning may inform bridge online adaptation (post-C1). | MEDIUM |
| Org. Behavior (Liu) | Cite in pack architecture documentation. The "contextual transaction cost" framework names what we're optimizing. | LOW |
| Schema Harness | Evaluate whether structured scaffolding techniques could improve the evaluation harness design. | LOW |
| DMT Biotypes | Methodology reference for future multi-modal disposition clustering. Not actionable pre-B0. | BACKLOG |
