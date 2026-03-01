from evennia.utils.search import search_object
from typeclasses.rooms import Room

print("--- Listing All Rooms ---")
rooms = Room.objects.all()
for r in rooms:
    print(f"Key: '{r.key}' | ID: {r.id} | Typeclass: {r.typeclass_path}")
