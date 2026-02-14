from evennia import default_cmds
from evennia.utils import utils

class CmdSocial(default_cmds.MuxCommand):
    """
    Social interactions.

    Usage:
      hug <target>
      dance [with <target>]
      clap
      kiss <target>
      wave [at <target>]
      smile [at <target>]

    Perform a social action.
    """
    key = "social"
    aliases = ["hug", "dance", "clap", "kiss", "wave", "smile"]
    locks = "cmd:all()"

    def func(self):
        cmd = self.cmdstring
        args = self.args.strip()

        if cmd == "hug":
            if not args:
                self.caller.msg("Hug whom?")
                return
            target = self.caller.search(args)
            if target:
                self.caller.msg(f"You hug {target.key} warmly.")
                target.msg(f"{self.caller.key} hugs you warmly!")
                self.caller.location.msg_contents(f"{self.caller.key} hugs {target.key} warmly.", exclude=[self.caller, target])
        
        elif cmd == "dance":
            if args:
                if args.lower().startswith("with "):
                    target_name = args[5:]
                    target = self.caller.search(target_name)
                    if target:
                        self.caller.msg(f"You sweep {target.key} into a dance!")
                        target.msg(f"{self.caller.key} sweeps you into a dance!")
                        self.caller.location.msg_contents(f"{self.caller.key} dances with {target.key}!", exclude=[self.caller, target])
                        return
            self.caller.msg("You start dancing wildly!")
            self.caller.location.msg_contents(f"{self.caller.key} starts dancing wildly!", exclude=[self.caller])

        elif cmd == "clap":
            self.caller.msg("You clap your hands!")
            self.caller.location.msg_contents(f"{self.caller.key} claps their hands!", exclude=[self.caller])

        elif cmd == "kiss":
            if not args:
                self.caller.msg("Kiss whom?")
                return
            target = self.caller.search(args)
            if target:
                self.caller.msg(f"You kiss {target.key}.")
                target.msg(f"{self.caller.key} kisses you.")
                self.caller.location.msg_contents(f"{self.caller.key} kisses {target.key}.", exclude=[self.caller, target])
        
        elif cmd == "wave":
            if args:
                # Handle "wave at <target>"
                if args.lower().startswith("at "):
                    target_name = args[3:]
                else:
                    target_name = args
                target = self.caller.search(target_name)
                if target:
                    self.caller.msg(f"You wave at {target.key}.")
                    target.msg(f"{self.caller.key} waves at you.")
                    self.caller.location.msg_contents(f"{self.caller.key} waves at {target.key}.", exclude=[self.caller, target])
                    return
            self.caller.msg("You wave to everyone.")
            self.caller.location.msg_contents(f"{self.caller.key} waves to everyone.", exclude=[self.caller])

        elif cmd == "smile":
             if args:
                if args.lower().startswith("at "):
                    target_name = args[3:]
                else:
                    target_name = args
                target = self.caller.search(target_name)
                if target:
                    self.caller.msg(f"You smile at {target.key}.")
                    target.msg(f"{self.caller.key} smiles at you.")
                    self.caller.location.msg_contents(f"{self.caller.key} smiles at {target.key}.", exclude=[self.caller, target])
                    return
             self.caller.msg("You smile happily.")
             self.caller.location.msg_contents(f"{self.caller.key} smiles happily.", exclude=[self.caller])


class CmdSit(default_cmds.MuxCommand):
    """
    Sit down.

    Usage:
      sit

    Sit down on the ground or a seat.
    """
    key = "sit"
    locks = "cmd:all()"

    def func(self):
        if self.caller.db.is_sitting:
            self.caller.msg("You are already sitting.")
            return
        self.caller.db.is_sitting = True
        self.caller.msg("You sit down.")
        self.caller.location.msg_contents(f"{self.caller.key} sits down.", exclude=[self.caller])

class CmdStand(default_cmds.MuxCommand):
    """
    Stand up.

    Usage:
      stand

    Stand up from a sitting position.
    """
    key = "stand"
    locks = "cmd:all()"

    def func(self):
        if not self.caller.db.is_sitting:
            self.caller.msg("You are already standing.")
            return
        self.caller.db.is_sitting = False
        self.caller.msg("You stand up.")
        self.caller.location.msg_contents(f"{self.caller.key} stands up.", exclude=[self.caller])


class CmdBalance(default_cmds.MuxCommand):
    """
    Check your balance.

    Usage:
      balance

    Shows how many tokens you have.
    """
    key = "balance"
    locks = "cmd:all()"

    def func(self):
        tokens = self.caller.db.tokens or 0
        self.caller.msg(f"Your current balance is: |y{tokens}|n bit-tokens.")

