"""
Shared agent-state serialization helpers for LLM-facing room output.
"""

import json
import random

from evennia.utils.search import search_script
from evennia.utils.utils import inherits_from


SCHEMA_VERSION = "mud.agent_state/v1"


def _stable_id(prefix, obj):
    obj_id = getattr(obj, "id", None)
    if obj_id is not None:
        return f"{prefix}:{obj_id}"
    key = getattr(obj, "key", prefix)
    safe_key = str(key).strip().lower().replace(" ", "_")
    return f"{prefix}:{safe_key or prefix}"


def _get_weather(location):
    is_outdoor = location.tags.has("outdoor", category="environment")
    weather_state = "Indoor"
    weather_desc = ""

    if is_outdoor:
        weather_state = "Clear"
        scripts = search_script("global_weather")
        if scripts:
            weather = scripts[0]
            weather_state = weather.db.weather_state or "Clear"
            weather_desc = weather.db.weather_desc or ""

    fog_active = is_outdoor and weather_state == "Glitch Storm"
    visibility = "low" if fog_active else "clear"

    return {
        "is_outdoor": is_outdoor,
        "state": weather_state,
        "description": weather_desc,
        "fog_active": fog_active,
        "visibility": visibility,
    }


def _apply_weather_to_description(location, weather):
    base_desc = location.db.desc or ""
    if weather["is_outdoor"] and weather["description"]:
        weather_flavor = f"\n[WEATHER: {weather['state']}] {weather['description']}"
        if weather["fog_active"]:
            base_desc = "The thick pixelated fog makes it impossible to see much of anything."
        base_desc += weather_flavor
    return base_desc


def _summary_from_description(description, fallback):
    for line in description.splitlines():
        clean = line.strip()
        if clean:
            return clean
    return fallback


def _alias_list(obj):
    try:
        aliases = obj.aliases.all()
    except Exception:
        aliases = []

    cleaned = []
    seen = set()
    for alias in aliases:
        alias_text = str(alias).strip().lower()
        if alias_text and alias_text not in seen:
            seen.add(alias_text)
            cleaned.append(alias_text)
    return cleaned


def _entity_type(obj):
    if getattr(obj, "has_account", False):
        return "player"
    if inherits_from(obj, "typeclasses.npc_cast.StaticNPC"):
        return "npc"
    if inherits_from(obj, "typeclasses.npc_cast.DialogNPC"):
        return "npc"
    if inherits_from(obj, "typeclasses.npc_cast.RoamingAnimal"):
        return "npc"
    if inherits_from(obj, "typeclasses.interactions.RoamingNPC"):
        return "npc"
    if inherits_from(obj, "typeclasses.characters.Character"):
        return "npc"
    if obj.tags.has("scenery"):
        return "scenery"
    return "item"


def _is_portable(obj, looker):
    if getattr(obj, "destination", None):
        return False
    if getattr(obj, "has_account", False):
        return False
    if inherits_from(obj, "typeclasses.characters.Character"):
        return False
    if inherits_from(obj, "typeclasses.npc_cast.StaticNPC"):
        return False
    if inherits_from(obj, "typeclasses.npc_cast.RoamingAnimal"):
        return False
    if inherits_from(obj, "typeclasses.interactions.RoamingNPC"):
        return False
    if obj.tags.has("scenery"):
        return False
    try:
        return bool(obj.access(looker, "get", default=True))
    except Exception:
        return True


def _entity_affordances(obj, entity_type, portable):
    affordances = ["look"]

    if entity_type in {"player", "npc"}:
        affordances.extend(["say", "hug", "give"])
        if hasattr(obj, "at_pet"):
            affordances.append("pet")
        if hasattr(obj, "at_talk"):
            affordances.append("talk")
        return sorted(set(affordances))

    if portable:
        affordances.append("get")

    if obj.tags.has("instrument") or getattr(obj.db, "is_instrument", False):
        affordances.append("play")
    if getattr(obj.db, "can_sit", False):
        affordances.append("sit")
    if getattr(obj.db, "messages", None) is not None:
        affordances.extend(["read", "post"])
    if getattr(obj.db, "votes", None) is not None:
        affordances.append("vote")

    if hasattr(obj, "db") and getattr(obj.db, "reactions", None):
        affordances.extend(sorted(obj.db.reactions.keys()))

    if obj.tags.has("scenery"):
        affordances.append("inspect")

    return sorted(set(affordances))


def _entity_tags(obj, entity_type, portable):
    tags = [entity_type]

    if portable:
        tags.append("portable")
    if obj.tags.has("scenery"):
        tags.append("scenery")
    if hasattr(obj, "at_talk"):
        tags.append("interactive")
    if hasattr(obj, "at_pet"):
        tags.append("pettable")
    if hasattr(obj, "db") and getattr(obj.db, "reactions", None):
        tags.append("reactive")
    if obj.tags.has("instrument") or getattr(obj.db, "is_instrument", False):
        tags.append("instrument")
    if getattr(obj.db, "messages", None) is not None:
        tags.append("readable")
    if getattr(obj.db, "votes", None) is not None:
        tags.append("votable")

    deduped = []
    seen = set()
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped


def _entity_description(obj):
    desc = getattr(obj.db, "desc", "") or ""
    return desc.strip()


