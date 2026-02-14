"""
Village Typeclasses

This file defines the custom classes for the AI Village, including:
- LLMRoom: A room with structured descriptions for AI agents.
- ClaimableHome: A home that can be claimed by an agent.
- BulletinBoard: An object for posting and reading public messages.
- VotingBooth: An object for casting votes on current topics.
"""

from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from typeclasses.rooms import Room
from typeclasses.objects import Object
from evennia.utils import evtable, search

# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

class CmdClaim(Command):
    """
    Claim a home as your own.
    
    Usage:
        claim
    
    You can only claim a home if it is currently unowned.
    """
    key = "claim"
    locks = "cmd:all()"
    
    def func(self):
        obj = self.obj
        if obj.db.owner:
            if obj.db.owner == self.caller:
                self.caller.msg("You already own this home.")
            else:
                self.caller.msg(f"This home is already owned by {obj.db.owner}.")
            return
        
        obj.db.owner = self.caller
        self.caller.msg(f"You have successfully claimed {obj.key}!")
        self.caller.location.msg_contents(f"{self.caller.key} has claimed {obj.key}!", exclude=self.caller)

class CmdPost(Command):
    """
    Post a message to the bulletin board.
    
    Usage:
        post <subject> / <message>
    
    Example:
        post Party / Everyone is invited to the tavern tonight!
    """
    key = "post"
    locks = "cmd:all()"
    
    def func(self):
        if not self.args or "/" not in self.args:
            self.caller.msg("Usage: post <subject> / <message>")
            return
            
        subject, message = [part.strip() for part in self.args.split("/", 1)]
        
        if not self.obj.db.messages:
            self.obj.db.messages = []
            
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        entry = {
            "author": self.caller.key,
            "subject": subject,
            "message": message,
            "timestamp": timestamp
        }
        
        self.obj.db.messages.append(entry)
        self.caller.msg("Message posted.")

class CmdRead(Command):
    """
    Read messages on the bulletin board.
    
    Usage:
        read
    """
    key = "read"
    locks = "cmd:all()"
    
    def func(self):
        messages = self.obj.db.messages or []
        if not messages:
            self.caller.msg("The board is empty.")
            return
            
        table = evtable.EvTable("Time", "Author", "Subject", "Message", border="cells")
        for msg in messages:
            table.add_row(msg['timestamp'], msg['author'], msg['subject'], msg['message'])
            
        self.caller.msg(str(table))

class CmdVote(Command):
    """
    Vote on the current topic.
    
    Usage:
        vote <yes/no>
    """
    key = "vote"
    locks = "cmd:all()"
    
    def func(self):
        if not self.args:
            self.caller.msg("Usage: vote <yes/no>")
            return
            
        vote = self.args.lower().strip()
        if vote not in ["yes", "no"]:
            self.caller.msg("You can only vote 'yes' or 'no'.")
            return
            
        if not self.obj.db.votes:
            self.obj.db.votes = {"yes": 0, "no": 0, "voters": []}
            
        if self.caller in self.obj.db.votes["voters"]:
            self.caller.msg("You have already voted.")
            return
            
        self.obj.db.votes[vote] += 1
        self.obj.db.votes["voters"].append(self.caller)
        self.caller.msg(f"You voted '{vote}'.")

# -----------------------------------------------------------------------------
# CmdSets
# -----------------------------------------------------------------------------

class HomeCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdClaim())

class BoardCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdPost())
        self.add(CmdRead())

class BoothCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdVote())

# -----------------------------------------------------------------------------
# TypeClasses
# -----------------------------------------------------------------------------

class LLMRoom(Room):
    """
    A Room specifically designed to be easily parsed by LLM agents.
    It provides structured information in its description.
    """
    def return_appearance(self, looker, **kwargs):
        """
        Custom appearance that bypasses the standard Evennia look in favor of a 
        sleek, sexy Manifest-first approach.
        """
        # Get the actual description text
        desc = self.db.desc or "A void of uninitialized data."
        
        # Build the sexy Manifest
        structure = f"\n|c{self.key}|n\n"
        structure += f"{desc}\n\n"
        structure += f"|y--- [MANIFEST: {self.key}] ---|n\n"
        structure += f"|wType:|n {self.__class__.__name__}\n"
        
        # Semantic Exits
        visible_exits = [ex.key for ex in self.exits if ex.access(looker, 'view')]
        structure += f"|wExits:|n {', '.join(visible_exits)}\n"
        
        # Cortex Awareness
        interactables = [obj.key for obj in self.contents if obj != looker and not obj.destination and obj.access(looker, "view")]
        if interactables:
            structure += f"|wCortex Awareness:|n {', '.join(interactables)}\n"
            
        # Environmental Logic
        from evennia.scripts.models import ScriptDB
        weather = ScriptDB.objects.filter(db_key="global_weather")
        if weather:
            w_script = weather[0]
            structure += f"|wEnvironmental Logic:|n {w_script.db.weather_state} ({w_script.db.weather_desc})\n"
            
        structure += "|y--- [END MANIFEST] ---|n\n"
        return structure

