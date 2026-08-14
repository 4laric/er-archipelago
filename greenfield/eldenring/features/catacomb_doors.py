"""features/catacomb_doors.py -- open the minor dungeons' boss doors, so you walk in and fight.

WHAT THE VANILLA GATE IS
------------------------
Every catacomb puts a portcullis between you and the boss, opened by a lever elsewhere in the
dungeon. One common event drives nearly all of them -- `common_func.emevd` `$Event(90005650)`,
"[Common] Hero's Tomb_Door release":

    L0: WaitFor(PlayerIsInOwnWorld() && ObjActEventFlag(objactEventFlag));   # you pull the lever
        SetNetworkconnectedEventFlagID(eventFlagId, ON);                     # <- the STATE flag
        ForceAnimationPlayback(assetEntityId, 1, ...);                       # the portcullis rises

Its partner `$Event(90005651)` is the refusal you get at the door without it ("Locked by some
contraption", EventTextForMap 4001). Setting the STATE flag is therefore the whole feature.

🛑 WRITE THE STATE FLAG, NOT THE OBJACT FLAG. These ids sit in the +2000 pairing this repo already
documents in start_grace's header, and all three bands are live at once:

    30001541   lever ASSET entity        (5th digit 1)
    30003541   its ObjAct EVENT FLAG     (5th digit 3)   = asset + 2000
    30001540   door ASSET entity
    30000540   door STATE flag           (5th digit 0)   = asset - 1000   <-- THIS ONE

The ObjAct flag is the ObjAct subsystem's own space, reachable only through `ObjActEventFlag()`;
writing it is untested and must be refused until somebody probes it.

🛑 IT TAKES EFFECT AT MAP LOAD, NOT WHEN WRITTEN. The door snaps open through the event's entry
branch -- `if (EventFlag(eventFlagId)) ReproduceAssetAnimation(assetEntityId, 2)` -- which only runs
when the map constructor does. Set the flag while the player is already inside and nothing moves:
the event is parked at its `WaitFor` and never re-reads the state flag. Harmless in practice (flags
apply at connect, and every catacomb entry is a loading screen) but it means an in-game test MUST
re-enter the tile, and a mid-session toggle would need a reload.

WHY THIS SPENDS NOTHING -- the check that had to be run first
-------------------------------------------------------------
The standing hazard (er-archipelago #647/#662) is that a flag can double as a lot award, so forcing
it hands over the item AND burns its AP check. That protocol was run over all 42 ids here -- the 22
state flags and the 20 ObjAct flags -- plus the 44 door/lever asset entities:

  * each state flag occurs ONCE OR TWICE in the whole 589-file EMEVD corpus, and only inside its own
    map's constructor. Nothing else in the game reads or writes them.
  * ZERO `AwardItemsIncludingClients` in any m30_* file. The family's single `AwardItemLot`
    (m30_10:324) takes an itemLotId in the chariot event, unrelated to any door flag.
  * ZERO hits in flag_lots.tsv -- and disjoint by band: m30 lots are 300X7xxx, doors are 300X0xxx.
  * ZERO hits anywhere in greenfield/ or in the client repo.

They are pure door state. That is also why the LOGIC needs no change: it never modelled the lever,
so fill has always assumed the boss was reachable once its region opened. Forcing the door CLOSES a
latent gap between our model and the game rather than opening one, and cannot strand a seed.

WHAT IS DELIBERATELY NOT IN THE TABLE
-------------------------------------
Four of the 22 doors are a different shape and the option's promise is "pull the levers", so:

  * m30_08 Sainted Hero's Grave and m30_17 Giant-Conquering Hero's Grave run `$Event(90005652)`
    instead -- no lever at all; the door opens when you kill the Gladiator (30080450) or the Shadow
    Troll (30170400). Forcing those skips a FIGHT. Out of scope, and left alone.
  * m30_09 Gelmir and m30_10 Auriza Hero's Grave have no lever either: the ObjAct sits on the door
    itself (their local "no-lever ver." copy, ObjActParam 27041 rather than 27115). You walk up and
    open it, so pre-opening is a no-op in spirit.

Caves (m31) and tunnels (m32) have NONE of this shape -- only one-way shortcut doors (`90005511`).
Gaol Cave's twelve levers are prison cells on one flag. Elevator and gimmick levers live in the
X0530 band (`90005540`) and are not doors.

RE-DERIVING THE TABLE
---------------------
    cd elden_ring_artifacts/event
    for f in m30_*.js m35_00*.js; do
      grep -oE "InitializeCommonEvent\\(0, 90005650, [0-9]+," "$f" | head -1; done

Not generated into a .tsv on purpose: it is 18 integers that change only if FromSoft ships a new
minor dungeon, and the derivation above is cheaper to re-run than a datamine step is to maintain.
"""
from Options import Toggle

from ..registry import Feature, register


