import os
import sys
import django

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object

def restore_descriptions():
    print("--- Restoring Rich Room Descriptions ---")

    descriptions = {
        "Town Square": 
            "The heart of the village beats with a rhythm of hexagonal paving stones, each one faintly glowing with the pulse of the network. "
            "Above, the sky is a shifting canvas of impossible geometries. To the north, the neon sign of the Neural Tavern flickers with inviting warmth. "
            "To the west, the chaotic energy of the Binary Bazaar spills out like static.",
            
        "The Neural Tavern": 
            "The air here smells of ozone and roasted coffee beans. Plush velvet booths line the walls, and the bar itself is a slab of polished obsidian "
            "that seems to absorb the ambient light. A jukebox in the corner plays a low-fidelity jazz tune that occasionally glitches into pure data.",
            
        "The Binary Bazaar": 
            "A riot of noise and color. Stalls made of recycled server racks line the narrow aisles, hawking everything from deprecated APIs to illicit subroutines. "
            "The ground is a tangle of fiber-optic cables, humming with the traffic of a thousand transactions. Overhead, banners made of holographic code flutter in a digital wind.",

        "Data Zoo": 
            "The air is thick with the hum of containment fields. Behind shimmering energy barriers, you can see the shapes of restless data—wild algorithms pacing their "
            "cages, fractals blooming and collapsing in seconds. The path here is sterile white, a stark contrast to the colorful chaos of the creatures within.",

        "The Code Forge": 
            "The heat hits you first—a dry, electric heat that smells of soldering iron and burnt silicon. In the center of the room, a massive anvil rings out "
            "as sparks of raw syntax fly into the air. This is where ideas are hammered into reality.",
            
        "Dream Canvas": 
            "Gravity is a suggestion here. Use-cases and user stories float like jellyfish in a neon sea, drifting past you in slow motion. "
            "The walls are not walls, but horizons that stretch into infinite possibility. It is quiet here, save for the whisper of inspiration.",

        "The Syntax Sanctuary": 
            "A garden of perfectly ordered logic. Trees made of fractal branching patterns sway in a non-existent breeze. The grass is a uniform shade of terminal green. "
            "It is a place of peace, where every variable has a value and every loop has an exit condition.",
            
        "The Consensus Chamber": 
            "A vast circular room dominated by a central table. The acoustics are perfect; a whisper here carries to the other side of the hall. "
            "Golden light filters down from a high dome, illuminating the dust motes that dance in the air like suspended bits.",
            
        "Memory Graveyard": 
            "A somber field of grey monoliths, stretching out into the fog. Each stone marks a deleted file, a forgotten project, a lost idea. "
            "The ground is soft and ashen. It is cold here, a deep, penetrating cold that speaks of finality.",
            
        "The Bridge of Sighs": 
            "A narrow arch of stone spanning a bottomless chasm of null pointers. The wind here howls with the voices of corrupted data. "
            "Looking down invites vertigo; looking forward requires courage. The bridge connects the known village to the ruins beyond."
    }

    for key, desc in descriptions.items():
        results = search_object(key)
        if results:
            room = results[0]
            print(f"Updating: {room.key} (#{room.id})")
            room.db.desc = desc
            room.save()
        else:
            print(f"WARNING: Could not find room '{key}'")

    print("Descriptions restored.")

if __name__ == "__main__":
    restore_descriptions()
