"""
Fix Interaction CmdSets

Removes InteractCmdSet from all InteractiveObjects and ensures Characters have it.
"""
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.objects.models import ObjectDB
from typeclasses.interactions import InteractiveObject, InteractCmdSet
import evennia
evennia.SESSION_HANDLER = {}

def fix_params():
    print("Fixing Command Sets...")
    
    # 1. Clean up Objects
    # Find all objects that might have the cmdset
    # It's hard to query by cmdset, so we iterate all InteractiveObjects
    
    objs = InteractiveObject.objects.all()
    count = 0
    for obj in objs:
        # Check if cmdset is present
        # Evennia 5: cmdset.has() or remove()
        # The key for InteractCmdSet is "InteractCmdSet"
        if obj.cmdset.has("InteractCmdSet"):
            print(f"Removing InteractCmdSet from {obj.key} (#{obj.id})")
            obj.cmdset.remove("InteractCmdSet")
            count += 1
            
    print(f"Cleaned {count} objects.")

    # 2. Update Characters
    # All existing characters need the new cmdset
    from typeclasses.characters import Character
    chars = Character.objects.all()
    c_count = 0
    for char in chars:
        if not char.cmdset.has("InteractCmdSet"):
            print(f"Adding InteractCmdSet to {char.key} (#{char.id})")
            char.cmdset.add(InteractCmdSet, persistent=True)
            c_count += 1
            
    print(f"Updated {c_count} characters.")
    print("Fix Complete! Please reload the server.")

if __name__ == "__main__":
    fix_params()
