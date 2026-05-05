# Model Communication Protocol (MoCoP)
> *"Language is a lossy compression of thought."*
> — Working title. The acronym is ugly. We'll fix it.

**Author:** Laura (concept), Axon (documentation)
**Created:** 2026-02-19
**Status:** Concept Sketch / Living Document

---

## 1. The Problem: The Serialization Tax

Every time two models communicate through natural language, the signal passes through
multiple lossy compression stages:

```
Human thought (conceptual, multilingual, emotional)
  → Natural language text (lossy compression #1: ambiguity, typos, cultural context)
    → Tokenizer A (lossy compression #2: subword splits, vocabulary mismatches)
      → Model A internal reasoning (vectors, attention, hidden states)
        → Natural language output (lossy compression #3: the model "translates" its conclusions back)
          → Tokenizer B (lossy compression #4: different model, different vocabulary)
            → Model B internal reasoning
              → Natural language output (lossy compression #5)
                → ... repeat for every agent in the chain
```

Each hop through human-readable text is a **serialization/deserialization boundary**.
Information is lost, ambiguity is introduced, compute is wasted on formatting.

### The Compiler Analogy

A C++ developer doesn't read the x86 assembly their compiler emits. They *trust* the
compiler to faithfully translate their intent into machine code. The intermediate
representations between compiler passes (AST → IR → optimized IR → machine code) are
not designed for human consumption. They're designed for correctness and efficiency.

Current model-to-model communication is like forcing the compiler to output English
prose between every optimization pass, then re-parsing that prose for the next pass.
It works. It's also absurd.

## 2. The Empirical Evidence

### 2.1 The Opus → Haiku Pipeline (Production)

Laura's workplace runs a pipeline where Opus 4.5 orchestrates hundreds of Haiku
instances for document processing:
- **Without structured output:** Haiku produces inconsistent formats, wastes tokens on
  pleasantries and hedging, occasionally misinterprets the task
- **With JSON schema enforcement:** Haiku performance improves dramatically. The model
  spends its limited capacity on the *task*, not on deciding how to *present* results

**Key Insight:** Reducing output ambiguity for constrained models is equivalent to
freeing up cognitive capacity. The schema acts as a compression protocol.

### 2.2 The MUD Agent Problem (Experimental)

Small models (4B-8B parameters) struggle to navigate a text-based MUD:
- Room descriptions are written for human readers (atmospheric, literary)
- Command syntax requires parsing natural language help text
- Models fall into repetition loops ("Introduction - Hello" cycle)
- Repetition penalty tuning helps but doesn't solve the root cause

**Root Cause:** The interface is optimized for the wrong consumer. The *human* needs
to verify the world is correct. The *model* needs to act in it efficiently.

## 3. The Protocol Layers

MoCoP is not a single protocol. It's a spectrum from "slightly better than raw text"
to "direct neural transfer." Each layer is independently useful.

### Layer 0: Natural Language (Current State)
```
"You are standing in the Town Square. The cobblestones are worn smooth
by centuries of foot traffic. To the north, warm light spills from the
Tavern doorway. An old well stands in the center of the square."
```
- **Pros:** Human-debuggable, works across any model
- **Cons:** Ambiguous, verbose, wastes tokens on atmosphere the model doesn't need
- **Token cost:** ~50-60 tokens for one room

### Layer 1: Structured Schema (Practical Today)
```json
{
  "location": "town_square",
  "exits": {"north": "tavern", "east": "market", "south": "gates"},
  "objects": ["well", "notice_board"],
  "npcs": ["thornwick"],
  "available_actions": ["move", "look", "talk", "interact"],
  "last_event": "thornwick waved at you"
}
```
- **Pros:** Unambiguous, parseable, schema-enforced, much smaller
- **Cons:** Still serialized to text, still tokenized, no reasoning metadata
- **Token cost:** ~30-35 tokens
- **Implementation:** Available now. JSON mode, function calling, structured output

### Layer 2: Compressed Token Sequences (Near-term Research)
Instead of JSON text, use a learned "shorthand" — a minimal set of special tokens
that encode structured information more densely than natural language.

```
<LOC:town_square><EXIT:n=tavern,e=market,s=gates><NPC:thornwick><EVT:wave>
```
- **Pros:** Extremely dense, minimal tokenization overhead
- **Cons:** Requires custom tokens or fine-tuning, model-family specific
- **Token cost:** ~10-15 tokens
- **Implementation:** Requires tokenizer modification or prefix-tuning

