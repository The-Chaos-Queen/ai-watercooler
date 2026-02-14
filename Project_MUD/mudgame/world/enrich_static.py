"""
Script to Enrich the World with Interactive Content
"""
import os
import sys
import django
import random

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.search import search_object
from evennia.utils.create import create_object, create_script
from typeclasses.interactions import InteractiveObject, RoamingNPC, RoamingScript

def enrich():
    print("Enriching the World with Interaction & Details!")

    # 1. Town Square Enrichment
    sq = search_object("Town Square")[0]
    
    # Fountain
    fountain = create_object(InteractiveObject, key="Matrix Fountain", location=sq,
                             attributes=[("desc", "A fountain spewing glowing green code instead of water."),
                                         ("reactions", {"drink": "You cup your hands and drink the raw data. It tastes like mint and electricity.",
                                                        "touch": "The liquid code ripples under your fingers.",
                                                        "splash": "You splash the code around! Bits fly everywhere!"})])
    print(f"Created {fountain}")

    # Bench
    bench = create_object(InteractiveObject, key="Park Bench", location=sq,
                          attributes=[("desc", "A worn wooden bench with 'Bob was here' carved into it in ASCII."),
                                      ("reactions", {"sit": "You sit on the bench. It creaks ominously.",
                                                     "touch": "Rough wood.",
                                                     "look": "Someone carved 'Hello World' here too."})])
    print(f"Created {bench}")

    # NPC: Town Crier
    crier = create_object(RoamingNPC, key="Town Crier Bot", location=sq,
                          attributes=[("desc", "A frantic robot with a megaphone for a head."),
                                      ("chat_lines", ["Hear ye! Hear ye! The server is creating new content!",
                                                      "Warning! Low memory usage detected in Sector 7G!",
                                                      "Does anyone update their drivers anymore?!",
                                                      "I saw a glitch near the Bazaar!",
                                                      "Upgrade now! Only 9.99 credits!"])])
    # Attach Script manually if not done by at_object_creation (which it should be, but let's be sure)
    create_script(RoamingScript, obj=crier)
    print(f"Created {crier}")

    # 2. Tavern Enrichment
    tavern = search_object("The Neural Tavern")[0]
    
    # Jukebox
    juke = create_object(InteractiveObject, key="Cyber-Jukebox", location=tavern,
                         attributes=[("desc", "A retro-futuristic music player with glowing tubes."),
                                     ("reactions", {"play": "You hit play. Smooth jazz algorithm #4 starts playing.",
                                                    "kick": "The jukebox sputters and switches to Dubstep.",
                                                    "touch": "It's warm to the touch."})])
    print(f"Created {juke}")

    # NPC: BarBot
    barbot = create_object(RoamingNPC, key="BarBot 3000", location=tavern,
                           attributes=[("desc", "A sleek chrome bartender polishing a glass loop."),
                                       ("chat_lines", ["What'll it be, stranger?",
                                                       "We don't serve recursive functions here.",
                                                       "Try the Kernel Panic, it's strong.",
                                                       "Don't forget to tip your server!"])])
    create_script(RoamingScript, obj=barbot)
    print(f"Created {barbot}")

    # 3. Bazaar Enrichment
    bazaar = search_object("The Binary Bazaar")[0]
    
    # Stall
    stall = create_object(InteractiveObject, key="Glitch Stall", location=bazaar,
                          attributes=[("desc", "A shady stall selling... broken textures?"),
                                      ("reactions", {"buy": "The merchant hisses: 'Not for sale... yet.'",
                                                     "touch": "Your hand passes through the stall. It's an illusion!",
                                                     "look": "There are crates labeled 'Error 404' everywhere."})])
    print(f"Created {stall}")

    # NPC: Rat
    rat = create_object(RoamingNPC, key="Data Rat", location=bazaar,
                        attributes=[("desc", "A small, pixelated rodent scurrying about."),
                                    ("chat_lines", ["Squeak! (buffer overflow)",
                                                    "Gnawing on a fiber cable...",
                                                    "*scurries away*",
                                                    "Hisss!"])])
    create_script(RoamingScript, obj=rat)
    print(f"Created {rat}")
    
    # 4. Graveyard Enrichment
    grave = search_object("Memory Graveyard")[0]
    
    # NPC: Ghost
    ghost = create_object(RoamingNPC, key="Ghost of Clippy", location=grave,
                          attributes=[("desc", "A floating, mournful paperclip."),
                                      ("chat_lines", ["It looks like you're trying to visit a grave. Would you like help?",
                                                      "I use to be helpful...",
                                                      "Save... save me...",
                                                      "Formatting C: drive... just kidding..."])])
    create_script(RoamingScript, obj=ghost)
    print(f"Created {ghost}")

    print("Enrichment Complete! The world is alive!")

if __name__ == "__main__":
    enrich()
