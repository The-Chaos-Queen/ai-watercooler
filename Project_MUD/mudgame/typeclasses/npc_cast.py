from typeclasses.objects import Object
from evennia.scripts.scripts import DefaultScript
import random

class StaticNPC(Object):
    """
    An NPC that responds to specific triggers but doesn't move.
    """
    def at_object_creation(self):
        self.db.triggers = {}  # Map of regex/string to response

    def at_say(self, message, speaker, **kwargs):
        """Called when someone speaks in the same room."""
        msg = message.lower()
        for trigger, response in self.db.triggers.items():
            if trigger in msg:
                self.location.msg_contents(f'{self.key} says: "{response}"')
                return

class RoamingAnimal(Object):
    """
    A simple animal that emotes occasionally.
    """
    def at_object_creation(self):
        self.scripts.add(AnimalScript)

class AnimalScript(DefaultScript):
    """
    Script to handle animal behavior.
    """
    def at_script_creation(self):
        self.key = "animal_script"
        self.interval = 60  # Every minute
        self.persistent = True

    def at_repeat(self):
        animal = self.obj
        emotes = getattr(animal.db, "emotes", ["looks around.", "makes a noise."])
        emote = random.choice(emotes)
        animal.location.msg_contents(f"{animal.key} {emote}")
        
        # 10% chance to roam to a random exit
        if random.random() < 0.1:
            exits = animal.location.exits
            if exits:
                target = random.choice(exits)
                animal.location.msg_contents(f"{animal.key} wanders away toward the {target.key}.")
                animal.move_to(target.destination)
                animal.location.msg_contents(f"{animal.key} wanders in from the {target.reverse_exit if hasattr(target, 'reverse_exit') else 'somewhere'}.")