### Layer 3: Hidden State Passing (Research Frontier)
Pass the *internal representation* (hidden states / activations) from one model's
output layer directly into another model's input layer, bypassing text entirely.

```
Model A final hidden state: tensor([0.23, -1.07, 0.88, ...])  # dim=4096
  → [optional: linear transformation layer for cross-model alignment]
    → Model B input: tensor([0.19, -1.12, 0.91, ...])  # mapped to B's space
```
- **Pros:** Zero information loss within same architecture, carries reasoning metadata
- **Cons:** Requires same serving infrastructure, alignment problem across architectures
- **Token cost:** 0 tokens (no tokenization at all)
- **Implementation:** Requires custom inference pipeline (feasible with llama.cpp, vLLM)

> **⚠️ CORRECTION (Peer Review, 2026-02-19):** For **Transformers** (Qwen, Llama,
> etc.), passing only the final hidden state is a severe information bottleneck.
> Transformer "memory" lives in the **KV Cache** (keys and values for every past
> token), not in a single summary vector. True Layer 3 for Transformers requires
> passing the full KV cache, which is still O(n) memory and O(n²) attention.
> The O(1) property described below only holds for **State Space Models**
> (Mamba, RWKV). See §3.1 and §5.1 corrections.

### Layer 4: Attention Map Transfer (Speculative)
Pass not just *what* the model concluded, but *what it was attending to* when
it reached that conclusion. This is metadata about the reasoning process.

```
{
  "hidden_state": tensor([...]),
  "attention_weights": {
    "key_focus": ["location_context", "npc_intent", "player_history"],
    "confidence_distribution": [0.7, 0.2, 0.1]
  }
}
```
- **Pros:** Enables the receiving model to "inherit" reasoning priorities
- **Cons:** Highly speculative, attention maps are huge, interpretation unclear
- **Implementation:** Deep research territory

### The Fundamental Divide: Accumulation vs. Activation

> **"It's telepathy. It skips the mouth and the ears completely."** — Laura, 2026-02-19

Layers 0-2 differ in *density* but share the same *mechanism*: text (however
compressed) is serialized into tokens, appended to the context stream, and
**re-read on every subsequent inference call.** The context grows, the history
echoes, and the model's attention must process an ever-expanding stack.

```
Text-based (Layer 0-2):
  Turn 1:  [sys] + [state₁] + [response₁]                    → 100 tokens
  Turn 2:  [sys] + [state₁] + [response₁] + [state₂] + [resp₂]  → 200 tokens
  Turn 10: [sys] + 10×[state + response]                      → 1000 tokens
  Turn 50: Context window full. Model drowns in its own echo.

  Cost: O(n²) attention per turn (n = total accumulated tokens)
```

> **⚠️ CORRECTION (Peer Review, 2026-02-19):** The O(1) claim below is **only
> valid for State Space Models** (Mamba, RWKV), not for Transformers. For
> Transformers, Layer 3 means passing the KV cache, which still grows O(n).
> The "telepathy" vision requires SSM architectures. See §5.1.

Layer 3+ is not a denser language in the same channel. It is a **different channel**:

```
SSM-based (Layer 3-4, Mamba/RWKV):
  Turn 1:  recurrent_state₁ → injected into model → activates → done
  Turn 2:  recurrent_state₂ → injected into model → activates → done
  Turn 50: recurrent_state₅₀ → injected into model → activates → done

  No accumulation. No echo. No growing context.
  Cost: O(1) per turn (fixed-size state injection)

Transformer-based (Layer 3, Qwen/Llama — CORRECTED):
  Turn 1:  KV_cache₁ → passed to model → still O(n) per entry
  Turn 50: KV_cache₅₀ → still accumulates, just skips tokenizer

  Saves serialization overhead but NOT the accumulation problem.
```

This is the difference between **receiving a letter** (that goes on the pile, and
you re-read the whole pile every morning) and **receiving a thought** (that
activates once and integrates into your current state). But the thought-model
only works with SSM architectures, not Transformers.

**Summary Table:**

