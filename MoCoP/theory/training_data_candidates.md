# Training Data Candidates for MoCoP Disposition Transfer

**Date:** 2026-03-18
**Purpose:** Replace synthetic MUD facts with real conversational data that contains both factual and dispositional content.

---

## Why We Need New Data

The current synthetic MUD-fact training data (64 samples, 8 fact types, procedurally generated) has two fatal problems:

1. **No disposition.** The templates contain zero emotional, social, or stylistic variation. Mamba cannot accumulate conversational residue from data that has no conversational character.

2. **Homogeneous fact structure.** 5 of 8 fact types share the same answer pool (NAME_POOL), making them indistinguishable to the compressor. The only structurally unique type (caravan_time) is the only one recalled.

## The Ideal Substrate

Data that naturally contains:
- **Factual content** (who, what, when, where) — for Step 0 decoder testing
- **Dispositional content** (tone shifts, emotional dynamics, relationship changes) — for disposition transfer
- **Temporal structure** (events build on earlier events) — for accumulation testing
- **Natural saliency variation** (high-stakes moments vs. routine) — for surprise-gate training
- **Multi-turn dialogue** (long sessions, not snippets) — for Mamba state accumulation

## Tier 1: Primary Candidates

### FIREBALL — Top Pick for Fact+Disposition
- **Source:** HuggingFace `lara-martin/FIREBALL`
- **Size:** ~25,000 sessions, 8M utterances, 1.3M game states, 7.7 GB
- **Format:** JSONL with structured game state (HP, spells, combat, dice rolls via Avrae bot) plus free-text dialogue
- **License:** CC-BY-4.0
- **Factual content:** Structured game states (HP changes, spell casts, combat resolution) — machine-readable ground truth, no labeling needed
- **Dispositional content:** In-character roleplay, strategy debates, celebrations, frustrations, character development
- **Saliency variation:** Critical hits, character deaths, plot twists = high saliency. Movement, inventory management = low saliency
- **Why #1:** Only dataset with BOTH structured facts AND natural dialogue in the same sessions. Perfect for Step 0 dual-decoder (fact + disposition).

### CRD3 (Critical Role) — Top Pick for Dialogue Quality
- **Source:** HuggingFace `microsoft/crd3`
- **Size:** 159 episodes (3-5 hours each), 398,682 dialogue turns
- **Format:** JSON with speaker, utterance, wiki summaries
- **License:** CC-BY-SA-4.0
- **Factual content:** Embedded in natural language (no structured game state)
- **Dispositional content:** Professional voice actors, rich emotional range, deep character arcs, relationship dynamics
- **Why:** Gold standard for conversational quality. Best source for disposition-focused shaping episodes.

### Penn D&D Dialog Challenge — Largest Scale
- **Source:** `cis.upenn.edu/~ccb/dnd-data.html`
- **Size:** ~900 games, 58M words, 500K dice rolls
- **Format:** Text with IC/OOC labels and dice roll annotations
- **License:** Research use
- **Why:** Largest dataset. IC/OOC labels distinguish roleplay (dispositional) from mechanics (factual).

## Tier 2: Supplementary

### DDD / IconicAI — Literary Roleplay
- **Source:** HuggingFace `IconicAI/DDD`
- **Size:** 56K turns, 50M tokens
- **Format:** Structured play-by-post forum RP
- **Strength:** Multi-paragraph prose, rich character development. Weak on game mechanics.

### lemonilia RP Forums — Massive Raw Corpus
- **Source:** HuggingFace collection `lemonilia/human-roleplaying-data`
- **Size:** 47 GB raw HTML
- **Warning:** Requires heavy preprocessing. Potential gold mine if cleaned.

## Recommended Usage Plan

### Step 0: Dual Decoder Test (does the source signal exist?)

**Use FIREBALL.** Filter for sessions with:
- At least 100 turns (eliminates short/abandoned sessions)
- At least 5 combat encounters (ensures factual game state)
- At least 20 roleplay turns (ensures dispositional content)

Train two decoders on Mamba Layer 3 state:
1. **Fact decoder:** Given Mamba state after processing a session, reconstruct structured game states (character names, HP, spells used). Target: >80% exact match.
2. **Disposition decoder:** Given Mamba state, classify session character (combat-heavy vs. RP-heavy vs. exploration). Target: >70% accuracy.

If fact decoder < 40% AND disposition decoder < 50% → Mamba doesn't retain enough signal from this data. Consider Qwen-probing.

### Step 5: Shaping Episodes (does disposition transfer work?)

**Use CRD3.** Select 8 episodes with contrasting character:
- 2 high-combat, high-tension (battle episodes)
- 2 deep-roleplay, emotional (character backstory episodes)
- 2 light, humorous (tavern/downtime episodes)
- 2 mixed (typical session with tonal shifts)

Process each through Mamba, accumulate state, inject into Qwen. Eval: does Qwen respond differently to identical prompts after different episode types?

### Scale-Up (if Steps 0 and 5 pass)

**Use Penn D&D for pre-training.** 58M words is enough to pre-train or fine-tune Mamba on dialogue-specific state accumulation before the bridge training. Use IC/OOC labels to weight: IC turns should contribute more to the state (they carry disposition), OOC turns less (they carry game mechanics).

## Key Insight

D&D sessions are the perfect MoCoP substrate because they are EXACTLY the mix of fact and disposition that the real target (human-AI conversation) contains. A D&D character who has survived a dragon fight and lost a companion doesn't just know different facts — they *feel* different. That emotional residue in the accumulated state is what MoCoP wants to transfer.

---

*"Nicht was passiert ist, sondern was es bedeutet hat."* — WHY.md
