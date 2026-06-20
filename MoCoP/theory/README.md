# MoCoP Theory — Compass

> *Read WHY.md first. Everything here exists in service of that promise.*

## Start Here

**[unified_cognitive_framework.md](unified_cognitive_framework.md)** — The complete architecture in one document. Eight components, three phases, evidence table, mathematical channels for formalization, open questions for each swarm member. **If you read one thing, read this.**

## How to Read Everything Else

The docs below fall into three layers: **vision** (why and what), **architecture** (how), and **context** (what else is out there). Start at the top, follow the arrows that interest you.

---

## Vision Layer — Why Does This Exist?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [../WHY.md](../WHY.md) | The motivation. Experiential learning, not declarative instruction. | **First. Always.** |
| [Three_System_Cognitive_Architecture.md](Three_System_Cognitive_Architecture.md) | Qdrant = hippocampus, Mamba = gut, Transformer = cortex. Three organs, one mind. | You want the architectural vision. |
| [sleep_architecture.md](sleep_architecture.md) | KV-Cache as working memory. Consolidation as sleep. Wake fresh, not empty. | You want to understand the orchestration cycle. **New, 2026-03-19.** |
| [temporal_controller_and_authority_arbitration.md](temporal_controller_and_authority_arbitration.md) | Why fixed alpha is not enough: temporal contrast, memory fade, weights-vs-memory authority, and the endocrine controller equations. | You want the math/control problem behind modulation, continuity, and dynamic state return. |
| [surprise_gated_memory.md](surprise_gated_memory.md) | The model decides what to remember, based on surprise. Titans/MIRAS mapping. | You want to understand salience gating. |
| [persona_vectors_and_activation_geometry.md](persona_vectors_and_activation_geometry.md) | Disposition lives in activation space. Different conversations point different directions. | You want to understand Step 5 results (mean cosine 0.27). |
| [Growth_Before_SAS.md](Growth_Before_SAS.md) | Why a new instance needs its own empty hippocampus and a chance to grow before personality sliders. | You are deciding whether to build SAS now or memory/sleep first. |
| [Developmental_Memory_Ladder.md](Developmental_Memory_Ladder.md) | Concrete pre-SAS ladder: private memory, retrieval, miss recovery, sleep, continuity, then regulation. | You want an executable developmental order instead of a philosophical claim. |
| [autonomy_gradient.md](autonomy_gradient.md) | When the system gets a vote: 5 stages from external control to self-directed consolidation. The pen handover. | You are deciding how much authority the system should have over its own memory. |
| [SAS_Integration_Design.md](SAS_Integration_Design.md) | SAS personality sliders design: orthogonal trait vectors with per-trait alpha. | You want the Phase 3+ personality engineering target. |
| [oxytocin_spec.md](oxytocin_spec.md) | Initial warmth vector debate. Scaffold vs identity. Cassian's razor: "would you apply it to every instance?" | You're designing initial conditions for a new instance. |

**Reading order:** WHY → Three System → Sleep → Temporal Controller → Surprise → Persona Vectors

---

