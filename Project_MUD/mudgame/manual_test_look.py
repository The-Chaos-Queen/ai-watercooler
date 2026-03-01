
import os
import sys
import django
import json
from unittest.mock import MagicMock

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from typeclasses.village import LLMRoom

def test_smart_look():
    print("--- Testing Smart Look Logic ---")
    
    # 1. Get Town Square
    town_square = search_object("Town Square")[0]
    print(f"Target Room: {town_square.key}")
    
    # 2. Mock a caller
    caller = MagicMock()
    caller.location = town_square
    caller.key = "TestAgent"
    
    # 3. Replicate smart_look logic (simplified) to avoid command instantiations
    # Copied logic from smart_look.py return_json_state
    
    location = caller.location
    players = []
    npcs = []
    items = []
    
    for obj in location.contents:
        if obj == caller: continue
        name = obj.key
        
        # Safe check for account
        is_player = False
        try:
            if obj.account:
                is_player = True
        except:
            pass
            
        if is_player: players.append(name)
        elif obj.is_typeclass("typeclasses.npc_cast.StaticNPC"): npcs.append(name)
        else: items.append(name)

    exits = [ex.key.lower() for ex in location.exits]
    
    data = {
        "location": {
            "name": location.key,
            "description": location.db.desc,
            "exits": exits
        },
        "entities": {
            "players": players,
            "npcs": npcs,
            "items": items
        }
    }
    
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(data, indent=2))
    print("--- END JSON ---")

if __name__ == "__main__":
    test_smart_look()
