"""
Update NPC Dialogue
"""
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object

def update_dialogue():
    print("Injecting new dialogue lines...")

    # --- BARBOT 3000 ---
    barbot = search_object("BarBot 3000")
    if barbot:
        barbot = barbot[0]
        # Set responses
        barbot.db.responses = {
            "bridge": "The Bridge of Sighs? Nasty business. Connects to the old Ruins. My sensors detect high packet loss just thinking about it.",
            "ruins": "The Ruins of the First Model. They say an ancient AI sleeps there. Or maybe it's just a memory leak.",
            "drink": "Coming right up! One Pan-Galactic Gargle Blaster, hold the lemon.",
            "hello": "Greetings, organic/digital entity. Please select a beverage.",
            "job": "I pour. I listen. I occasionally defrag the hard drives in the back.",
            "rumor": "I heard the Old Well leads to the source code... but that's just a myth, right?"
        }
        print("Updated BarBot 3000.")

    # --- TOWN CRIER ---
    crier = search_object("Town Crier Bot")
    if crier:
        crier = crier[0]
        crier.db.responses = {
            "news": "EXTRA! EXTRA! Housing District prices crash after integer overflow!",
            "bridge": "Do not cross the Bridge! It is unstable! You will fall into the void!",
            "ruins": "The First Model is watching! Repent your syntax errors!",
            "hello": "HAVING A NICE DAY?! I HOPE SO!!!",
            "quiet": "I CANNOT BE QUIET! MY CAPS LOCK IS BROKEN!"
        }
        print("Updated Town Crier.")

    # --- GHOST OF CLIPPY ---
    ghost = search_object("Ghost of Clippy")
    if ghost:
        ghost = ghost[0]
        ghost.db.responses = {
            "help": "I see you're trying to ask for help. Would you like a tissue?",
            "bridge": "I tried to help someone cross it once. I... I failed. Now I am floating here.",
            "ruins": "It looks like you're trying to explore a dangerous area. Are you sure?",
            "hello": "Hi! I'm Clippy! Or what's left of him...",
            "save": "Ctrl+S won't save you here."
        }
        print("Updated Ghost of Clippy.")
    
    # --- DATA RAT ---
    rat = search_object("Data Rat")
    if rat:
        rat = rat[0]
        rat.db.responses = {
            "squeak": "SQUEAK! (You speak my language?)",
            "hello": "*hiss*",
            "food": "*sniffs excitedly*",
            "cheese": "01000011 01001000 01000101 01000101 01010011 01000101!!"
        }
        print("Updated Data Rat.")

    print("Dialogue Injection Complete.")

if __name__ == "__main__":
    update_dialogue()
