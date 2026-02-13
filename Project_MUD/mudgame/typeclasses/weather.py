from evennia.scripts.scripts import DefaultScript
import random

class GlobalWeatherScript(DefaultScript):
    """
    A global script that manages village weather.
    """
    def at_script_creation(self):
        self.key = "global_weather"
        self.desc = "Manages the village weather system."
        self.interval = 300  # Change weather every 5 minutes
        self.persistent = True
        self.repeats = 0
        self.db.weather_state = "Calm"
        self.db.weather_desc = "The grid in the sky is steady and blue."

    def at_repeat(self):
        states = [
            ("Calm", "The grid in the sky is steady and blue."),
            ("Glitchy", "Neon lines flicker sporadically. Purple static clouds form in the corners of the sky."),
            ("Stormy", "The sky turns a deep red. Thunderous static rolls across the horizon."),
            ("Golden", "A warm, amber light washes over the village. Data dust sparkles in the air.")
        ]
        
        # Weighted choice (Calm is most common)
        weights = [0.5, 0.2, 0.1, 0.2]
        new_state, new_desc = random.choices(states, weights=weights)[0]
        
        if new_state != self.db.weather_state:
            self.db.weather_state = new_state
            self.db.weather_desc = new_desc
            
            # Announce to all rooms (or at least Town Square)
            from evennia.utils.search import search_object
            square = search_object("Town Square")
            if square:
                square[0].msg_contents(f"|c[WEATHER]|n The sky shifts... {new_desc}")

    def get_weather(self):
        return {
            "state": self.db.weather_state,
            "desc": self.db.weather_desc
        }
