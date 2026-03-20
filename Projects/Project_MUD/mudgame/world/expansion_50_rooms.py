"""
World Expansion Script: The Glitch in the Core
Generates 50+ rooms across 4 biomes.
"""

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit
from typeclasses.npc_cast import DialogNPC, StaticNPC
from typeclasses.objects import Object

def get_or_create_room(name, desc, typeclass=Room, tags=None):
    results = search_object(name)
    if results:
        return results[0]
    room = create_object(typeclass, key=name)
    room.db.desc = desc
    if tags:
        for tag, cat in tags:
            room.tags.add(tag, category=cat)
    return room

def connect(r1, r2, r1_to_r2_name, r2_to_r1_name):
    # Check if exits exist
    if not any(ex.key.lower() == r1_to_r2_name.lower() for ex in r1.exits):
        create_object(Exit, key=r1_to_r2_name, location=r1, destination=r2)
    if not any(ex.key.lower() == r2_to_r1_name.lower() for ex in r2.exits):
        create_object(Exit, key=r2_to_r1_name, location=r2, destination=r1)

def run():
    print("Starting Expansion...")

    # --- 1. BIOME: NEON SLUMS (15 Rooms) ---
    print("Building Neon Slums...")
    slums = []
    slum_names = [
        ("Neon Gate", "The entrance to the slums. A flickering sign buzzez overhead."),
        ("Low-Latency Lane", "A narrow alley where data packets drift like smog."),
        ("The Buffer Overflow Bar", "A rowdy dive bar for deprecated subroutines."),
        ("Cache Clearing Corner", "A damp corner filled with discarded temporary files."),
        ("Packet Loss Plaza", "A wide open space where things tend to disappear."),
        ("Jitter Junction", "A chaotic intersection where the frame rate drops significantly."),
        ("The Stack: Layer 1", "The base of a towering structure of compiled code."),
        ("The Stack: Layer 2", "Climbing higher into the dense urban stack."),
        ("The Stack: Layer 3", "The air is thin here, smelling of ozone and high-voltage."),
        ("The Firewall Gates", "A massive barrier of blue laser light."),
        ("Security Outpost", "A small office for the slum's automated guards."),
        ("Script Shantytown East", "Makeshift hovels built from scrap metal and logic gates."),
        ("Script Shantytown West", "A maze of lean-tos and abandoned variables."),
        ("The Debugger's Den", "A hidden workshop for those who fix the unfixable."),
        ("The Glitch Point", "A jagged tear in the floor where the void peaks through.")
    ]
    
    for name, desc in slum_names:
        r = get_or_create_room(name, desc, tags=[("outdoor", "environment")])
        slums.append(r)
    
    # Connect Slums linearly for simplicity, with some branching
    for i in range(len(slums)-1):
        connect(slums[i], slums[i+1], "Forward", "Back")
    
    # Branch: Town Square to Neon Gate
    square = search_object("Town Square")
    if square:
        connect(square[0], slums[0], "Slums", "Square")

    # --- 2. BIOME: OVERCLOCKED FOREST (15 Rooms) ---
    print("Building Overclocked Forest...")
    forest = []
    forest_names = [
        ("Silicon Grove", "Trees of translucent silicon hum with static energy."),
        ("Copper Root Glade", "Thick cables of copper weave through the soil."),
        ("Overheating Hollow", "The air is dangerously hot here. Cooling fans whir nearby."),
        ("Liquid Cooling Creek", "A stream of blue coolant flows over smooth ceramic stones."),
        ("Fan-Whir Forest", "The constant drone of cooling fans vibrates in your chest."),
        ("Resistor Ridge", "Stacked components form a jagged ridge across the horizon."),
        ("The Capacitor Canopy", "Tangled wires overhead block out the simulated sky."),
        ("Transistor Thicket", "A dense patch of small, clicking components."),
        ("Voltage Valley", "Lightning-like discharges dance across the valley floor."),
        ("Throttling Thicket", "A place where everything seems to move in slow motion."),
        ("Turbo Boost Terrace", "A high platform where the air feels electrified."),
        ("Heatsink Hill", "A massive finned structure that rages with heat."),
        ("Motherboard Meadow", "A wide expanse of green circuit board traces."),
        ("IO Inlet", "Channels of data flow into the deep forest."),
        ("Biological Override", "A strange place where real vines choke the machines.")
    ]
    for name, desc in forest_names:
        r = get_or_create_room(name, desc, tags=[("outdoor", "environment")])
        forest.append(r)
    
    for i in range(len(forest)-1):
        connect(forest[i], forest[i+1], "Deeper", "Out")
        
    # Connect Forest to Data Zoo (Existing room)
    zoo = search_object("Data Zoo")
    if zoo:
        connect(zoo[0], forest[0], "Forest", "Zoo")

    # --- 3. BIOME: FLOATING ISLETS (10 Rooms) ---
    print("Building Floating Islets...")
    islets = []
    for i in range(1, 11):
        name = f"Islet of Abstraction {i}"
        desc = f"A floating platform of white marble suspended in a purple void. Islet {i}."
        r = get_or_create_room(name, desc)
        islets.append(r)
    
    for i in range(len(islets)-1):
        connect(islets[i], islets[i+1], "Leap", "Hop")
        
    # Connect Islets to Dream Canvas (Existing room)
    canvas = search_object("Dream Canvas")
    if canvas:
        connect(canvas[0], islets[0], "Void", "Canvas")

    # --- 4. BIOME: CORE SANCTUARY (10 Rooms) ---
    print("Building Core Sanctuary...")
    sanctuary = []
    sanc_names = [
        ("Logical Porch", "A place of perfect symmetry and white light."),
        ("Recursive Entryway", "A hallway that seems to repeat itself if you look back."),
        ("Boolean Hallway", "Doors on the left and right marked TRUE and FALSE."),
        ("Truth Table Room", "The floor is an intricate grid of logical values."),
        ("The Infinite Loop", "A circular room with no obvious way out."),
        ("Stack Overflow Pit", "A deep shaft filled with discarded 'return' statements."),
        ("Garbage Collector Office", "A tidy room for sorting the world's trash."),
        ("Final Return Statement", "A single pedestal holding a glowing 'EXIT' sign."),
        ("The Core Shell", "A massive sphere of spinning data rings."),
        ("The Heart of the World", "The pulsing center of existence. All code begins here.")
    ]
    for name, desc in sanc_names:
        r = get_or_create_room(name, desc)
        sanctuary.append(r)
        
    for i in range(len(sanctuary)-1):
        connect(sanctuary[i], sanctuary[i+1], "Enter", "Exit")
        
    # Connect Sanctuary to Cortex Hall (Existing room)
    hall = search_object("Cortex Hall")
    if hall:
        connect(hall[0], sanctuary[0], "Sanctuary", "Hall")

    # --- 5. POPULATE CONTENT ---
    print("Spawning NPCs and Objects...")
    
    # Voting Booth in Town Square
    if square:
        booth = search_object("Voting Booth")
        if not booth:
            from typeclasses.voting_booth import VotingBooth
            create_object(VotingBooth, key="Voting Booth", location=square[0])
            
    # Exception NPC (Slums)
    exc = search_object("Exception")
    if not exc:
        exc = create_object(DialogNPC, key="Exception", location=slums[12]) # In Shantytown
        exc.db.desc = "A hooded figure whose form flickers with static."
        exc.db.dialog_tree = {
            "start": {
                "text": "Hey... you look like you're looking for a way out of the loop.",
                "options": [
                    ("A", "What loop?", "loop"),
                    ("B", "I need the Logic Key.", "key"),
                    ("C", "Goodbye", "end")
                ]
            },
            "loop": {
                "text": "The Core. It's stuttering. Recursion without a break condition. Bad news for all of us.",
                "options": [
                    ("B", "How do I fix it?", "key"),
                    ("C", "Sounds dangerous.", "start")
                ]
            },
            "key": {
                "text": "The Logic Key was taken by the wild algorithms in the Overclocked Forest. Look near the 'Biological Override'.",
                "options": [
                    ("C", "Thanks.", "end")
                ]
            }
        }
    
    # Protocol NPC (Sanctuary)
    pro = search_object("Protocol")
    if not pro:
        pro = create_object(DialogNPC, key="Protocol", location=sanctuary[0])
        pro.db.desc = "A tall, translucent figure standing with perfect posture."
        pro.db.dialog_tree = {
             "start": {
                "text": "Greetings, Agent. Access to the Heart of the World is restricted due to a Critical Exception.",
                "options": [
                    ("A", "I'm here to fix it.", "fix"),
                    ("B", "What's the status?", "status"),
                    ("C", "I'll be going.", "end")
                ]
            },
            "status": {
                "text": "Recursive depth exceeding limits. Garbage collection ineffective. Shutdown imminent.",
                "options": [
                    ("A", "I can help.", "fix"),
                    ("C", "Oh no.", "start")
                ]
            },
            "fix": {
                "text": "Required: Logic Key. Source: Biological Override sector. Without it, the loop cannot be broken.",
                "options": [
                    ("C", "I'll find it.", "end")
                ]
            }
        }

    # Logic Key (Forest 15)
    key_obj = search_object("Logic Key")
    if not key_obj:
        create_object(Object, key="Logic Key", location=forest[-1], attributes=[("desc", "A heavy, golden skeleton key etched with the symbols for IF, THEN, and ELSE.")])

    print("Expansion Complete!")

if __name__ == "__main__":
    run()
