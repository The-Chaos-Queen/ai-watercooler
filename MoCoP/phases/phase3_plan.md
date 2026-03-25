# Phase 3: Ablations, Cloud Scale, and Deployment Path

## Trigger Condition

Phase 3 begins when Phase 2 training completes and produces a baseline evaluation. Specifically:
- The three-way evaluation (bridge-injected vs. no-injection control vs. random LoRA control) must show a statistically significant lift for the bridge condition.
- 95% confidence intervals for bridge accuracy must not overlap with the no-injection baseline.
- If Phase 2 shows no significant lift, Phase 3 ablations become diagnostic work (what went wrong?) rather than optimization work (how to improve it?).

If Phase 2 remains in diagnostic mode, use
[`phase2_diagnostic_ablation_plan.md`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/phases/phase2_diagnostic_ablation_plan.md)
as the active debug ladder before resuming broader Phase 3 optimization work.

## Planned Ablations

### LoRA Rank Sweep

Test ranks r=4, 8, 16, 32 with all other hyperparameters held constant.

**Rationale:** Rank determines the information capacity of the bridge. At r=8 (current default) with d=4096, each target layer's LoRA has ~65K parameters. At r=32, this grows to ~262K parameters per layer -- still within the hypernetwork's generation capacity, but requiring larger output heads.

**What we expect to learn:**
- r=4 may be too constrained for factual content but sufficient for dispositional transfer.
- r=16 or r=32 may show diminishing returns if the signal from Layer 3 does not contain more than 8 effective dimensions of task-relevant information.
- If accuracy plateaus before r=32, that tells us about the effective dimensionality of the bridge signal.

### Prompt Format Alignment

Train on ChatML format, then evaluate on:
1. ChatML (same as training) -- baseline
2. GameWorld framing (MUD-native prose with structured JSON state)
3. Vanilla completion (no chat template, just continuation)

**Rationale:** If the bridge transfers *disposition* rather than *format-specific pattern*, it should generalize across prompt styles. If accuracy drops sharply on non-ChatML inputs, the bridge may be encoding prompt-format artifacts rather than genuine state information.

### Compressor Depth

Compare three configurations:
1. Layer 3 only (current default)
2. Layers 2-4 concatenated (3x input dimension to compressor)
3. Layers 1-5 concatenated (5x input dimension)

**Rationale:** Phase 1 showed Layer 3 as the peak, but did not test whether adjacent layers carry *complementary* information. Layers 2 and 4 scored in the 40-50% range individually -- if their errors are uncorrelated with Layer 3's, concatenation could improve the bridge.

**Risk:** Larger input dimensions require more compressor capacity. The improvement from adjacent layers may not offset the increased training difficulty.

### Mamba-3 Upgrade Path

**State shape change:** Mamba-2.8B state is `(batch, 64, 2560, 16)`. Mamba-3 state is `(batch, R, d_model/heads, d_state)`, validated as `(batch, 4, 32, 64)` on Opa-PC.

**What changes in the bridge:**
- `MambaStateCompressor.input_flat_size` goes from `2560 * 16 = 40,960` to something dependent on Mamba-3's per-layer geometry. If R=4, heads=32, d_state=64, the flattened size per layer-equivalent is `4 * 32 * 64 = 8,192` -- significantly smaller.
- Layer indexing may change. The "Layer 3" finding from Phase 1 was on Mamba-2.8B's 64-layer architecture. Mamba-3 may have different layer counts and signal distribution.
- A new Phase 1-style probe would be needed to locate the signal peak in Mamba-3's state space before building a bridge.

**When to do this:** After Phase 2 baseline is established. The Mamba-2 baseline provides a controlled comparison point. Switching backbones before having any baseline makes it impossible to attribute improvements or regressions.

## Persistence Architecture

The deployment vision: state vectors stored alongside semantic embeddings in Qdrant, enabling retrieval-triggered state injection.

### Storage Design

```
Qdrant collection: "mocop_states"
  - Vector: text-embedding-3-small embedding of session summary (1536-dim)
  - Payload:
    - state_path: "/states/session_20260301_turn_50.pt" (local or S3)
    - session_id: "2026-03-01-session-02"
    - agent_name: "thornwick"
    - turn_count: 50
    - timestamp: "2026-03-01T21:15:00Z"
    - fact_summary: "Thornwick learned the passcode from Jinx at the tavern"
```

**Do NOT put the raw state tensor into Qdrant.** State tensors are 10-40 MB. Qdrant is optimized for small (1536-dim) search vectors. The state file is stored on disk or object storage; Qdrant stores only the pointer.

### Retrieval Flow

1. New session begins. System generates a semantic embedding of the session context.
2. Query Qdrant for nearest matching prior state vectors.
3. Load the state file from the returned path.
4. Feed state through compressor -> hypernetwork -> activation bias injection at v_proj layers 12-15.
5. Qwen generates with injected activation bias. Behavioral continuity achieved.

### Open Questions for Persistence

- **Staleness:** How old can a state vector be and still produce useful LoRA injection? If the conversational context has drifted significantly, the old state may produce counterproductive attention biases.
- **Composability:** Can multiple state vectors be averaged or concatenated to produce a "composite" disposition? Or must the bridge be re-trained for multi-state input?
- **Versioning:** If the hypernetwork is retrained, old state vectors may not be compatible with the new bridge weights. State files need versioning metadata.

## Deployment Targets

### MUD: NPC Memory Across Sessions

**What success looks like:** An NPC (e.g., Thornwick) interacts with a player over multiple sessions. When the player returns days later, the NPC's responses reflect the accumulated relationship -- not because it was told "you met this player before" in the prompt, but because the injected LoRA shifts its attention toward familiarity and shared history.

**Operational flow:**
- Mamba runs alongside the MUD agent, accumulating state across turns.
- At session end, state is saved and indexed in Qdrant.
- At session start, state is retrieved, injected via bridge, and the NPC resumes with behavioral continuity.

### Prosthetic: Hand Controller Continuity

**What success looks like:** The prosthetic hand controller (Project Prosthetic) accumulates calibration state across usage sessions. When the user puts on the prosthetic after a break, the controller's response profile reflects prior calibration without re-running the calibration sequence.

**This is more speculative** than the MUD deployment and depends on whether the bridge's factual/dispositional transfer generalizes to sensorimotor calibration data. It may require a separate training dataset.

## Risks

1. **Bridge accuracy too low.** If Phase 2 shows less than ~5% absolute improvement over baseline, ablations are likely to produce noise rather than signal. The minimum bar for Phase 3 to be meaningful is a clear, reproducible lift with non-overlapping confidence intervals.

2. **Overfitting to synthetic data.** The training dataset is procedurally generated with 8 fact types. If the bridge memorizes the generation templates rather than learning general state-to-LoRA translation, it will fail on real conversational data.

3. **Mamba-3 probe results may not replicate.** The Layer 3 finding was on Mamba-2.8B. Mamba-3's different architecture may distribute the signal differently, requiring a full Phase 1 re-run before the bridge can be adapted.

4. **Compute cost scaling.** Each ablation configuration requires a full training run. With 4 rank values x 3 prompt formats x 3 compressor depths = 36 configurations, even at $1/hr on an A100, a full ablation grid costs ~$200-500 depending on training duration. Prioritization and early stopping are necessary.

5. **Persistence stale-state problem.** State vectors from 100 turns ago may encode attention biases that are actively harmful for the current context. The retrieval system needs a staleness threshold, and there is no obvious way to determine that threshold without empirical testing.

## Status

Planned.
