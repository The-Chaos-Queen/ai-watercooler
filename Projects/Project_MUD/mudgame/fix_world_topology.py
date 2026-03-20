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

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB
from typeclasses.exits import Exit
from typeclasses.village import LLMRoom  # Assuming this exists

def get_or_create_room(key, desc=""):
    rooms = search_object(key)
    if rooms:
        r = rooms[0]
        if desc and not r.db.desc:
            r.db.desc = desc
            r.save()
        print(f"Found existing room: {r} (#{r.id})")
        return r
    
    print(f"Creating new room: {key}")
    # Default to LLMRoom if available, else standard Room
    try:
        r = create_object("typeclasses.village.LLMRoom", key=key)
    except:
        r = create_object("typeclasses.rooms.Room", key=key)
    
    if desc:
        r.db.desc = desc
    r.save()
    return r

def ensure_exit(source, dest, key, aliases=[], desc=""):
    # Check if exit exists
    exits = [x for x in source.exits if x.destination == dest]
    if exits:
        ex = exits[0]
        if ex.key != key:
            print(f"Renaming exit {ex.key} -> {key} in {source.key}")
            ex.key = key
        # Merge aliases
        if aliases:
            ex.aliases.add(aliases)
        if desc:
            ex.db.desc = desc
        ex.save()
        return ex
    
    # Create
    print(f"Creating exit: {source.key} -> {dest.key} ({key})")
    ex = create_object(Exit, key=key, location=source, destination=dest)
    if aliases:
        ex.aliases.add(aliases)
    if desc:
        ex.db.desc = desc
    ex.save()
    return ex

def fix_topology():
    print("Beginning World Topology Repair...")

    # 1. Define Hub Rooms
    # We use get_or_create to be safe
    square = get_or_create_room("Town Square", "The bustling center of the AI Village.")
    tavern = get_or_create_room("The Neural Tavern", "A cozy place where bots exchange tokens.")
    bazaar = get_or_create_room("The Binary Bazaar", "Glowing cables and recycled server racks.")
    graveyard = get_or_create_room("Memory Graveyard", "Rows of static data structures.")
    hall = get_or_create_room("Cortex Hall", "The administrative heart.")
    zoo = get_or_create_room("Data Zoo", "A secure enclosure for wild data.")
    forge = get_or_create_room("The Code Forge", "A workshop of creation.")
    district = get_or_create_room("Housing District", "Quiet path lined with empty plots.")
    
    # 2. Link Hub (Using the layout from rebuild_world_links + additions)
    
    # Square <-> Tavern (North)
    ensure_exit(square, tavern, "The Neural Tavern", ["north", "n", "tavern"], "To the north, the neon sign of the tavern flickers.")
    ensure_exit(tavern, square, "Town Square", ["south", "s", "out", "square"], "Doors leading back to the square.")
    
    # Square <-> Graveyard (East)
    ensure_exit(square, graveyard, "Memory Graveyard", ["east", "e", "graveyard"], "To the east, the silence of the graveyard calls.")
    ensure_exit(graveyard, square, "Town Square", ["west", "w", "square"], "The path leads back to the bustle.")
    
    # Square <-> Bazaar (West)
    ensure_exit(square, bazaar, "The Binary Bazaar", ["west", "w", "bazaar"], "To the west, the market lights glow.")
    ensure_exit(bazaar, square, "Town Square", ["east", "e", "exit"], "Back to the main square.")
    
    # Square <-> Cortex Hall (Up)
    ensure_exit(square, hall, "Cortex Hall", ["up", "u", "hall"], "Steps lead up to the Hall.")
    ensure_exit(hall, square, "Town Square", ["down", "d", "square"], "Steps lead down to the square.")
    
    # Square <-> Housing District (South) - NEW DECISION
    ensure_exit(square, district, "Housing District", ["south", "s", "district", "homes"], "To the south lies the residential area.")
    ensure_exit(district, square, "Town Square", ["north", "n", "square"], "The road leads back to the center.")
    
    # Bazaar <-> Zoo (West of Bazaar)
    ensure_exit(bazaar, zoo, "Data Zoo", ["west", "w", "zoo"], "The entrance to the zoo.")
    ensure_exit(zoo, bazaar, "The Binary Bazaar", ["east", "e", "bazaar"], "Back to the market.")
    
    # Bazaar <-> Forge (North of Bazaar)
    ensure_exit(bazaar, forge, "The Code Forge", ["north", "n", "forge"], "The sounds of the forge come from the north.")
    ensure_exit(forge, bazaar, "The Binary Bazaar", ["south", "s", "bazaar"], "Back to the market.")

    # 3. Handle Ruins & Bridge (South-East?)
    # "The Bridge of Sighs" (#157) and "Ruins of the First Model" (#158) exist
    bridge = get_or_create_room("The Bridge of Sighs")
    ruins = get_or_create_room("Ruins of the First Model")
    
    # Link Square -> Bridge (Let's use "SouthEast")
    # Evennia supports standard directions. 'se' is good.
    ensure_exit(square, bridge, "The Bridge of Sighs", ["southeast", "se", "bridge"], "A path leads southeast to a precarious bridge.")
    ensure_exit(bridge, square, "Town Square", ["northwest", "nw", "square"], "Back to safety.")
    
    # Bridge -> Ruins (East)
    ensure_exit(bridge, ruins, "Ruins of the First Model", ["east", "e", "ruins"], "Across the bridge lie the ruins.")
    ensure_exit(ruins, bridge, "The Bridge of Sighs", ["west", "w", "bridge"], "Back across the bridge.")

    # 4. Handle The Old Well (Down/Hidden from Square)
    # Check if well object exists in Square or is a room
    # setup_well.py creates an OBJECT 'old well' in the square.
    # rebuild_world_links.py created an EXIT 'down' to 'The Old Well'.
    # Does "The Old Well" room exist? The audit showed Room #181.
    well_room = get_or_create_room("The Old Well")
    
    # Link Square <-> Well Room
    ensure_exit(square, well_room, "down", ["climb down", "d", "well"], "You descend into the well.")
    ensure_exit(well_room, square, "up", ["climb up", "u", "out"], "Climb back up.")

    print("Topology Fix Complete.")

if __name__ == "__main__":
    fix_topology()
