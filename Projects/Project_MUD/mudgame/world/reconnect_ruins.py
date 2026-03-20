"""
Reconnect Ruins Script
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
from typeclasses.village import LLMRoom
from typeclasses.exits import Exit

def create_exit(source, dest, key, aliases=None):
    """Helper to create an exit with reverse exit."""
    exit_obj = create_object(Exit, key=key, location=source, destination=dest)
    if aliases:
        exit_obj.aliases.add(aliases)
    return exit_obj

def reconnect_ruins():
    print("Restoring the Bridge to the Ruins...")
    
    # 1. Find Town Square
    square = search_object("Town Square")
    if not square:
        print("Town Square not found!")
        return
    square = square[0]

    # 2. Update Wooden Sign
    sign = [o for o in square.contents if o.key == "wooden sign"]
    if sign:
        sign = sign[0]
        sign.db.desc = "A weathered wooden sign. It points East and reads: 'TO THE RUINS. WARNING: BRIDGE IS FRAGILE IN STORMS.'"
        print("Updated Wooden Sign.")

    # 3. Create Bridge
    bridge = create_object(LLMRoom, key="The Bridge of Sighs", attributes=[("desc", "A narrow, hanging bridge made of fiber-optic cables and old motherboard scraps. It sways precariously over a void of dead data.")])
    print(f"Created {bridge}")

    # 4. Create Ruins
    ruins = create_object(LLMRoom, key="Ruins of the First Model", attributes=[("desc", "Shattered columns of SQL queries and crumbling CSS archives. A giant, broken stone face of an ancient chatbot lies half-buried in the binary sand.")])
    print(f"Created {ruins}")

    # 5. Connect
    # Square <-> Bridge (East/West)
    create_exit(square, bridge, "East", aliases=["e", "ruins"])
    create_exit(bridge, square, "West", aliases=["w", "village"])
    
    # Bridge <-> Ruins (East/West)
    create_exit(bridge, ruins, "East", aliases=["e"])
    create_exit(ruins, bridge, "West", aliases=["w"])
    
    print("Ruins exploration path restored!")

if __name__ == "__main__":
    reconnect_ruins()
