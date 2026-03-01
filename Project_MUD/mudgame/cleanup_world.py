import os
import sys
import django
import traceback

# Add the project directory to sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

# Setup Django
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from evennia.utils.search import search_object

def cleanup():
    print("--- Searching for ALL Bartenders ---")
    bartender_matches = list(search_object("Bartender"))
    barbot_matches = list(search_object("Barbot"))
    all_bartenders = bartender_matches + barbot_matches
    print(f"Total bartenders/barbots found: {len(all_bartenders)}")
    
    tavern = search_object("Neural Tavern")
    if tavern:
        tavern = tavern[0]
        # Move all bartenders to the tavern first so we can see them together
        for b in all_bartenders:
            if b.location != tavern:
                print(f"Moving {b.key} ({b.id}) to Neural Tavern for reconciliation.")
                b.location = tavern
        
        # Now refetch contents from the actual tavern instance
        bartenders = [obj for obj in tavern.contents if obj.key.lower() in ["barbot", "bartender"]]
        
        if len(bartenders) > 1:
            print(f"Found {len(bartenders)} bartenders in Tavern. Keeping '{bartenders[0].key}' and deleting others.")
            for i in range(1, len(bartenders)):
                print(f"Deleting duplicate: {bartenders[i].key} ({bartenders[i].id})")
                bartenders[i].delete()
        elif len(bartenders) == 1:
            print(f"Only one bartender remains: {bartenders[0].key}")

    print("\n--- Relocating Voting Booth ---")
    booth = search_object("Voting Booth")
    nexus = search_object("Nexus Hall") or search_object("Cortex Hall")
    
    if booth and nexus:
        booth = booth[0]
        nexus = nexus[0]
        if booth.location != nexus:
            print(f"Moving {booth.key} to {nexus.key}")
            booth.location = nexus
        else:
            print(f"Voting Booth is already in {nexus.key}")
    else:
        print("Could not find booth or target room.")

if __name__ == "__main__":
    cleanup()
