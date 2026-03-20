from typeclasses.objects import Object
from evennia.scripts.scripts import DefaultScript
import random

class StaticNPC(Object):
    """
    An NPC that responds to specific triggers but doesn't move.
    """
    def at_object_creation(self):
        self.db.triggers = {}  # Map of regex/string to response

    def msg(self, text, from_obj=None, **kwargs):
        """
        Intercept messages to search for triggers.
        """
        super().msg(text, from_obj=from_obj, **kwargs)
        
        # Handle tuple or string
        content = text[0] if isinstance(text, (list, tuple)) else text
        if not isinstance(content, str):
            return

        # Simple extraction: anything between the first and last quote
        if '"' in content:
            try:
                actual_speech = content.split('"')[1]
                self.at_say(actual_speech, from_obj)
            except Exception:
                pass
        # Fallback for systems that don't use quotes
        elif 'says:' in content:
             self.at_say(content.split('says:')[1].strip(), from_obj)

    def at_say(self, message, speaker, **kwargs):
        """Called when someone speaks or uses CmdBar."""
        if not message: return
        
        # Cooldown check (2 seconds for responsiveness)
        import time
        now = time.time()
        last_time = self.db.last_trigger_time or 0
        if now - last_time < 2:
            return
        
        msg_text = message.lower()
        for trigger, response in self.db.triggers.items():
            if trigger in msg_text:
                self.db.last_trigger_time = now
                # Handle special effects
                effects = self.db.trigger_effects or {}
                effect = effects.get(trigger)
                
                if effect and speaker:
                    # Token check (e.g., "cost": 10)
                    cost = effect.get("cost", 0)
                    if cost > 0:
                        tokens = speaker.db.tokens or 0
                        if tokens < cost:
                            self.location.msg_contents(f'{self.key} says: "You need {cost} tokens for that, and you only have {tokens}."')
                            return
                        speaker.db.tokens = tokens - cost
                        speaker.msg(f"|r-{cost} tokens|n")

                    # Item give (e.g., "give": {"key": "Drink", "desc": "..."})
                    give_info = effect.get("give")
                    if give_info:
                        from evennia.utils.create import create_object
                        from typeclasses.objects import Object
                        item = create_object(Object, key=give_info["key"], location=speaker, attributes=[("desc", give_info["desc"])])
                        speaker.msg(f"|gThe {self.key} slides a {give_info['key']} across the counter to you.|n")
                        self.location.msg_contents(f"{self.key} slides a {give_info['key']} to {speaker.key}.", exclude=[speaker])

                self.location.msg_contents(f'{self.key} says: "{response}"')
                return

    def at_pet(self, petter):
        """Called when someone pets the NPC."""
        # Special pet response if defined
        pet_msg = self.db.pet_response or "looks at you with quiet appreciation."
        self.location.msg_contents(f"{self.key} {pet_msg}")

class RoamingAnimal(Object):
    """
    A simple animal that emotes occasionally and responds to petting.
    """
    def at_object_creation(self):
        self.scripts.add(AnimalScript)
        self.db.triggers = {}

    def at_pet(self, petter):
        """Called when someone pets the animal."""
        pet_emotes = self.db.pet_emotes or ["purrs loudly.", "wags its tail.", "nuzzles your hand."]
        self.location.msg_contents(f"{self.key} {random.choice(pet_emotes)}")

    def at_say(self, message, speaker, **kwargs):
        """Animals might 'reply' with an emote when spoken to."""
        msg = message.lower()
        replies = self.db.speak_replies or ["tilts its head at you.", "makes a soft noise.", "looks curious."]
        # 50% chance to react to speech
        if random.random() < 0.5:
            self.location.msg_contents(f"{self.key} {random.choice(replies)}")

class NPCScript(DefaultScript):
    """
    Script to handle idle NPC behavior (mumbling, movements, etc).
    """
    def at_script_creation(self):
        self.key = "npc_script"
        self.interval = 45  # Every 45 seconds
        self.persistent = True

    def at_repeat(self):
        npc = self.obj
        if not npc or not npc.location:
            return
            
        # Idle mumbles/emotes
        mumbles = npc.db.mumbles or []
        if mumbles and random.random() < 0.4:
            npc.location.msg_contents(f"{npc.key} {random.choice(mumbles)}")

class AnimalScript(DefaultScript):
    """
    Script to handle animal behavior.
    """
    def at_script_creation(self):
        self.key = "animal_script"
        self.interval = 30  # Every 30 seconds for more life
        self.persistent = True

    def at_repeat(self):
        animal = self.obj
        # Emotes
        if random.random() < 0.7:  # 70% chance to emote each tick
            emotes = getattr(animal.db, "emotes", ["looks around.", "makes a noise."])
            emote = random.choice(emotes)
            animal.location.msg_contents(f"{animal.key} {emote}")
        
        # 20% chance to roam to a random exit
        if random.random() < 0.2:
            exits = animal.location.exits
            if exits:
                target = random.choice(exits)
                animal.location.msg_contents(f"{animal.key} wanders away toward the {target.key}.")
                animal.move_to(target.destination)
                animal.location.msg_contents(f"{animal.key} wanders in.")
class DialogNPC(StaticNPC):
    """
    An NPC that supports menu-driven dialog.
    Triggered by 'talk <npc>'.
    Responds to A, B, C while in a dialog state.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.dialog_tree = {
            "start": {
                "text": "Hello, I am a dialog NPC.",
                "options": [
                    ("A", "Ask about the quest", "quest"),
                    ("B", "Ask about the weather", "weather"),
                    ("C", "Say goodbye", "end")
                ]
            },
            "news": {
                "text": "I have no news for you.",
                "options": [
                    ("C", "Back", "start")
                ]
            }
        }

    def at_talk(self, caller):
        """Called by the 'talk' command."""
        self.display_dialog(caller, "start")

    def display_dialog(self, caller, node_key):
        """Displays a node of the dialog tree to the caller."""
        if node_key == "end":
            caller.msg(f"{self.key} nods as you conclude the conversation.")
            if self.key in caller.ndb.active_dialogs:
                del caller.ndb.active_dialogs[self.key]
            return

        node = self.db.dialog_tree.get(node_key)
        if not node:
            caller.msg(f"{self.key} seems to have lost their train of thought.")
            return

        # Track state on the caller
        if not caller.ndb.active_dialogs:
            caller.ndb.active_dialogs = {}
        caller.ndb.active_dialogs[self.key] = node_key

        # Construct message
        msg = f"|w{self.key}|n says: \"{node['text']}\"\n"
        for opt_key, opt_desc, _ in node["options"]:
            msg += f"  |g[{opt_key}]|n {opt_desc}\n"
        
        caller.msg(msg)

    def at_say(self, message, speaker, **kwargs):
        """Intercept A/B/C if in dialog state."""
        if not speaker or not speaker.ndb.active_dialogs or self.key not in speaker.ndb.active_dialogs:
            # Fallback to static trigger logic if not in a dialog menu
            super().at_say(message, speaker, **kwargs)
            return

        node_key = speaker.ndb.active_dialogs[self.key]
        node = self.db.dialog_tree.get(node_key)
        
        choice = message.strip().upper()
        if len(choice) > 1: # Just check first letter if they said 'say A'
             if choice.startswith("LIFT "): choice = choice[5:] # handle some common prefixes
             choice = choice[0]

        for opt_key, _, next_node in node["options"]:
            if choice == opt_key.upper():
                self.display_dialog(speaker, next_node)
                return

        # If they said something else and we are in dialog, maybe they want to ignore the menu?
        # Or just repeat the menu.
        super().at_say(message, speaker, **kwargs)
