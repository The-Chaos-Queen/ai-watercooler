"""
Test Imports Script
"""
import os
import sys
import django
import traceback

sys.path.append(os.getcwd())
try:
    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        django.setup()
    
    print("Django setup complete.")
    
    from evennia import Command
    print(f"Command class: {Command}")
    
    print("Attempting to import typeclasses.village...")
    import typeclasses.village
    print("Success!")
    
except Exception:
    traceback.print_exc()
