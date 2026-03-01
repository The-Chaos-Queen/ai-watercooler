from evennia.commands.default.general import CmdLook
import json

class CmdSmartLook(CmdLook):
    """
    look

    Usage:
      look
      look <obj>
      look at <obj>
      look around
      
    Observes your surroundings or a specific object.
    Use 'look --json' to get the room state in JSON format (for agents).
    """
    key = "look"
    aliases = ["l", "ls", "look at", "look around"]
    
    def func(self):
        """
        Handle the look command.
        """
        print(f"DEBUG: CmdSmartLook called with args='{self.args}'")
        # Check for JSON flag
        if self.args and ("--json" in self.args):
            self.return_json_state()
            return

        # If the user typed "look at <obj>", self.args will be " at <obj>"
        # or if they typed "look at", self.args might be " at"
        # We need to clean up "at" or "around" if they are present
        
        if self.args:
            args = self.args.strip()
            # Handle "look at <obj>" -> "look <obj>"
            if args.lower().startswith("at "):
                self.args = args[3:] # Strip "at "
            # Handle "look around" -> "look"
            elif args.lower() == "around":
                self.args = ""
                
            if self.args:
                try:
                    from commands.social import fuzzy_match
                    match = fuzzy_match(self.caller, self.args, candidates=self.caller.location.contents + self.caller.location.exits, quiet=True)
                    if match:
                        self.args = match.key
                except Exception as e:
                    print(f"DEBUG: fuzzy_match error in look: {e}")
        
        super().func()

    def return_json_state(self):
        """
        Return the current room state as a JSON string.
        """
        print("DEBUG: return_json_state START")
        try:
            caller = self.caller
            location = caller.location
            
            if not location:
                caller.msg('{"error": "No location"}')
                return

            print(f"DEBUG: Processing location {location.key}")

            # Weather Integration
            is_outdoor = location.tags.has("outdoor", category="environment")
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

            # Entities
            players = []
            npcs = []
            items = []
            
            # Filter contents
            for obj in location.contents:
                if obj == caller:
                    continue
                
                # If fog is active, hide some objects
                if fog_active and not (obj.has_account or obj.is_typeclass("typeclasses.characters.Character")):
                    import random
                    if random.random() < 0.5:
                        continue  # Hidden by fog
                
                name = obj.key
                 
                if obj.has_account:
                    players.append(name)
                elif obj.is_typeclass("typeclasses.npc_cast.StaticNPC") or \
                     obj.is_typeclass("typeclasses.npc_cast.RoamingAnimal") or \
                     (obj.is_typeclass("typeclasses.characters.Character") and not obj.has_account):
                    npcs.append(name)
                else:
                    items.append(name)

            # Exits
            exits = []
            for ex in location.exits:
                if fog_active:
                    import random
                    if random.random() < 0.3:
                        continue # Exit hidden by fog!
                exits.append((ex.destination.key if hasattr(ex, 'destination') and ex.destination else ex.key).lower())

            # Weather additions to description
            base_desc = location.db.desc or ""
            if is_outdoor and weather_desc:
                weather_flavor = f"\n[WEATHER: {weather_state}] {weather_desc}"
                if fog_active:
                    base_desc = "The thick pixelated fog makes it impossible to see much of anything."
                
                base_desc += weather_flavor

            # Construct JSON data
            data = {
                "location": {
                    "name": location.key,
                    "description": base_desc,
                    "weather": weather_state if is_outdoor else "Indoor",
                    "exits": exits
                },
                "entities": {
                    "players": players,
                    "npcs": npcs,
                    "items": items
                },
                "recent_events": [], 
                "turn": 0,
                "your_character": {
                    "name": caller.key,
                    "role": getattr(caller.db, "role", "adventurer"),
                    "current_action": None
                }
            }
            
            # critical debug
            json_str = json.dumps(data, indent=2)
            print(f"DEBUG: sending JSON: {json_str[:50]}...")
            
            caller.msg(json_str)
        except Exception as e:
            import traceback
            traceback.print_exc()
            caller.msg(f'{{"error": "{str(e)}"}}')
