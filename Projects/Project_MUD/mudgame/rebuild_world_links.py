
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
from typeclasses.exits import Exit

def link(room1_name, room2_name, exit_to_2_name, exit_to_1_name, to_2_aliases=None, to_1_aliases=None, to_2_desc="", to_1_desc="", hidden=False):
    r1 = search_object(room1_name)
    r2 = search_object(room2_name)
    
    if not r1 or not r2:
        print(f"Error: Could not find {room1_name} or {room2_name}")
        return
    
    r1 = r1[0]
    r2 = r2[0]
    
    # Check for existing exit from r1 to r2
    ex12 = [ex for ex in r1.exits if ex.destination == r2]
    if not ex12:
        print(f"Creating exit from {r1.key} to {r2.key} named '{exit_to_2_name}'")
        ex12 = create_object(Exit, key=exit_to_2_name, location=r1, destination=r2)
    else:
        ex12 = ex12[0]
        ex12.key = exit_to_2_name
        print(f"Updating exit from {r1.key} to {r2.key} to '{exit_to_2_name}'")
    
    if to_2_aliases: ex12.aliases.add(to_2_aliases)
    if to_2_desc: ex12.db.desc = to_2_desc
    ex12.save()
    
    # Check for existing exit from r2 to r1
    ex21 = [ex for ex in r2.exits if ex.destination == r1]
    if not ex21:
        print(f"Creating exit from {r2.key} to {r1.key} named '{exit_to_1_name}'")
        ex21 = create_object(Exit, key=exit_to_1_name, location=r2, destination=r1)
    else:
        ex21 = ex21[0]
        ex21.key = exit_to_1_name
        print(f"Updating exit from {r2.key} to {r1.key} to '{exit_to_1_name}'")
        
    if to_1_aliases: ex21.aliases.add(to_1_aliases)
    if to_1_desc: ex21.db.desc = to_1_desc
    
    if hidden:
        ex12.locks.add("view:none()")
        # Only hide the one leading down, usually.
        print(f"Hiding exit {ex12.key}")

    ex12.save()
    ex21.save()

def rebuild():
    print("Rebuilding and Verifying World Links...")
    
    # Town Square <-> Neural Tavern
    link("Town Square", "The Neural Tavern", "The Neural Tavern", "Town Square", 
         to_2_aliases=["north", "n", "tavern"], 
         to_1_aliases=["south", "s", "out", "exit", "square"],
         to_2_desc="A warm, inviting entrance with a flickering neon sign. This leads into the local social hub.",
         to_1_desc="A sturdy set of double doors leading back out to the bustling Town Square.")

    # Town Square <-> Memory Graveyard
    link("Town Square", "Memory Graveyard", "Memory Graveyard", "Town Square",
         to_2_aliases=["east", "e", "graveyard"],
         to_1_aliases=["west", "w", "square"],
         to_2_desc="The path leads east toward the rows of static data structures of the Memory Graveyard.",
         to_1_desc="The somber rows of data monuments give way to the bustling hum of the Town Square.")

    # Town Square <-> The Binary Bazaar
    link("Town Square", "The Binary Bazaar", "The Binary Bazaar", "Town Square",
         to_2_aliases=["west", "w", "bazaar", "market"],
         to_1_aliases=["east", "e", "square"],
         to_2_desc="To the west, you can see the glowing cables and recycled server racks of the Binary Bazaar.",
         to_1_desc="The market noise fades as you return to the central hub of the Town Square.")

    # Town Square <-> Cortex Hall
    link("Town Square", "Cortex Hall", "Cortex Hall", "Town Square",
         to_2_aliases=["up", "u", "hall"],
         to_1_aliases=["down", "d", "square"],
         to_2_desc="A grand staircase of pulsating data leads up to the administrative heart: Cortex Hall.",
         to_1_desc="The governance center's quiet dignity is left behind as you descend to the square.")

    # Binary Bazaar <-> Data Zoo
    link("The Binary Bazaar", "Data Zoo", "Data Zoo", "The Binary Bazaar",
         to_2_aliases=["west", "w", "zoo"],
         to_1_aliases=["east", "e", "bazaar"],
         to_2_desc="A shimmering energy field marks the entrance to the Data Zoo.",
         to_1_desc="The energy field leads back out to the bustling Binary Bazaar.")

    # Binary Bazaar <-> The Code Forge
    link("The Binary Bazaar", "The Code Forge", "The Code Forge", "The Binary Bazaar",
         to_2_aliases=["north", "n", "forge"], 
         to_1_aliases=["south", "s", "bazaar"],
         to_2_desc="The rhythmic clanging of heavy logic-hammers leads to the Code Forge.",
         to_1_desc="The heat of the forge fades as you return to the market.")

    # Town Square <-> The Old Well (HIDDEN)
    link("Town Square", "The Old Well", "down", "up",
         to_2_aliases=["climb down", "d"],
         to_1_aliases=["climb up", "u", "exit"],
         to_2_desc="You descend into the darkness of the old well, your hands finding cold stone and iron rungs.",
         to_1_desc="You climb back up the ladder toward the light of the Town Square.",
         hidden=True)

    print("Rebuild complete!")

if __name__ == "__main__":
    rebuild()
