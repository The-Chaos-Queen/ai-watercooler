import os
import sys
import django

# Add the current directory to sys.path
sys.path.append(os.getcwd())

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB

try:
    print("--- Checking Jinx Permissions ---")
    try:
        jinx = AccountDB.objects.get(username="Jinx")
        if "Builder" not in jinx.permissions.all():
            jinx.permissions.add("Builder")
            jinx.save()
            print(f"Granted Builder permission to {jinx.username}")
        else:
            print(f"{jinx.username} already has Builder permission: {jinx.permissions.all()}")
            
    except AccountDB.DoesNotExist:
        print("Account 'Jinx' does not exist. Listing all accounts:")
        for acc in AccountDB.objects.all():
            print(f" - {acc.username} (#{acc.id})")
        sys.exit(1)

    print("\n--- Finding Town Square ---")
    town_squares = ObjectDB.objects.filter(db_key="Town Square")
    ts = None
    if town_squares:
        # Prefer #80 as per logs, otherwise take first
        ts = next((t for t in town_squares if t.id == 80), town_squares[0])
        print(f"Found Town Square: {ts.name} (#{ts.id})")
    else:
        print("Town Square not found. Listing 'Square' locations:")
        start_rooms = ObjectDB.objects.filter(db_key__contains="Square")
        for r in start_rooms:
             print(f"Possible match: {r.name} (#{r.id})")
        sys.exit(1)

    print("\n--- Checking Jinx Character ---")
    try:
        # Assuming Jinx has a character linked
        char = jinx.db._first_login_puppet
        # If not set, try to find a character named Jinx
        if not char:
            # Need to filter because get might return multiple if not unique
            chars = ObjectDB.objects.filter(db_key__iexact="Jinx")
            if chars:
                char = chars[0]
        
        if char:
             print(f"Jinx Character: {char.name} (#{char.id})")
             print(f"Current Home: {char.home}")
             print(f"Current Location: {char.location}")
             
             # Move to Town Square if needed
             if char.location != ts:
                 char.location = ts
                 char.save()
                 print(f" -> Moved Jinx to {ts.name} (#{ts.id})")
             else:
                 print(" -> Already at Town Square")
             
             if char.home != ts:
                 char.home = ts
                 char.save()
                 print(f" -> Set Jinx home to {ts.name} (#{ts.id})")
             else:
                 print(" -> Home is already set correctly")

             # Check cmdset
             print(f"\nCmdsets on character:")
             for cmdset in char.cmdset.all():
                 print(f" - {cmdset.key} ({cmdset.path})")
                 
             # List available commands
             # We can try to list commands available to the character
             # But this requires a session. We can inspect the cmdset content.
             # commands = []
             # for cmdset in char.cmdset.all():
             #    commands.extend([cmd.key for cmd in cmdset.commands])
             # print(f"Available commands (approx): {commands}")

        else:
             print("No character found for Jinx account.")

    except Exception as e:
        print(f"Error checking character: {e}")

except Exception as e:
    print(f"Error: {e}")