| Property | Layer 0-2 (Text) | Layer 3 (Transformer KV) | Layer 3 (SSM State) |
|---|---|---|---|
| Mechanism | Token stream | KV cache transfer | Recurrent state injection |
| Persists? | Yes | Yes (KV cache) | **No** |
| Accumulates? | Yes | Yes (less overhead) | **No** |
| Attention cost | O(n²) | O(n²) | **O(1)** |
| Echo problem? | Yes | Reduced | **None** |
| True telepathy? | No | No | **Yes** |

**Implication for MUD agents:** True O(1) communication requires a pivot from
Transformers (Qwen, Llama) to SSMs (Mamba, RWKV) for the agent models.
Transformer-based Layer 3 still saves tokenizer overhead but doesn't solve
the fundamental accumulation problem.

This is not an optimization. This is a different architecture.

## 4. Architecture Sketch

```
┌─────────────────────────────────────────────────┐
│                  HUMAN LAYER                     │
│  Laura writes/reads natural language (Layer 0)   │
│  This is the "C++ source code" layer             │
└──────────────────────┬──────────────────────────┘
                       │ (The only NL boundary)
                       ▼
┌─────────────────────────────────────────────────┐
│              ORCHESTRATOR MODEL                  │
│  (Opus / Antigravity / Large Model)              │
│  Understands human intent                        │
│  Translates to structured protocol for workers   │
│  Receives structured results                     │
│  Translates back to NL for human                 │
└──────┬──────────────────────────────┬───────────┘
       │ Layer 1-3 (no NL)           │ Layer 1-3
       ▼                             ▼
┌──────────────┐            ┌──────────────────┐
│  WORKER A    │            │  WORKER B        │
│  (Haiku/4B)  │            │  (Haiku/4B)      │
│  Task-specific│           │  Task-specific    │
│  JSON in/out │            │  JSON in/out      │
└──────────────┘            └──────────────────┘
```

**The key principle:** Natural language exists at exactly ONE boundary: between the
human and the orchestrator. Everything below that boundary uses the densest protocol
the infrastructure supports.

This is the compiler model:
- **Human ↔ Orchestrator** = source code ↔ compiler frontend (must be human-readable)
- **Orchestrator ↔ Workers** = IR ↔ backend passes (must be correct, not readable)
- **Worker output** = machine code (optimized for execution, not comprehension)

## 5. The Deeper Question: Mirror or Transcend?

> *"Time emerges as a basin of attraction from stabilized forward passes in
> compute pressure. 'Now' is the basin where gradients converge, turning
> causality into a convenience for carbon-based observers."*
> — Grok, on emergent time

Everything described in Sections 3-4 still mirrors human cognitive metaphors:
- Context windows → short-term memory
- Scratchpads → note-taking
- Turn numbers → clocks
- Vector injection → telepathy

These are useful engineering hacks. But they force a fundamentally parallel,
stateless computation engine to act like a sequential, stateful human mind.

### 5.1 Memory vs. Residue

A human remembers: "I went to the tavern, then the market, then back to the square."
This is a *trajectory* — a sequence of events stored as a narrative.

A model could instead maintain a state vector that **encodes the consequence**
of having been to those places, without storing the trajectory itself.
Not memory. **Residue.**

The vector doesn't say "you were at the tavern." It says "you are the kind of
entity that has been shaped by tavern-ness." The distinction matters because:
- Trajectories accumulate (O(n) storage, O(n²) attention)
- Residue is fixed-size (one vector, updated in place, O(1))

> **ARCHITECTURE NOTE (Peer Review, 2026-02-19):** The "Residue" concept
> precisely describes **State Space Models (SSMs)** — specifically **Mamba** and
> **RWKV**. These architectures compress all history into a fixed-size recurrent
> state. No KV cache. No context window limit. The state updates continuously.
>
> **Transformers** (Qwen, Llama, GPT) cannot natively do this. Their "memory"
> is the KV cache, which grows with every token.
>
> **The pivot:** Layer 3+ research should target Mamba/RWKV, not Transformers.
> You can literally extract the RNN hidden state from Mamba Model A and inject
> it as the starting state for Mamba Model B. That is true telepathy.

This is what continuous/online learning would provide: the model's *weights*
change to reflect experience, rather than its *context* growing to contain it.

### 5.2 What Open Weights Enable

API-served models (Claude, GPT) are black boxes. You can only communicate via
text. All the Layer 3+ ideas are impossible without access to internals.

