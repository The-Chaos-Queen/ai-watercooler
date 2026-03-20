"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent
from .agent_state import build_agent_state, tagged_agent_state


class Room(ObjectParent, DefaultRoom):
    def return_appearance(self, looker, **kwargs):
        """
        Handle the 'look' command output.
        Returns a JSON payload for AI agents or standard text for humans.
        """

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

        state = build_agent_state(looker, location=self, turn=0, recent_events=[])
        return tagged_agent_state(state)
