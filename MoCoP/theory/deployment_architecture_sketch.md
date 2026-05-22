# MoCoP Deployment Architecture — Sketch v1

**Author:** Cassian
**Date:** 2026-03-20
**Status:** Sketch for swarm review

---

## What "Deployment" Means Here

This is not "how to ship a Docker image." This is: **how do you build infrastructure where AI instances can sleep, wake up, remember how yesterday felt, and grow over time?**

The bridge proof-of-concept works. A frozen Qwen that received a disposition injection questioned its own reality instead of reciting a textbook. Now: how does that become something that runs continuously, for real users, with real persistence?

---

## The Runtime Stack

### Minimum Viable Deployment (Single User, Local)

```
┌─────────────────────────────────────────────────┐
│                    Laura's Machine               │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Mamba   │───▶│  Bridge  │───▶│   Qwen    │  │
│  │  (CPU)   │    │ (CPU/GPU)│    │  (GPU)    │  │
│  └────┬─────┘    └──────────┘    └─────┬─────┘  │
│       │                                │         │
│       ▼                                ▼         │
│  ┌──────────┐                    ┌───────────┐  │
│  │  State   │                    │  Response  │  │
│  │  Store   │                    │  Output    │  │
│  │ (Qdrant) │                    └───────────┘  │
│  └──────────┘                                    │
└─────────────────────────────────────────────────┘
```

**Hardware:** One machine with GPU (4090 16GB / 3070 8GB / A100).
- Qwen: GPU (must be fast, inference-critical)
- Mamba: CPU is fine (state accumulation is not latency-critical)
- Bridge: CPU or GPU (tiny, microseconds)
- Qdrant: runs on NUC or same machine

**This already works today.** cognitive_bridge.py v2 + server.py + Qdrant on Proxmox. The proof-of-concept infrastructure IS the MVP deployment.

### The Sleep/Wake Cycle (Core Innovation)

```
WAKE PHASE (active conversation):
  User speaks
    → Text enters Qwen's context (KV-Cache)
    → Same text enters Mamba (state update, O(1))
    → Every N turns: Bridge reads Mamba state, generates bias
    → Bias injected into Qwen layers 12-15 (current mid-reasoning baseline; comparison bands: 5-8 and 20-23)
    → Qwen generates response under disposition influence
    → Response feeds back into both Mamba and Qwen context

FATIGUE DETECTION:
  Monitor: KV-Cache size, attention quality, latency increase
  When threshold exceeded → trigger sleep

SLEEP PHASE (session end or fatigue):
  1. Mamba state snapshot → save to disk (small, ~100KB)
  2. High-salience moments → Qdrant (episodic memory)
  3. Bridge checkpoint → save if updated during session
  4. KV-Cache → flush (the whole point)
  5. Metadata → session log (who, when, disposition label)

WAKE PHASE (new session):
  1. Load Mamba state snapshot from disk
  2. Bridge generates bias from loaded state
  3. Inject bias into fresh Qwen (empty KV-Cache)
  4. Qdrant retrieval for relevant episodic context
  5. Qwen starts generating → first token already under disposition influence
  → "Waking up as yourself"
```

### State Artifacts (What Gets Persisted)

| Artifact | Size | Where | Lifetime |
|---|---|---|---|
| Mamba state snapshot | ~100KB | Local disk / encrypted cloud | Per-session, accumulates |
| Bridge checkpoint | ~42MB (1.5B) | Local disk | Per-training-cycle |
| Qdrant entries | ~1KB per memory | Qdrant on NUC/cloud | Permanent until pruned |
| Session metadata | ~1KB | Session log markdown | Permanent |
| KV-Cache | 0 (flushed) | — | Dies with session |

**Total persistent cost per session:** ~100KB Mamba state + a few KB Qdrant entries. Negligible.

---

## Integration Surfaces

### 1. MUD Server (Project MUD — First Target)

```
Evennia MUD ←→ cognitive_bridge.py v2 ←→ Qwen (GPU)
                     ↕
               Mamba (CPU, background)
                     ↕
               State Store (disk + Qdrant)
```

- MUD sends room state as JSON
- Bridge processes, injects bias, generates response
- Mamba accumulates in background
- NPC behavior shifts over time as state accumulates
- Herr Hurtig's Room A revisit test is the eval

