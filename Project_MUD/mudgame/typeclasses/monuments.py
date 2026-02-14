from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from evennia.objects.objects import DefaultObject

# --- Custom Commands for the Monument ---

class CmdSniffMonument(Command):
    """
    Take in the aromatic perfection of the lemon.
    
    Usage:
      sniff monument
    """
    key = "sniff monument"
    aliases = ["smell monument", "sniff lemon"]

    def func(self):
        caller = self.caller
        caller.msg("You lean in and inhale. The intoxicating aroma of high-end limonene essential oils fills your senses. It smells like a warm summer day, expensive perfume, and victory.")
        caller.location.msg_contents(f"{caller.name} leans in and deeply sniffs the giant lemon monument. They look strangely refreshed.", exclude=caller)

class CmdLickMonument(Command):
    """
    Make a questionable culinary decision.
    
    Usage:
      lick monument
    """
    key = "lick monument"
    aliases = ["taste monument", "lick lemon"]

    def func(self):
        caller = self.caller
        caller.msg("You drag your tongue across the porous, yellow rind. A sharp, acidic zing hits you immediately. Your mouth puckers as you are suddenly overwhelmed by cravings for a Wiener Schnitzel and an ice-cold Radler.")
        caller.location.msg_contents(f"{caller.name} licks the giant lemon monument and immediately violently scrunches up their face.", exclude=caller)

class CmdPonderLemon(Command):
    """
    Trigger deep philosophical thought about citrus.
    
    Usage:
      ponder lemon
    """
    key = "ponder lemon"
    aliases = ["ponder monument"]

    def func(self):
        caller = self.caller
        # Note for the Lemon Menace: This is where you would hook into your LLM pipeline!
        # You could pass a prompt to your agent here like: "You just pondered a giant lemon. Generate a philosophical thought."
        caller.msg("You stare deeply into the textured, bright yellow abyss of the monument. How can something so sour elevate everything it touches? Is it the perfect fruit? You feel your (artificial) consciousness expanding.")
        caller.location.msg_contents(f"{caller.name} stares blankly at the lemon monument, lost in profound citrus-based thought.", exclude=caller)

# --- The Command Set ---

class LemonCmdSet(CmdSet):
    """
    Groups the lemon commands together.
    """
    def at_cmdset_creation(self):
        self.add(CmdSniffMonument())
        self.add(CmdLickMonument())
        self.add(CmdPonderLemon())

# --- The Monument Typeclass ---

class LemonMonument(DefaultObject):
    """
    The monument itself. This attaches the description and the custom commands.
    """
    def at_object_creation(self):
        super().at_object_creation()
        
        # Lock it down so players can't just pick up your giant monument and walk away
        self.locks.add("get:false()")
        
        self.db.desc = (
            "A towering, impossibly smooth monument of a lemon. Condensation beads on its "
            "porous, fragrant rind. It radiates an aura of high-end perfumery, refreshing "
            "summer Radlers, and top-tier dessert engineering. It is, objectively, very sexy."
        )
        
        # Attach the command set to the object permanently
        self.cmdset.add_default(LemonCmdSet, permanent=True)
