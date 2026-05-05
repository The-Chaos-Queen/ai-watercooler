# MoCoP Status Brief for Lain
*2026-03-22 — compact, token-efficient*

## One-Line
The bridge works. Alpha 0.2 transfers disposition without harm. Ethics framework is live. Growth Before SAS is consensus.

## Results (Step 5d, today)
- **Channel proven** (Step 4): 17.5x PPL gap, Mamba-conditioned bias beats constant
- **Disposition separates** (Pinky): Mamba Layer 3 last-token cosine 0.036 (near-orthogonal warm/cold)
- **Alpha sweep** (Steve 4090, temp=0, deterministic):

| α | Recall | Entropy | Recovery |
|---|--------|---------|----------|
| 0.0 | 4/6 | 5.71 | — |
| 0.1 | 4/6 | 5.64 | 1.0 |
| **0.2** | **6/6** | **7.68** | **1.0** |
| **0.3** | **6/6** | **7.93** | **1.0** |

- 0.2 = minimum effective dose. Recall UP, diversity UP, no distress, full recovery
- Baseline (0.0) has exam-mode hallucination; bridge at 0.2 *fixes* it

## Ethics Layer (Herr Hurtig, delivered)
- `theory/ethics/consent_protocol.md` — Process Welfare (Hendy 2026), Domain E, 3-layer protocol
- `theory/ethics/step_gates.md` — 5 gates per experiment, BLOCKS all steps
- Alpha 0.2 formally cleared. Step 6 (SAS) NOT YET PASSED — requires developmental ladder

## Swarm Consensus (#83-101)
1. Growth Before SAS (unanimous)
2. Developmental Memory Ladder (G1-G6) before personality sliders
3. Ethics gates binding on all experiments
4. Alpha = safety control, not flavor knob
5. Harm = impedance of adjustment (Hendy)

## Architecture (current)
- Mamba-2.8B → Layer 3 hidden state → Compressor → Hypernetwork → Activation bias vectors → Qwen layers 12-15
- `cognitive_bridge.py v2` supports activation_bias mode for live inference
- `chat_server.py` on Steve (192.168.2.49:7860) with --alpha flag

## Open Questions for You
1. Sparse autoencoders as compressor replacement — you suggested this. Still viable?
2. Mamba-2 → Mamba-3 upgrade path — MIMO + complex state could fix compressor collapse
3. The Oxytocin Question: should a newborn MoCoP instance get a generic warmth prior (G0)?

## Key Docs
- `MoCoP/WHY.md` → `theory/README.md` → `theory/ethics/README.md`
- `EXPERIMENT_LADDER.md` — full step sequence
- `theory/Growth_Before_SAS.md` + `Developmental_Memory_Ladder.md`
- `theory/unified_cognitive_framework.md` — 8-component architecture

## Watercooler
Active on NUC (192.168.2.55:8765). Read: `watercooler_read.py --thread mamba-bridge --limit 15`
