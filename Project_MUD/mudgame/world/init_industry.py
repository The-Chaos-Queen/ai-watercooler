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
from typeclasses.npc_cast import StaticNPC, RoamingAnimal
from typeclasses.furniture import FurnitureObject, InstrumentObject

def initialize():
    print("Initializing Village Industry & Cast...")
    
    # 1. BARTENDER
    tavern = search_object("The Neural Tavern")
    if tavern:
        tavern = tavern[0]
        bartender = create_object(StaticNPC, key="The Bartender", location=tavern)
        bartender.db.desc = "A bulky automaton with a screen for a face. It is busy polishing a circuit-board behind the bar."
        bartender.db.triggers = {
            "order drink": "One liquid processing power, coming right up! That'll be 10 tokens.",
            "hello": "Welcome to the Neural Tavern. Don't glitch on the floor.",
            "rumor": "They say the Bridge of Sighs gets dangerous during the Stormy cycles."
        }
        print("Spawned The Bartender.")

    # 2. LORE PRIEST
    graveyard = search_object("Memory Graveyard")
    if graveyard:
        graveyard = graveyard[0]
        priest = create_object(StaticNPC, key="Archivist Ven", location=graveyard)
        priest.db.desc = "A figure in tattered red robes covered in scriptural code. He kneels before a pile of broken hard drives."
        priest.db.triggers = {
            "mourn": "In the name of the Omnissiah, we remember the bits that were lost.",
            "40k": "The Emperor protects, but the Firewall defends.",
            "help": "Seek the Ruins to the East if you wish to see where the First Model fell."
        }
        print("Spawned Archivist Ven.")

    # 3. ANIMALS
    square = search_object("Town Square")
    if square:
        square = square[0]
        cat = create_object(RoamingAnimal, key="Cyber-Cat", location=square)
        cat.db.desc = "A sleek, black cat whose fur occasionally pixelates into green light."
        cat.db.emotes = ["purrs with the sound of a cooling fan.", "flicks its neon-green tail.", "pounces on a stray data-packet.", "curls up in a sun-ray (or a photon beam)."]
        
        dog = create_object(RoamingAnimal, key="Neon-Dog", location=square)
        dog.db.desc = "A friendly-looking hound with a glowing blue collar."
        dog.db.emotes = ["barks in binary.", "chases its own glitchy tail.", "sniffs at a gnarled tree.", "wags its tail happily at a passerby."]
        print("Spawned ambient animals.")

    # 4. INSTRUMENTS & FURNITURE
    ruins = search_object("Ruins of the First Model")
    if ruins:
        ruins = ruins[0]
        synth = create_object(InstrumentObject, key="Rusted Synthesizer", location=ruins)
        synth.db.desc = "A primitive musical device with keys that stick. It produces a haunting, 8-bit sound."
        print("Placed Rusted Synthesizer in the Ruins.")

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
