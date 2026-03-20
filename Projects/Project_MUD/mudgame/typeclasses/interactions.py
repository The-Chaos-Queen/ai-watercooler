"""
Interaction Commands
"""
from evennia.objects.objects import DefaultCharacter, DefaultObject
from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from evennia.scripts.scripts import DefaultScript
from evennia.utils import search
import random

# Standard interval script for roaming


# -----------------------------------------------------------------------------
# Interactive Commands
# -----------------------------------------------------------------------------

class CmdInteract(Command):
    """
    Generic interaction command.
    Matches: touch, push, pull, smell, lick, shake
    """
    key = "touch"
    aliases = ["push", "pull", "smell", "lick", "shake", "rub", "sit", "stand", "dance", "read", "use", "kick", "drink", "splash", "buy", "play", "order"]
    locks = "cmd:all()"
    
    def func(self):
        verb = self.cmdstring.lower()
        
        # verbs that don't need a target
        social_solo = ["dance", "sit", "stand", "clap", "cheer", "laugh", "cry"]
        
        if not self.args:
            if verb in social_solo:
                self.caller.location.msg_contents(f"{self.caller.key} {verb}s.")
                return
            else:
                self.caller.msg(f"{self.cmdstring.title()} what?")
                return
            
        target = self.caller.search(self.args)
        if not target:
            return
            
        # Check if object has specific reaction for this verb
        if hasattr(target, "db") and target.db.reactions and verb in target.db.reactions:
            msg = target.db.reactions[verb]
            
            # Special case for "buy" or "order" - check cost?
            # Implemented as reaction text for now, but could be fancier later.
            
            self.caller.msg(f"You {verb} the {target.key}. {msg}")
            self.caller.location.msg_contents(f"{self.caller.key} {verb}s the {target.key}.", exclude=self.caller)
        else:
            defaults = {
                "touch": "It feels solid.",
                "smell": "It smells vaguely of ozone.",
                "lick": "Tastes like copper and static. Gross.",
                "push": "It doesn't budge.",
                "pull": "Nothing happens.",
                "shake": "Rattle rattle.",
                "dance": "You dance with it.",
                "sit": "You sit on it.",
                "stand": "You stand on it."
            }
            self.caller.msg(f"You {verb} the {target.key}. {defaults.get(verb, 'Nothing happens.')}")

class CmdSay(Command):
    """
    Speak to the room.
    
    Usage:
      say <message>
      " <message>
      ' <message>
    """
    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Say what?")
            return

        speech = self.args.strip()
        self.caller.location.msg_contents(f'{self.caller.key} says, "{speech}"')

class CmdMove(Command):
    """
    Move in a direction or to an exit name.
    
    Usage:
      move <direction/exit>
      go <direction/exit>
      walk <direction/exit>
    """
    key = "move"
    aliases = ["go", "walk"]
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Move where?")
            return
            
        direction = self.args.strip().lower()
        
        # Check for matching exit. 
        # We search specifically in the room's exits.
        # Note: 'candidates' argument restricts search to a specific list.
        if not self.caller.location:
            self.caller.msg("You are nowhere.")
            return

        # Simple manual match first (often faster/safer than generic search for exits)
        match = None
        for ex in self.caller.location.exits:
            exit_names = {ex.key.lower()}
            exit_names.update(alias.lower() for alias in ex.aliases.all())

            if getattr(ex, "destination", None):
                exit_names.add(ex.destination.key.lower())
                try:
                    exit_names.update(alias.lower() for alias in ex.destination.aliases.all())
                except Exception:
                    pass

            if direction in exit_names:
                match = ex
                break
        
        if match:
            # We found an exit. Traverse it!
            # Move the character
            self.caller.move_to(match.destination)
        else:
             # Fallback: try standard search just in case (e.g. for custom commands on exits)
             # but usually move_to is what we want for basic movement
             self.caller.msg(f"You cannot move '{direction}'.")

class CmdTalk(Command):
    """
    Talk to an NPC to start a dialog.
    
    Usage:
      talk <npc>
    """
    key = "talk"
    aliases = ["chat", "speak"]
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Talk to whom?")
            return
            
        target = self.caller.search(self.args)
        if not target:
            return
            
        if hasattr(target, "at_talk"):
            target.at_talk(self.caller)
        else:
            self.caller.msg(f"{target.key} doesn't seem to have much to say.")

