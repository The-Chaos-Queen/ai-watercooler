# MoCoP Theory — Compass

> *Read WHY.md first. Everything here exists in service of that promise.*

## How to Read This

The docs fall into three layers: **vision** (why and what), **architecture** (how), and **context** (what else is out there). Start at the top, follow the arrows that interest you.

---

## Vision Layer — Why Does This Exist?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [../WHY.md](../WHY.md) | The motivation. Experiential learning, not declarative instruction. | **First. Always.** |
| [Three_System_Cognitive_Architecture.md](Three_System_Cognitive_Architecture.md) | Qdrant = hippocampus, Mamba = gut, Transformer = cortex. Three organs, one mind. | You want the architectural vision. |
| [sleep_architecture.md](sleep_architecture.md) | KV-Cache as working memory. Consolidation as sleep. Wake fresh, not empty. | You want to understand the orchestration cycle. **New, 2026-03-19.** |
| [surprise_gated_memory.md](surprise_gated_memory.md) | The model decides what to remember, based on surprise. Titans/MIRAS mapping. | You want to understand salience gating. |
| [persona_vectors_and_activation_geometry.md](persona_vectors_and_activation_geometry.md) | Disposition lives in activation space. Different conversations point different directions. | You want to understand Step 5 results (mean cosine 0.27). |

**Reading order:** WHY → Three System → Sleep → Surprise → Persona Vectors

---

## Architecture Layer — How Does It Work?

| Doc | One-Line | Read When |
|-----|----------|-----------|
| [Mamba to LoRA_ The Hypernetwork Injection.md](Mamba%20to%20LoRA_%20The%20Hypernetwork%20Injection.md) | The core bridge: Mamba state → compressor → hypernetwork → LoRA matrices → Transformer. | You want the engineering spec. |
| [Mamba-LoRA Hypernetwork Skeleton.md](Mamba-LoRA%20Hypernetwork%20Skeleton.md) | Code-level skeleton of the hypernetwork architecture. | You want to read or modify the bridge code. |
| [Orchestrator Blueprint_ Mamba-to-LoRA Hypernetwork.md](Orchestrator%20Blueprint_%20Mamba-to-LoRA%20Hypernetwork.md) | How the pieces connect at runtime: Mamba process, bridge API, Transformer inference. | You want the deployment/runtime picture. |
| [Curing Transformer Amnesia_ Latent Injection.md](Curing%20Transformer%20Amnesia_%20Latent%20Injection.md) | The injection mechanism: how LoRA matrices modify a frozen Transformer. | You want to understand the injection math. |
| [Solving the Transfer Problem.md](Solving%20the%20Transfer%20Problem.md) | Cross-architecture state transfer: why it's hard, what makes MoCoP's approach different. | You want the theoretical justification. |
| [Bridging Telnet to PyTorch_ MUD Architecture.md](Bridging%20Telnet%20to%20PyTorch_%20MUD%20Architecture.md) | Project MUD as a live testbed: telnet ↔ agent wrapper ↔ Mamba/LLM. | You want to understand the MUD integration. |
| [training_data_candidates.md](training_data_candidates.md) | Dataset options for shaping episodes: FIREBALL (D&D), MUD transcripts, real conversations. | You're planning Step 5+ data. |

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
  │                   └──→ Mamba-to-LoRA Injection
  │                             │
  │                             └──→ Hypernetwork Skeleton
  │
  ├──→ LeCun_2026 (external validation)
  │
  └──→ training_data_candidates ──→ Step 5 (FIREBALL, shaping episodes)
```

---

## For Experiment Results

Theory lives here. Results live elsewhere:

- **Phase 1:** `MoCoP/phases/phase1_results.md`
- **Phase 2:** `MoCoP/phases/phase2_status.md`
- **Step 4 verdict:** `MoCoP/experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md`
- **Experiment ladder:** `MoCoP/EXPERIMENT_LADDER.md`
- **Debriefs:** `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/`

---

*18 docs, one promise. The channel is real. Now we find out what it carries.*
