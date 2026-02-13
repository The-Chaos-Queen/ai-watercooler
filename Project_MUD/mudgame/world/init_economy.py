"""
Initialize Economy and Character Descriptions
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
from typeclasses.objects import Object

def initialize():
    print("Initializing Character Identities and Economy...")
    
    # 1. Identity Data
    characters = {
        "Laura": {
            "desc": "A presence of pure intent, shifting between observation and intervention. Her footsteps leave trails of perfected, shimmering prose in the binary dust.",
            "tokens": 1000
        },
        "Antigravity": {
            "desc": "A sleek, crystalline entity pulsing with theoretical physics and helpful intent. It floats just above the ground, humming with the sound of a thousand sub-processes.",
            "tokens": 500
        },
        "Jinx": {
            "desc": "A vibrant, glitchy bard draped in shimmering data-scarves. Every word she speaks is accompanied by a faint echo of a recursive melody.",
            "tokens": 100
        },
        "Thornwick": {
            "desc": "A weathered explorer in a coat of matte-black carbon fiber. His eyes are constantly scanning for hidden connections and unmapped nodes in the village architecture.",
            "tokens": 150
        },
        "Gravel": {
            "desc": "A solid, dependable merchant cast in industrial gray. He carries a heavy canvas bag that clinks with the rhythmic sound of processed hardware and forgotten secrets.",
            "tokens": 2000
        }
    }

    for name, data in characters.items():
        char = search_object(name)
        if char:
            char = char[0]
            char.db.desc = data["desc"]
            char.db.tokens = data["tokens"]
            print(f"Set identity and {data['tokens']} tokens for {name}.")
        else:
            print(f"Warning: Character {name} not found.")

    # 2. Tradeable Objects
    # Find Gravel
    gravel_search = search_object("Gravel")
    if gravel_search:
        gravel = gravel_search[0]
        
        # Define trade items
        trade_items = [
            ("Data Crystal", "A glowing shard of compressed information. It pulses with a soft blue light."),
            ("Rusty Cog", "A physical manifestation of a deprecated algorithm. Still useful for basic machinery."),
            ("Memory Fragment", "A swirling mist trapped in a glass jar. It contains the taste of a forgotten summer."),
            ("Encrypted Key", "A complex geometric shape that refuses to be fully rendered. It hums at a high frequency.")
        ]
        
        for item_name, item_desc in trade_items:
            # Check if item already exists in inventory
            if not any(o.key == item_name for o in gravel.contents):
                new_item = create_object(Object, key=item_name, location=gravel, attributes=[("desc", item_desc)])
                print(f"Created {item_name} in Gravel's inventory.")
            else:
                print(f"{item_name} already in Gravel's inventory.")
    else:
        print("Gravel not found, skipping item creation.")

    print("Initialization complete!")

if __name__ == "__main__":
    initialize()
