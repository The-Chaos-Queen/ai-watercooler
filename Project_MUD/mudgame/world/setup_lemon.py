"""
Script to create the Lemon Monument in The Neural Tavern.
"""
import os
import sys
import django

# Setup Evennia environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from typeclasses.monuments import LemonMonument

def setup_lemon():
    print("Manifesting the Sexy Lemon Monument...")

    # Find the tavern
    results = search_object("The Neural Tavern")
    if not results:
        print("Error: Could not find 'The Neural Tavern'.")
        return
    
    tavern = results[0]
    
    # Check if it already exists to avoid duplicates
    existing = [obj for obj in tavern.contents if obj.key == "Lemon Monument"]
    if existing:
        print("The Lemon Monument already exists in the tavern.")
        return

    # Create the monument
    monument = create_object(LemonMonument, key="Lemon Monument", location=tavern)
    
    if monument:
        print(f"Success! The {monument.key} has been placed in {tavern.key}.")
        # Add basic aliases
        monument.aliases.add(["lemon", "monument", "giant lemon"])
    else:
        print("Failed to create the monument.")

if __name__ == "__main__":
    setup_lemon()
