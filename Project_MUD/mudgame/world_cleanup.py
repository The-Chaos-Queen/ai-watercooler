
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

def cleanup():
    # 1. Cleanup Archivist Ven
    graveyard = search_object("Memory Graveyard")
    if graveyard:
        graveyard = graveyard[0]
        vens = [obj for obj in graveyard.contents if obj.key == "Archivist Ven"]
        if len(vens) > 1:
            print(f"Found {len(vens)} Archivist Vens. Deleting duplicates...")
            for v in vens[1:]:
                v.delete()
        else:
            print("Only one Archivist Ven found.")

    # 2. Cleanup Town Square West Exits
    square = search_object("Town Square")
    if square:
        square = square[0]
        w_exits = [ex for ex in square.exits if ex.key.lower() == "west"]
        print(f"Found {len(w_exits)} West exits in Town Square.")
        for ex in w_exits:
            dest = ex.destination
            print(f" - Exit '{ex.key}' leads to {dest}")
            if "Data Zoo" in str(dest):
                print(f"Deleting old exit to Data Zoo...")
                ex.delete()
            elif "Binary Bazaar" in str(dest):
                print("Keeping exit to Binary Bazaar.")

if __name__ == "__main__":
    cleanup()
