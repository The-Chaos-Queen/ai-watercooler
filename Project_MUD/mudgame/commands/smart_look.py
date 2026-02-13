from evennia.commands.default.general import CmdLook

class CmdSmartLook(CmdLook):
    """
    look

    Usage:
      look
      look <obj>
      look at <obj>
      look around
      
    Observes your surroundings or a specific object.
    """
    key = "look"
    aliases = ["l", "ls", "look at", "look around"]
    
    def func(self):
        """
        Handle the look command.
        """
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
