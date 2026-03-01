import os
import sys
import django

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB

def cleanup_orphans():
    print("--- Cleaning up Orphaned/Duplicate Rooms ---")
    # Orphaned duplicates identified in list_all_objs
    orphans = [129, 132, 138, 141, 144]
    
    # Tutorial rooms (IDs 3-64) are also unreachable/dead ends as per world_audit.md
    # Let's keep them for now unless asked to nuke, but let's definitely kill the new duplicates.
    
    for oid in orphans:
        try:
            obj = ObjectDB.objects.get(id=oid)
            print(f"Deleting duplicate/orphan: {obj.key} (#{obj.id})")
            obj.delete()
        except ObjectDB.DoesNotExist:
            pass

    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup_orphans()
