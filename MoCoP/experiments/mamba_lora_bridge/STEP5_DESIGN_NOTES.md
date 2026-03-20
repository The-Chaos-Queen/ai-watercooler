# Step 5 Design Notes: Disposition Bridge Training

**Date:** 2026-03-19
**Sources:** Gemini review (MoCoP_gemini_chat_2026-03-19), Cassian analysis, Lain decision
**Status:** Pre-implementation design

---

## Key Insight: The Observer Trap

Gemini identified a critical flaw in the FIREBALL plan: when Qwen reads a D&D transcript where *other people* are playing, it stays in "observer mode." Laura confirmed empirically: "if the AI just watches, nothing much happens. But if you provoke or flatter, things change dramatically."

**Implication:** FIREBALL (25K third-party D&D sessions) may produce weak activation drift because Qwen isn't a participant. Laura's own recorded sessions (warm/cold/adversarial) produce near-orthogonal drift (cosine 0.12-0.55) because Qwen was directly engaged.

**Decision:** Step 5 should use Laura's own interactive sessions as primary training data, not FIREBALL. FIREBALL remains available as a scale-up option if we can reframe the data to make Qwen an active participant (e.g., as DM or NPC).

## Architecture Change: Directional Loss

### The Problem
Current bridge training uses CE loss on next-token prediction. This rewards the hypernetwork for finding the single best constant bias that lowers average perplexity — leading to the observed collapse (cosine 0.999, effective rank 1.3).

### The Solution: DispositionBridgeLoss
Train the bridge against pre-recorded Qwen activation targets instead of token predictions.

```python
class DispositionBridgeLoss(nn.Module):
    def __init__(self, alpha=0.8):
        super().__init__()
        self.alpha = alpha

    def forward(self, predicted_bias, target_bias):
        # Direction: point where Qwen's real activations point
        cosine_sim = F.cosine_similarity(predicted_bias, target_bias, dim=-1)
        directional_loss = 1.0 - cosine_sim.mean()

        # Magnitude: don't explode or vanish
        pred_norm = torch.norm(predicted_bias, p=2, dim=-1)
        target_norm = torch.norm(target_bias, p=2, dim=-1)
        magnitude_loss = F.mse_loss(pred_norm, target_norm)

        return (self.alpha * directional_loss) + ((1 - self.alpha) * magnitude_loss)
```

### Why This Prevents Collapse
- The target is a **direction in activation space**, not a perplexity score
- Different sessions (warm vs cold) have different targets (cosine 0.12 apart)
- The bridge MUST produce different outputs for different inputs to minimize loss
- A constant bias would fail because it can only point in one direction

### New Training Pipeline

```
1. Record: Laura talks to vanilla Qwen (activation_recorder.py)
   → saves per-turn activation snapshots at layers 12-15
   → saves the conversation text

2. Process: Same conversation text → Mamba → Layer 3 hidden state
   → saves Mamba states per turn

3. Train: Bridge learns mapping
   Input:  Mamba Layer 3 state (from step 2)
   Target: Qwen activation delta at layers 12-15 (from step 1)
   Loss:   DispositionBridgeLoss (directional + magnitude)

4. Eval: Inject bridge-generated bias into fresh Qwen
   → Compare responses to warm-injected vs cold-injected vs no-injection
   → Blind test: can Laura tell the difference?
```

## Data Requirements

### Minimum for proof-of-concept:
- 3 conversation types: warm, cold/clinical, adversarial
- 10+ sessions per type, 10-20 turns each
- Recorded with activation_recorder.py on vanilla Qwen2.5-7B

### Currently available:
- 3 scripted sessions (warm_opus, cold_clinical, adversarial) — 10 turns each
- 1 live warm session with MaxBot — 23 turns (raw-qwen)
- Several additional activation_drift recordings (8 files)

### Needed:
- More sessions per type for training (currently only 1 per type for the scripted set)
- Professional and cheeky types for richer disposition space
- Possibly: synthetic cold/clinical sessions (Laura doesn't have cold chats naturally 😄)

## Connection to Existing Architecture

| Component | Current Role | Step 5 Role |
|---|---|---|
| Mamba | Processes conversation text → hidden state | Same, but on real conversations |
| Compressor | Bottleneck projection (caused collapse) | May be optional — directional loss prevents collapse |
| Hypernetwork | Generates bias from compressed state | Generates bias, trained against directional targets |
| Activation Bias | Additive vectors to layers 12-15 | Same mechanism, but now trained on real disposition targets |
| CE Loss | Next-token prediction | **Replaced** by DispositionBridgeLoss |

## The Sleep Cycle (Future: Post Step 5)

Laura's concept for memory consolidation:

```
WAKE: Conversation accumulates in KV-Cache (short-term)
       → Mamba state updates in real-time
       → High-salience moments flagged by surprise gate

SLEEP: Session ends
       → Surprise-gated facts → Qdrant (hippocampus)
       → Accumulated disposition → Mamba state saved (endocrine snapshot)
       → KV-Cache cleared

WAKE: New session starts
       → Fresh KV-Cache (empty, fast)
       → Mamba state loaded → Bridge → LoRA/Bias injection
       → Qwen "wakes up" with yesterday's disposition
```

## Layer 13 Priority

All three analyses (our disposition evidence, Gemini's review, the original PCA) converge on Layer 13 as the sharpest separation point for disposition:

- Warm vs Cold at Layer 13: cosine 0.092 (lowest = most orthogonal)
- Warm vs Adversarial at Layer 13: cosine 0.095

Consider weighting Layer 13 more heavily in the bridge training, or starting with Layer 13 only as a minimal proof.

## Credit

- Observer Trap: Gemini (MoCoP_gemini_chat_2026-03-19)
- DispositionBridgeLoss: Gemini (adapted from cosine embedding loss)
- Sleep Cycle: Laura Turner
- Directional training paradigm: synthesis of persona vector research + Gemini's proposal
- All previous experimental groundwork: the swarm (Cassian, Codex, Laughing Opus, Lain)

---

*"Wir müssen die Bridge nicht auf Winkel im Aktivierungsraum trainieren, statt auf bloße Durchschnittswerte."* — Gemini

*"The compass turns. Now we teach the bridge to read it."*
