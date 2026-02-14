import os
import sys
import django
from django.conf import settings

# Setup Django/Evennia environment
sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception as e:
        print(f"Django setup failed: {e}")
        sys.exit(1)

from evennia.utils.search import search_object
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils import utils

def clean_text(text):
    if not text: return ""
    return text.replace("\n", " ").strip()

def analyze_world():
    print("Starting World Analysis...")
    
    # Create a dummy character to generate dynamic descriptions
    tester = None
    try:
        tester = create_object("typeclasses.characters.Character", key="WorldTester", location=None, home=None)
        print("Created temporary tester character.")
    except Exception as e:
        print(f"Could not create tester character: {e}")
        # Fallback: inspection without a character context might miss dynamic bits
    
    all_rooms = ObjectDB.objects.filter(db_location=None, db_typeclass_path__icontains='room')
    
    report = []
    report.append("# World Audit Report\n")
    report.append(f"TOTAL ROOMS: {all_rooms.count()}\n")
    
    issues = []
    
    # Build graph for connectivity check
    room_map = {} # id -> {exits: [dest_id], name: str}
    
    for room in all_rooms:
        room_id = room.id
        room_key = room.key
        
        # 1. Check Description
        desc = room.db.desc
        dynamic_desc = ""
        if tester:
            try:
                # Set location to trigger any hooks
                tester.location = room
                # Capture return_appearance
                dynamic_desc = room.return_appearance(tester)
            except Exception as e:
                dynamic_desc = f"ERROR getting appearance: {e}"
                issues.append(f"- **[Room #{room.id}] {room_key}**: Crash on look ({e})")

        if not desc and not dynamic_desc:
            issues.append(f"- **[Room #{room.id}] {room_key}**: NO DESCRIPTION")
        elif desc and len(desc) < 20: # Heuristic for too short
             issues.append(f"- **[Room #{room.id}] {room_key}**: Description too short ('{clean_text(desc)}')")

        # 2. Check Exits
        exits = room.exits
        exit_ids = []
        if not exits:
            issues.append(f"- **[Room #{room.id}] {room_key}**: DEAD END (No exits)")
        
        for ex in exits:
            dest = ex.destination
            if not dest:
                issues.append(f"- **[Room #{room.id}] {room_key}**: Broken Exit '{ex.key}' -> None")
            else:
                exit_ids.append(dest.id)
                if dest == room:
                    issues.append(f"- **[Room #{room.id}] {room_key}**: Loop Exit '{ex.key}' -> Self")
        
        room_map[room_id] = {'name': room_key, 'exits': exit_ids}

        # 3. Check Contents (Objects)
        for obj in room.contents:
            if obj.db_typeclass_path and 'exit' in obj.db_typeclass_path: continue
            if obj == tester: continue
            
            if not obj.db.desc:
                issues.append(f"- **[Room #{room.id}] {room_key}**: Object '{obj.key}' has no description")

    # 4. Check Connectivity (Islands)
    # Find rooms that are not reachable from a "Start" room. 
    # Usually Limbo (#2) or a main hub is start. Let's assume Room #2 or first available.
    if room_map:
        start_id = min(room_map.keys()) # Heuristic: lowest ID is usually start/limbo
        # or search for "Limbo"
        limbos = [r.id for r in all_rooms if "Limbo" in r.key]
        if limbos: start_id = limbos[0]
            
        visited = set()
        queue = [start_id]
        while queue:
            curr = queue.pop(0)
            if curr in visited: continue
            visited.add(curr)
            if curr in room_map:
                for dest in room_map[curr]['exits']:
                    if dest not in visited:
                        queue.append(dest)
        
        unreachable = set(room_map.keys()) - visited
        if unreachable:
            report.append(f"\n## Unreachable Rooms (Islands)\n")
            for uid in unreachable:
                rname = room_map[uid]['name']
                report.append(f"- [#{uid}] {rname}")
                issues.append(f"- **[Room #{uid}] {rname}**: ISOLATED/UNREACHABLE from start #{start_id}")

    report.append("\n## Issues Found\n")
    if issues:
        report.extend(issues)
    else:
        report.append("No major issues found.")

    # Cleanup
    if tester:
        tester.delete()

    with open("world_audit.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print("Audit complete. See world_audit.md")

if __name__ == "__main__":
    analyze_world()