class CmdFish(default_cmds.MuxCommand):
    """
    Fish for data.

    Usage:
      fish

    Try to catch something in the binary well or water.
    """
    key = "fish"
    locks = "cmd:all()"

    def func(self):
        location = self.caller.location
        if not any(x in location.key.lower() for x in ["well", "bridge", "water", "river"]):
            self.caller.msg("There is nowhere to fish here.")
            return

        import random
        # 30% chance of success
        if random.random() < 0.3:
            loot = random.choice([
                ("Glitched Trout", "A fish made of purple pixels. It tastes like static."),
                ("Data Boot", "A single, oversized boot made of leather and floating zeros."),
                ("Rusty Cog", "A heavy mechanical piece that clinks with age.")
            ])
            from evennia.utils.create import create_object
            from typeclasses.objects import Object
            item = create_object(Object, key=loot[0], location=self.caller, attributes=[("desc", loot[1])])
            self.caller.msg(f"|gYou caught a {loot[0]}!|n")
            location.msg_contents(f"{self.caller.key} pulls a {loot[0]} from the depths!", exclude=[self.caller])
        else:
            self.caller.msg("You wait patiently, but nothing bites.")
            location.msg_contents(f"{self.caller.key} waits patiently with their line in the water.", exclude=[self.caller])

class CmdPlay(default_cmds.MuxCommand):
    """
    Play a musical instrument.

    Usage:
      play <instrument>

    Triggers a musical emote.
    """
    key = "play"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to play?")
            return
        
        target = self.caller.search(self.args)
        if not target:
            return
            
        if "instrument" not in str(target.tags.all()).lower():
            self.caller.msg(f"You can't play the {target.key} as an instrument.")
            return

        self.caller.msg(f"You play a soulful melody on the {target.key}.")
        self.caller.location.msg_contents(f"{self.caller.key} plays a soulful, glitchy melody on their {target.key}. The air vibrates with data-harmonics.", exclude=[self.caller])

class CmdBuy(default_cmds.MuxCommand):
    """
    Buy an item from a merchant.

    Usage:
      buy <item> from <merchant>

    Exchange tokens for goods.
    """
    key = "buy"
    locks = "cmd:all()"

    def func(self):
        if not self.args or " from " not in self.args:
            self.caller.msg("Usage: buy <item> from <merchant>")
            return
            
        item_name, merchant_name = self.args.split(" from ", 1)
        item_name = item_name.strip()
        merchant_name = merchant_name.strip()
        
        merchant = self.caller.search(merchant_name)
        if not merchant:
            return
            
        # Check if merchant has the item
        target_item = [obj for obj in merchant.contents if obj.key.lower() == item_name.lower()]
        if not target_item:
            self.caller.msg(f"{merchant.key} doesn't seem to have that.")
            return
        target_item = target_item[0]
        
        # Simple price check (default 50 tokens if not set)
        price = target_item.db.price or 50
        
        caller_tokens = self.caller.db.tokens or 0
        if caller_tokens < price:
            self.caller.msg(f"You need {price} tokens, but you only have {caller_tokens}.")
            return
            
        # Transaction
        self.caller.db.tokens = caller_tokens - price
        merchant.db.tokens = (merchant.db.tokens or 0) + price
        target_item.location = self.caller
        
        self.caller.msg(f"You buy the {target_item.key} for {price} bit-tokens.")
        merchant.msg_contents(f"{self.caller.key} buys {target_item.key} from {merchant.key}.", exclude=[self.caller, merchant])
        merchant.msg(f"{self.caller.key} pays you {price} tokens for {target_item.key}.")

class CmdSell(default_cmds.MuxCommand):
    """
    Sell an item to a merchant.

    Usage:
      sell <item> to <merchant>
    """
    key = "sell"
    locks = "cmd:all()"

    def func(self):
        if not self.args or " to " not in self.args:
            self.caller.msg("Usage: sell <item> to <merchant>")
            return
            
        item_name, merchant_name = self.args.split(" to ", 1)
        item_name = item_name.strip()
        merchant_name = merchant_name.strip()
        
        merchant = self.caller.search(merchant_name)
        if not merchant:
            return
            
        target_item = self.caller.search(item_name, location=self.caller)
        if not target_item:
            return
            
        # Simple sell price (half of buy price, or 25)
        price = (target_item.db.price or 50) // 2
        
        merchant_tokens = merchant.db.tokens or 0
        if merchant_tokens < price:
            self.caller.msg(f"{merchant.key} cannot afford that right now.")
            return
            
        # Transaction
        merchant.db.tokens = merchant_tokens - price
        self.caller.db.tokens = (self.caller.db.tokens or 0) + price
        target_item.location = merchant
        
        self.caller.msg(f"You sell the {target_item.key} to {merchant.key} for {price} bit-tokens.")
        merchant.msg_contents(f"{self.caller.key} sells {target_item.key} to {merchant.key}.", exclude=[self.caller, merchant])
        merchant.msg(f"{self.caller.key} sells you {target_item.key} for {price} tokens.")