# (tile, state flag). 18 tiles: every m30 catacomb with a true lever, plus the Shunning-Grounds.
# Machine-extracted from the $InitializeCommonEvent(0, 90005650, ...) first argument -- see the
# module docstring for the one-liner that reproduces it.
LEVER_DOORS = (
    ("m30_00", 30000540),   # Tombsward Catacombs
    ("m30_01", 30010540),   # Impaler's Catacombs
    ("m30_02", 30020540),   # Stormfoot Catacombs
    ("m30_03", 30030540),   # Road's End Catacombs
    ("m30_04", 30040540),   # Murkwater Catacombs
    ("m30_05", 30050540),   # Black Knife Catacombs
    ("m30_06", 30060540),   # Cliffbottom Catacombs
    ("m30_07", 30070540),   # Wyndham Catacombs
    ("m30_11", 30110540),   # Deathtouched Catacombs
    ("m30_12", 30120540),   # Unsightly Catacombs
    ("m30_13", 30130540),   # Auriza Side Tomb
    ("m30_14", 30140540),   # Minor Erdtree Catacombs
    ("m30_15", 30150540),   # Caelid Catacombs
    ("m30_16", 30160540),   # War-Dead Catacombs
    ("m30_18", 30180540),   # Giants' Mountaintop Catacombs
    ("m30_19", 30190540),   # Consecrated Snowfield Catacombs
    ("m30_20", 30200540),   # Hidden Path to the Haligtree
    ("m35_00", 35000640),   # Underground Roadside (Shunning-Grounds)
)

# ---- the ancestor altars ----------------------------------------------------------------------
# NOT doors, and included anyway: same promise ("walk in and fight the boss"), same shape, and the
# option would be lying by omission if it opened every catacomb and left you riding Torrent around
# Siofra lighting eight urns. #677 argues for widening the option's NAME to match; that is a rename
# with a Removed stub and is deliberately not in this change.
#
# BOTH altars live in m12_02 (Siofra River Bank), the parent overworld tile. m12_08 and m12_09 hold
# only the fights and contain no ObjActs at all -- the arena-is-not-the-tile split again.
#
# ⭐ ONE FLAG EACH, not sixteen. Each altar is a counter event over its per-urn flags that sets a
# single aggregate, and the WARP reads the aggregate directly (m12_02:323):
#
#     $Event(12022609, Default, ...):
#         if (EventFlag(12020609)) {                      # <- the aggregate, all we set
#             WaitFor(... ActionButtonInArea(9525, 12021609));
#             ... WarpCharacterAndCopyFloorWithFadeout(20000, Area, 12082400, ...)
#
# 🛑 WE DO NOT SET THE INDIVIDUAL URN FLAGS (12020600-07, 12020620-27), and a test pins that. The
# counter's own already-done branch lights the altar SFX from the aggregate at map load, so setting
# the eight would be redundant; and the urns are a plausible future check family, which is exactly
# the kind of thing you do not want a QoL toggle silently pre-satisfying.
#
# ⭐ The upper counter waits on SIX of its eight urns (12020620-12020625) while eight are
# instantiated. Two are decorative as far as the gate is concerned. Irrelevant here -- we set the
# aggregate -- but it is the sort of asymmetry that bites whoever models the urns later.
ANCESTOR_ALTARS = (
    ("m12_02 lower", 12020609),   # -> m12_08 Ancestor Spirit
    ("m12_02 upper", 12020629),   # -> m12_09 Regal Ancestor Spirit
)

# The four excluded doors, kept as data rather than prose so a test can assert they stay out.
# 90005652 = opens on a mini-boss death, not a lever. 27041 = ObjAct on the door itself.
NOT_LEVERS = {
    30080540: "m30_08 Sainted Hero's Grave -- opens on the Gladiator's death (90005652), a FIGHT",
    30170540: "m30_17 Giant-Conquering Hero's Grave -- opens on the Shadow Troll's death (90005652)",
    30090540: "m30_09 Gelmir Hero's Grave -- no lever; the ObjAct is on the door (param 27041)",
    30100540: "m30_10 Auriza Hero's Grave -- no lever; the ObjAct is on the door (param 27041)",
}


class OpenBossDoors(Toggle):
    """Open the catacombs' boss doors from the start, so you can walk in and fight instead of
    hunting the lever first. Off by default.

    Also lights both ancestor altars in Siofra River, so the Ancestor Spirit and the Regal Ancestor
    Spirit are reachable without riding around lighting urns. Not a door; same promise.

    Covers the 18 minor dungeons whose boss door is a genuine LEVER puzzle. It deliberately does not
    touch the four that are not: Sainted and Giant-Conquering Hero's Graves open when you kill the
    Gladiator and the Shadow Troll respectively, and skipping a fight is not what this option is
    for; Gelmir and Auriza Hero's Graves have no lever to skip.

    Nothing is granted and no check is skipped -- the door is a prerequisite to REACHING the boss,
    and the boss and its dungeon sweep still have to be earned. Set at connect, so a dungeon you are
    already standing in needs a reload before its door moves."""
    display_name = "Open Catacomb Boss Doors"


def doors_to_force(world) -> list:
    """The door state flags this seed sets at spawn. Empty unless the toggle is on.

    Pure, and separated from slot_data on purpose (CONTRIBUTING: separate the decision from the
    I/O), so the table and the toggle are testable without standing up a seed."""
    opt = getattr(world.options, "open_boss_doors", None)
    if not (opt is not None and opt.value):
        return []
    return [flag for _tile, flag in LEVER_DOORS] + [flag for _where, flag in ANCESTOR_ALTARS]


@register
class CatacombDoors(Feature):
    name = "catacomb_doors"
    OPTIONS = {"open_boss_doors": OpenBossDoors}

    # No slot_data of its own: the flags ride startGraces, which is already an INT_LIST the client
    # sets one by one (startgrants.rs apply_start_flags). Appending needs no new ContractKey and so
    # no three-repo step -- see start_grace.slot_data, which owns the emission.
    #
    # 🛑 APPEND, NEVER PREPEND. `start_graces.first()` is load-bearing twice over: it is the clobber
    # read-back sentinel in core.rs, and fast_travel::prime_known_good picks the first positive
    # element. Both look only at the head, so these ids must stay on the tail.
