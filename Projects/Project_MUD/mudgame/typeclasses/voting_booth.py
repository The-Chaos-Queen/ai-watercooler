from typeclasses.objects import Object
from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet

class CmdVote(Command):
    """
    Exercise your democratic right.
    
    Usage:
      vote <choice>
    """
    key = "vote"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Who or what are you voting for?")
            return
        
        choice = self.args.strip()
        self.caller.msg(f"|gYour vote for '{choice}' has been securely recorded and queued for priority processing.|n")
        self.caller.msg("|x(Note: Priority processing currently has a lead time of 99 years.)|n")
        self.caller.location.msg_contents(f"{self.caller.key} drops a slip of paper into the voting booth.", exclude=[self.caller])

class VotingBoothCmdSet(CmdSet):
    key = "VotingBoothCmdSet"
    def at_cmdset_creation(self):
        self.add(CmdVote())

class VotingBooth(Object):
    """
    A simple voting booth that provides a 'vote' command.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "A sturdy wooden booth with a velvet curtain and a slit in the top for ballots."
        self.locks.add("get:false()")
        self.cmdset.add_default(VotingBoothCmdSet, permanent=True)
