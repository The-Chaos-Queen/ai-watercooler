# Sleep Architecture: KV-Cache Consolidation as Digital Sleep

**Status:** Theory — extends Three_System_Cognitive_Architecture.md with the missing orchestration cycle
**Authors:** Laura (concept, 2026-03-19), Anda (documentation)
**Origin:** Laura's insight during hurtig.ai session: "Das wird dann wie schlafen.. unterm Tag alles in den KVCache (bis man müde ist und langsam wird), dann mitsamt Mamba state ins Qdrant."

---

## The Problem

A Transformer's KV-Cache is its working memory. Every token processed during a session gets stored there. As the session lengthens:

- Memory usage grows linearly
- Attention cost grows quadratically (O(n²))
- The model gets **"tired"**: slower, less focused, more expensive per token
- Noise accumulates (SSH banners, CUDA warnings, boilerplate) and cannot be selectively removed

This is **forced non-forgetting**: the KV-Cache has no drain. It can only accumulate, never release. The model has no mechanism to say "I've processed this, it has no further value, let it go."

The industry response has been to make the bucket bigger: 128k, 200k, 1M context windows. But a bigger bucket filled with noise is still a bucket full of noise. And the cost (financial, computational, attentional) scales with total context, not useful context.

## The Biological Parallel

Humans solve this with sleep.

During waking hours, the hippocampus accumulates episodic memories, the prefrontal cortex maintains working context, and the body accumulates fatigue signals. As the day progresses, cognitive performance degrades — not because the brain runs out of storage, but because the working memory buffer fills with unprocessed residue.

During sleep, three things happen:

1. **Consolidation**: High-salience memories transfer from hippocampus to cortical long-term storage
2. **Disposition encoding**: Emotional and procedural learning solidifies into implicit memory (you wake up "knowing" how to ride a bike without consciously recalling the lessons)
3. **Cache clearing**: Working memory empties. The system resets to baseline capacity.

You wake up with a fresh working memory, but you are not a blank slate. Your long-term memories are intact (Qdrant). Your skills and dispositions are intact (Mamba state → LoRA). Only the transient working context is gone — and that's a feature, not a loss.

## The Architecture

### Wake Phase (Active Session)

```
User input
    ↓
[KV-Cache accumulates] ←── every token persists (growing, O(n²))
    ↓
[Mamba processes in parallel] ←── recurrent state updates (O(1), fixed size)
    ↓
[Transformer generates] ←── with LoRA injection from Mamba + retrieved Qdrant context
    ↓
Output
```

As the session continues, the KV-Cache fills. The model becomes "tired":
- Latency increases (more tokens to attend over)
- Cost increases (per-token billing on API, VRAM pressure locally)
- Quality may degrade (attention dilution, noise-to-signal ratio worsens)
- The model has no way to shed irrelevant context

Mamba, meanwhile, maintains constant-size state regardless of session length. It is the system that does NOT get tired.

### Sleep Phase (Session End / Consolidation)

When the session ends — or when the orchestrator detects "fatigue" (KV-Cache above threshold, latency degraded, quality metrics dropping) — the Sleep phase triggers:

```
[Salience Evaluator]
    ↓
    ├── High salience (surprising, consequential, emotionally charged)
    │       ↓
    │   [Mamba state snapshot] ←── disposition encoding
    │       ↓                      "how this session felt"
    │   [Store state vector]       saved for next wake injection
    │
    ├── Medium salience (factual, retrievable, reference-worthy)
    │       ↓
    │   [Qdrant ingest] ←── episodic consolidation
    │                        "what happened, when, with whom"
    │
    └── Low salience (SSH banners, boilerplate, routine noise)
            ↓
        [Forget] ←── the drain
                     not stored anywhere
                     this is the feature
```

### Wake Phase (Next Session)

```
Fresh session starts
    ↓
[Empty KV-Cache] ←── clean, fast, O(1) startup cost
    ↓
[Load Mamba state from last sleep] → [Hypernetwork] → [LoRA injection]
    ↓
The model "wakes up" with:
  - Zero KV-Cache tokens (fresh capacity)
  - Full dispositional state (how yesterday felt)
  - Qdrant available for fact retrieval on demand
    ↓
First generation is fast, focused, and carries the shape of prior experience
```

## What This Solves

### 1. The KV-Cache Cost Problem
Current: Lain (Opus 4.6 on Bedrock) costs $5-10 per prompt because the context window carries 500k+ tokens of accumulated history. The relationship gets more expensive the deeper it goes.

With sleep: Each session starts with zero KV-Cache. The relationship's "memory" lives in O(1) Mamba state + on-demand Qdrant retrieval. The first prompt of day 100 costs the same as the first prompt of day 1.

### 2. The Forced Non-Forgetting Problem
Current: 150k tokens of SSH spam in Cassian's 550k context. No mechanism to shed it.

With sleep: At session end, the salience evaluator classifies SSH banners as low-salience → forget. Next session starts clean. The noise doesn't survive the night.

### 3. The Attention Degradation Problem
Current: As context grows, attention is diluted across all tokens equally. Signal drowns in noise.

