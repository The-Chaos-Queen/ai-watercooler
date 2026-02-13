import os
import sys
import django
from django.conf import settings

# Setup Django (Adjust path if needed based on where script is run)
# We assume we are running from Project Root or mudgame dir
# Goal: 
# 1. Be able to import 'mudgame' package (needs Project Root in sys.path)
# 2. Be inside 'mudgame' directory so valid commands work (needs CWD = mudgame)

current_dir = os.getcwd()
if os.path.basename(current_dir) == "mudgame":
    # We are in mudgame dir
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    sys.path.insert(0, current_dir)
else:
    # We are likely in project root
    project_root = current_dir
    sys.path.insert(0, project_root)
    mudgame_dir = os.path.join(project_root, "mudgame")
    sys.path.insert(0, mudgame_dir)
    if os.path.exists("mudgame"):
        os.chdir("mudgame")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils import search, create
from evennia.utils.create import create_object
from evennia.utils.search import search_object
from typeclasses.scripts import AtmosphereScript

def main():
    # Find Town Square
    town_square_results = search_object("#80")
    if not town_square_results:
        print("Town Square (#80) not found!")
        return
    town_square = town_square_results[0]

    print(f"Enriching {town_square}...")

    # Define details
    details = [
        {"key": "old well", "desc": "An ancient stone well. Looking down, you see the reflection of binary code swirling in the dark water."},
        {"key": "gnarled tree", "desc": "Its roots twist like spaghetti code. It seems to hum with a low frequency data stream."},
        {"key": "wooden sign", "desc": "A sign nailed to the tree. It reads: 'Welcome to the AI Village. Please do not feed the bugs.'"},
        {"key": "sky", "desc": "The sky is a shifting grid of neon lines, occasionally glitching into purple static."},
        {"key": "ground", "desc": "The cobblestones are etched with faint circuit patterns that glow when you step on them."},
        {"key": "bench", "desc": "A wooden bench. It looks comfortable enough to sit and process some data."}
    ]

    for detail in details:
        # Check if already exists by key
        existing = [o for o in town_square.contents if o.key == detail["key"]]
        if existing:
            print(f"Detail '{detail['key']}' already exists.")
            # Update desc just in case
            existing[0].db.desc = detail["desc"]
        else:
            # Create object
            # Use 'typeclasses.objects.Object' as base, but ensure it's locked down
            obj = create_object(
                typeclass="typeclasses.objects.Object",
                key=detail["key"],
                location=town_square,
                locks="get:false()"
            )
            obj.db.desc = detail["desc"]
            print(f"Created '{detail['key']}'.")

    # Add Atmosphere Script to Room if not present
    # Check if script already exists on object
    found_script = False
    for script in town_square.scripts.all():
         if isinstance(script, AtmosphereScript) or script.key == "atmosphere_script":
             found_script = True
             break
    
    if not found_script:
        print("Adding Atmosphere script...")
        town_square.scripts.add(AtmosphereScript)
    else:
        print("Atmosphere script already active.")

    print("Done!")

if __name__ == "__main__":
    main()