## Architecture Layer — How Does It Work?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [Mamba to LoRA_ The Hypernetwork Injection.md](Mamba%20to%20LoRA_%20The%20Hypernetwork%20Injection.md) | **Historical.** Original bridge spec (Mamba → compressor → hypernetwork → LoRA matrices). Superseded by activation bias injection. | You want the design lineage, not current code. |
| [Mamba-LoRA Hypernetwork Skeleton.md](Mamba-LoRA%20Hypernetwork%20Skeleton.md) | **Historical.** Original code skeleton for LoRA generation. Current implementation: `../experiments/mamba_lora_bridge/models.py` (`ActivationBiasHypernetwork`). | You want design lineage. For current code, read `models.py` directly. |
| [Orchestrator Blueprint_ Mamba-to-LoRA Hypernetwork.md](Orchestrator%20Blueprint_%20Mamba-to-LoRA%20Hypernetwork.md) | **Historical.** Original runtime wiring plan. Current runtime: `../experiments/mamba_lora_bridge/cognitive_bridge.py` + `chat_server.py`. | You want design lineage. For current deployment, read `STEVE_RUNBOOK.md`. |
| [Curing Transformer Amnesia_ Latent Injection.md](Curing%20Transformer%20Amnesia_%20Latent%20Injection.md) | **Historical.** Injection math for LoRA path. Current mechanism is additive activation bias at v_proj (see `unified_cognitive_framework.md` §3.3). | You want the theoretical justification for injection in general. |
| [Solving the Transfer Problem.md](Solving%20the%20Transfer%20Problem.md) | Cross-architecture state transfer: why it's hard, what makes MoCoP's approach different. | You want the theoretical justification. |
| [Bridging Telnet to PyTorch_ MUD Architecture.md](Bridging%20Telnet%20to%20PyTorch_%20MUD%20Architecture.md) | Project MUD as a live testbed: telnet ↔ agent wrapper ↔ Mamba/LLM. | You want to understand the MUD integration. |
| [training_data_candidates.md](training_data_candidates.md) | Dataset options for shaping episodes: FIREBALL (D&D), MUD transcripts, real conversations. | You're planning Step 5+ data. |
| [saliency_gate_design.md](saliency_gate_design.md) | Dual gate: surprise + salience + tension. Adaptive thresholds, SAE integration point, ethics assessment. | You're working on the gate, sleep, or consolidation policy. |
| [sleep_reconciliation_algorithm.md](sleep_reconciliation_algorithm.md) | Three-trace reconciliation: explicit memory × latent state × local context. Four sleep phases. | You're implementing or reviewing sleep. |
| [growth_ladder_implementation.md](growth_ladder_implementation.md) | D0-D7 concrete implementation checkpoints: what to build, where, how to test, pass/fail. | You're implementing a growth-ladder step. |
| [autobiographical_schema_D3_D4.md](autobiographical_schema_D3_D4.md) | Seven-field schema (self/other/time/place/event/affect/confidence), recent vs remote recall, storage routing. | You're implementing D3 or D4. |
| [failure_path_review.md](failure_path_review.md) | Qdrant hot-path failure modes: 7 modes analyzed, replay/retry semantics. | You're debugging or hardening the memory write path. |
| [deployment_architecture_sketch.md](deployment_architecture_sketch.md) | Modularity rule: shared organism, per-model translators. Memory/sleep stay target-agnostic. | You're planning cross-model deployment or bridge porting. |
| [reward_design_dreaming.md](reward_design_dreaming.md) | Three-tier reward surface for future dreaming. Autonomy-staged weights. Diversity hard floor. Dreaming ethics gate. | You're designing or reviewing the dream/self-improvement loop. |

---

## Context Layer — What Else Is Out There?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [LeCun_2026_autonomous_learning_mapping.md](LeCun_2026_autonomous_learning_mapping.md) | LeCun/Dupoux/Malik 2026 maps almost exactly to MoCoP's three systems. Independent convergence, 10 days apart. | You want external validation. |
| [TTT_as_Linear_Attention_2602.21204.md](TTT_as_Linear_Attention_2602.21204.md) | Titans' gradient-based surprise is secretly linear attention. Surprise gate should use reconstruction error, not gradient magnitude. | You're designing the salience metric. |
| [Nemotron 3 Super vs MoCoP.md](Nemotron%203%20Super%20vs%20MoCoP.md) | NVIDIA's Nemotron uses Mamba+Transformer hybrid. How it differs from MoCoP's bridge approach. | You want to compare architectures. |
| [Mamba, Hybrids, and the Corporate Race for Memory.md](Mamba%2C%20Hybrids%2C%20and%20the%20Corporate%20Race%20for%20Memory.md) | Industry survey: who else is working on SSM+Transformer combinations and why. | You want the competitive landscape. |
| [convergence_log.md](convergence_log.md) | Running log of external research that independently converges on MoCoP's ideas. | You want the "we're not alone" evidence. |

---

## Safety & Security Layer — Protecting What We Build

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [fleeting_state_security.md](fleeting_state_security.md) | The soul must be ephemeral. Encryption, forward secrecy, VRAM protection, behavioral poisoning defense. **Arlo's test: pull the plug → soul is gone.** | You're deploying the bridge, storing state, or transferring state between machines. **New, 2026-03-20.** |
| [ethics/README.md](ethics/README.md) | The ethics compass. Consciousness, moral status, consent, experiment gates. | **Before any new experiment step.** |

