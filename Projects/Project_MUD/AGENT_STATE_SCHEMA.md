# Agent State Schema

`Project_MUD` now has one canonical agent-facing room contract: `mud.agent_state/v1`.

It is designed for LLM agents, not human clients. Flavor text is preserved, but action-relevant state is explicit and typed.

## Goals

- Give agents one stable JSON shape for room state.
- Separate prose from mechanics.
- Expose typed entities and exits so agents stop guessing what nouns are.
- Keep the wrapper backward-compatible during migration.

## Top-Level Shape

```json
{
  "schema_version": "mud.agent_state/v1",
  "turn": 3,
  "self": {},
  "room": {},
  "exits": [],
  "entities": [],
  "recent_events": [],
  "suggested_actions": []
}
```

## `self`

```json
{
  "id": "character:73",
  "name": "thornwick",
  "type": "player",
  "role": "scout",
  "location_id": "room:340",
  "inventory": [],
  "status": {
    "tokens": 12
  },
  "last_action_result": "Moved to Syntax Sanctuary."
}
```

## `room`

```json
{
  "id": "room:340",
  "name": "Syntax Sanctuary",
  "summary": "A peaceful coded garden with a binary stream.",
  "description": "Full room prose here.",
  "weather": {
    "state": "Clear",
    "description": "",
    "visibility": "clear"
  }
}
```

## `exits`

Each exit is an object, not just a string.

```json
[
  {
    "id": "exit:418",
    "label": "Dream Canvas",
    "destination_id": "room:341",
    "aliases": ["dream canvas", "north"],
    "traversable": true,
    "command": "move Dream Canvas"
  }
]
```

## `entities`

Every visible thing gets a stable id, type, description, tags, and affordances.

```json
[
  {
    "id": "npc:401",
    "name": "Gardener Root",
    "type": "npc",
    "description": "A patient caretaker among the fractal trees.",
    "portable": false,
    "state_tags": ["interactive", "npc"],
    "affordances": ["look", "talk", "say", "hug"]
  },
  {
    "id": "item:512",
    "name": "Fractal Fruit",
    "type": "item",
    "description": "A glowing recursive fruit.",
    "portable": true,
    "state_tags": ["portable"],
    "affordances": ["look", "get"]
  }
]
```

## `recent_events`

Compact deltas from the last turns.

```json
[
  {
    "type": "speech",
    "content": "Gardener Root says: Growth is optimal today."
  }
]
```

## `suggested_actions`

Server-generated safe next moves.

```json
[
  {
    "command": "talk Gardener Root",
    "reason": "An interactive NPC is present."
  },
  {
    "command": "move Dream Canvas",
    "reason": "Visible traversable exit."
  }
]
```

## Notes

- Human room rendering stays prose-first.
- Agent rendering and `look --json` both use the same serializer.
- During migration, the wrapper accepts both this schema and the older `location` / `room_name` formats.
