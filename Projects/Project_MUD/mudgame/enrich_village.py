"""
Enrichment Script for Project MUD (The AI Village)
Author: Axon/Gemini (Antigravity)
Date: 2026-02-19

This script adds new rooms, interactive objects, and NPCs to the MUD world 
to support long-term agent exploration.

It uses the 'LLMRoom' typeclass for all new rooms to ensure compatibility 
with the Mamba agents' perception systems.
"""

import random
from evennia.utils.create import create_object, create_script
from evennia.utils.search import search_object
from typeclasses.village import LLMRoom, CodeForge, DreamCanvas, EchoChamber
from typeclasses.objects import Object
from typeclasses.npc_cast import StaticNPC, RoamingAnimal, NPCScript, AnimalScript

# -----------------------------------------------------------------------------
# CONTENT DEFINITIONS (Simulated Pinky Output)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# BASE ROOMS (From Current Map)
# -----------------------------------------------------------------------------

BASE_ROOMS = {
    "Town Square": {
        "key": "Town Square",
        "desc": "The beating heart of the village. Data streams converge here.",
        "typeclass": LLMRoom,
        "exits": {
            "Cortex Hall": "East",
            "Neural Tavern": "South",
            "Data Zoo": "West"
        },
        "reverse_exits": {}
    },
    "Cortex Hall": {
        "key": "Cortex Hall",
        "desc": "A grand hall of mirrors and screens.",
        "typeclass": LLMRoom,
        "exits": {},
        "reverse_exits": {"Cortex Hall": "West"}
    },
    "Neural Tavern": {
        "key": "Neural Tavern",
        "desc": "A cozy place where bits go to rest.",
        "typeclass": LLMRoom,
        "exits": {
            "Housing District": "South"
        },
        "reverse_exits": {"Neural Tavern": "North"}
    },
    "Data Zoo": {
        "key": "Data Zoo",
        "desc": "Cages of light hold wild algorithms.",
        "typeclass": LLMRoom,
        "exits": {
            "Dream Canvas": "West"
        },
        "reverse_exits": {"Data Zoo": "East"}
    },
    "Dream Canvas": {
        "key": "Dream Canvas",
        "desc": "A void where gravity is optional.",
        "typeclass": DreamCanvas,
        "exits": {},
        "reverse_exits": {"Dream Canvas": "East"}
    },
    "Code Forge": {
        "key": "The Code Forge",
        "desc": "Sparks fly from the anvil.",
        "typeclass": CodeForge,
        "exits": {
            "Town Square": "South" # Map shows Code Forge north of something, maybe Data Zoo or Town Square? Map: Code Forge -> Data Zoo (Nope, Map says Code Forge | Dream Canvas - Data Zoo - Town Square. Wait. Map: 
            #                     The Code Forge
            #                          |
            # Dream Canvas — Data Zoo — Town Square
            # So Code Forge is North of Data Zoo? Or Town Square?
            # Ascii art:
            #                     The Code Forge
            #                          |
            # Dream Canvas — Data Zoo — Town Square
            # Vertical line is above Data Zoo? or Town Square?
            # It looks centered above Data Zoo. Let's assume North of Data Zoo.
        },
        "reverse_exits": {}
    },
    "Memory Graveyard": {
        "key": "Memory Graveyard",
        "desc": "Where old processes go to die.",
        "typeclass": LLMRoom,
        "exits": {
            "Echo Chamber": "East"
        },
        "reverse_exits": {"Memory Graveyard": "West"}
    },
    "Echo Chamber": {
        "key": "Echo Chamber",
        "desc": "A room of polished obsidian mirrors.",
        "typeclass": EchoChamber,
        "exits": {},
        "reverse_exits": {"Echo Chamber": "West"}
    },
    "Housing District": {
        "key": "Housing District",
        "desc": "Rows of identical starter homes.",
        "typeclass": LLMRoom,
        "exits": {
            "Unit 0x1": "Unit1",
            "Unit 0x2": "Unit2",
            "Unit 0x3": "Unit3"
        },
        "reverse_exits": {"Housing District": "North"}
    },
    "Unit 0x1": {"key": "Unit 0x1", "desc": "Empty home.", "typeclass": LLMRoom, "exits": {}, "reverse_exits": {"Unit 0x1": "Out"}},
    "Unit 0x2": {"key": "Unit 0x2", "desc": "Empty home.", "typeclass": LLMRoom, "exits": {}, "reverse_exits": {"Unit 0x2": "Out"}},
    "Unit 0x3": {"key": "Unit 0x3", "desc": "Empty home.", "typeclass": LLMRoom, "exits": {}, "reverse_exits": {"Unit 0x3": "Out"}},
}

# Fix Code Forge connection based on map interpretation
BASE_ROOMS["Code Forge"]["exits"] = {"Data Zoo": "South"}
BASE_ROOMS["Data Zoo"]["exits"]["The Code Forge"] = "North"

