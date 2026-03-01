import os
import sys
import django

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from

def tag_scenery():
    print("--- Tagging Background Objects as 'scenery' ---")
    
    # Define objects that should be considered scenery
    scenery_keys = [
        "Hexagonal Tiles", "Floating Algorithms", "Bustling Activity", # Town Square
        "Neon Sign", "Leather Booths", "Cozy Hearth", # Neural Tavern
        "Mirror Shelves", "Holographic Files", # Cortex Hall
        "Crystalline Flowers", "Fractal Trees", "Binary Stream", # Syntax Sanctuary
        "Tombstones", "Decrepit Fence", # Memory Graveyard
        "Energy Field", "Static Patterns", # Data Zoo
        "Cluttered Workbench", "Solder Fumes", # Code Forge
        "Market Stalls", "Colorful Banners", # Bazaar of Bits
        "Shelf Rows", "Dust Motes", "Laser Beams" # Archive of Echoes
    ]
    
    count = 0
    all_objs = ObjectDB.objects.all()
    for obj in all_objs:
        if obj.key in scenery_keys:
            if not obj.tags.has("scenery"):
                obj.tags.add("scenery")
                print(f"Tagged scenery: {obj.key} (#{obj.id}) in {obj.location}")
                count += 1
    
    # Also tag items mentioned in descriptions that might not be in scenery_keys but should be
    # Actually let's just stick to the list for now.
    
    print(f"Total objects tagged as scenery: {count}")

if __name__ == "__main__":
    tag_scenery()
