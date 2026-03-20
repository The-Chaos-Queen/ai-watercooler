import os
import sys
from collections import defaultdict

import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB


def exit_score(exit_obj):
    aliases = []
    try:
        aliases = list(exit_obj.aliases.all())
    except Exception:
        pass

    dest_name = exit_obj.destination.key if exit_obj.destination else ""
    key_matches_dest = int((exit_obj.key or "").strip().lower() == dest_name.strip().lower())
    has_desc = int(bool(getattr(exit_obj.db, "desc", None)))
    alias_count = len(aliases)

    return (key_matches_dest, has_desc, alias_count, -exit_obj.id)


def dedupe_exits():
    rooms = [obj for obj in ObjectDB.objects.all() if not getattr(obj, "db_destination", None)]
    removed = 0

    for room in rooms:
        by_destination = defaultdict(list)
        for exit_obj in room.exits:
            if exit_obj.destination:
                by_destination[exit_obj.destination.id].append(exit_obj)

        for destination_id, duplicates in by_destination.items():
            if len(duplicates) < 2:
                continue

            keep = max(duplicates, key=exit_score)
            destination = keep.destination.key if keep.destination else str(destination_id)
            print(f"[ROOM {room.id} {room.key}] keeping exit #{keep.id} '{keep.key}' -> {destination}")

            for exit_obj in duplicates:
                if exit_obj.id == keep.id:
                    continue
                print(f"  deleting duplicate exit #{exit_obj.id} '{exit_obj.key}'")
                exit_obj.delete()
                removed += 1

    print(f"Removed {removed} duplicate exits.")


if __name__ == "__main__":
    dedupe_exits()
