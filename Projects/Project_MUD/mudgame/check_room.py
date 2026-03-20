from evennia.utils.search import search_object

print("--- Checking The Bazaar of Bits ---")
rooms = search_object("The Bazaar of Bits")
if rooms:
    room = rooms[0]
    print(f"Key: '{room.key}'")
    print(f"Desc: {room.db.desc}")
    print(f"Exits: {[x.key for x in room.exits]}")
    print(f"Contents: {[x.key for x in room.contents]}") 
else:
    print("Room not found.")
