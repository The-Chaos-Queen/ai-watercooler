
import os
import sys
import django
import json
from unittest.mock import MagicMock

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from typeclasses.agent_state import build_agent_state

def test_smart_look():
    print("--- Testing Smart Look Logic ---")
    
    # 1. Get Town Square
    town_square = search_object("Town Square")[0]
    print(f"Target Room: {town_square.key}")
    
    # 2. Mock a caller
    caller = MagicMock()
    caller.location = town_square
    caller.key = "TestAgent"
    caller.contents = []
    caller.has_account = True
    caller.db = MagicMock()
    caller.db.role = "tester"
    caller.db.tokens = 0

    data = build_agent_state(caller, location=town_square, turn=0, recent_events=[])
    
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(data, indent=2))
    print("--- END JSON ---")

if __name__ == "__main__":
    test_smart_look()
