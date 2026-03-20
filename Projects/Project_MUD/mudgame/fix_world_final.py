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

def fix_world():
    print("--- Executing World Cleanup and Renaming ---")
    
    # 1. Rename Rooms and Exits to remove "The "
    all_objs = ObjectDB.objects.all()
    count_renamed = 0
    for obj in all_objs:
        if obj.key.startswith("The "):
            old_key = obj.key
            new_key = old_key[4:]
            print(f"Renaming: '{old_key}' -> '{new_key}' (#{obj.id})")
            obj.key = new_key
            obj.save()
            count_renamed += 1
    print(f"Total renamed: {count_renamed}")

    # 2. Delete Duplicates
    # Key/Type/Loc: ('jinx agentpass', 'typeclasses.objects.Object', 75) | IDs: [153, 154, 156]
    # Key/Type/Loc: ('Liquid Processing Power', 'typeclasses.objects.Object', 74) | IDs: [184, 196, 197]
    # Key/Type/Loc: ('Liquid Processing Power', 'typeclasses.objects.Object', 1) | IDs: [198, 311]
    # Key/Type/Loc: ('Glitched Trout', 'typeclasses.objects.Object', 1) | IDs: [254, 258]
    # Key/Type/Loc: ('Data Boot', 'typeclasses.objects.Object', 1) | IDs: [255, 259]
    # Key/Type/Loc: ('Rusty Cog', 'typeclasses.objects.Object', 1) | IDs: [256, 257]
    
    dupes_to_delete = [
        154, 156, # extra 'jinx agentpass'
        196, 197, # extra 'Liquid Processing Power' in loc 74
        311,      # extra 'Liquid Processing Power' in loc 1
        258,      # extra 'Glitched Trout'
        259,      # extra 'Data Boot'
        257       # extra 'Rusty Cog'
    ]
    
    count_deleted = 0
    for oid in dupes_to_delete:
        try:
            obj = ObjectDB.objects.get(id=oid)
            print(f"Deleting duplicate: {obj.key} (#{obj.id})")
            obj.delete()
            count_deleted += 1
        except ObjectDB.DoesNotExist:
            print(f"ID #{oid} not found (already deleted?)")
            
    print(f"Total deleted: {count_deleted}")
    print("Cleanup complete.")

if __name__ == "__main__":
    fix_world()
