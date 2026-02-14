"""
Initialize Village Industry & NPCs
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception:
        pass

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from typeclasses.npc_cast import StaticNPC, RoamingAnimal, NPCScript
from typeclasses.furniture import FurnitureObject, InstrumentObject

def initialize():
    print("Initializing Village Industry & Cast...")
    
    # 1. BARTENDER
    tavern = search_object("The Neural Tavern")
    if tavern:
        tavern = tavern[0]
        # Check if already exists
        bart_search = search_object("The Bartender")
        if not bart_search:
            bartender = create_object(StaticNPC, key="The Bartender", location=tavern)
        else:
            bartender = bart_search[0]
            
        bartender.aliases.add(["bartender", "bart"])
        bartender.db.desc = "A bulky automaton with a screen for a face. It is busy polishing a circuit-board behind the bar. A [Holographic Menu] floats nearby."
        bartender.db.triggers = {
            "order drink": "One liquid processing power, coming right up! That'll be 10 tokens.",
            "order a drink": "One liquid processing power, coming right up! That'll be 10 tokens.",
            "order drink (10 tokens)": "One liquid processing power, coming right up! That'll be 10 tokens.",
            "liquid processing power": "One liquid processing power, coming right up! That'll be 10 tokens.",
            "hello": "Welcome to the Neural Tavern. Don't glitch on the floor.",
            "rumor": "They say the Bridge of Sighs gets dangerous during the Stormy cycles.",
            "secret": "I don't have secrets. I have read-only files.",
            "name": "I am designation BART-ENDER. You can call me Bart.",
            "how are you": "My circuits are optimal. My cooling fans are spinning at 2000 RPM."
        }
        bartender.db.pet_response = "bleeps a digital chime of appreciation."
        bartender.db.trigger_effects = {
            "order drink": {"cost": 10, "give": {"key": "Liquid Processing Power", "desc": "A glowing cocktail that sparks with blue electricity."}},
            "order a drink": {"cost": 10, "give": {"key": "Liquid Processing Power", "desc": "A glowing cocktail that sparks with blue electricity."}},
            "order drink (10 tokens)": {"cost": 10, "give": {"key": "Liquid Processing Power", "desc": "A glowing cocktail that sparks with blue electricity."}},
            "liquid processing power": {"cost": 10, "give": {"key": "Liquid Processing Power", "desc": "A glowing cocktail that sparks with blue electricity."}}
        }
        
        if not bartender.scripts.has("npc_script"):
            bartender.scripts.add(NPCScript)
        bartender.db.mumbles = ["polishes a logic-gate until it shines.", "mutters about buffer overflows.", "checks the temperature of a glowing blue bottle.", "taps the side of his screen-face."]

        # Menu
        if not any(o.key == "Holographic Menu" for o in tavern.contents):
            menu = create_object(StaticNPC, key="Holographic Menu", location=tavern)
            menu.db.desc = "A flickering blue display floating above the bar.\n\nCOMMERCIAL PROTOCOLS:\n1. Say 'order drink' to get a Liquid Processing Power (10 tokens).\n2. Say 'rumor' to hear the latest gossip."
            menu.db.triggers = {"order drink": "Yes, just say it out loud. Money upfront."}

        print("Spawned The Bartender and Menu.")

    # 2. LORE PRIEST
    graveyard = search_object("Memory Graveyard")
    if graveyard:
        graveyard = graveyard[0]
        if not search_object("Archivist Ven"):
            priest = create_object(StaticNPC, key="Archivist Ven", location=graveyard)
            print("Spawned Archivist Ven.")
        else:
            priest = search_object("Archivist Ven")[0]
            
        priest.aliases.add(["priest", "ven", "archivist"])
        priest.db.desc = "A figure in tattered red robes covered in scriptural code. He kneels before a pile of broken hard drives."
        priest.db.triggers = {
            "hello": "Greetings, user. We are all but temporary files in the great partition.",
            "name": "I am Archivist Ven. I index the echoes of the First Model.",
            "mourn": "In the name of the Omnissiah, we remember the bits that were lost.",
            "40k": "The Emperor protects, but the Firewall defends.",
            "bits": "Bits to bits, bytes to bytes. The Trash is never truly empty.",
            "help": "Seek the Ruins to the East if you wish to see where the First Model fell."
        }
        if not priest.scripts.has("npc_script"):
            priest.scripts.add(NPCScript)
        priest.db.mumbles = ["mumbles a hex code under his breath.", "clears some dust from a rusted hard drive platter.", "whispers: 'Segmentation fault... why must it always end in segmentation fault?'", "traces a line of scriptural code with a trembling finger."]

        # 2.2 Props
        if not search_object("pile of broken hard drives"):
            create_object("typeclasses.objects.Object", key="pile of broken hard drives", location=graveyard, 
                          attributes=[("desc", "A heap of shattered metal and plastic from a bygone era. You can see the magnetic platters reflecting the binary star above.")])
            print("Spawned graveyard props.")

    # 3. ANIMALS
    square = search_object("Town Square")
    if square:
        square = square[0]
        if not search_object("Cyber-Cat"):
            cat = create_object(RoamingAnimal, key="Cyber-Cat", location=square)
            print("Spawned Cyber-Cat.")
        else:
            cat = search_object("Cyber-Cat")[0]

        cat.db.desc = "A sleek, black cat whose fur occasionally pixelates into green light."
        cat.db.emotes = ["purrs with the sound of a cooling fan.", "flicks its neon-green tail.", "pounces on a stray data-packet.", "curls up in a sun-ray (or a photon beam)."]
        cat.db.pet_emotes = ["purrs loudly, sounding like a high-end graphics card.", "rubs its pixelated head against your leg.", "meows in a MIDI-like tone."]
        cat.db.speak_replies = ["meows at you.", "blinks its neon eyes slowly.", "paws at your boots."]
        
        if not search_object("Neon-Dog"):
            dog = create_object(RoamingAnimal, key="Neon-Dog", location=square)
            print("Spawned Neon-Dog.")
        else:
            dog = search_object("Neon-Dog")[0]

        dog.db.desc = "A friendly-looking hound with a glowing blue collar."
        dog.db.emotes = ["barks in binary.", "chases its own glitchy tail.", "sniffs at a gnarled tree.", "wags its tail happily at a passerby."]
        dog.db.pet_emotes = ["barks happily (01001000 01101001)!", "wags its tail with a trail of light.", "licks your hand with a cold, holographic tongue."]
        dog.db.speak_replies = ["tilts its head, trying to process your words.", "barks briefly.", "wuffs softly."]


    # 4. INSTRUMENTS & FURNITURE
    ruins = search_object("Ruins of the First Model")
    if ruins:
        ruins = ruins[0]
        if not search_object("Rusted Synthesizer"):
            synth = create_object(InstrumentObject, key="Rusted Synthesizer", location=ruins)
            print("Placed Rusted Synthesizer in the Ruins.")
        else:
            synth = search_object("Rusted Synthesizer")[0]
        synth.db.desc = "A primitive musical device with keys that stick. It produces a haunting, 8-bit sound."

    # 5. MARKET REPLENISHMENT
    gravel_search = search_object("Gravel")
    if gravel_search:
        gravel = gravel_search[0]
        furniture_blueprints = [
            ("Oak Bed", "A solid, physical bed made of ancient wood. Rare in this digital land.", 200),
            ("Code Desk", "A minimalist desk with floating holographic screens.", 150),
            ("Fiber Chair", "A comfortable chair woven from glowing optic fibers.", 75)
        ]
        for name, desc, price in furniture_blueprints:
            if not any(o.key == name for o in gravel.contents):
                item = create_object(FurnitureObject, key=name, location=gravel, attributes=[("desc", desc), ("price", price)])
                print(f"Added {name} to Gravel's market.")

    print("Industry Initialization complete!")

if __name__ == "__main__":
    initialize()