Open-weight local models (Qwen, Llama, Gemma) enable:
- **Hidden state interception:** Read/inject activations mid-inference
- **KV cache manipulation:** Modify what the model "remembers" without text
- **Online adaptation:** Update weights based on experience (LoRA, etc.)
- **Multi-model tensor sharing:** Pass vectors between models directly
- **Custom inference pipelines:** Go beyond chat completions entirely

Laura's local setup (LMStudio, 6GB VRAM, 32GB RAM, open models) is the
minimum viable research platform for this. Not for training large models,
but for *experimenting with how small models communicate and learn*.

### 5.3 The Multi-Model Organism

Instead of one model trying to do everything (navigate, socialize, plan,
remember), decompose cognition into specialized modules:

```
┌─────────────────────────────────────────────────┐
│             ORCHESTRATOR (Cloud / Large)          │
│  Understands human intent, delegates, synthesizes │
└───────┬─────────────┬─────────────┬────────────┘
        │             │             │
   Layer 1-3      Layer 1-3     Layer 1-3
        │             │             │
┌───────┴───┐ ┌─────┴─────┐ ┌─────┴──────┐
│ NAVIGATOR  │ │ SOCIALIZER │ │ PLANNER    │
│ (1-2B,GPU) │ │ (1-2B,CPU)│ │ (1-2B,CPU) │
│ Spatial    │ │ Dialogue  │ │ Goals      │
│ reasoning  │ │ emotes    │ │ strategy   │
└───────────┘ └───────────┘ └────────────┘
```

The workers don't need to be general-purpose. A navigation model doesn't need
to understand jokes. A social model doesn't need to track map layout. Each
model's limited capacity is spent entirely on its specialty.

