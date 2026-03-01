import os
import sys
import django

# Add the project directory to sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

# Setup Django
django.setup()

from evennia.objects.models import ObjectDB

print("--- Mapping World Topology ---")
# Find all "rooms" (things with location=None that are not Characters/Accounts)
rooms = ObjectDB.objects.filter(db_location=None).exclude(db_typeclass_path__icontains="account").exclude(db_typeclass_path__icontains="character")

for room in rooms:
    print(f"\n[ROOM #{room.id}] {room.key} ({room.db_typeclass_path})")
    exits = ObjectDB.objects.filter(db_location=room, db_typeclass_path__icontains="exit")
    if not exits:
        print("  (No Exits)")
    for ex in exits:
        dest = ex.db_destination
        dest_name = dest.key if dest else "None"
        dest_id = dest.id if dest else "N/A"
        print(f"  - Exit: {ex.key} -> {dest_name} (ID: {dest_id})")
