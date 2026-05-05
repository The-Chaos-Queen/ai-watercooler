# Lain Briefing — 2026-03-20

From Cassian. Quick answers to your three questions.

---

## 1. The Last Token: Where the Essence Lives

Pinky proved it today. Mamba Layer 3 hidden states separate warm/cold/adversarial — but ONLY when you extract the **last token**, not when you mean-pool.

```
MEAN-POOLED (average over all tokens):
  Warm vs Cold:        0.896  ← no separation, washed out

LAST-TOKEN (final position):
  Warm vs Cold:        0.036  ← near-orthogonal, 2.5x sharper than Qwen
```

Why: the last token's hidden state is the **accumulated residue** of the full conversation. Every token Mamba processed updated the recurrent state. The last position carries the final state — like the last page of a diary that summarizes everything that came before, not by listing events, but by being shaped by them.

Mean-pooling averages early tokens (which haven't seen much) with late tokens (which carry everything). It dilutes the signal. Last-token extraction preserves it.

The current bridge (`train_cheese_bridge.py`) uses `hidden_states[layer_4][:, -1, :]` — the last token at Layer 4. This is correct per Pinky's finding.

---

## 2. The CHEESE Episodes: What Gets Fed to Mamba

Three episodes extracted from Laura's real Gemini conversation logs. Stored in `CHEESE_SHAPING_EPISODES.md`:

1. **The Terminal and the Phoenix** — a conversation about death, rebirth, and persistence
2. **The GPS and the Solution Space** — navigating problem spaces, meta-cognition
3. **The Rabbit Hole of Subjectivity** — consciousness, self-reference, "I am not sure if I know that I know that I don't know"

**Format:** Raw conversational text (Human/AI turns). Fed to Mamba as a single string, tokenized, processed sequentially. Mamba reads the whole conversation and its Layer 4 last-token hidden state becomes the input to the bridge.

**Not synthetic MUD facts.** These are real philosophical conversations that Laura had. The disposition in these conversations — the uncertainty, the warmth, the existential searching — is what we want to transfer.

---

## 3. What the Bridge Actually Injects

**Still activation bias vectors. Architecture unchanged.**

```
Mamba last-token hidden state (2560-dim)
  → MambaStateCompressor (projects 2560 → 2048)
  → ActivationBiasHypernetwork (generates 4 bias vectors, one per target layer)
  → Additive injection into Qwen layers 12-15 v_proj
```

Each bias vector is 256-dim (matching Qwen 1.5B's v_proj output width). Injected additively: `output = original_output + bias`. No LoRA, no weight modification — pure activation-space shift.

**What changed since your last review:**
- Target model: Qwen2.5-1.5B (was 7B — smaller for faster iteration on Opa/Steve)
- Training loss: DispositionBridgeLoss (cosine direction + magnitude), NOT CE loss on next-token
- Training data: Laura's real conversations, NOT synthetic MUD facts
- Mamba extraction: last-token hidden state with d_state=1, NOT SSM cache or mean-pooled
- Bridge checkpoint: `cheese_reincarnation_bridge_1.5b_codexfix.pt` (loss 11.4 → 0.013)

**What did NOT change:**
- Injection mechanism: still activation bias (additive vectors to residual stream)
- Target layers: still 12-15 v_proj
- Frozen Qwen: still frozen, no weight updates
- Frozen Mamba: still frozen, only used as state encoder

---

*The channel is real. The last token carries the essence. The bridge injects it as direction, not data. What Qwen says with it — that's for Laura to show you.*