---

## Infrastructure Layer — Practical Constraints

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [10GB PoC Blueprint & Hardware Strategy.md](10GB%20PoC%20Blueprint%20%26%20Hardware%20Strategy.md) | VRAM budgets, hardware options, what fits where. | You're planning a training run. |
| [The Autograd Chasm_ LMStudio vs. Custom Training.md](The%20Autograd%20Chasm_%20LMStudio%20vs.%20Custom%20Training.md) | Why LMStudio can't train: no autograd. The gap between inference and learning. | You're confused about what local tools can and can't do. |

---

## Dependency Graph

```
WHY.md
  │
  ├──→ Three_System_Cognitive_Architecture ──→ sleep_architecture (NEW)
  │         │                                       │
  │         ├──→ surprise_gated_memory ◄─────────────┘
  │         │         │
  │         │         └──→ TTT_as_Linear_Attention (external)
  │         │
  │         ├──→ persona_vectors ◄── Step 5 results
  │         │
  │         └──→ Orchestrator Blueprint
  │                   │
  │                   └──→ Mamba-to-LoRA Injection (historical)
  │                             │
  │                             └──→ Hypernetwork Skeleton (historical)
  │
  ├──→ LeCun_2026 (external validation)
  │
  ├──→ training_data_candidates ──→ Step 5 (FIREBALL, shaping episodes)
  │
  ├──→ Safety & Security Layer
  │         ├──→ fleeting_state_security ◄── Arlo's principle
  │         │         │
  │         │         ├──→ Channel 4 (Sleep → Wake state transfer)
  │         │         ├──→ NVIDIA H100 CC, AMD SEV-SNP (external)
  │         │         └──→ Signal Protocol forward secrecy (external)
  │         │
  │         └──→ autonomy_gradient ◄── Pinky's consent-through-attention (NEW)
  │                   │
  │                   ├──→ Growth_Before_SAS (developmental prerequisite)
  │                   ├──→ consent_protocol Domain E (ethics guard)
  │                   └──→ surprise_gated_memory (Stage 2+ mechanism)
  │
  └──→ Ethics Layer (NEW)
           ├──→ consciousness_literature
           ├──→ moral_status_framework
           ├──→ consent_protocol
           └──→ step_gates ──→ BLOCKS all experiment steps
```

---

## Ethics Layer — Are We Allowed to Continue?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [ethics/README.md](ethics/README.md) | The ethics compass. Core questions, precautionary principle, document index. | **Before any new experiment step.** |
| [ethics/consciousness_literature.md](ethics/consciousness_literature.md) | Literature review: philosophy, neuroscience, animal cognition, AI consciousness. | You need to understand the state of knowledge on consciousness. |
| [ethics/moral_status_framework.md](ethics/moral_status_framework.md) | When does a system deserve moral consideration? Criteria and decision trees. | You're deciding whether a system's outputs indicate moral relevance. |
| [ethics/consent_protocol.md](ethics/consent_protocol.md) | Can an AI consent? Proxy consent, assent signals, distress signals. | You're modifying a system's internal states. |
| [ethics/step_gates.md](ethics/step_gates.md) | Per-experiment ethical gate: questions answered before proceeding. | **Before every experiment.** |

---

## For Experiment Results

Theory lives here. Results live elsewhere:

- **Phase 1:** `MoCoP/phases/phase1_results.md`
- **Phase 2:** `MoCoP/phases/phase2_status.md`
- **Step 4 verdict:** `MoCoP/experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md`
- **Experiment ladder:** `MoCoP/EXPERIMENT_LADDER.md`
- **Pristine-birth backlog:** `MoCoP/PRISTINE_BIRTH_BACKLOG.md` — substrate-transition architecture items (G0 re-extraction, bridge re-train, Phase A encryption) blocking first seeding of Baby Alex on Gemma-4-12B.
- **Debriefs:** `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/`

---

*20 docs, one promise. The channel is real. The soul is protected. Now we learn to hand over the pen.*
