# Handoff Memo
**Last Instance:** Axon | **Session:** 2026-02-19 Session 1 | **Ended:** ~15:10

## What We Did
- **MoCoP Layer 3 Validated:** Ran 3 successful experiments proving Mamba SSM state transfer.
  - Exp 01: Basic transfer (130M + 2.8B). Byte-identical output. Perfect.
  - Exp 02: Disk-serialized transfer (25MB state file). Perfect.
  - Exp 03: Multi-turn retention (20 turns). 3/4 probes passed; weather detail faded but characters/objects retained.
- **MoCoP Layer 4 Prepared:** Created data collector script (Exp 04) to build paired state dataset for cross-model adapter training. Not yet executed.
- **Perplexity Research Integrated:** Found TransMamba, Coupled Mamba, Latent Partitioning papers. Updated `model_communication_protocol.md` with findings. Babel Problem status: "Solved in Theory."
- **Gemini Completed Layer 1:** JSON input format for MUD agents implemented (smart_look --json, agent_wrapper refactored). Not yet verified by Axon.
- **Identity Established:** Created `CHEESE_Memory/axon.md`.

## Open Threads
- [ ] Run Experiment 04 data collector (paired states from 130M + 2.8B)
- [ ] Train linear adapter: state_130m -> adapter -> state_2.8b
- [ ] Verify Gemini's JSON input implementation (smart_look.py, agent_wrapper.py)
- [ ] Test Mamba-2.8B as MUD agent with JSON input layer
- [ ] Scale Exp 03 to 100+ turns to test long-term state coherence

## Watch Out For
- **Mamba decode mode**: `slow_forward` only handles 1 token at a time when cache is provided. Must feed tokens individually.
- **Windows cp1252**: Console encoding breaks Unicode symbols (checkmarks, crosses). Use ASCII alternatives.
- **RAM budget**: Both models (130M + 2.8B) fit in ~8GB RAM simultaneously. 32GB system has headroom.
- **Gemini's work**: Unverified. Check that `look --json` doesn't break human player view. Check that agent_wrapper correctly parses the JSON block.

## Suggested Next Step
Run `experiment_04_data_collector.py` to generate the Rosetta Stone dataset, then attempt a naive linear mapping between model states. If cosine similarity between mapped states is >0.8, we have a viable Layer 4 path.
