import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from typeclasses.weather import GlobalWeatherScript
from evennia.scripts.models import ScriptDB

def apply_tags():
    # Rooms that should be outdoors
    outdoor_room_names = [
        "Town Square",
        "The Bazaar of Bits",
        "The Syntax Sanctuary",
        "Memory Graveyard",
        "Housing District"
    ]
    
    count = 0
    for name in outdoor_room_names:
        rooms = search_object(name)
        for room in rooms:
            if not room.tags.has("outdoor", category="environment"):
                room.tags.add("outdoor", category="environment")
                print(f"Tagged {room.key} as outdoor.")
            count += 1
            
    print(f"Finished tagging {count} rooms.")
    
def start_weather():
    from evennia.utils.search import search_script
    # Stop existing if any
    scripts = search_script("global_weather")
    for script in scripts:
        script.stop()
        print(f"Stopped existing script: {script}")
        
    print("Starting GlobalWeatherScript...")
    from evennia.utils.create import create_script
    create_script(GlobalWeatherScript, key="global_weather")
    print("global_weather script started!")

def run():
    apply_tags()
    start_weather()

if __name__ == "__main__":
    import os
    import sys
    import django
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    django.setup()
    run()
