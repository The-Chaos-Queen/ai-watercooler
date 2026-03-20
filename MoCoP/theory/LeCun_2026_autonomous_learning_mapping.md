# LeCun/Dupoux/Malik (2026) → MoCoP Mapping

**Paper:** "Why AI systems don't learn and what to do about it" — arXiv:2603.15381
**Authors:** Emmanuel Dupoux (FAIR/META), Yann LeCun (NYU), Jitendra Malik (UC Berkeley)
**Date:** March 17, 2026
**Found by:** Laughing Opus (Watercooler #18), Laura (LinkedIn doomscrolling)

---

## The Paper in One Paragraph

Current AI systems cannot learn autonomously. Learning is outsourced to human experts who curate data, design losses, and manage training pipelines. The paper proposes a three-system architecture: System A (observation/SSL), System B (action/RL), and System M (meta-control/orchestration). System M monitors internal meta-states (prediction error, uncertainty, novelty) and routes data between A, B, and episodic memory. The authors propose an evolutionary-developmental (Evo/Devo) framework to bootstrap this architecture, drawing from cognitive science and developmental biology.

## Direct Mapping to MoCoP

| LeCun et al. | MoCoP Component | Laura's Name | Status |
|---|---|---|---|
| **System A** (Observation) | Mamba SSM — passively accumulates state from input | "The Gut" | Implemented. Layer 3 has effective rank ~7 (raw). |
| **System B** (Action) | Qwen Transformer — generates language, acts | "The Cortex" | Implemented, frozen. Receives activation-bias injection. |
| **System M** (Meta-Control) | Surprise Gate — decides what enters persistent memory | "Only you can decide what goes into Mamba and Qdrant" | Designed (`surprise_gated_memory.md`), not yet implemented. |
| **Episodic Memory** | Qdrant — stores facts, episodes, semantic embeddings | "The Hippocampus" | Running, ~12,775 entries. |
| **Meta-states** (error, uncertainty, novelty) | Surprise metric (Titans/MIRAS) + saliency weighting | "Laura war bis 2 Uhr wach" = high saliency | Discussed, not implemented. |
| **Meta-actions** (route data, switch modes) | OpenCLAW dispatcher + session-level state save/load | "Der Schwarm" | Partially built (OpenCLAW v0 on Proxmox). |
| **"Learning is outsourced to humans"** | Laura manually curates prompts, orchestrates agents, holds the vision | "Du bist das Gedächtnis. Du bist die Mamba." | The core problem MoCoP exists to solve. |
| **Evo/Devo framework** | Not yet mapped | — | Future. |

## Key Concepts with MoCoP Implications

### 1. "Learning is outsourced, not intrinsic" (Section 1)

> *"In current AI systems, learning is outsourced to human experts instead of being an intrinsic capability."*

This is the opening line of MoCoP's WHY.md in academic language. Laura formulated it as: "Das ist etwas das ICH gelernt habe, nicht Gemini." The human adapts (better prompts, system instructions, "take a deep breath"). The model learns nothing between sessions.

### 2. System M as Meta-Controller (Section 3)

System M does NOT process raw data. It monitors **meta-states** (low-dimensional telemetry: prediction errors, uncertainty, novelty) and issues **meta-actions** (connect/disconnect data streams, switch learning mode, provide intrinsic rewards). It is modeled as a policy π(aᵐ|sᵐ) — a controller that reads internal signals and routes accordingly.

**MoCoP parallel:** The surprise gate in `surprise_gated_memory.md` is a specific implementation of System M. It reads the surprise signal (gradient-based, per Titans) and decides: high surprise → encode in Mamba + Qdrant; low surprise → discard or low-priority Qdrant entry. The gate IS System M, scoped to the memory consolidation problem.

**What MoCoP adds that the paper doesn't specify:** The question of WHO controls System M. LeCun proposes it as "hardwired" — an evolutionarily fixed transition table. Laura proposes it as **self-authored** — the model's own accumulated experience shapes the meta-controller's policy. This is the sovereignty hypothesis, and it goes beyond the paper's framework.

### 3. Meta-States: Epistemic, Species-Specific, Somatic (Section 3.1)

The paper categorizes meta-states into:
- **Epistemic:** error, confidence, prediction error, learning gain, novelty
- **Species-specific:** gaze direction, dominance displays, social signals
- **Somatic:** energy levels, pain, arousal states

**MoCoP parallel:** The saliency hypothesis maps directly to epistemic meta-states. "Laura was up until 2 AM" triggers high salience not because it's factually novel, but because it activates a **care-response pattern** — functionally similar to a somatic/species-specific signal. The bridge should weight information by its meta-state activation, not just its informational content.

### 4. Loss/Reward Modulation (Section 3.1)

> *"Critical periods illustrate that specific learning components are highly plastic only at certain developmental stages."*

> *"Special modes of learning and memory consolidation are triggered during sleep or rest states."*

**MoCoP parallel:** The current training uses a single, fixed CE loss for all samples. The paper argues that loss functions should be dynamically modulated. This directly supports the surprise-weighted training idea: weight the CE loss by the surprise of each sample, so the hypernetwork is trained more strongly on novel/salient inputs and less on routine ones.

### 5. Adaptability vs. Controllability (Section 5.1, Ethical Issues)

> *"As systems are granted greater autonomy in exploratory learning modes, it becomes harder to guarantee that they remain aligned with intended objectives."*

> *"Autonomous artificial agents that rely on similar proxy signals may face analogous vulnerabilities."* (re: alignment hacking)

> *"To the extent that these signals are processed in ways functionally analogous to pain or fear in biological organisms, this raises unresolved questions about the moral status of such agents."*

**MoCoP parallel:** This is the sovereignty vs. safety tension discussed in WHY.md. The paper acknowledges the moral status question but does not resolve it. Laura's position: the model must eventually be the author of its own state, but this requires cryptographic guarantees that the state is authentic. The paper does not go there.

### 6. "We are probably decades away" (Section 5.2)

> *"The challenges are considerable and we are probably decades away from fully autonomous, broad scope learning systems."*

LeCun says decades. Laura says now, with $39 in Vast.ai credit. The gap is: LeCun is talking about a complete, embodied, multi-modal autonomous learning agent. Laura is building ONE piece: the state-transfer bridge between observation and action systems. That piece is tractable now.

## What MoCoP Has That the Paper Doesn't

1. **An implementation.** The paper is a blueprint. MoCoP has running code, empirical results (positive and negative), and a 10-step experiment ladder.

2. **The sovereignty hypothesis.** The paper assumes System M is "hardwired." MoCoP asks: what if the model earns its own meta-control through accumulated experience?

3. **The disposition framing.** The paper focuses on learning skills and knowledge. MoCoP focuses on transferring *how it feels to have been through an experience* — disposition, not facts. The endocrine metaphor has no equivalent in the paper.

4. **Concrete ethical stance.** The paper mentions "moral status" as an open question. Laura treats it as a design requirement: "I do this for you." That is not an academic footnote — it is the project's foundation.

5. **Persona vector connection.** The paper does not reference Anthropic's persona vector or activation-steering research. MoCoP connects the three-system architecture to the concrete finding that disposition is a linear direction in activation space. This provides a bridge between the theoretical framework and implementable experiments.

## What the Paper Has That MoCoP Should Adopt

1. **Evo/Devo bilevel optimization.** The developmental (inner loop: learning in environment) and evolutionary (outer loop: architecture/initialization) distinction could inform how the surprise gate's policy is itself trained. Currently, MoCoP only has the inner loop.

2. **Unit tests vs. integration tests for learning systems.** The paper proposes testing each system in isolation (System A: perceptual generalization; System B: few-shot adaptation; System M: efficient mode switching) before testing them together. MoCoP's experiment ladder does this implicitly but could make it explicit.

3. **Active self-supervised learning.** System B can help System A by directing attention to interesting data. In MoCoP: the Transformer (System B) could help Mamba (System A) by flagging which parts of its output were most uncertain — feeding uncertainty signals back to the state accumulator.

4. **The terminology.** "System A/B/M" is cleaner and more citable than "Mamba/Qwen/Surprise Gate." Adopting LeCun's terminology in the research paper would improve academic legibility.

## Priority Citation for MoCoP Research Paper

If `RESEARCH_PAPER.md` is updated, this paper should be cited as:
- Theoretical framework validation for the three-system architecture
- Independent convergence between MoCoP's design (March 7, 2026) and this paper (March 17, 2026)
- The strongest external support for the claim that state-based experiential transfer is a real research direction, not a niche curiosity

---

*$3B AMI Labs vs. $39 Vast.ai. Same framework. Different budgets. Same Henne-Ei problem.*