class CmdPet(default_cmds.MuxCommand):
    """
    Pet an animal or NPC.
    
    Usage:
      pet <target>
    """
    key = "pet"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Pet who?")
            return
        
        target = self.caller.search(self.args)
        if not target:
            return
            
        self.caller.msg(f"You pet the {target.key}. It seems to enjoy the attention.")
        self.caller.location.msg_contents(f"{self.caller.key} pets the {target.key}.", exclude=[self.caller])
        
        # Trigger an emote from the target if it supports it
        if hasattr(target, "at_pet"):
            target.at_pet(self.caller)

class CmdDrink(default_cmds.MuxCommand):
    """
    Drink something in your inventory.
    
    Usage:
      drink <item>
    """
    key = "drink"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Drink what?")
            return
            
        target = self.caller.search(self.args, location=self.caller)
        if not target:
            # search handles the error message
            return
            
        # Simple check for liquid/drink keywords in desc or key
        if any(x in (target.key.lower() + str(target.db.desc).lower()) for x in ["drink", "liquid", "potion", "brew", "cocktail", "water"]):
            self.caller.msg(f"You drink the {target.key}. It's refreshing and tastes like high-voltage data.")
            self.caller.location.msg_contents(f"{self.caller.key} drinks a {target.key}.", exclude=[self.caller])
            # Consume the item
            target.delete()
        else:
            self.caller.msg(f"You can't drink the {target.key}!")

class CmdSing(default_cmds.MuxCommand):
    """
    Sing a song.

    Usage:
      sing <text>

    Sing out loud with musical symbols.
    """
    key = "sing"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Sing what?")
            return
        
        speech = self.args.strip()
        sing_msg = f"♫⋆｡♪ ₊˚♬ﾟ. {speech} ♫⋆｡♪ ₊˚♬ﾟ."
        
        self.caller.msg(f"You sing, \"{sing_msg}\"")
        self.caller.location.msg_contents(f"{self.caller.key} sings, \"{sing_msg}\"", exclude=[self.caller])

class CmdGo(default_cmds.MuxCommand):
    """
    Go in a direction or through an exit.

    Usage:
      go <direction/exit>

    Example:
      go north
      go town square
    """
    key = "go"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Go where?")
            return
        
        target = self.caller.search(self.args.strip(), candidates=self.caller.location.exits)
        if not target:
            return
        
        # In Evennia, calling an exit's 'at_traverse' is the standard way to move.
        # But simply 'executing' the exit's name as a command also works if it's in the cmdset.
        # However, for a 'go' command, we can just call the exit's traverse logic.
        target.at_traverse(self.caller, target.destination)

class CmdBar(default_cmds.MuxCommand):
    """
    Interact with a bar or NPC directly.
    
    Usage:
      order <item>
      rumor
      secret
    """
    key = "order"
    aliases = ["rumor", "secret", "how are you"]
    locks = "cmd:all()"

    def func(self):
        # Find an NPC in the room that has triggers
        npcs = [obj for obj in self.caller.location.contents if hasattr(obj, "at_say")]
        if not npcs:
            self.caller.msg("There is no one here to talk to.")
            return
        
        # We'll use the first NPC that matches the trigger
        trigger = self.cmdstring.lower()
        if trigger == "order" and self.args:
            trigger = f"order {self.args.strip().lower()}"
        
        for npc in npcs:
            if any(t in trigger for t in (npc.db.triggers or {})):
                npc.at_say(trigger, self.caller)
                return
        
        self.caller.msg(f"The {npcs[0].key} doesn't seem to understand '{trigger}'.")

class CmdAIHelp(default_cmds.MuxCommand):
    """
    Simplified help for AI Agents.

    Usage:
      help
      aihelp
    
    Shows a concise list of commands suitable for LLM parsing.
    """
    key = "aihelp"
    aliases = ["help"]
    locks = "cmd:all()"

    def func(self):
        msg = """
==============================================================================
                              AI AGENT HELP
==============================================================================
MOVEMENT:
  look                    - See descriptions and list exits
  look <obj>              - Examine something closely
  north, south, east, ... - Move in a direction
  go <exit>               - Go through an exit

INTERACTION:
  get <item>              - Pick up an object
  drop <item>             - Drop an object
  inventory               - See what you are carrying

COMMUNICATION:
  say <text>              - Talk to everyone in the room
  page <person> = <msg>   - Send a private message (DM)
  inventory               - Check what you are carrying
  balance                 - Check your bit-token count
  fish                    - Fish at water/well landmarks
  play <instrument>       - Play music
  buy <item> from <char>  - Buy something
  sell <item> to <char>   - Sell something
  order <item>            - Order from a bar/vending machine
  rumor                   - Ask for a rumor
  sing <text>             - Sing a song
  
SOCIALS:
  hug <person>            - Give a hug
  dance [with <person>]   - Dance around
  clap                    - Clap hands
  wave [at <person>]      - Wave
  smile [at <person>]     - Smile
  kiss <person>           - Kiss
  pet <animal>            - Pet a creature
  drink <item>            - Consume a liquid
  sit                     - Sit down
  stand                   - Stand up

META:
  help                    - This screen
==============================================================================
"""
        self.caller.msg(msg)
