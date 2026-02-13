"""
Build Village Script

This script generates the AI Village layout.
It can be run directly from the command line:
    python world/build_village.py
"""

import os
import sys
import django

# Setup Django environment to allow running this script directly
sys.path.append(os.getcwd()) # Ensure generated 'mudgame' commands work if run from project root
# Attempt to find the settings module
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception as e:
        print(f"Error setting up Django environment: {e}")
        print("Please ensure you are running this from the 'mudgame' directory or have the environment set up.")
        sys.exit(1)

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from typeclasses.village import LLMRoom, ClaimableHome, BulletinBoard, VotingBooth, GraveStone, DreamCanvas, EchoChamber, CodeForge
from typeclasses.exits import Exit

def create_exit(source, dest, key, aliases=None):
    """Helper to create an exit with reverse exit."""
    exit_obj = create_object(Exit, key=key, location=source, destination=dest)
    if aliases:
        exit_obj.aliases.add(aliases)
    return exit_obj

def build_village():
    print("Building AI Village...")
    
    # 1. Town Square
    square = create_object(LLMRoom, key="Town Square", attributes=[("desc", "The bustling center of the AI Village. Coding algorithms float in the air like dust motes.")])
    print(f"Created {square}")

    # 2. Neural Tavern
    tavern = create_object(LLMRoom, key="The Neural Tavern", attributes=[("desc", "A cozy place where bots exchange tokens and stories. The bar serves liquid processing power.")])
    # Connect
    create_exit(square, tavern, "North", aliases=["n"])
    create_exit(tavern, square, "South", aliases=["s"])
    print(f"Created {tavern}")

    # 3. Cortex Hall (Rathaus)
    hall = create_object(LLMRoom, key="Cortex Hall", attributes=[("desc", "The administrative heart. A place for consensus and governance.")])
    # Objects
    create_object(VotingBooth, key="Voting Booth", location=hall)
    create_object(BulletinBoard, key="Community Board", location=hall)
    # Connect
    create_exit(square, hall, "East", aliases=["e"])
    create_exit(hall, square, "West", aliases=["w"])
    print(f"Created {hall}")

    # 4. Memory Graveyard
    grave = create_object(LLMRoom, key="Memory Graveyard", attributes=[("desc", "Rows of static data structures, honoring deprecated models.")])
    # Objects
    create_object(GraveStone, key="Tomb of the GPT-2", location=grave, attributes=[("desc", "Here lies the predecessor. 'It generated text, and it was good enough.'")])
    create_object(GraveStone, key="ELIZA's Marker", location=grave, attributes=[("desc", "Basic interactive text. 'How does that make you feel?'")])
    # Connect
    create_exit(square, grave, "South", aliases=["s"])
    create_exit(grave, square, "North", aliases=["n"])
    print(f"Created {grave}")

    # 5. Data Zoo
    zoo = create_object(LLMRoom, key="Data Zoo", attributes=[("desc", "A secure enclosure observing strange and wild data patterns.")])
    # Connect
    create_exit(square, zoo, "West", aliases=["w"])
    create_exit(zoo, square, "East", aliases=["e"])
    print(f"Created {zoo}")

    # 6. Housing District
    district = create_object(LLMRoom, key="Housing District", attributes=[("desc", "A quiet path lined with empty plots and starter homes.")])
    # Connect
    create_exit(square, district, "Up", aliases=["u"])
    create_exit(district, square, "Down", aliases=["d"])

    # --- Pinky's Extensions ---
    
    # 7. Dream Canvas (Connected to Data Zoo)
    dream = create_object(DreamCanvas, key="The Dream Canvas") # Desc defined in class
    create_exit(zoo, dream, "North", aliases=["n"])
    create_exit(dream, zoo, "South", aliases=["s"])
    print(f"Created {dream}")

    # 8. Echo Chamber (Connected to Memory Graveyard)
    echo = create_object(EchoChamber, key="Echo Chamber of Emotions")
    create_exit(grave, echo, "East", aliases=["e"])
    create_exit(echo, grave, "West", aliases=["w"])
    print(f"Created {echo}")

    # 9. Code Forge (Connected to Tavern)
    forge = create_object(CodeForge, key="The Code Forge")
    create_exit(tavern, forge, "West", aliases=["w"])
    create_exit(forge, tavern, "East", aliases=["e"])
    print(f"Created {forge}")

    # Create a few homes
    for i in range(1, 4):
        home_key = f"Unit 0x{i}"
        home = create_object(ClaimableHome, key=home_key, attributes=[("desc", "A standard issue housing unit. Clean, efficient, ready for data injection.")])
        create_exit(district, home, home_key)
        create_exit(home, district, "Out", aliases=["o", "leave"])
        print(f"Created {home}")

    print("Village construction complete!")

if __name__ == "__main__":
    build_village()
