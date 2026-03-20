import os
import sys
import django
import re

# Setup Django
sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception:
        pass

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object

def generate_aliases(name):
    """
    Generate aliases like "neural tavern", "tavern" from "The Neural Tavern".
    """
    aliases = set()
    name = str(name).strip()
    lower_name = name.lower()
    aliases.add(lower_name)
    
    # Remove 'the ', 'a ', 'an '
    stripped = re.sub(r'^(the|a|an)\s+', '', lower_name)
    if stripped and stripped != lower_name:
         aliases.add(stripped)
         
    # Add individual words if there are multiple
    words = stripped.split()
    if len(words) > 1:
         for word in words:
             # Exclude tiny words
             if len(word) > 2 and word not in ['and', 'of', 'in', 'on', 'at', 'to', 'the']:
                 aliases.add(word)
                 
    return list(aliases)

def main():
    print("Starting global exit renaming...")
    # Find all objects that have a destination (Exits)
    all_exits = []
    for obj in ObjectDB.objects.all():
        if obj.db_destination:
            all_exits.append(obj)
            
    modified = 0
    for ex in all_exits:
        dest = ex.destination
        if not dest:
            continue
            
        dest_name = dest.key
        old_name = ex.key
        
        # We rename the exit its destination name
        ex.key = dest_name
        
        # Generate new aliases
        new_aliases = generate_aliases(dest_name)
        
        # Clear out old aliases to remove "north", "south", etc.
        ex.aliases.clear()
        
        for al in new_aliases:
            ex.aliases.add(al)
            
        ex.save()
            
        print(f"Updated exit [Old: {old_name}] -> [New: {ex.key}], Aliases: {new_aliases}")
        modified += 1
        
    print(f"Finished updating {modified} exits.")

if __name__ == "__main__":
    main()
