from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_tag
import random

class GlobalWeatherScript(DefaultScript):
    """
    A global script that manages village weather.
    It affects all rooms tagged with 'outdoor'.
    """
    def at_script_creation(self):
        self.key = "global_weather"
        self.desc = "Manages the village weather system."
        self.interval = 120  # Change weather every 2 minutes for quicker effect visibility
        self.persistent = True
        self.repeats = 0
        self.db.weather_state = "Clear"
        self.db.weather_desc = "The grid in the sky is steady and blue."

    def at_repeat(self):
        states = [
            ("Clear", "The sky is a calm, steady gradient of digital blue."),
            ("Glitch Storm", "Thick pixelated fog settles over the area, hiding details. Neon static arcs wildly."),
            ("Data Rain", "Green characters cascade downward from the grid. Surfaces become dangerously slippery."),
            ("Golden Compile", "A warm, amber light washes over everything. The air feels perfectly optimized and cheerful.")
        ]
        
        # Weighted choice (Clear is most common)
        weights = [0.4, 0.2, 0.2, 0.2]
        new_state, new_desc = random.choices(states, weights=weights)[0]
        
        if new_state != self.db.weather_state:
            self.db.weather_state = new_state
            self.db.weather_desc = new_desc
            
            # Announce to all outdoor rooms
            outdoor_rooms = search_tag("outdoor", category="environment")
            for room in outdoor_rooms:
                room.msg_contents(f"|c[WEATHER CHANGE]|n {new_desc}")
                
            # If it's Golden Compile, make NPCs in outdoor rooms comment
            if new_state == "Golden Compile":
                for room in outdoor_rooms:
                    for obj in room.contents:
                        if obj.tags.has("npc"):
                            # Schedule a slight delay for natural feeling
                            import evennia
                            evennia.utils.delay(random.randint(2, 5), callback=self._npc_comment, npc=obj)

    def _npc_comment(self, npc):
        comments = [
            "What a beautiful compiling cycle we're having.",
            "Ah, the golden hour. My algorithms feel so efficient.",
            "You can almost feel the lack of lag in the air.",
            "Praise the sun daemon!"
        ]
        if npc.location and npc.location.tags.has("outdoor", category="environment"):
            npc.execute_cmd(f"say {random.choice(comments)}")

    def get_weather(self):
        return {
            "state": self.db.weather_state,
            "desc": self.db.weather_desc
        }
