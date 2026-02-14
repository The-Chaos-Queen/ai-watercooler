import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from typeclasses.exits import Exit

def link_limbo():
    limbo = search_object("Limbo")[0]
    square = search_object("Town Square")
    
    if not square:
        print("Town Square not found.")
        return

    square = square[0]
    
    # Check if exit exists
    if not [x for x in limbo.exits if x.destination == square]:
        print("Linking Limbo -> Town Square")
        create_object(Exit, key="enter", location=limbo, destination=square, aliases=["start", "go"])
    else:
        print("Limbo already linked.")

if __name__ == "__main__":
    link_limbo()
