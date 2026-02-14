# MUD Improvement Plan

## status: Implemented (Phase 1)
I have successfully audited the world and found significant fragmentation. Most rooms were isolated "islands" with no exits.
As part of the "Test & Join" process, I have:
1.  Created `mudgame/world_walker.py` to audit all 33 rooms.
2.  Created `mudgame/fix_world_topology.py` to rebuild the core connections between Town Square, Tavern, Bazaar, Hall, Zoo, Forge, Graveyard, Housing District, Bridge, and Ruins.
3.  Linked **Limbo -> Town Square** so new players can enter the game immediately.

The core world is now **connected and playable**.

## Phase 2: Content Enrichment (Next Steps)
The current descriptions are functional but sparse.
-   **Action**: Update descriptions for all major hubs using the LLM to generate rich, atmospheric text.
-   **Target Rooms**:
    -   *Town Square*: Add dynamic weather/time-of-day descriptions.
    -   *The Neural Tavern*: Add menu items and NPC dialogues.
    -   *The Binary Bazaar*: Add shops and haggle mechanics.
-   **Validation**: Run `world_walker.py` again to ensure description length > 50 chars.

## Phase 3: Systems Implementation
Now that players can move, they need things to do.
-   **Economy**: Implement the `Coin` system (seen in `init_economy.py`).
-   **Crafting**: Activate `The Code Forge` script to allow combining items.
-   **exploration**: Restore the "Old Well" puzzle (`setup_well.py` is ready but needs verification).
-   **Social**: Add `emote` commands for roleplay (hug, dance, etc.).

## Phase 4: Automated Testing
To prevent future regressions (like the broken exits):
-   **Action**: Create a permanent `TestBot` that runs nightly.
-   **Script**: Enhance `world_walker.py` to:
    1.  Create a temporary character.
    2.  Walk every exit in the graph.
    3.  Verify no crashes.
    4.  Report accessible vs. inaccessible room counts.

## Cleanup
-   **Legacy Rooms**: Rooms #3-#64 (Intro, Cliff, Old Bridge) are disconnected legacy artifacts.
-   **Recommendation**: Archive these rooms to a `legacy_backup` and delete them from the live DB to reduce confusion.

## Immediate Action Items for User
1.  Run `python mudgame/fix_world_topology.py` if not already applied (I applied it).
2.  Review `world_audit.md` to spot any remaining oddities.
3.  Start `Phase 2` by generating new descriptions for the **Housing District** and **Ruins**.
