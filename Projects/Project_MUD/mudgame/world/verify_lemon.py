"""
Verification script for the Lemon Monument.
"""
import os
import sys
import django

# Setup Evennia environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.objects.models import ObjectDB

def verify():
    print("Verifying the Lemon Monument...")

    # Find the monument
    monuments = search_object("Lemon Monument")
    if not monuments:
        print("Error: 'Lemon Monument' not found!")
        return
    
    lemon = monuments[0]
    print(f"Found {lemon.key} (#id: {lemon.id})")
    
    # Check location
    if lemon.location.key == "The Neural Tavern":
        print(f"Correctly located in {lemon.location.key}")
    else:
        print(f"Incorrect location: {lemon.location.key}")

    # Check typeclass
    typeclass_path = lemon.db_typeclass_path
    print(f"Typeclass: {typeclass_path}")
    if "typeclasses.monuments.LemonMonument" in typeclass_path:
        print("Typeclass is correct.")
    else:
        print("Typeclass is incorrect!")

    # Check description
    if "towering, impossibly smooth monument of a lemon" in lemon.db.desc:
        print("Description is correct.")
    else:
        print("Description is missing or wrong.")

    # Check commands
    cmdset = lemon.cmdset.all()[0]
    print(f"Default CmdSet: {cmdset}")
    
    # Check specific commands in cmdset
    # Note: Accessing internal structure of cmdset for verification
    cmd_keys = [cmd.key for cmd in cmdset]
    print(f"Commands in CmdSet: {cmd_keys}")
    
    required_cmds = ["sniff monument", "lick monument", "ponder lemon"]
    for cmd in required_cmds:
        if cmd in cmd_keys:
            print(f"  [PASS] {cmd}")
        else:
            print(f"  [FAIL] {cmd}")

if __name__ == "__main__":
    verify()
