# Task Brief: MUD Agent JSON Input Format (Layer 1)

## Context
We're running a text MUD (Multi-User Dungeon) with AI agents powered by small
LLMs (1-8B parameters). The agents currently receive room state as **natural
language text** (Layer 0), which wastes tokens and confuses small models.

The agent **output** is already structured JSON (enforced via LMStudio schema).
The gap is the **input** side.

## Current Input (Layer 0 - what agents see now)
```
The Town Square
A bustling cobblestone square. A fountain gurgles in the center.
Obvious exits: tavern, market, temple
Players here: Thornwick
Items here: a wooden sign
```

## Proposed Input (Layer 1 - what we want)
```json
{
  "location": {
    "name": "The Town Square",
    "description": "A bustling cobblestone square. A fountain gurgles in the center.",
    "exits": ["tavern", "market", "temple"]
  },
  "entities": {
    "players": ["Thornwick"],
    "npcs": [],
    "items": ["a wooden sign"]
  },
  "recent_events": [
    {"type": "say", "actor": "Thornwick", "content": "Good morning!"},
    {"type": "arrive", "actor": "Jinx", "content": "Jinx arrives from the tavern."}
  ],
  "turn": 15,
  "your_character": {
    "name": "Jinx",
    "role": "bard",
    "current_action": null
  }
}
```

## What Needs to Change

### 1. MUD Server Side (Evennia)
The MUD server (Evennia, Python) needs a function that serializes the current
room state into the JSON format above. This should be called by the agent
wrapper before sending state to the LLM.

Key files to look at:
- `agent_wrapper.py` — The Python script that connects agents to the MUD
- The Evennia room/object classes that hold state

### 2. Agent Wrapper Side
`agent_wrapper.py` currently scrapes room descriptions as text. It needs to:
- Call the new serialization function to get JSON state
- Include the JSON state in the LLM prompt (as a structured system/user message)
- Keep the output schema as-is

### 3. System Prompt Update
The agent's system prompt needs to tell it: "You receive world state as JSON.
Your actions are also JSON. Here is the schema for both."

## Constraints
- Don't break existing human player experience (they still see prose)
- The JSON should include ALL information currently in the text description
- Keep recent_events to last 5-10 events (not the full history)
- Agent character cards / personality should remain in the system prompt
- Must work with LMStudio's structured output enforcement

## Files Location
Everything is in: `c:\Users\cerub\OneDrive\Dokumente\LLM\`
- MUD code: look for Evennia project files
- Agent wrapper: `agent_wrapper.py` (search for it)
- Character cards: likely in CHEESE_Memory or nearby

## Success Criteria
- Agent receives JSON state instead of prose
- Agent still produces valid action JSON
- Small models (4B) show improved task completion vs. prose input
