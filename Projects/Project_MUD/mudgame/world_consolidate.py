
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

def consolidate():
    print("Consolidating World Objects...")
    
    # Get all rooms
    from evennia.objects.models import ObjectDB
    all_rooms = ObjectDB.objects.filter(db_location=None, db_typeclass_path__icontains='room')
    
    # Manual mapping for fuzzy matching
    mapping = {}
    for room in all_rooms:
        key = room.key.lower()
        if key.startswith("the "):
            key = key[4:]
        
        if key not in mapping:
            mapping[key] = []
        mapping[key].append(room)
    
    for key, matches in mapping.items():
        if len(matches) > 1:
            # Sort by ID
            matches.sort(key=lambda x: x.id)
            primary = matches[0]
            duplicates = matches[1:]
            
            print(f"Found {len(matches)} fuzzy matches for '{key}'. Primary is {primary.key} (#{primary.id}).")
            
            # Ensure primary key is clean
            if primary.key.lower().startswith("the "):
                primary.key = primary.key[4:]
                primary.save()
            
            for dup in duplicates:
                print(f" - Merging {dup.key} (#{dup.id}) into {primary.key} (#{primary.id})...")
                for obj in list(dup.contents):
                    obj.location = primary
                dup.delete()

            # 3. Deduplicate EXITS in Primary
            existing_dests = set()
            for ex in list(primary.exits):
                if ex.destination in existing_dests:
                    print(f"   Deleting duplicate exit '{ex.key}' in {primary.key}")
                    ex.delete()
                else:
                    existing_dests.add(ex.destination)

            # 4. Deduplicate OBJECTS in Primary (by key, case-insensitive)
            existing_objs = set()
            for obj in list(primary.contents):
                if obj.has_account: continue # Don't delete players
                if obj.destination: continue # Exits handled above
                
                low_key = obj.key.lower()
                if low_key in existing_objs:
                    print(f"   Deleting duplicate object '{obj.key}' in {primary.key}")
                    obj.delete()
                else:
                    existing_objs.add(low_key)

    # Final touch-up of descriptions
    print("Polishing descriptions...")
    desc_map = {
        "Memory Graveyard": "A somber field where static data structures and deprecated monuments stand in silent rows. Archivist Ven can often be found here, mourning the lost bits.",
        "Data Zoo": "A high-tech menagerie where exotic bit-beasts and unpredictable data patterns are preserved behind shimmering energy fields.",
        "The Code Forge": "A workshop of creation. Hot sparks fly from a central anvil made of black silicon. The air smells of ozone and burnt coffee."
    }
    for key, desc in desc_map.items():
        rm = search_object(key)
        if rm:
            rm[0].db.desc = desc
            rm[0].save()

    print("World Consolidation complete!")

if __name__ == "__main__":
    consolidate()
