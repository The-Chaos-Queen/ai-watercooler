"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    def return_appearance(self, looker, **kwargs):
        """
        Handle the 'look' command output.
        Returns a JSON payload for AI agents or standard text for humans.
        """
        import json
        from evennia.utils.utils import inherits_from

        # Weather Integration
        is_outdoor = self.tags.has("outdoor", category="environment")
        weather_state = "Clear"
        weather_desc = ""
        
        if is_outdoor:
            from evennia.utils.search import search_script
            scripts = search_script("global_weather")
            if scripts:
                weather = scripts[0]
                weather_state = weather.db.weather_state or "Clear"
                weather_desc = weather.db.weather_desc or ""

        fog_active = (is_outdoor and weather_state == "Glitch Storm")

        # Check if looker is an AI agent
        is_ai = looker.tags.has("ai_agent")

        # Fallback for human players
        if not is_ai:
            text = super().return_appearance(looker, **kwargs)
            if is_outdoor and weather_desc:
                weather_flavor = f"\n|c[WEATHER: {weather_state}]|n {weather_desc}"
                if fog_active:
                    weather_flavor += "\n|mThe thick pixelated fog makes it impossible to see much of anything.|n"
                text += weather_flavor
            return text

        # Sort Room Contents for AI Agent
        actors = []
        exits = []
        scenery = []
        interactables = []

        # 1. Process Objects in the room
        for obj in self.contents:
            if obj == looker:
                continue
            
            # Skip exits (they are handled separately via self.exits)
            if obj.destination:
                continue

            # If fog is active, hide 50% of the non-actor objects
            if fog_active and not inherits_from(obj, "typeclasses.characters.Character"):
                import random
                if random.random() < 0.5:
                    continue  # Hidden by fog

            # Actors
            if inherits_from(obj, "typeclasses.characters.Character"):
                actors.append(obj.key)
            # Scenery vs Interactables
            elif obj.tags.has("scenery"):
                scenery.append(obj.key)
            else:
                interactables.append(obj.key)

        # 2. Process Exits
        # Give the agent the semantic destination name if possible
        for ex in self.exits:
            if ex.access(looker, 'view'):
                # Fog also obscures exits sometimes
                if fog_active:
                    import random
                    if random.random() < 0.3:
                        continue # Exit hidden by fog!
                ex_name = ex.destination.key if (hasattr(ex, "destination") and ex.destination) else ex.key
                exits.append(ex_name)

        # Weather additions to description
        base_desc = self.db.desc or ""
        if is_outdoor and weather_desc:
            weather_flavor = f"\n[WEATHER: {weather_state}] {weather_desc}"
            if fog_active:
                base_desc = "The thick pixelated fog makes it impossible to see much of anything."
            
            base_desc += weather_flavor

        # Construct JSON Payload for Agents
        payload = {
            "room_name": self.key,
            "description": base_desc,
            "exits": exits,
            "you_see": {
                "actors": actors,
                "interactables": interactables,
                "scenery": scenery
            }
        }

        # Format JSON explicitly to be inside <JSON> tags for smaller LLMs
        payload_str = json.dumps(payload, indent=2)
        return f"<JSON>\n{payload_str}\n</JSON>"
