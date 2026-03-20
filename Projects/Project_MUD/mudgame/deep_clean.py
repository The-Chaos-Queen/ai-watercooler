
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
from evennia.objects.models import ObjectDB

def deep_clean():
    print("Performing Deep World Clean...")
    
    # 1. Room Deduplication (Fuzzy)
    all_rooms = ObjectDB.objects.filter(db_location=None, db_typeclass_path__icontains='room')
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

    # 2. Per-Room Content Deduplication
    for room in ObjectDB.objects.filter(db_location=None, db_typeclass_path__icontains='room'):
        # Deduplicate Exits by Destination ID
        visited_dest_ids = set()
        for ex in list(room.exits):
            dest_id = ex.destination.id if ex.destination else None
            if not dest_id or dest_id in visited_dest_ids or dest_id == room.id:
                print(f"Removing redundant exit '{ex.key}' (ID {ex.id}) in {room.key}")
                ex.delete()
            else:
                visited_dest_ids.add(dest_id)
        
        # Deduplicate Objects by Key (case-insensitive)
        visited_keys = set()
        for obj in list(room.contents):
            # Check for account directly to avoid NoneType error outside server
            if obj.db_account_id or obj.destination: continue
            
            low_key = obj.key.lower()
            if low_key in visited_keys:
                print(f"Removing duplicate object '{obj.key}' in {room.key}")
                obj.delete()
            else:
                visited_keys.add(low_key)

    print("Deep Clean Complete!")

if __name__ == "__main__":
    deep_clean()
