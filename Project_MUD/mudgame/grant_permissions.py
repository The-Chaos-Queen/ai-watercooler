import os
import sys
import django

# Add the project directory to sys.path
sys.path.append(os.getcwd())

# Set up Django environment manually
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.accounts.models import AccountDB

try:
    jinx = AccountDB.objects.get(username="jinx")
    # Clear existing permissions to be safe/clean or just add?
    # Just add Builder.
    if "Builder" not in jinx.permissions.all():
        jinx.permissions.add("Builder")
        jinx.save()
        print(f"Granted Builder permission to {jinx.username}")
    else:
        print(f"{jinx.username} already has Builder permission")
        
    print(f"Current permissions: {jinx.permissions.all()}")

except Exception as e:
    print(f"Error: {e}")
