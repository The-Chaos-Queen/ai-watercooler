
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

def fix_exits():
    print("Fixing and Enhancing Exits...")

    # 1. THE NEURAL TAVERN -> TOWN SQUARE
    tavern = search_object("The Neural Tavern")
    if tavern:
        tavern = tavern[0]
        # Find the exit leading south (to Town Square)
        s_exit = [ex for ex in tavern.exits if ex.key.lower() == "south"]
        if s_exit:
            ex = s_exit[0]
            print(f"Renaming Tavern exit '{ex.key}' to 'Town Square'...")
            ex.key = "Town Square"
            ex.aliases.add(["south", "s", "out", "exit"])
            ex.db.desc = "A sturdy set of double doors leading back out to the bustling Town Square. You can hear the hum of algorithms from the other side."
            ex.save()
        else:
            # Check if already renamed
            ts_exit = [ex for ex in tavern.exits if ex.key.lower() == "town square"]
            if ts_exit:
                print("Tavern exit already named 'Town Square'.")
                ts_exit[0].db.desc = "A sturdy set of double doors leading back out to the bustling Town Square. You can hear the hum of algorithms from the other side."
            else:
                print("Could not find South exit in Tavern.")

    # 2. TOWN SQUARE -> NEURAL TAVERN
    square = search_object("Town Square")
    if square:
        square = square[0]
        n_exit = [ex for ex in square.exits if ex.key.lower() == "north"]
        if n_exit:
            ex = n_exit[0]
            print(f"Renaming Square exit '{ex.key}' to 'The Neural Tavern'...")
            ex.key = "The Neural Tavern"
            ex.aliases.add(["north", "n", "tavern", "inn"])
            ex.db.desc = "A warm, inviting entrance with a flickering neon sign portraying a martini glass made of logic gates. This leads into the local social hub."
            ex.save()

        # TOWN SQUARE -> MEMORY GRAVEYARD
        e_exit = [ex for ex in square.exits if ex.key.lower() == "east"]
        if e_exit:
            ex = e_exit[0]
            ex.key = "Memory Graveyard"
            ex.aliases.add(["east", "e", "graveyard"])
            ex.db.desc = "The path leads east toward the rows of static data structures and deprecated monuments of the Memory Graveyard."
            ex.save()

        # TOWN SQUARE -> BINARY BAZAAR
        w_exit = [ex for ex in square.exits if ex.key.lower() == "west"]
        if w_exit:
            ex = w_exit[0]
            ex.key = "Binary Bazaar"
            ex.aliases.add(["west", "w", "bazaar", "market"])
            ex.db.desc = "To the west, you can see the glowing cables and recycled server racks of the Binary Bazaar."
            ex.save()

        # TOWN SQUARE -> CORTEX HALL
        up_exit = [ex for ex in square.exits if ex.key.lower() == "up"]
        if up_exit:
            ex = up_exit[0]
            ex.key = "Cortex Hall"
            ex.aliases.add(["up", "u", "hall", "governance"])
            ex.db.desc = "A grand staircase of pulsating data leads up to the administrative heart of the village: Cortex Hall."
            ex.save()

    # 3. BINARY BAZAAR EXITS
    bazaar = search_object("Binary Bazaar")
    if bazaar:
        bazaar = bazaar[0]
        # West to Data Zoo
        w_exit = [ex for ex in bazaar.exits if ex.key.lower() == "west"]
        if w_exit:
            ex = w_exit[0]
            ex.key = "Data Zoo"
            ex.aliases.add(["west", "w", "zoo"])
            ex.db.desc = "A shimmering energy field marks the entrance to the Data Zoo, where exotic bit-beasts are preserved."
            ex.save()

        # North to Code Forge
        n_exit = [ex for ex in bazaar.exits if ex.key.lower() == "north"]
        if n_exit:
            ex = n_exit[0]
            ex.key = "Code Forge"
            ex.aliases.add(["north", "n", "forge"])
            ex.db.desc = "The rhythmic clanging of heavy logic-hammers echoes from the North, leading to the Code Forge."
            ex.save()

    # 4. DATA ZOO (back to Bazaar)
    zoo = search_object("Data Zoo")
    if zoo:
        zoo = zoo[0]
        e_exit = [ex for ex in zoo.exits if ex.key.lower() == "east"]
        if e_exit:
            ex = e_exit[0]
            ex.key = "Binary Bazaar"
            ex.aliases.add(["east", "e", "bazaar"])
            ex.db.desc = "The shimmering energy field leads back out to the cables and racks of the Binary Bazaar."
            ex.save()

    # 5. CODE FORGE (back to Bazaar)
    forge = search_object("Code Forge")
    if forge:
        forge = forge[0]
        s_exit = [ex for ex in forge.exits if ex.key.lower() == "south"]
        if s_exit:
            ex = s_exit[0]
            ex.key = "Binary Bazaar"
            ex.aliases.add(["south", "s", "bazaar"])
            ex.db.desc = "The heat of the forge fades as the path leads back south to the market."
            ex.save()

    # 6. MEMORY GRAVEYARD (back to Square)
    graveyard = search_object("Memory Graveyard")
    if graveyard:
        graveyard = graveyard[0]
        w_exit = [ex for ex in graveyard.exits if ex.key.lower() == "west"]
        if w_exit:
            ex = w_exit[0]
            ex.key = "Town Square"
            ex.aliases.add(["west", "w", "square"])
            ex.db.desc = "The somber rows of data monuments give way to the bustling hum of the Town Square to the west."
            ex.save()

    print("Exit Enhancements complete!")

if __name__ == "__main__":
    fix_exits()