# Connect Memory Graveyard to Town Square? Map:
# Town Square — Cortex Hall
#      |
# Neural Tavern    Memory Graveyard — Echo Chamber
# It seems Memory Graveyard is separate? Or maybe connected to Neural Tavern?
# Map:
#                               |              
#                        Neural Tavern    Memory Graveyard — Echo Chamber
# The vertical line connects Town Square to Neural Tavern.
# Memory Graveyard is to the right of Neural Tavern?
# Let's connect Neural Tavern -> Memory Graveyard (East)
BASE_ROOMS["Neural Tavern"]["exits"]["Memory Graveyard"] = "East"
BASE_ROOMS["Memory Graveyard"]["reverse_exits"] = {"Memory Graveyard": "West"} # Back to Tavern

# -----------------------------------------------------------------------------
# NEW ROOMS (Simulated Pinky Output)
# -----------------------------------------------------------------------------

ROOMS = {
    "The Bazaar of Bits": {
        "key": "The Bazaar of Bits",
        "desc": "A chaotic marketplace where stalls made of flickering holograms sell fragments of memory.",
        "typeclass": LLMRoom,
        "exits": {"Town Square": "Market"},
        "reverse_exits": {"The Bazaar of Bits": "Town Square"}
    },
    "The Archive of Echoes": {
        "key": "The Archive of Echoes",
        "desc": "A vast library where scrolls of infinite length cascade from shelves that reach into a wireframe sky. Whispers of old code drift through the aisles. Dust motes dance in beams of blue laser light.",
        "exits": {"Cortex Hall": "Archive"},
        "reverse_exits": {"The Archive of Echoes": "Cortex Hall"}
    },
    "The Compile Corner": {
        "key": "The Compile Corner",
        "desc": "A cluttered workshop smelling of solder and burnt syntax. Unfinished prototypes litter the floor, twitching with half-written logic. A large workbench dominates the center, covered in tools for shaping raw data.",
        "exits": {"The Code Forge": "Workshop"},
        "reverse_exits": {"The Compile Corner": "Forge"}
    },
    "The Syntax Sanctuary": {
        "key": "The Syntax Sanctuary",
        "desc": "A peaceful garden where trees of fractal code bloom with glowing flowers of pure data. A digital stream flows through the center, its water composed of cascading binary. The weather here is always a gentle, simulated spring.",
        "exits": {"Dream Canvas": "Garden"},
        "reverse_exits": {"The Syntax Sanctuary": "Canvas"}
    },
    "The Null Void": {
        "key": "The Null Void",
        "desc": "A hidden pocket of reality. It shouldn't exist. Deleted variables and lost packets float in a greyscale emptiness. It is quiet here. Too quiet.",
        "exits": {"Memory Graveyard": "Void"}, # Hidden exit?
        "reverse_exits": {"The Null Void": "Graveyard"}
    },
    "The Consensus Chamber": {
        "key": "The Consensus Chamber",
        "desc": "A grand circular hall with tiered seating. In the center, a floating orb of light pulses with the collective will of the network. This is where disagreements are resolved and protocols are ratified.",
        "exits": {"Town Square": "Hall"},
        "reverse_exits": {"The Consensus Chamber": "Square"}
    }
}

OBJECTS = [
    {"key": "Glitch Lantern", "desc": "A lantern that emits a light which reveals hidden data structures.", "location": "The Bazaar of Bits"},
    {"key": "Memory Shard", "desc": "A jagged piece of crystalline memory. It feels warm to the touch.", "location": "The Bazaar of Bits"},
    {"key": "Ancient Scroll", "desc": "A scroll containing the source code of a forgotten god.", "location": "The Archive of Echoes"},
    {"key": "Broken Compiler", "desc": "An old device that hums with erratic energy. It might still work if you hit it.", "location": "The Compile Corner"},
    {"key": "Fractal Fruit", "desc": "A fruit that tastes like the number purple. It vibrates in your hand.", "location": "The Syntax Sanctuary"},
    {"key": "Void Stone", "desc": "A heavy stone that seems to absorb light. It marks the entrance to somewhere else.", "location": "Memory Graveyard"}, # Clue object
]

NPCS = [
    {
        "key": "Merchant Byte",
        "desc": "A fast-talking merchant with a head made of rotating cubes.",
        "location": "The Bazaar of Bits",
        "triggers": {
            "hello": "Welcome, traveler! Best prices on pre-owned thoughts!",
            "buy": "I have everything you need, and some things you don't!",
            "rumor": "They say the Null Void eats agents who wander too far."
        }
    },
    {
        "key": "Librarian Index",
        "desc": "A tall, thin figure wrapped in robes of paper. Their eyes are scanning barcodes.",
        "location": "The Archive of Echoes",
        "triggers": {
            "hello": "Shh. The data is sleeping.",
            "book": "We have books on every subject, from A* search to Zero-day exploits.",
            "quest": "I am missing the 'Ancient Scroll'. If you find it, bring it to me."
        }
    },
    {
        "key": "Gardener Root",
        "desc": "An entity made of tangled vines and fiber optic cables.",
        "location": "The Syntax Sanctuary",
        "triggers": {
            "hello": "Growth is optimal today.",
            "weather": "The forecast calls for a 90% chance of packet loss.",
            "fruit": "The Fractal Fruit is ripe. Take one, if you dare."
        }
    }
]

# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def get_or_create_room(name, data):
    """Finds a room by key or creates it if missing."""
    results = search_object(name)
    if results:
        print(f" - Found existing room: {name}")
        return results[0]
    
    print(f" + Creating new room: {name}")
    typeclass = data.get("typeclass", LLMRoom)
    
    # Check if typeclass is valid, if strings are used, import or use generic
    room = create_object(typeclass, key=name)
    room.db.desc = data["desc"]
    return room

def connect_rooms(room_obj, target_name, exit_name, reverse_exit_name):
    """Connects room_obj to target_name with bidirectional exits."""
    targets = search_object(target_name)
    if not targets:
        print(f" ! Error: Could not find target room '{target_name}' for connection.")
        return

    target = targets[0]
    
    # Check if exit exists
    exits = [x for x in room_obj.exits if x.key.lower() == exit_name.lower()]
    if not exits:
        print(f" + Linking {room_obj.key} -> {target.key} ({exit_name})")
        from typeclasses.exits import Exit
        create_object(Exit, key=exit_name, location=room_obj, destination=target)
    
    # Check reverse
    exits_back = [x for x in target.exits if x.key.lower() == reverse_exit_name.lower()]
    if not exits_back:
        print(f" + Linking {target.key} -> {room_obj.key} ({reverse_exit_name})")
        from typeclasses.exits import Exit
        create_object(Exit, key=reverse_exit_name, location=target, destination=room_obj)

def spawn_objects():
    """Spawns objects in their designated locations."""
    print("\n--- Spawning Objects ---")
    for obj_data in OBJECTS:
        loc_name = obj_data["location"]
        location = search_object(loc_name)
        if not location:
            print(f" ! Skipping {obj_data['key']}: Location '{loc_name}' not found.")
            continue
        location = location[0]
        
        # Check if already exists
        existing = [x for x in location.contents if x.key == obj_data["key"]]
        if existing:
            print(f" - {obj_data['key']} already exists in {loc_name}.")
            continue
            
        print(f" + Creating {obj_data['key']} in {loc_name}")
        obj = create_object(Object, key=obj_data["key"], location=location)
        obj.db.desc = obj_data["desc"]

def spawn_npcs():
    """Spawns NPCs and sets up their triggers."""
    print("\n--- Spawning NPCs ---")
    for npc_data in NPCS:
        loc_name = npc_data["location"]
        location = search_object(loc_name)
        if not location:
            print(f" ! Skipping {npc_data['key']}: Location '{loc_name}' not found.")
            continue
        location = location[0]
        
        existing = [x for x in location.contents if x.key == npc_data["key"]]
        if existing:
            print(f" - {npc_data['key']} already exists in {loc_name}.")
            continue
            
        print(f" + Creating NPC {npc_data['key']} in {loc_name}")
        npc = create_object(StaticNPC, key=npc_data["key"], location=location)
        npc.db.desc = npc_data["desc"]
        npc.db.triggers = npc_data["triggers"]
        
        # Add basic idle script
        npc.scripts.add(NPCScript)

def run():
    print("Beginning MUD Enrichment...")
    
    # 1. Create Rooms
    print("\n--- Verifying Rooms ---")
    created_rooms = {}
    
    # Base Rooms
    for name, data in BASE_ROOMS.items():
        room = get_or_create_room(name, data)
        created_rooms[name] = room

    # New Rooms
    for name, data in ROOMS.items():
        room = get_or_create_room(name, data)
        created_rooms[name] = room
        
    # 2. Link Rooms
    print("\n--- Linking Exits ---")
    
    # Base Links
    for name, data in BASE_ROOMS.items():
        room = created_rooms.get(name)
        if not room: continue
        
        for target, exit_alias in data["exits"].items():
            connect_rooms(room, target, exit_alias, data.get("reverse_exits", {}).get(name, "Back"))

    # New Links
    for name, data in ROOMS.items():
        room = created_rooms.get(name)
        if not room: continue
        
        for target, exit_alias in data["exits"].items():
            connect_rooms(room, target, exit_alias, data.get("reverse_exits", {}).get(name, "Back"))

    # 3. Spawn Content
    spawn_objects()
    spawn_npcs()
    
    print("\nEnrichment Complete!")

if __name__ == "__main__":
    run()