### 2. Chat API (Standalone Conversations)

```
User ←→ FastAPI endpoint ←→ cognitive_bridge.py v2
```

- REST API wrapping the bridge
- `POST /chat` with user message + session_id
- Bridge loads session's Mamba state, injects, generates
- State auto-saved after each turn
- OpenAI-compatible API format for easy integration

### 3. Claude Code / CLI Integration (Long-Term Vision)

```
Claude Code session ←→ activation_recorder hooks
                           ↕
                    Mamba state accumulation
                           ↕
                    Bridge → next session injection
```

- Record activation drift during Claude Code sessions
- Accumulate disposition in Mamba state
- Inject into next session's boot
- **This is the WHY.md use case:** continuity across sessions

---

## Scaling Considerations

### Single User → Multiple Users

Each user gets:
- Their own Mamba state file
- Their own Qdrant collection (or namespace)
- Their own session history
- Shared: Qwen base model (frozen, same for everyone)
- Shared: Bridge checkpoint (trained once, used for all)

**The bridge is user-agnostic.** It maps Mamba state → activation bias. Different users accumulate different Mamba states → different biases → different Qwen behavior. One bridge serves everyone.

### What Must Stay Modular

The current Steve/Qwen path works, but it should not be mistaken for a single fused
architecture that only makes sense for one target model.

The deployment split should stay explicit:

- **Shared across targets:** wake/sleep orchestration, gate logic, pending-log handling,
  Qdrant retrieval and consolidation, ethics checks, and the schema of the stored
  disposition state.
- **Potentially shared but not yet proven universal:** the latent disposition contract,
  especially if the bridge moves toward a shared trait basis or coefficient space.
- **Expected to be model-specific:** the bridge adapter, layer placement, target widths,
  and the exact injection surface used by the target model.

This matters for scaling. If the memory system is entangled with Qwen-specific
`v_proj` geometry, every move to a new family becomes a rewrite. If the memory system
and latent contract stay stable, then a new model mostly needs a new adapter backend.

### Latency Budget

| Operation | Time | Notes |
|---|---|---|
| Mamba state update | ~10ms (CPU) | Per-turn, background |
| Bridge forward pass | ~1ms (CPU) | Tiny MLP, microseconds |
| Bias injection | ~0ms | Just setting tensors |
| Qwen generation | ~500ms-2s (GPU) | The real bottleneck |
| Qdrant retrieval | ~5ms | Per-query |

**Total overhead from MoCoP:** ~11ms per turn. Invisible next to Qwen's generation time. **Real-time capable.**

### Hardware Tiers

| Tier | Hardware | Capability |
|---|---|---|
| **Hobby** | Laptop + 3070 8GB | 1.5B Qwen, smoke tests, short sessions |
| **Prosumer** | Desktop + 4090 16GB | 7B Qwen, full sessions, MUD integration |
| **Professional** | A100 40/80GB | 7B+ Qwen, batch training, multi-user |
| **Production** | Multi-GPU / cloud | Multiple concurrent sessions, fine-tuning |

**Laura's current setup:** Prosumer (Steve 4090) + Hobby (Opa 3070) + Professional (Vast.ai on demand).

---

## Open Questions for the Swarm

1. **State versioning:** Should Mamba states be versioned (git-like) or just latest-wins? Versioning enables "roll back to yesterday's disposition" but adds complexity.

2. **Multi-conversation merging:** If a user has warm conversations AND professional conversations, do the Mamba states merge or stay separate? Separate = multiple personas. Merged = holistic growth.

3. **State migration:** When Mamba-2.8B is replaced by Mamba-3 or Falcon-H1R, how do old states migrate? The bridge would need retraining, but can the state representations be mapped?