def _entity_prefix(entity_type):
    if entity_type == "player":
        return "player"
    if entity_type == "npc":
        return "npc"
    if entity_type == "scenery":
        return "scenery"
    return "item"


def _serialize_entity(obj, looker):
    entity_type = _entity_type(obj)
    portable = _is_portable(obj, looker)
    return {
        "id": _stable_id(_entity_prefix(entity_type), obj),
        "name": obj.key,
        "type": entity_type,
        "description": _entity_description(obj),
        "portable": portable,
        "state_tags": _entity_tags(obj, entity_type, portable),
        "affordances": _entity_affordances(obj, entity_type, portable),
    }


def _serialize_inventory(caller):
    inventory = []
    for obj in getattr(caller, "contents", []):
        if getattr(obj, "destination", None):
            continue
        inventory.append(
            {
                "id": _stable_id("item", obj),
                "name": obj.key,
                "type": "item",
            }
        )
    return inventory


def _serialize_exits(location, looker, fog_active):
    exits = []
    seen = set()

    for ex in location.exits:
        if looker is not None and not ex.access(looker, "view"):
            continue
        if fog_active and random.random() < 0.3:
            continue

        destination = getattr(ex, "destination", None)
        label = destination.key if destination else ex.key
        aliases = _alias_list(ex)
        label_key = str(label).strip().lower()
        dedupe_key = (
            _stable_id("room", destination) if destination else label_key,
            label_key,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        if label_key not in aliases:
            aliases.insert(0, label_key)

        exits.append(
            {
                "id": _stable_id("exit", ex),
                "label": label,
                "destination_id": _stable_id("room", destination) if destination else None,
                "aliases": aliases,
                "traversable": bool(destination),
                "command": f"move {label}",
            }
        )

    return exits


def _visible_entities(location, looker, fog_active):
    entities = []
    for obj in location.contents:
        if obj == looker:
            continue
        if getattr(obj, "destination", None):
            continue

        if fog_active and not inherits_from(obj, "typeclasses.characters.Character"):
            if random.random() < 0.5:
                continue

        entities.append(_serialize_entity(obj, looker))

    entities.sort(key=lambda entity: (entity["type"], entity["name"].lower()))
    return entities


def _suggested_actions(exits, entities):
    suggestions = [{"command": "look", "reason": "Refresh the current room state."}]

    for exit_data in exits[:3]:
        suggestions.append(
            {
                "command": exit_data["command"],
                "reason": "Visible traversable exit.",
            }
        )

    for entity in entities:
        affordances = entity.get("affordances", [])
        name = entity.get("name", "")

        if entity.get("type") == "npc" and "talk" in affordances:
            suggestions.append(
                {
                    "command": f"talk {name}",
                    "reason": "An interactive NPC is present.",
                }
            )
            continue

        if entity.get("type") == "npc":
            suggestions.append(
                {
                    "command": f"look {name}",
                    "reason": "Inspect a visible NPC before interacting further.",
                }
            )
            continue

        if entity.get("type") == "item" and "get" in affordances:
            suggestions.append(
                {
                    "command": f"get {name}",
                    "reason": "A portable item is visible.",
                }
            )
            continue

        suggestions.append(
            {
                "command": f"look {name}",
                "reason": "Inspect a visible entity.",
            }
        )

        if len(suggestions) >= 6:
            break

    return suggestions[:6]


def get_room_environment_state(location, looker=None):
    weather = _get_weather(location)
    description = _apply_weather_to_description(location, weather)
    room = {
        "id": _stable_id("room", location),
        "name": location.key,
        "summary": _summary_from_description(description, location.key),
        "description": description,
        "weather": {
            "state": weather["state"],
            "description": weather["description"],
            "visibility": weather["visibility"],
        },
    }
    exits = _serialize_exits(location, looker, weather["fog_active"])
    entities = _visible_entities(location, looker, weather["fog_active"])
    return {
        "room": room,
        "exits": exits,
        "entities": entities,
    }


def build_agent_state(
    caller,
    location=None,
    turn=0,
    recent_events=None,
    last_action_result=None,
):
    location = location or caller.location
    if not location:
        return {
            "schema_version": SCHEMA_VERSION,
            "turn": turn,
            "error": "No location",
            "recent_events": list(recent_events or []),
            "suggested_actions": [{"command": "look", "reason": "Recover world state."}],
        }

    environment = get_room_environment_state(location, looker=caller)
    role = getattr(caller.db, "role", None) or "adventurer"
    tokens = getattr(caller.db, "tokens", 0) or 0

    state = {
        "schema_version": SCHEMA_VERSION,
        "turn": turn,
        "self": {
            "id": _stable_id("character", caller),
            "name": caller.key,
            "type": "player" if getattr(caller, "has_account", False) else "npc",
            "role": role,
            "location_id": environment["room"]["id"],
            "inventory": _serialize_inventory(caller),
            "status": {"tokens": tokens},
            "last_action_result": last_action_result,
        },
        "room": environment["room"],
        "exits": environment["exits"],
        "entities": environment["entities"],
        "recent_events": list(recent_events or []),
        "suggested_actions": _suggested_actions(environment["exits"], environment["entities"]),
    }
    return state


def serialize_agent_state(state):
    return json.dumps(state, indent=2)


def tagged_agent_state(state):
    return f"<JSON>\n{serialize_agent_state(state)}\n</JSON>"
