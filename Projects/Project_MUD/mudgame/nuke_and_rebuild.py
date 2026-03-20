
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

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object

def nuke():
    print("NUKING DUPLICATES AND REDUNDANT EXITS...")
    
    # 1. Delete ALL exits (we will rebuild them)
    exits = list(ObjectDB.objects.filter(db_typeclass_path__icontains='exit'))
    print(f"Deleting {len(exits)} exits...")
    for ex in exits:
        try:
            ex.delete()
        except Exception:
            pass
        
    # 2. Delete duplicate rooms aggressively
    all_rooms = list(ObjectDB.objects.filter(db_location=None, db_typeclass_path__icontains='room'))
    mapping = {}
    for room in all_rooms:
        key = room.key.lower()
        if key.startswith("the "): key = key[4:]
        if key not in mapping: mapping[key] = []
        mapping[key].append(room)
        
    for key, matches in mapping.items():
        if len(matches) > 1:
            matches.sort(key=lambda x: x.id)
            primary = matches[0]
            for dup in matches[1:]:
                print(f"Merging {dup.key} (#{dup.id}) into {primary.key} (#{primary.id})")
                for obj in list(dup.contents):
                    obj.location = primary
                dup.delete()
    
    print("NUKE COMPLETE. Rebuilding...")

if __name__ == "__main__":
    nuke()
    # Now import and run the rebuilder
    import rebuild_world_links
    rebuild_world_links.rebuild()
    print("REBUILD COMPLETE.")
