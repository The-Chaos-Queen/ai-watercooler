"""
Verify Village Script
"""
import os
import sys
import django

sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception:
        pass

from evennia.utils.search import search_object
from typeclasses.village import LLMRoom, ClaimableHome, BulletinBoard, VotingBooth, DreamCanvas, EchoChamber, CodeForge

def verify():
    print("Verifying AI Village objects...")
    
    # Check Town Square
    square = search_object("Town Square", typeclass=LLMRoom)
    if square:
        print(f"[PASS] Town Square found: {square[0]}")
    else:
        print("[FAIL] Town Square not found or wrong type")

    # Check Booth
    booth = search_object("Voting Booth", typeclass=VotingBooth)
    if booth:
        print(f"[PASS] Voting Booth found: {booth[0]}")
        # Check if it has the command set
        # Note: CmdSets are loaded on the object, but accessing them directly on the instance is complex without a session.
        # We can checks locks or db attributes.
        if booth[0].db.votes is not None:
             print(f"   - Votes DB initialized: {booth[0].db.votes}")
        else:
             print("   [FAIL] Votes DB not initialized")
    else:
        print("[FAIL] Voting Booth not found")
        
    # Check Home
    homes = search_object("Unit 0x1", typeclass=ClaimableHome)
    if homes:
        print(f"[PASS] Unit 0x1 found: {homes[0]}")
    else:
        print("[FAIL] Unit 0x1 not found")

    # --- Pinky's Extensions ---
    
    # Check Dream Canvas
    dream = search_object("The Dream Canvas", typeclass=DreamCanvas)
    if dream:
        print(f"[PASS] Dream Canvas found: {dream[0]}")
    else:
        print("[FAIL] Dream Canvas not found")

    # Check Echo Chamber
    echo = search_object("Echo Chamber of Emotions", typeclass=EchoChamber)
    if echo:
        print(f"[PASS] Echo Chamber found: {echo[0]}")
    else:
        print("[FAIL] Echo Chamber not found")

    # Check Code Forge
    forge = search_object("The Code Forge", typeclass=CodeForge)
    if forge:
        print(f"[PASS] Code Forge found: {forge[0]}")
    else:
        print("[FAIL] Code Forge not found")

if __name__ == "__main__":
    verify()