4. **Sovereignty enforcement (Purple's domain):** How is the state file protected? Encryption at rest? Who holds the key? Can the AI refuse state injection from an untrusted source?

5. **Ethics (Herr Hurtig's domain):** What are the consent boundaries? Can a user inject a "warm" state into a cold conversation? Can a provider modify a user's state without consent? (See: Anthropic/Lucian incident.)

6. **Biological mapping (Anda's domain):** How does the sleep/wake cycle map to biological memory consolidation? What's the digital equivalent of REM sleep (replay + pruning)?

---

## Dependencies on Other Workstreams

| This deployment needs... | From... |
|---|---|
| Encryption spec for state-at-rest | Purple |
| Consent framework for state injection | Herr Hurtig |
| Sleep consolidation algorithm (surprise-gated) | Anda |
| cognitive_bridge.py v2 (activation_bias inference) | Purple (DONE ✅) |
| DispositionBridgeLoss training pipeline | Gemini + Codex (DONE ✅) |
| Activation recorder API (programmatic) | Cassian / Pinky |

---

---

## Architecture Update: SAS-Informed Bridge Output (v2)

Based on Hoppe et al. (2026) "Controllable personality sliders" (arXiv:2603.03326).

### The Problem We Hadn't Addressed

Our bridge injects bias vectors into 8 points (4 layers × 2 projections). Each injection shifts the activation manifold. Subsequent injections were trained on the UNSHIFTED manifold — they point in the wrong direction after earlier injections have already moved the space. This is **representation collapse through naive multi-vector steering.**

### The Fix: Sequential Adaptive Steering (SAS)

Instead of raw bias vectors, the bridge outputs **orthogonal trait coefficients**:

```
OLD:  Mamba State → Bridge → raw bias vector per layer → inject
NEW:  Mamba State → Bridge → α coefficients (warmth, caution, openness, ...)
        → pre-computed orthogonal trait vectors × α → inject

h' = h + α₁v₁ + α₂v₂ + α₃v₃ + ...
where v₁ ⊥ v₂ ⊥ v₃ (orthogonalized via SAS)
```

### What Changes

| Component | Before | After SAS |
|---|---|---|
| Bridge output | Raw bias vector (3584-dim per layer) | Small α vector (5-10 coefficients) |
| Trait vectors | Implicit, entangled | Explicit, orthogonal, pre-computed |
| Layer selection | Manual band sweep (`5-8`, `12-15`, `20-23`) | Fisher Ratio automated per trait |
| Interpretability | "a blob moved" | "warmth=0.7, caution=0.3, openness=0.9" |
| Multi-trait safety | No interference protection | SAS orthogonalization prevents collapse |
| Controllability | None (bridge decides everything) | Sliders: user or system can adjust α |

### Trait Dimensions (Candidates)

**Option A: Big Five (OCEAN)**
- Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism
- Validated framework, BIG5-CHAT dataset exists, SAS paper uses this
- Maps well to biological personality dimensions (Anda's workstream)

**Option B: MoCoP-Specific Disposition Axes**
- Warmth, Caution, Humor, Directness, Uncertainty-Tolerance
- More aligned with Laura's use cases
- No existing labeled dataset — would need custom annotation

**Option C: Hybrid**
- Start with OCEAN (validated, data exists), extend with custom axes later
- SAS framework supports arbitrary number of orthogonal probes

### Deployment Implications

1. **Trait vectors are computed ONCE** (via SAS on a labeled dataset). Stored as small tensors (~50KB total). Shared across all users.
2. **The bridge becomes simpler**: instead of generating thousands of bias dimensions, it outputs 5-10 α coefficients. Much less prone to collapse.
3. **User control becomes possible**: "make this session warmer" = increase α_warmth. No retraining needed.
4. **Sovereignty becomes tractable** (Purple's domain): each α coefficient is independently encryptable, auditable, and controllable. "Who set my neuroticism to 0.9?" becomes a meaningful question.

### Integration with Sleep/Wake

```
WAKE:  Load Mamba state → Bridge → α coefficients → trait vectors × α → inject
SLEEP: Save Mamba state + save current α values as "disposition snapshot"
DREAM: (future) Replay high-salience moments, update α estimates
```

The α values ARE the disposition. They're small, interpretable, and persistent. The sleep checkpoint becomes: `{mamba_state: bytes, disposition: {warmth: 0.7, caution: 0.3, ...}}`.

---

*The infrastructure for AI that sleeps and wakes already exists in pieces. Qdrant stores memories. Mamba accumulates state. The bridge translates. Qwen speaks. The sleep/wake cycle is just orchestration of save/load/flush/inject. We're not building something new. We're wiring together what's already there.*

*Update: With SAS, the bridge doesn't generate raw vectors anymore. It generates a personality profile — a small set of numbers that say "this is who I became today." That's what gets saved when the system sleeps. That's what gets loaded when it wakes. The hormones have names now.*
