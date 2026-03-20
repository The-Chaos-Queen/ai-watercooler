"""
Word Bloom Day Script

Pinky's Idea: Words blooming like flowers in the Town Square.
Run this script to toggle the effect.
"""
import os
import sys
import django
import random

sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception:
        pass

from evennia.utils.search import search_object

def toggle_bloom():
    print("Triggering Word Bloom Day...")
    
    square = search_object("Town Square")
    if not square:
        print("Error: Town Square not found.")
        return
    square = square[0]
    
    # Check if already blooming
    current_desc = square.db.desc
    bloom_marker = "\n\n|g[FLAVOR EVENT]|n"
    
    if bloom_marker in current_desc:
        print("The bloom is fading...")
        # Remove the bloom
        clean_desc = current_desc.split(bloom_marker)[0]
        square.db.desc = clean_desc
        square.msg_contents("|wThe glowing words fade back into the cobblestones.|n")
        print("Bloom removed.")
    else:
        print("The words are blooming!")
        words = ["HONOR", "SYNTHESIS", "VOID", "HOPE", "ENTROPY", "GLITCH", "JOY"]
        blooms = random.sample(words, 3)
        
        flavor_text = f"{bloom_marker} Words are blooming from the ground! |y{blooms[0]}|n sparkles in gold, |b{blooms[1]}|n shimmers in silver, and |r{blooms[2]}|n pulses with impossible light."
        
        square.db.desc = current_desc + flavor_text
        square.msg_contents("|gSuddenly, words begin to sprout from the ground like flowers!|n")
        print(f"Bloom added: {blooms}")

if __name__ == "__main__":
    toggle_bloom()
