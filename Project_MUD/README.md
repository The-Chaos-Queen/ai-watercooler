# Project MUD: LLM Agents in a Text World

> "Operation erfolgreich, Patient tot." — The Wunderland School of Game Design

## Vision

A locally-hosted MUD (Multi-User Dungeon) where multiple LLM agents live, explore,
quest, and interact with each other and with Laura. Pure text interface eliminates
the spatial reasoning limitations that plague LLM-game integrations.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Evennia MUD Server                │
│         (Python, telnet:4000, web:4001)     │
│                                             │
│  Tutorial World → Custom Rooms → Quests     │
├─────────────────────────────────────────────┤
│ Connections:                                │
│   ├── telnet → Agent 1 (Explorer/Ranger)    │
│   ├── telnet → Agent 2 (Bard/Storyteller)   │
│   ├── telnet → Agent 3 (Merchant/Crafter)   │
│   └── web    → Laura (observing, playing)   │
└─────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼────┐  ┌─────▼────┐
    │ Ollama  │   │ Ollama   │  │ LMStudio │
    │ Qwen3:8b│   │ Qwen3:8b │  │ Pinky    │
    └─────────┘   └──────────┘  └──────────┘

Each agent has:
  - System prompt (personality, goals, quirks)
  - Scratchpad (persistent notes, maps, inventory tracking)
  - Rolling context (last N interactions)
  - Command parser (MUD output → structured → LLM → MUD command)
```

## Agent Design

### Scratchpad System
Each agent maintains a local markdown file as persistent memory:
- **Map**: Room connections they've discovered ("Tavern → north → Town Square")
- **Inventory notes**: What they carry, what they want
- **Quest log**: Active tasks, clues found
- **People met**: Other agents/NPCs and impressions
- **Danger zones**: Where they died or got hurt

The scratchpad is injected into the LLM prompt on each turn, giving agents
genuine persistent memory across their session.

### Agent Personas (Initial Cast)

1. **Thornwick** (Cautious Explorer)
   - Model: Qwen3:8b via Ollama
   - Goal: Map the entire world, document everything
   - Personality: Methodical, writes detailed notes, avoids unnecessary combat
   - Quirk: Numbers every room discovery in their scratchpad

2. **Jinx** (Chaotic Bard)
   - Model: Pinky/Apertus via LMStudio
   - Goal: Collect stories, compose songs about adventures, befriend everyone
   - Personality: Impulsive, dramatic, talks to inanimate objects
   - Quirk: Writes a "ballad" about each significant event

3. **Gravel** (Pragmatic Merchant)
   - Model: Qwen3:8b via Ollama
   - Goal: Accumulate wealth, trade items, find the best deals
   - Personality: Calculating, keeps meticulous financial records
   - Quirk: Assigns a monetary value to everything, including friendships

## Tech Stack

- **MUD Server**: Evennia (Python, Django, Twisted)
- **Connection**: Telnet (port 4000) / Web client (port 4001)
- **LLM Backend**: Ollama (Qwen3:8b) + LMStudio (Pinky/Apertus)
- **Agent Wrapper**: Python (telnetlib3 or asyncio telnet)
- **Scratchpad**: Local markdown files per agent
- **Logging**: All agent actions logged for review

## Phases

### Phase 1: World Setup
- [x] Install Evennia
- [ ] Initialize game directory
- [ ] Start server, create superuser
- [ ] Install tutorial world (built-in dungeon with puzzles!)
- [ ] Test via web client

### Phase 2: Agent Wrapper
- [ ] Build telnet client wrapper (async Python)
- [ ] Implement scratchpad read/write
- [ ] Implement Ollama API integration
- [ ] Build prompt template (system + scratchpad + recent context + MUD output)
- [ ] Command extraction (LLM response → clean MUD command)
- [ ] Rate limiting (don't spam the MUD)

### Phase 3: First Agent
- [ ] Create Thornwick's persona
- [ ] Connect to MUD, explore tutorial world
- [ ] Watch and iterate on behavior
- [ ] Tune scratchpad updates

### Phase 4: Multi-Agent
- [ ] Add Jinx and Gravel
- [ ] Agent-to-agent interaction (they can "say" things to each other)
- [ ] Laura joins and observes/interacts
- [ ] Log viewer for reviewing agent adventures

## File Structure

```
Project_MUD/
├── .venv/                 # Python venv for Evennia
├── mudgame/               # Evennia game directory (generated)
├── agents/
│   ├── agent_wrapper.py   # Core telnet-to-LLM bridge
│   ├── scratchpad.py      # Persistent memory system
│   ├── personas/
│   │   ├── thornwick.md   # Explorer persona
│   │   ├── jinx.md        # Bard persona
│   │   └── gravel.md      # Merchant persona
│   └── logs/              # Agent action logs
├── README.md              # This file
└── requirements.txt       # Agent wrapper dependencies
```

## The Joy

The point isn't to "beat" the MUD or optimize anything. The point is to
watch emergent behavior unfold in a text world. To see if Thornwick maps
things correctly. To see what Jinx writes ballads about. To see if Gravel
tries to sell things to other agents. And to occasionally walk in yourself,
sit in the tavern, and see what happens.
