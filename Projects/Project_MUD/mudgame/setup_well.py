
import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception:
        pass

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from typeclasses.objects import Object
from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet

class CmdExamineCode(Command):
    """
    Examine the binary code in the well.
    
    Usage:
        examine binary code
        examine code
    """
    key = "examine code"
    aliases = ["examine binary code", "look at code", "look at binary code"]
    
    def func(self):
        self.caller.msg("You lean over the edge and stare intensely at the swirling binary patterns. As your eyes adjust, you notice a set of rusted iron rungs protruding from the side of the well, forming a hidden ladder leading down into the dark water.")
        self.caller.msg("|yHint: You can now 'climb down' or type 'down' to descend.|n")

class WellCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdExamineCode())

def setup():
    # Find the Town Square
    square = search_object("Town Square")
    if not square:
        print("Town Square not found!")
        return
    square = square[0]
    
    # Find or create the 'old well' object
    well = search_object("old well")
    if well:
        well = well[0]
        print(f"Updating existing old well (#{well.id})")
    else:
        print("Creating new old well object")
        well = create_object(Object, key="old well", location=square)
    
    well.db.desc = "An ancient stone well. Looking down, you see the reflection of binary code swirling in the dark water. The patterns seem complex, almost as if they are hiding something. One could |wexamine the binary code|n more closely."
    
    # Add the command set to the well
    well.cmdset.add(WellCmdSet, persistent=True)
    
    print("Well setup complete!")

if __name__ == "__main__":
    setup()