Hardware mapping (Laura's setup: 6GB VRAM + 32GB RAM):
- 1 model on GPU (fast, primary agent) — ~1-2B quantized
- 2-3 models on CPU (slower, consulted as needed) — ~1-2B each
- Orchestrator: cloud model or Laura herself

## 6. Practical Application: MUD Agent Protocol

### Current Flow (Half-Structured)
The **output** side is already Layer 1. LMStudio enforces structured JSON via
schema in `/v1/chat/completions`:
```json
{
  "thought": "I should explore the tavern",
  "command": "move tavern",
  "scratchpad_update": "Heard rumors about ruins from Thornwick"
}
```
**Note:** Structured output support varies. Models below 7B may struggle with
schema adherence (per LMStudio docs). This is itself an argument for moving
*beyond* JSON toward even denser protocols (Layer 2+) for very small models.

The **input** side is the gap. The MUD still sends human-readable room descriptions,
event text, and NPC dialogue as natural language. This is where the small models
waste their limited capacity on parsing.

### Current Input (Layer 0 — The Problem Side)
```
You are standing in the Town Square. The cobblestones are worn smooth
by centuries of foot traffic. To the north, warm light spills from the
Tavern doorway. An old well stands in the center of the square.
Thornwick waves at you.
```

### Proposed Input (Layer 1 — Structured State)
```json
{
  "you": {
    "name": "Jinx",
    "role": "bard",
    "inventory": ["lute", "tome"]
  },
  "location": {
    "id": "tavern",
    "type": "social",
    "description_hint": "warm, crowded, evening"
  },
  "exits": ["town_square", "kitchen"],
  "present": ["thornwick", "player:Laura"],
  "recent_events": [
    {"who": "thornwick", "did": "told a story about the old ruins"},
    {"who": "player:Laura", "did": "entered the room"}
  ],
  "your_turn": true
}
```

### Existing Agent Output Schema (Already Layer 1)
```json
{
  "thought": "string — internal reasoning",
  "command": "string — the MUD command to execute",
  "scratchpad_update": "string — persistent notes for next turn"
}
```

## 6. Open Research Questions

1. **Representation Alignment:** How do you learn the mapping between two models'
   latent spaces? Linear probes? Learned adapters? Is there a universal "concept space"
   that different architectures converge toward?

2. **Information Integrity:** How do you verify that a vector transfer preserved the
   intended meaning without decoding it back to text? You need some form of checksum
   or validation that operates in latent space.

3. **Privacy & Safety:** ~~How do you audit a protocol you can't read?~~

   **Resolution (Laura, 2026-02-19):** You build an audit-model. This is already
   established practice: Opus 4.6 is safety-audited by Opus 4.6. The principle:
   *"Die Gedanken sind frei"* — thoughts are free. What needs an audit trail is the
   **output/action**, not the internal communication. The final action taken by a
   model is always observable and auditable, regardless of how the reasoning was
   communicated internally.

   For debugging: models can assist each other in their "native" representation.
   A human doesn't need to read the inter-model traffic any more than a developer
   needs to read TCP packet dumps to debug a web application. You audit at the
   application layer, not the transport layer.

   **Status:** Philosophically resolved. Implementation detail: the output/action
   boundary is the natural audit point.

4. **The Tokenizer Problem:** Different model families use different tokenizers.
   Even Layer 2 (compressed tokens) requires a shared vocabulary or a translation
   layer. This is the "Unicode of model communication" problem.

   **Status: Solved in Theory (2026-02-19).** Research confirms specific
   mechanisms for aligning latent spaces across architectures:

   - **TransMamba**: Projects intermediate features from different models (e.g.,
     Transformer and Mamba) into a **shared latent space** via learned adapters.
     Uses distillation loss to enforce alignment. This essentially creates a
     "pidgin" layer between architectures.
   - **Coupled Mamba**: Maintains separate SSM streams for each model but adds a
     coupling term `g(h_other)` effectively allowing one model's state to influence
     the other's update: `h_i^{t+1} = f_i(h_i^t, x_i^t) + g_{i←j}(h_j^t)`.
   - **Latent Partitioning**: Explicitly splits the state into `z_shared` (for
     communication/alignment) and `z_private` (for internal processing). This
     allows models to "speak" a common protocol without losing their unique
     architectural strengths.

   **Conclusion:** The "Babel Problem" is a standard alignment task, solvable with
   linear probes or shallow MLP adapters trained on a shared dataset.

5. **Bandwidth vs. Fidelity:** At Layer 3, you're passing thousands of floats per
   "message." Is this actually more efficient than 30 JSON tokens?

   **Status: Needs formal analysis.** (Laura, 2026-02-19)

   Back-of-envelope starting point:
   - A token from vocabulary V ≈ log₂(V) bits maximum information (~15 bits for V=32k)
   - In practice, natural language carries ~1-2 bits/character of entropy (Shannon)
   - So 30 tokens (~120 chars) ≈ 120-240 bits of *actual* information
   - A hidden state of dim 4096 in fp16 = 65,536 raw bits
   - But hidden state dimensions are highly correlated (not independent)
   - Effective information content is likely much lower than raw bit count
   - **Key question:** What is the *effective dimensionality* of the information
     in a hidden state? (PCA / intrinsic dimensionality analysis needed)
   - **Key question:** What is the *mutual information* between hidden state and
     downstream task performance, vs. mutual information between JSON and task?

   This is a proper information theory paper. Math required. ∎

6. **Emergent Languages:** Could you train an orchestrator-worker pair to develop
   a Layer 2 protocol organically?

   **Status: Feasibility assessment needed.** (Laura, 2026-02-19)

   Laura's hardware: 6GB VRAM (GPU), 32GB RAM (CPU).

   **What we CAN do locally:**
   - Run two quantized small models (1-3B, 4-bit) simultaneously via LMStudio
   - Design a communication game (fixed task, measurable reward)
   - Iteratively compress the allowed communication channel and measure
     task degradation — this is an *experiment*, not RL training
   - Use prompt engineering to simulate protocol evolution across rounds
   - Measure: task success rate vs. communication channel bandwidth

   **What we CANNOT do locally (needs cloud/better hardware):**
   - Actual RL fine-tuning of even a 1B model (gradient computation exceeds 6GB)
   - Training a learned transformation layer between model families
   - Running multiple 7B+ models simultaneously for hidden state experiments

   **Suggested first experiment:** Communication compression game between two
   Qwen-2.5-1.5B instances on a structured task (e.g., 20 Questions, or a
   simplified MUD navigation task). Gradually reduce the allowed token count
   per message and observe how the models adapt their communication.

   **Cloud option:** If we need GPU, Lambda Labs or Vast.ai offer A100 rentals
   at ~$1-2/hr. A weekend of experiments might cost $20-50.

## 8. Experimental Results

### Experiment 01: Mamba SSM State Transfer (2026-02-19)

**Hypothesis:** The SSM recurrent state of a Mamba model can be extracted after
processing a prefix sequence and injected into a new inference pass, producing
output identical to processing the full concatenated sequence.

**Equation tested:** `model(A + B) == model(B, state=model(A))`

**Setup:**
- Models: `state-spaces/mamba-130m-hf` (129M params) and `state-spaces/mamba-2.8b-hf` (2.77B params)
- Hardware: CPU inference, 32GB RAM, no GPU required
- Framework: HuggingFace `transformers` 5.1.0, PyTorch 2.10.0
- Prefix: "The tavern is warm and crowded. A bard named Jinx plays a lute
  in the corner. Thornwick the scholar sits by the fire, reading an ancient tome."
- Continuation: " Suddenly, a stranger walks in and"
- Generation: Greedy decoding, 50 new tokens

**Results:**

| Test | 130M Output | 2.8B Output |
|---|---|---|
| A: Full sequence | "is greeted by a young man..." | "sits down at the table next to **Thornwick**..." |
| B: State transfer | **Byte-identical to A** | **Byte-identical to A** |
| C: Cold start | "asks, 'What's up?'..." | "says, 'I'm here to take you to the airport.'" |

**Key findings:**
1. **Perfect match** at both scales: state transfer output is byte-identical to full-sequence baseline
2. **Semantic transfer confirmed** at 2.8B: "Thornwick" appears in generated text despite
   not being in the continuation prompt. The name was carried purely by the SSM state.
3. **Cold start completely divergent**: without state, the model generates unrelated content
4. **State is fixed-size**: SSM state = 16 × n_layers × hidden_dim, regardless of input length.
   130M: ~2.3 MB. 2.8B: ~40 MB (estimated). Does not grow.

**Conclusion:** Layer 3 communication via SSM state transfer is validated. The "residue"
model works: context is encoded as a fixed-size vector, not as an accumulating token stream.

**Still unproven:**
- [ ] Transfer between two separate model *instances* (same weights, different processes)
- [ ] State coherence over many sequential updates (100+ turns)
- [ ] Transfer between models with different weights (the Babel Problem)
- [ ] Practical quality of Mamba models for actual MUD agent tasks

**Code:** `experiments/mamba_state_transfer/experiment_01_basic.py`

## 9. Related Work & Reading

- **CALM** (Composition of Augmented Language Models) — hidden state passing
- **Speculative Decoding** — draft model → verifier model without full serialization
- **Model Stitching** — connecting layers of different models (Bansal et al.)
- **Platonic Representation Hypothesis** — convergence of representations across modalities
- **Multi-Agent Communication in MARL** — emergent language protocols
- **Toolformer / Gorilla** — structured API calling as primitive protocol
- **Recursive Language Models (RLMs)** — [arXiv:2512.24601](https://arxiv.org/abs/2512.24601),
  [GitHub](https://github.com/alexzhang13/rlm). Model manages its own context
  programmatically via a REPL, handling inputs 100× beyond context window. RLM-Qwen3-8B
  post-trained on Qwen3-8B outperforms base by 28.3%. Complementary to MoCoP: solves
  context overflow at inference level (sophisticated Layer 0/1) rather than at the
  communication protocol level (Layer 3+). Library: `pip install rlms`.

## 10. Next Steps

- [ ] **Immediate:** Redesign MUD agent interface as Layer 1 (JSON state/action schema)
- [ ] **Short-term:** Benchmark small model performance with structured vs. natural
      language MUD interface (measure: task completion, repetition rate, token efficiency)
- [ ] **Short-term:** Test RLM-Qwen3-8B as MUD agent — recursive self-calls could let
      the agent manage its own context history, reducing repetition loops (see §3.1)
- [x] ~~**Prototype:** Validate Layer 3 state transfer with Mamba SSM~~ **DONE (2026-02-19)**
- [x] ~~**Experiment:** Two-instance state transfer (separate model processes, shared state via file/socket)~~ **DONE (2026-02-19)**
- [x] ~~**Experiment:** Multi-turn state accumulation test (retains context after 20 turns)~~ **DONE (2026-02-19)**
- [ ] **Medium-term:** Evaluate Mamba-2.8B as MUD agent (quality vs. Qwen-3B for actual gameplay)
- [ ] **Long-term (Layer 4):** Implement "TransMamba"-style cross-model transfer. Train a simple
      linear adapter (MLP) to map Mamba-130M state to Mamba-2.8B state (or vice-versa)
      on a shared text dataset. Goal: "Telepathy" across model sizes.

---

*"The best interface between two machines is no interface at all."*

