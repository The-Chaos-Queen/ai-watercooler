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

def analyze_world():
    print("--- Detailed World Analysis ---")
    
    # 1. Check for Room names starting with "The "
    rooms = ObjectDB.objects.filter(db_typeclass_path__contains='Room')
    print("\n[ROOMS WITH ARTICLES]")
    for r in rooms:
        if r.key.startswith("The "):
            print(f"Room: '{r.key}' | ID: {r.id}")

    # 2. Check for Exit names starting with "The "
    exits = ObjectDB.objects.filter(db_typeclass_path__contains='Exit')
    print("\n[EXITS WITH ARTICLES]")
    for e in exits:
        if e.key.startswith("The "):
            print(f"Exit: '{e.key}' | ID: {e.id} | Location: {e.location}")

    # 3. Check for Duplicates
    print("\n[POSSIBLE DUPLICATES]")
    keys = {}
    all_objs = ObjectDB.objects.all()
    for obj in all_objs:
        k = (obj.key, obj.db_typeclass_path, obj.db_location_id)
        if k in keys:
            keys[k].append(obj.id)
        else:
            keys[k] = [obj.id]
    
    for k, ids in keys.items():
        if len(ids) > 1:
            print(f"Key/Type/Loc: {k} | IDs: {ids}")

if __name__ == "__main__":
    analyze_world()
