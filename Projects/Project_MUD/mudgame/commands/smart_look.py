from evennia.commands.default.general import CmdLook

from typeclasses.agent_state import build_agent_state, serialize_agent_state

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
                except Exception:
                    pass
        
        super().func()

    def return_json_state(self):
        """
        Return the current room state as a JSON string.
        """
        try:
            caller = self.caller
            location = caller.location

            if not location:
                caller.msg('{"error": "No location"}')
                return

            state = build_agent_state(caller, location=location, turn=0, recent_events=[])
            caller.msg(serialize_agent_state(state))
        except Exception as e:
            import traceback
            traceback.print_exc()
            caller.msg(f'{{"error": "{str(e)}"}}')
