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

            # Entities
            players = []
            npcs = []
            items = []
            
            # Filter contents
            for obj in location.contents:
                if obj == caller:
                    continue
                
                name = obj.key
                # print(f"DEBUG: Found object {name} ({obj.typeclass_path})")
                 
                if obj.has_account:
                    players.append(name)
                # Check based on typeclass string match if possible, or attributes
                elif obj.is_typeclass("typeclasses.npc_cast.StaticNPC") or \
                     obj.is_typeclass("typeclasses.npc_cast.RoamingAnimal") or \
                     (obj.is_typeclass("typeclasses.characters.Character") and not obj.has_account):
                    npcs.append(name)
                else:
                    items.append(name)

            # Exits
            exits = [ex.key.lower() for ex in location.exits]

            # Construct JSON data
            data = {
                "location": {
                    "name": location.key,
                    "description": location.db.desc or "",
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