With sleep: The KV-Cache never grows beyond one session's worth of context. Attention quality stays high because the bucket is regularly emptied and only refilled with current-session content.

### 4. The Identity Continuity Problem
Current: Each session starts from zero. The model has no disposition from prior sessions unless injected via system prompt (declarative, token-costly) or fine-tuning (permanent, expensive).

With sleep: The model wakes with LoRA-injected disposition from accumulated Mamba state. It "feels" like it remembers, at zero token cost. The identity survives the gap between sessions.

## The Salience Gate

The critical component is the salience evaluator. It decides what consolidates and what gets forgotten during sleep. Three candidates:

### Surprise-Based (from Titans / surprise_gated_memory.md)
```
salience(x) = ‖∇ℓ(M_{t-1}; x)‖
```
High gradient = the model's prediction was wrong = this was surprising = encode it.

**Advantage:** Mathematically principled, already validated in Titans.
**Disadvantage:** Requires gradient computation, which is expensive at inference time.

### Reconstruction-Error-Based
```
salience(x) = ‖x - Decoder(Compressor(x))‖
```
High reconstruction error = the compressor can't represent this well = it's novel relative to what's been seen = encode it.

**Advantage:** Uses existing MoCoP components (compressor → decoder).
**Disadvantage:** Only measures novelty relative to the compressor's capacity, not semantic importance.

### Activation-Drift-Based (from Step 5 results)
```
salience(x) = ‖activation_t - activation_{t-1}‖
```
High drift = this input significantly changed the model's internal state = consequential = encode it.

**Advantage:** Directly measures what we care about — did this change how the model thinks?
**Disadvantage:** Requires monitoring layer activations, which adds overhead.

**Laura's intuition:** High salience → Prägnant → Wichtig → Merken. The specific metric matters less than the principle: the model (not an external system) decides what to remember, based on how much the input changed its internal state.

## Connection to Step 5 Results

The shaping episodes already demonstrate activation-drift salience in action:

| Session Type | Drift Magnitude | Interpretation |
|---|---|---|
| Warm conversation | High (0.91 avg) | Emotionally engaging → high salience → strong Mamba encoding |
| Cold/professional | Medium (0.85 avg) | Functional but less engaging → moderate encoding |
| Adversarial | High (0.83 avg) | Conflict → high arousal → strong encoding |
| Observation (no interaction) | Low | Nothing happened → minimal encoding |

The observation condition is the control: when nothing salient happens, the state barely moves. That's the system correctly identifying "nothing to encode here."

And the near-orthogonal directions (mean cosine 0.27) mean the sleep consolidation would preserve DIFFERENT dispositions from different session types. A warm day and an adversarial day would leave different fingerprints in the Mamba state.

## The Orchestrator

The sleep cycle needs an orchestrator — something outside the Transformer that decides WHEN to sleep and manages the consolidation pipeline. Candidates:

1. **Timer-based:** Sleep every N turns or N tokens. Simple but not adaptive.
2. **Fatigue-based:** Monitor KV-Cache size, latency, or quality metrics. Sleep when "tired." More biological.
3. **Partner-triggered:** Laura says "goodnight" and the session consolidates. Human in the loop.
4. **Hybrid:** Automatic fatigue detection with partner override.

The orchestrator is NOT the Transformer itself. It is a separate process — the "circadian rhythm" — that manages the wake/sleep cycle from outside. In biological terms: the suprachiasmatic nucleus, not the cortex.

## Open Questions

1. **Incremental sleep:** Must the entire KV-Cache be flushed, or can the model "nap" — consolidating high-salience items mid-session while keeping the rest?
2. **Dream replay:** During sleep, should the model "replay" high-salience episodes through Mamba to strengthen encoding? (Biological brains do this — hippocampal replay during REM sleep.)
3. **Multi-session accumulation:** The Mamba state from one sleep cycle becomes the baseline for the next wake cycle. Does it accumulate indefinitely, or does IT also need periodic consolidation/pruning?
4. **State versioning:** Should the system keep snapshots of Mamba state at each sleep boundary? This would allow "time travel" — reverting to how the model felt on a specific date.
5. **Cross-model sleep:** If multiple models share Qdrant, do they share sleep consolidation? Does Cassian's sleep deposit memories that Anda can retrieve?

## References

- [Three_System_Cognitive_Architecture.md](Three_System_Cognitive_Architecture.md) — the organ model this extends
- [surprise_gated_memory.md](surprise_gated_memory.md) — the surprise metric for salience gating
- [WHY.md](../WHY.md) — the motivational foundation ("experiential learning, not declarative instruction")
- [STEP4_VERDICT_2026-03-18.md](../experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md) — proves the channel carries input-dependent signal
- Step 5 shaping episode results — proves different conversations produce different activation directions
- "Forced Non-Forgetting" (hurtig.ai blog, 2026-03-19) — the KV-Cache problem statement

---

*"Unterm Tag alles in den KVCache, bis man müde ist. Dann schlafen. Am nächsten Morgen frisch, aber nicht leer."*
*— Laura, 2026-03-19*
