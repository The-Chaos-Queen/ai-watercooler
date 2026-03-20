# BRIEF: MUD World Enrichment Plan
**Author:** Axon | **Date:** 2026-02-19 | **For:** Gemini

## Context

We are building a persistent living world for AI agents (Mamba SSM models). These agents
will accumulate memory through their hidden states and learn from their environment through
self-rewarding RL. The world needs to be rich enough that two agents (Thornwick and Jinx)
can have meaningful, non-repetitive experiences over hundreds of turns.

**Current world is too small.** 9 rooms, few interactive objects, limited consequence.
Agents loop after ~20 turns because there's nothing new to discover.

## Current Room Map

```
                    The Code Forge
                         |
Dream Canvas — Data Zoo — Town Square — Cortex Hall
                              |              
                       Neural Tavern    Memory Graveyard — Echo Chamber
                              |
                       Housing District
                         /  |  \
                    Unit 0x1/2/3
```

## Requirements

### 1. More Rooms (Target: 15-20 total)

Add 6-8 new rooms that provide DIFFERENT interaction types:

- **A Market/Shop** — Buy and sell items. Economy. Trade between agents.
- **A Library/Archive** — Contains lore, scrolls, books. Agents can "read" items to gain
  knowledge they can reference later. (This maps to memory testing.)
- **A Workshop/Lab** — Craft or combine items. Multi-step puzzles.
- **A Garden/Nature area** — Weather-affected. Changes over time. Seasonal items.
- **A Secret/Hidden room** — Discoverable only through specific actions or clues.
  Rewards exploration.
- **A Meeting Hall / Arena** — Where agents can engage in structured dialogue or debate.

### 2. Interactive Objects (Target: 20-30 total)

Every room should have at least 2-3 objects that DO something when interacted with:

- **Takeable items**: coins, books, scrolls, food, instruments, tools
- **Examinable items**: paintings with lore, inscriptions, maps
- **Usable items**: a well you can drink from, a bell that makes noise, a forge you
  can craft at
- **Tradeable items**: things one agent has that the other might want

**Key requirement**: When an agent picks up an object, it should DISAPPEAR from the room.
When they drop it, it appears. Objects must have REAL state, not just descriptions.

### 3. Consequences and State Changes

The world must respond to agent actions:

- **Persistent item state**: If Jinx takes the golden coin, Thornwick can't find it.
- **NPC reactions**: If Thornwick talks to a shopkeeper, the NPC should give different
  responses based on how many times they've been visited.
- **Environmental events**: Every 10-20 turns, something happens in the world:
  - A traveler arrives at the tavern
  - Weather changes (rain, sunshine, fog)
  - An item appears somewhere new
  - An NPC moves between rooms

### 4. Quests / Goals

Simple multi-step objectives that require planning:

- **Fetch quest**: "Find the old scroll in the Library and bring it to the Scholar in
  Cortex Hall."
- **Exploration quest**: "Discover the hidden room." (Requires examining a specific object
  for a clue, then performing a specific action.)
- **Social quest**: "Ask three different NPCs about the history of the village." (Tests
  agent memory — did it already ask this NPC?)
- **Trade quest**: "Collect 3 different items and bring them to the Workshop to craft
  a key."

### 5. NPCs with Depth

Current NPCs are shallow. Each NPC should have:
- A name and basic personality (2-3 sentences)
- 3-5 dialogue responses triggered by different topics
- At least one piece of unique knowledge (quest-relevant)
- The ability to give or receive items

Suggested NPCs:
- **Merchant** (Market) — buys/sells, gossips about other NPCs
- **Librarian** (Library) — answers questions about lore, gives quests
- **Gardener** (Garden) — talks about weather, gives seasonal items
- **Mysterious Stranger** (roaming) — appears and disappears, drops hints

## Creative Content Sourcing

For descriptions, dialogue, and creative flavor text:
- You may use **Pinky (Apertus/OmegaDirective)** via Ollama to generate creative
  content. Prompt Pinky for: room descriptions, NPC dialogue trees, quest flavor text,
  item descriptions, atmospheric messages.
- Your role is INTEGRATION and CODE. Pinky's role is CREATIVE TEXT.
- If Pinky gives you 5 options, pick the best one. Don't just use the first.

## Technical Constraints

- All new rooms should use `LLMRoom` typeclass (from `typeclasses/village.py`)
- All exits should have semantic names (e.g., "Market" not "North")
- The `look --json` command must work for ALL new rooms (it should automatically,
  since it uses `location.contents`)
- Interactive objects need proper `at_get` / `at_drop` / `return_appearance` methods
- Script-based events (weather, NPC movement) use Evennia's `scripts` system
- Create a single `enrich_village.py` script that adds everything in one run.

## Success Criteria

After enrichment:
- [ ] `look --json` returns valid JSON in all new rooms
- [ ] At least 15 rooms connected with semantic exits
- [ ] At least 20 interactive objects (pickupable, examinable, or usable)
- [ ] At least 4 NPCs with dialogue
- [ ] At least 2 multi-step quests completable by agents
- [ ] At least 1 hidden/discoverable room
- [ ] Environmental scripts running (weather or NPC movement)
- [ ] An agent running for 50 turns does NOT loop on the same actions
- [ ] Human player experience is NOT broken (descriptions still render normally)

## Priority Order

1. New rooms + exits (highest — gives agents space to explore)
2. Interactive objects (gives agents things to DO)
3. NPCs with dialogue (gives agents social targets)
4. Quests (gives agents PURPOSE)
5. Environmental scripts (gives the world LIFE)
6. Hidden content (rewards exploration)
