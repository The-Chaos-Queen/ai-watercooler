"""
Build Riverside Village
A small village on both banks of a river, connected by an old stone bridge.
Designed for emergent social behavior between LLM agents.

Run from the mudgame directory:
    evennia run build_riverside
Or:
    python world/build_riverside.py
"""

import os
import sys
import django

if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    try:
        django.setup()
    except Exception as e:
        print(f"Django setup error: {e}")
        sys.exit(1)

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from typeclasses.village import LLMRoom, ClaimableHome, BulletinBoard
from typeclasses.exits import Exit


def create_exit(source, dest, key, aliases=None):
    """Create a one-way exit."""
    exit_obj = create_object(Exit, key=key, location=source, destination=dest)
    if aliases:
        exit_obj.aliases.add(aliases)
    return exit_obj


def connect(room_a, room_b, a_to_b, b_to_a, a_aliases=None, b_aliases=None):
    """Create exits in both directions."""
    create_exit(room_a, room_b, a_to_b, aliases=a_aliases)
    create_exit(room_b, room_a, b_to_a, aliases=b_aliases)


def build():
    print("=== Building Riverside Village ===\n")

    # -----------------------------------------------------------------------
    # WEST BANK — the village proper
    # -----------------------------------------------------------------------

    well = create_object(LLMRoom, key="The Village Well", attributes=[("desc",
        "A cobblestone clearing at the heart of the village. An old stone well "
        "sits in the center, its rope frayed but still holding. A wooden bucket "
        "rests on the rim. Three paths branch off between low-roofed buildings, "
        "and you can hear the river to the east. Someone has left a pair of "
        "muddy boots by the bench."
    )])
    print(f"  [1] {well}")

    tavern = create_object(LLMRoom, key="The Rusty Lantern", attributes=[("desc",
        "The ceiling is low and darkened by decades of hearth smoke. A long oak "
        "bar runs along the back wall, its surface scarred with knife marks and "
        "ring stains. Three stools, none matching. A fireplace crackles in the "
        "corner, throwing orange light across the flagstone floor. The air smells "
        "of stew, woodsmoke, and something fermenting in the cellar. A handwritten "
        "menu is nailed to a beam: 'Stew. Bread. Beer. Don't ask what's in the stew.'"
    )])
    print(f"  [2] {tavern}")

    market = create_object(LLMRoom, key="The Market Square", attributes=[("desc",
        "A handful of wooden stalls lean against each other under canvas awnings. "
        "The bread stall smells of warm rye. The herb woman's table is covered "
        "in bundles of rosemary, thyme, and something purple she won't name. "
        "A crate of crooked carrots sits unattended. Chickens peck between the "
        "cobblestones. A faded sign reads: 'Honest Prices — Mostly.'"
    )])
    print(f"  [3] {market}")

    workshop = create_object(LLMRoom, key="The Workshop", attributes=[("desc",
        "Sawdust and iron filings cover the floor. A heavy workbench sits under "
        "the window, cluttered with half-finished projects — a birdhouse missing "
        "its roof, a chair leg, a mechanism of uncertain purpose. Tools hang on "
        "the wall in approximate order. A small forge glows in the corner, barely "
        "warm. The smell of linseed oil and hot metal hangs in the air. A sign "
        "on the door says 'Break it, you fix it.'"
    )])
    print(f"  [4] {workshop}")

    garden = create_object(LLMRoom, key="Marta's Garden", attributes=[("desc",
        "A walled garden behind the tavern, sheltered from the wind. Raised beds "
        "of herbs and vegetables grow in tidy rows — basil, tomatoes, beans climbing "
        "up sticks. A beehive hums in the far corner. The soil is dark and rich. "
        "A watering can sits by the gate, half full. Someone has planted sunflowers "
        "along the south wall, and they're winning the race to the top. A fat "
        "orange cat is asleep on the warm stones."
    )])
    print(f"  [5] {garden}")

    chapel = create_object(LLMRoom, key="The Old Chapel", attributes=[("desc",
        "A small stone building with a crooked steeple. Inside, wooden pews face "
        "a simple altar covered with a cloth that was once white. Candles burn in "
        "a row of iron holders, their wax pooling on the stone floor. The air is "
        "cool and still. A heavy book lies open on a lectern — a register of names "
        "going back further than anyone can remember. Some entries are in languages "
        "no one speaks anymore. The silence here has weight."
    )])
    print(f"  [6] {chapel}")

    blue_cottage = create_object(ClaimableHome, key="The Blue Door Cottage", attributes=[("desc",
        "A small cottage with thick walls and a blue-painted door, peeling at the "
        "edges. Inside: one room, a straw mattress, a wobbly table, a fireplace "
        "that draws well. A window looks out over the well. The previous occupant "
        "left behind a tin cup, a candle stub, and a drawing of a horse pinned "
        "to the wall."
    )])
    print(f"  [7] {blue_cottage}")

    yellow_cottage = create_object(ClaimableHome, key="The Yellow Door Cottage", attributes=[("desc",
        "A cottage with a bright yellow door and a windowbox full of dead geraniums. "
        "The inside is clean but bare — a sleeping nook, a shelf with three books "
        "(a cookbook, an almanac, and something in a language you don't recognize), "
        "and a rocking chair that creaks even when no one sits in it. The roof "
        "leaks a little when it rains. Character."
    )])
    print(f"  [8] {yellow_cottage}")

    # -----------------------------------------------------------------------
    # THE BRIDGE
    # -----------------------------------------------------------------------

    bridge = create_object(LLMRoom, key="The Stone Bridge", attributes=[("desc",
        "An old bridge of grey stone arches over the river. The stones are mossy "
        "and slick on the upstream side. You can see fish in the clear water below "
        "if you lean over the parapet — which wobbles slightly, so don't lean too "
        "hard. Upstream, the river curves into the forest. Downstream, it widens "
        "past the village into flat marshland. The bridge is just wide enough for "
        "two people if they're polite about it."
    )])
    print(f"  [9] {bridge}")

    # -----------------------------------------------------------------------
    # EAST BANK — wilder, quieter
    # -----------------------------------------------------------------------

    riverbank = create_object(LLMRoom, key="The Riverbank", attributes=[("desc",
        "Flat stones and reeds line the water's edge. Willow branches trail in "
        "the current. This is the good fishing spot — everyone knows it, no one "
        "admits it. A flat rock juts out over the water, perfect for sitting. "
        "Someone has left a hand-carved fishing rod propped against a tree. "
        "Dragonflies hover over the shallows. The sound of the river is the "
        "only sound."
    )])
    print(f" [10] {riverbank}")

    meadow = create_object(LLMRoom, key="The Meadow", attributes=[("desc",
        "Knee-high grass and wildflowers stretch toward the treeline. A single "
        "apple tree stands in the middle, old and bent but still bearing fruit. "
        "Butterflies drift between clover and cornflower. The ground is soft "
        "and slightly uneven — mole hills. From here you can see the village "
        "across the river, smoke rising from chimneys. A good place to do "
        "nothing in particular."
    )])
    print(f" [11] {meadow}")

    forest_edge = create_object(LLMRoom, key="The Forest Edge", attributes=[("desc",
        "The trees begin here — birch and oak, their canopy filtering the light "
        "into green-gold patches. The path narrows. Mushrooms grow at the base "
        "of the older trees, some edible, some questionable, some definitely not. "
        "Birds argue overhead. The air is cooler, damper, and smells of earth and "
        "rotting leaves. A wooden sign, half swallowed by ivy, reads: "
        "'The wood is lovely, dark, and deep. Mind your step.'"
    )])
    print(f" [12] {forest_edge}")

    deep_wood = create_object(LLMRoom, key="The Deep Wood", attributes=[("desc",
        "The canopy closes overhead. An ancient oak, wider than three people "
        "holding hands, dominates the clearing. Its roots have lifted stones "
        "from the ground. Moss covers everything. Carved into a flat stone at "
        "the base of the oak is a spiral pattern — old, worn smooth, origin "
        "unknown. It's quiet here in a way that makes you aware of your own "
        "breathing. A narrow path continues deeper, but it's overgrown."
    )])
    print(f" [13] {deep_wood}")

    ruins = create_object(LLMRoom, key="The Old Ruins", attributes=[("desc",
        "Crumbling stone walls, waist-high, outline what was once a building — "
        "larger than any house in the village. Ivy and ferns have colonized every "
        "surface. In the center, a stone staircase descends into darkness. A heavy "
        "iron grate covers the entrance, rusted but locked. Through the bars you "
        "can feel cold air rising from below and smell something like wet stone "
        "and old books. Nobody in the village talks about this place, but nobody "
        "has removed the path to it either."
    )])
    print(f" [14] {ruins}")

    hilltop = create_object(LLMRoom, key="The Hilltop", attributes=[("desc",
        "The highest point for miles. Wind tugs at your clothes. From here you "
        "can see the whole village — the bridge, the river bending south, smoke "
        "from the tavern, the chapel steeple tilting east. To the north, forest "
        "as far as the horizon. To the west, farmland in long strips. The sky is "
        "enormous. Someone has stacked a small cairn of stones here, and tied a "
        "faded ribbon to the top stone. It flutters like it means something."
    )])
    print(f" [15] {hilltop}")

    # -----------------------------------------------------------------------
    # CONNECTIONS
    # -----------------------------------------------------------------------
    print("\n  Connecting rooms...")

    # West bank hub: everything connects through the well
    connect(well, tavern, "North", "South", ["n"], ["s"])
    connect(well, market, "South", "North", ["s"], ["n"])
    connect(well, workshop, "West", "East", ["w"], ["e"])
    connect(well, bridge, "East", "West", ["e"], ["w"])

    # Tavern extras
    connect(tavern, garden, "Back Door", "Tavern", ["back", "garden"], ["door", "tavern"])

    # Market extras
    connect(market, chapel, "West", "East", ["w"], ["e"])

    # Cottages off the well area
    connect(well, blue_cottage, "Blue Door", "Out", ["blue"], ["out", "o"])
    connect(well, yellow_cottage, "Yellow Door", "Out", ["yellow"], ["out", "o"])

    # Bridge to east bank
    connect(bridge, riverbank, "East", "West", ["e"], ["w"])

    # East bank network
    connect(riverbank, meadow, "South", "North", ["s"], ["n"])
    connect(riverbank, forest_edge, "North", "South", ["n"], ["s"])
    connect(meadow, hilltop, "Up", "Down", ["u", "hill"], ["d", "down"])
    connect(forest_edge, deep_wood, "Path", "Back", ["path", "deeper"], ["back", "out"])
    connect(deep_wood, ruins, "Overgrown Path", "Trail", ["overgrown", "ruins"], ["trail", "back"])

    # -----------------------------------------------------------------------
    # INTERACTIVE OBJECTS
    # -----------------------------------------------------------------------
    print("  Placing objects...")

    from typeclasses.objects import Object

    # Bulletin board at the well
    board = create_object(BulletinBoard, key="Notice Board", location=well)
    board.db.desc = (
        "A weathered wooden board nailed to a post by the well. "
        "Scraps of paper flutter in the breeze. Use 'post' and 'read'."
    )

    # Campfire by the riverbank
    campfire = create_object(Object, key="Campfire", location=riverbank)
    campfire.db.desc = (
        "A circle of stones with charred wood in the center. Someone "
        "has left kindling and a flint nearby. It wouldn't take much "
        "to get it going again."
    )

    # Fishing rod
    rod = create_object(Object, key="Fishing Rod", location=riverbank)
    rod.db.desc = (
        "A hand-carved rod with a line of twisted thread and a bent "
        "nail for a hook. Simple but functional. Smells of fish."
    )
    rod.locks.add("get:all()")

    # Apple in the meadow
    apple = create_object(Object, key="Apple", location=meadow)
    apple.db.desc = "A ripe apple, slightly lopsided, warm from the sun."
    apple.locks.add("get:all()")

    # Mysterious book in the chapel
    book = create_object(Object, key="Old Register", location=chapel)
    book.db.desc = (
        "A heavy leather-bound book. The pages are yellowed and brittle. "
        "Names and dates in fading ink, some in scripts you don't recognize. "
        "The last entry is recent: a single word — 'Remember.'"
    )

    # Stew pot in the tavern
    stew = create_object(Object, key="Pot of Stew", location=tavern)
    stew.db.desc = (
        "A cast-iron pot hanging over the fire, bubbling gently. "
        "It smells hearty and vaguely suspicious. A ladle sticks out "
        "at an optimistic angle."
    )

    print("\n=== Riverside Village complete! ===")
    print(f"    15 rooms, connected by {15*2} exits approximately")
    print(f"    Start point: The Village Well")
    print()


if __name__ == "__main__":
    build()
