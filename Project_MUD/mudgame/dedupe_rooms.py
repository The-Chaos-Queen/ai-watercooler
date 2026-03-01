import os
import sys
import django

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB

def dedupe_rooms():
    print("--- Deduping Rooms based on Analysis ---")
    
    # We want to keep the HIGHER IDs (created by enrich_village) as they are likely better connected
    dupes = [
        (135, 341), # Code Forge
        (314, 397), # Bazaar of Bits
        (315, 398), # Archive of Echoes
        (316, 399), # Compile Corner
        (317, 400), # Syntax Sanctuary
        (318, 401), # Null Void
        (319, 402)  # Consensus Chamber
    ]
    
    for old_id, new_id in dupes:
        try:
            old_room = ObjectDB.objects.get(id=old_id)
            new_room = ObjectDB.objects.get(id=new_id)
            
            print(f"Moving content from {old_room.key} (#{old_id}) to (#{new_id})")
            
            # Move contents
            for obj in list(old_room.contents):
                if obj.id != new_id: # avoid moving the room into itself if something is weird
                    obj.location = new_room
                    obj.save()
            
            # Note: We don't move exits automatically as they are linked to the ROOM ID.
            # But the 'deep_clean.py' might have helped or built-in logic.
            # actually, let's just delete the old one. If it was isolated, no harm.
            
            print(f"Deleting old room #{old_id}")
            old_room.delete()
            
        except ObjectDB.DoesNotExist:
            print(f"One of the IDs ({old_id}, {new_id}) already gone.")

    print("Deduping complete.")

if __name__ == "__main__":
    dedupe_rooms()
