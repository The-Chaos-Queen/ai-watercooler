
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

def run_check():
    a = search_object('Antigravity')
    if not a:
        print("Antigravity not found!")
        return
    a = a[0]
    
    rooms = [
        'Town Square', 
        'The Neural Tavern', 
        'Memory Graveyard', 
        'The Binary Bazaar', 
        'Cortex Hall', 
        'Data Zoo', 
        'The Code Forge'
    ]
    
    print("="*60)
    print("MUD WORLD TOUR - ANTIGRAVITY INSPECTION")
    print("="*60)
    
    for rname in rooms:
        r = search_object(rname)
        if not r:
            print(f"\n[ERROR] Room '{rname}' NOT FOUND!")
            continue
        
        r = r[0]
        # Move Antigravity to verify appearance
        a.location = r
        a.save()
        
        print(f"\n--- {r.key} (#{r.id}) ---")
        print(r.return_appearance(a))
        print("-" * 40)
        exits = [f"{ex.key} -> {ex.destination.key if ex.destination else 'None'}" for ex in r.exits]
        print(f"Exits: {exits}")
    
    print("\n" + "="*60)
    print("TOUR COMPLETE")
    print("="*60)

if __name__ == "__main__":
    run_check()