class InteractCmdSet(CmdSet):
    key = "InteractCmdSet"
    def at_cmdset_creation(self):
        self.add(CmdInteract())
        self.add(CmdSay())
        self.add(CmdMove())
        self.add(CmdTalk())

# -----------------------------------------------------------------------------
# TypeClasses
# -----------------------------------------------------------------------------

from typeclasses.objects import Object

class InteractiveObject(Object):
    """
    An object that adds the InteractCmdSet to the *character* when they are in the same room,
    or simply exists to be looked at/touched.
    
    Actually, to make 'touch <obj>' work globally, we usually add the command to the Character 
    or the Object. If added to Object, you must 'touch object'.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()") # Fixed furniture
        self.db.reactions = {} # {"verb": "Message"}


# -----------------------------------------------------------------------------
# Scripts (for automation)
# -----------------------------------------------------------------------------

class RoamingScript(DefaultScript):
    def at_script_creation(self):
        self.key = "roaming_script"
        self.interval = 30 # seconds
        self.persistent = True
        
    def at_repeat(self):
        npc = self.obj
        if not npc or not npc.location:
            self.stop()
            return
            
        # Chat
        if hasattr(npc.db, "chat_lines") and npc.db.chat_lines and random.random() < 0.3:
            line = random.choice(npc.db.chat_lines)
            npc.location.msg_contents(f"{npc.key} says: '{line}'")
            
        # Roam
        if random.random() < (getattr(npc.db, "roam_chance", 0.4)):
            exits = [ex for ex in npc.location.exits]
            if exits:
                ex = random.choice(exits)
                npc.move_to(ex.destination, move_hooks=True)

class RoamingNPC(DefaultCharacter):
    """
    An NPC that moves around randomly and responds to keywords.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.roam_chance = 0.4
        self.db.chat_lines = ["The network is slow today.", "Have you seen the new protocols?", "Beep boop."]
        self.db.responses = {} # {"keyword": "Response"}
        self.scripts.add(RoamingScript)

    def msg(self, text=None, from_obj=None, **kwargs):
        """
        Custom msg() to snoop on text sent to this NPC.
        """
        super().msg(text=text, from_obj=from_obj, **kwargs)
        
        if not text:
            return

        if isinstance(text, tuple):
            text = text[0]
            
        if not isinstance(text, str):
            return

        # Don't respond to ourselves (Object logic)
        if from_obj == self:
            return
            
        # Don't respond to our own echoes (Text logic)
        # Assuming format "Name says: ..."
        if self.key in text:
            return

        # Ignore system messages not containing speech
        if "says" not in text and '"' not in text and "'" not in text:
            return

        lower_text = text.lower()
        
        # Cooldown/Memory check
        import time
        # Ensure ndb attribute exists for detailed memory
        # Structure: { sender_id: { keyword: timestamp } }
        if not getattr(self.ndb, "interaction_memory", None):
            self.ndb.interaction_memory = {}
            
        now = time.time()
        # Use a safe ID even if from_obj is None (unlikely but safe)
        sender_id = from_obj.id if from_obj and hasattr(from_obj, 'id') else "unknown"
        
        if self.db.responses:
            for keyword, response in self.db.responses.items():
                if keyword in lower_text:
                    # Check per-user memory
                    user_memory = self.ndb.interaction_memory.get(sender_id, {})
                    last_time = user_memory.get(keyword, 0)
                    
                    # specific cooldowns
                    cooldown = 5 # default 5 seconds
                    # Long cooldown for greetings to prevent loop
                    if keyword in ["hello", "hi", "greetings", "welcome", "met", "meet"]:
                        cooldown = 600 # 10 minutes
                        
                    if now - last_time < cooldown:
                        return # Ignore this trigger

                    # Respond
                    self.location.msg_contents(f'{self.key} says: "{response}"', exclude=[self])
                    
                    # Update memory
                    if sender_id not in self.ndb.interaction_memory:
                         self.ndb.interaction_memory[sender_id] = {}
                    self.ndb.interaction_memory[sender_id][keyword] = now
                    return