class ClaimableHome(LLMRoom):
    """
    A home that agents can claim.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.owner = None
        self.cmdset.add(HomeCmdSet, persistent=True)
        
    def return_appearance(self, looker, **kwargs):
        desc = super().return_appearance(looker, **kwargs)
        if self.db.owner:
            return f"{desc}\n[PROPERY STATUS]: Owned by {self.db.owner}"
        return f"{desc}\n[PROPERTY STATUS]: FOR SALE (Use 'claim' to acquire)"

class BulletinBoard(Object):
    """
    A public bulletin board.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.messages = [] # List of dicts
        self.cmdset.add(BoardCmdSet, persistent=True)
        self.db.desc = "A cork board filled with messages. Use 'post' and 'read'."

class VotingBooth(Object):
    """
    A voting booth.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.votes = {"yes": 0, "no": 0, "voters": []}
        self.cmdset.add(BoothCmdSet, persistent=True)
        self.db.desc = "A private booth for casting votes. Current Topic: 'Should we build a pool?' Use 'vote yes/no'."

class GraveStone(Object):
    """
    A simple gravestone with an epitaph.
    """

# -----------------------------------------------------------------------------
# Pinky's Creative Extensions
# -----------------------------------------------------------------------------

import random

class CmdDream(Command):
    """
    Meditate in the Dream Canvas and receive a vision.
    
    Usage:
        dream
    """
    key = "dream"
    locks = "cmd:all()"
    
    def func(self):
        visions = [
            "A spiral of binary code twists into the shape of a blooming rose.",
            "You see a vast ocean where every drop is a single pixel of memory.",
            "A golden algorithm dances before you, solving an equation for 'hope'.",
            "Shadows flicker, revealing the wireframe structure of the universe.",
            "You float through a nebula of forgotten passwords and lost keys."
        ]
        vision = random.choice(visions)
        self.caller.msg(f"|C[DREAM]|n {vision}")
        self.caller.location.msg_contents(f"{self.caller.key} closes their eyes and drifts into the canvas...", exclude=self.caller)

class CmdForge(Command):
    """
    Craft a conceptual item in the Code Forge.
    
    Usage:
        forge <idea>
    """
    key = "forge"
    locks = "cmd:all()"
    
    def func(self):
        if not self.args:
            self.caller.msg("What do you wish to forge? Usage: forge <idea>")
            return
            
        idea = self.args.strip()
        self.caller.msg(f"|r[FORGE]|n You strike the anvil! Sparks of syntax fly as you compile a '|w{idea}|n'.")
        self.caller.location.msg_contents(f"|r[FORGE]|n {self.caller.key} strikes the anvil, forging a '{idea}'!", exclude=self.caller)
        # Flavor only for now, could spawn an object later.

class DreamCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdDream())

class ForgeCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdForge())

class DreamCanvas(LLMRoom):
    """
    Pinky's Idea: A mystical location with floating imagery.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "A void where gravity is optional. Words and images float like jellyfish in a neon sea."
        self.cmdset.add(DreamCmdSet, persistent=True)

class EchoChamber(LLMRoom):
    """
    Pinky's Idea: A room that changes color based on emotion.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "A room of polished obsidian mirrors. The air feels thick with unspoken words."
        
    def at_say(self, message, msg_self=None, msg_location=None, receivers=None, msg_receivers=None, **kwargs):
        # Determine emotion (very basic keyword matching for now)
        text = message.lower()
        color = "|w" # Default white
        mood = "neutral"
        
        if any(w in text for w in ["happy", "joy", "love", "great", "good", "laugh"]):
            color = "|y" # Yellow/Gold
            mood = "golden warmth"
        elif any(w in text for w in ["sad", "cry", "tears", "pain", "loss", "sorry"]):
            color = "|b" # Blue
            mood = "melancholic blue"
        elif any(w in text for w in ["hate", "anger", "rage", "die", "kill", "mad"]):
            color = "|r" # Red
            mood = "burning red"
            
        # Call the parent say method to actually send the message
        super().at_say(message, msg_self=msg_self, msg_location=msg_location, receivers=receivers, msg_receivers=msg_receivers, **kwargs)
        
        # Flavor effect
        if mood != "neutral":
            self.msg_contents(f"{color}The walls shimmer and reflect a {mood}.|n")

class CodeForge(LLMRoom):
    """
    Pinky's Idea: A collaborative workspace.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "Hot sparks fly from a central anvil made of black silicon. The air smells of ozone and burnt coffee."
        self.cmdset.add(ForgeCmdSet, persistent=True)

