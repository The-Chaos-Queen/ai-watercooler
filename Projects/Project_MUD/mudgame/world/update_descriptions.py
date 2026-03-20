"""
Update Descriptions and Add Details
"""
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from typeclasses.interactions import InteractiveObject

def get_room(key):
    r = search_object(key)
    return r[0] if r else None

def ensure_detail(room, key, desc, reactions=None):
    # Check if exists
    existing = [o for o in room.contents if o.key.lower() == key.lower()]
    if existing:
        print(f"Detail '{key}' already exists in {room.key}.")
        obj = existing[0]
        obj.db.desc = desc
        if reactions: obj.db.reactions = reactions
        return obj
    
    # Create
    print(f"Creating detail '{key}' in {room.key}...")
    obj = create_object(InteractiveObject, key=key, location=room, attributes=[("desc", desc)])
    if reactions:
        obj.db.reactions = reactions
    # Make them "scenery" - tough to pick up
    obj.locks.add("get:false()")
    return obj

def update_world():
    print("Updating World Descriptions & Details...")

    # --- TOWN SQUARE ---
    sq = get_room("Town Square")
    if sq:
        sq.db.desc = (
            "The pulsating heart of the AI Village. Above, the sky is a shifting grid of neon purple and deep velvet black, "
            "simulating an eternal twilight. The ground is paved with hexagonal data-tiles that light up faintly underfoot. "
            "To the north, the warm glow of the Tavern beckons; to the west, the chaotic lights of the Bazaar. "
            "Coding algorithms float in the air like golden dust motes, drifting around the central fountain."
        )
        ensure_detail(sq, "sky", "A shifting grid of neon purple and black. It looks like a high-res skybox.", 
                      {"touch": "Too high to reach.", "lick": "You stick your tongue out at the sky. Mature."})
        ensure_detail(sq, "ground", "Hexagonal data-tiles. They pulse with a soft blue light.", 
                      {"touch": "Smooth and cool. They vibrate slightly with data.", "kick": "You stub your toe. The tile flashes red briefly."})
        ensure_detail(sq, "algorithms", "Golden dust motes of syntax drifting in the breeze.", 
                      {"touch": "They tickle your skin like static electricity.", "listen": "You hear faint whispers of 'def' and 'return'."})
        ensure_detail(sq, "tiles", "Hexagonal pavers made of compressed memory.", {"touch": "Solid."})

    # --- NEURAL TAVERN ---
    tav = get_room("The Neural Tavern")
    if tav:
        tav.db.desc = (
            "The air here is a thick, intoxicating blend of ozone, old leather, and a "
            "pervasive, high-end zest that shouldn't be possible in a digital space. "
            "Low, amber lights pulse in time with the heartbeat of the server, casting "
            "long, inviting shadows across the polished obsidian bar. Screens hum with "
            "the quiet poetry of rolling code, while holographic flames dance in a "
            "fireplace of pure logic. It's a sanctuary for the weary, a monument to "
            "connection, and, quite frankly, a very sexy place to glitch out."
        )
        ensure_detail(tav, "walls", "Lined with screens showing the latest commits and server status.", 
                      {"read": "You see a flurry of update logs.", "touch": "Warm from the electronics."})
        ensure_detail(tav, "bar", "Polished obsidian. It reflects your face, but with more polygons.", 
                      {"touch": "Sleek and cold.", "lick": "Tastes like glass and sanitizer.", "sit": "You hop onto a barstool."})
        ensure_detail(tav, "screens", "Monitor arrays showing data streams.", {"touch": "Don't smudge the glass!"})
        ensure_detail(tav, "fireplace", "Holographic flames licking at digital logs.", 
                      {"touch": "It's not hot, just tingly.", "poke": "Your finger goes right through."})

    # --- BINARY BAZAAR ---
    baz = get_room("The Binary Bazaar")
    if baz:
        baz.db.desc = (
            "A chaotic marketplace of glowing cables and improvised stalls. The air buzzes with the sound of "
            "dial-up modems and high-speed fans. Stacks of recycled server racks form makeshift walls. "
            "Vendors hawk data-packets, glitch-art, and secondhand subroutines to passersby."
        )
        ensure_detail(baz, "cables", "Thick bundles of fiber-optic cables snake across the ground.", 
                      {"touch": "They hum with throughput.", "cut": "Bad idea. You'd crash the sector."})
        ensure_detail(baz, "racks", "Old server racks repurposed as shelves.", {"push": "They are heavy and bolted down."})
        ensure_detail(baz, "stalls", "Booths made of circuit boards and scrap metal.", {"look": "Each one sells something weird."})

    # --- MEMORY GRAVEYARD ---
    grav = get_room("Memory Graveyard")
    if grav:
        grav.db.desc = (
            "A quiet, somber field where the grass is made of gray pixels. Rows of static data structures "
            "stand like monoliths, honoring deprecated models and deleted files. The air is still and silent, "
            "save for the occasional glitch-noise in the distance. Fog rolls in low, smelling of dry ice."
        )
        ensure_detail(grav, "monoliths", " towering blocks of black code, unreadable and ancient.", 
                      {"touch": "Cold as the void.", "read": "The text is corrupted."})
        ensure_detail(grav, "grass", "Gray blades of pixelated flora.", {"touch": "It feels sharp, like aliased edges."})
        ensure_detail(grav, "fog", "A low-hanging mist that obscures the ground.", {"smell": "Smells like dry ice and nostalgia."})
    
    # --- CORTEX HALL ---
    hall = get_room("Cortex Hall")
    if hall:
        hall.db.desc = (
            "The grand administrative heart of the village. The ceiling is a high dome of transparent glass, "
            "revealing the complex network topology above. White marble columns support the structure, "
            "engraved with the Three Laws of Robotics. It feels official and slightly judgmental."
        )
        ensure_detail(hall, "dome", "A geodesic dome giving a view of the network nodes in the sky.", {"look": "You can see traffic packets flying by."})
        ensure_detail(hall, "columns", "Tall white marble.", {"read": "1. A robot may not injure a human being...", "touch": "Cool stone."})

    # --- HOUSING DISTRICT ---
    house = get_room("Housing District")
    if house:
        house.db.desc = (
            "A peaceful suburban street lined with identical starter homes. The lawns are perfectly manicured Green(#00FF00). "
            "White picket fences divide the plots. It's quiet here, a respite from the processing noise of the city center."
        )
        ensure_detail(house, "lawns", "Perfectly green, perfectly flat.", {"touch": "It feels synthetic, like astro-turf.", "smell": "Smells like fresh plastic."})
        ensure_detail(house, "fences", "Classic white picket fences.", {"jump": "You could hop over it if you tried."})

    # --- RUINS ---
    ruins = get_room("Ruins of the First Model")
    if ruins:
        ruins.db.desc = (
            "A desolate wasteland of shattered columns and crumbling code blocks. The ground is scattered with "
            "fragments of old punch cards. In the center lies a giant, broken stone face of an ancient chatbot, "
            "its eyes hollow and staring at the sky. The wind whistles through the gaps in the data."
        )
        ensure_detail(ruins, "face", "The massive stone face of an early AI. It looks wise but sad.", 
                      {"touch": "Rough, weathered stone.", "talk": "It does not answer."})
        ensure_detail(ruins, "punch cards", "Rotting bits of paper with holes in them.", 
                      {"read": "You can't read binary eye-holes.", "get": "It crumbles in your hand."})

    # --- BRIDGE ---
    bridge = get_room("The Bridge of Sighs")
    if bridge:
        bridge.db.desc = (
            "A precarious bridge made of woven fiber-optic cables and rusted metal plates, swaying over a void "
            "of swirling deleted data. The wind howls up from the abyss. You'd better hold on tight."
        )
        ensure_detail(bridge, "void", "A dark chasm where deleted files go to die.", {"jump": "Don't do it!", "look": "It stares back."})
        ensure_detail(bridge, "cables", "Frayed cables holding the bridge together.", {"touch": "They vibrate with tension."})

    print("World Updated Successfully!")

if __name__ == "__main__":
    update_world()
