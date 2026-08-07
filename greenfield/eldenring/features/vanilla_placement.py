"""vanilla_placement -- put every item back where the base game keeps it.

THE AXIS THIS ADDS
------------------
There are two independent axes in this world and, until now, an option on only one of them:

  * TOPOLOGY -- which region gates which. Owned by features/natural_progression.py.
  * PLACEMENT -- which item sits on which location. Owned by NOTHING; `item_shuffle` is frozen ON
    (defaults.py), so every seed shuffles.

The motivating case (Discord, "Kro", 2026-08-07) is a group who want a co-op deathlink run with the
game otherwise untouched: "we dont really want any randomization ... KEY items, like the dectus,
golden seeds, etc being in normal locations". `natural_progression` SOUNDS like that request and is
its opposite on the axis they named: it preserves vanilla's dependency SHAPE while fully SHUFFLING
the gate items, so the Dectus halves still scatter across the multiworld. This feature is the
missing axis.

WHY THE TWO MODES CANNOT BE COMBINED (the ruling this module enforces)
----------------------------------------------------------------------
natural_progression.set_rules carries a cycle-breaker that forbids each key from the checks of every
region it gates, precisely so fill cannot strand a key behind its own gate. Vanilla placement takes
that freedom away, and GATE_CLAUSES then self-gates: "Stormveil": [("Rusty Key",)] and the Rusty
Key's vanilla home is the Stormveil Rampart Tower -- a region gated on an item inside itself. It is
not one region either: the Remembrance of the Grafted (Liurnia's key) drops from Godrick, INSIDE the
self-gated Stormveil, so the reachability fixpoint collapses to 4 of 32 regions. The combination is
an OptionError, never a FillError.

The ruling that follows is the whole design: VANILLA PLACEMENT MEANS NO AP REGION GATING AT ALL.
num_regions is ignored, GATE_CLAUSES is unused, every entrance rule is True. That is not a loss --
vanilla Elden Ring already gates itself and ships beatable. The AP lock layer exists to REPLACE
vanilla gating; when placement is vanilla, replacing it is exactly the wrong move.

WHY THERE IS NO `keys` SCOPE (Fable ruling, 2026-08-07)
-------------------------------------------------------
The obvious middle setting -- pin the key items, shuffle the rest -- was specced and REJECTED, and
the reason is worth keeping because it will be proposed again:

  1. INCOMPLETENESS IS UNWINNABLE-SHAPED. With the region graph flat, AP believes all 4916 locations
     are sphere-0 and is structurally blind to vanilla's own doors. Any in-game-gating item NOT on
     the hand-written pin list can then self-strand when shuffled (the Discarded Palace Key landing
     inside the chest it opens). Vanilla's soft gates -- NPC questlines, Varre's invasions, Ranni's
     chain -- mean that list can never be argued complete.
  2. THE CONTAINMENT IS LEAKY, AND PLUGGING IT MAKES THE SCOPE POINTLESS. Confining the damage needs
     local_items forced on, but local_items.names_to_localize covers ITEM_CATALOG + progressives and
     NOT the Rune sentinel, so the Rune-fallback slots break the pigeonhole and can still admit a
     foreign item. Plug that and the scope is hermetic -- zero multiworld interaction -- at which
     point it delivers nothing `all` does not, while carrying an unauditable hand list.

`all` is strictly sounder, so `all` ships alone (one sound mode per system). The option is a Choice
rather than a Toggle so `keys` can be ADDED later if a real vanilla logic graph is ever built --
adding a Choice value is compat-safe, and a dead value shipped today is not.

WHY `all` IS SOUND, FOR A REASON WORTH STATING
----------------------------------------------
Every location holds its own vanilla item, so no foreign item can land here and no item of ours can
leave: the world is HERMETIC by construction. AP's logic model is now a lie (it believes everything
is sphere-0) and the lie touches nothing, because there is no foreign item whose reachability it
could mis-promise. Hermeticity is also what makes the receive path safe here: F4 -- one bad foreign
item drops the whole received batch -- cannot fire when no foreign item is ever in the stream.

ZERO CLIENT WORK
----------------
The mode emits EXISTING contract keys with empty values (areaLockFlags [], regionOpenFlags {},
regionGraces {}, no naturalKeyTriggers), so CONTRACT_HASH does not move, no client half is needed and
no version is bumped. contract.CONTRACT_HASH is a sha256 over the CONTRACT tuples only -- key names
and shapes -- so an empty value for a declared key is invisible to it.

  🛑 area_locks.slot_data has NO mode branch: it emits kick-watch ranges for ALL regions
  unconditionally (its 2026-07-08 UN-FOLD dead-drop fix). Untouched, this mode would ship
  BORN-SOFTLOCKED -- every region sealed and no Lock item in existence to bloom it. That branch is
  the one genuinely load-bearing edit outside this file.

The DLC world-map reveal normally rides lockRevealFlags (granted on Lock receipt); with no Locks it
never fires, and the connect-time path in the client's startgrants.rs already grants the DLC pieces
gated on enable_dlc, so the reveal still happens. See area_locks.py's own note on that split.

WHAT THIS MODE IS NOT
---------------------
Vanilla PLACEMENT, not vanilla BALANCE. The frozen QoL behaviours (auto_upgrade,
flatten_regular_upgrades, the start lantern/flasks/steed) are unaffected and still apply, and the
vanilla-inherent missables are inherited as-is -- the Erdtree burn still strands Leyndell's checks
exactly as the base game does. Both are documented in presets/vanilla-deathlink.yaml rather than
guarded here: guarding vanilla against itself is out of scope for a mode whose entire premise is
"change nothing".
"""
import logging

from Options import Choice, OptionError

from ..registry import Feature, register

try:
    from ..item_ids import LOCATION_ITEM
except Exception:  # pragma: no cover -- pre-regen data
    LOCATION_ITEM = {}


class VanillaPlacement(Choice):
    """WHERE THE ITEMS ARE. 'off' (default) is the randomizer: every check's vanilla item is
    shuffled across the multiworld.

    'all' puts every item back exactly where the base game keeps it -- the Dectus halves in Fort
    Haight and Fort Faroth, the Academy Glintstone Key on its corpse, every Golden Seed on its
    sapling. Checks still fire, the tracker still works and Death Link still works, so this is the
    setting for a group who want to play the base game together and share deaths rather than
    randomize anything. Nothing is sent to or received from other worlds: the seed is self-contained
    by design.

    Progression is gated the way the base game gates it, so the region locks are not used at all and
    Number of Regions is ignored -- the whole map is in play from the start, and the Leyndell wall,
    the Rold Medallion and every other door work as they always did.

    This is vanilla PLACEMENT, not vanilla BALANCE: the quality-of-life behaviours this world always
    applies (automatic weapon upgrades, the flattened upgrade curve, the starting lantern and flasks)
    still apply. It also inherits the base game's own missables -- burning the Erdtree still strands
    Leyndell's checks."""
    display_name = "Vanilla Placement"
    option_off = 0
    option_all = 1
    default = 0


def is_on(world) -> bool:
    opt = getattr(getattr(world, "options", None), "vanilla_placement", None)
    return bool(opt is not None and int(opt.value) != 0)


def pins(world):
    """[(ap_id, vanilla item name or None), ...] in the order core.create_items walks the kept
    locations. None = no inventory good to pin (gestures and the unnamed `check -` rows: 67 of 4916
    on main), which takes the same Rune fallback item_shuffle already gives it.

    Pure over LOCATION_ITEM + the walk order, so it unit-tests without a live fill."""
    from ..data import LOCATIONS
    from ..core import HUB
    out = []
    for rn in [HUB] + list(world._kept()):
        for row in LOCATIONS.get(rn, []):
            ap_id = row[1]
            out.append((ap_id, LOCATION_ITEM.get(ap_id)))
    return out


@register
class VanillaPlacementFeature(Feature):
    name = "vanilla_placement"
    OPTIONS = {"vanilla_placement": VanillaPlacement}

    def generate_early(self, world) -> None:
        if not is_on(world):
            return
        # THE COMBINATION IS REJECTED, LOUDLY AND BY NAME. CONTRIBUTING's headline gate wants an
        # actionable OptionError rather than the FillError (or, worse, the quietly-unwinnable seed)
        # that the self-gating collapse would otherwise produce.
        _np = getattr(world.options, "natural_progression", None)
        if _np is not None and int(_np.value):
            raise OptionError(
                "[eldenring] vanilla_placement and natural_progression are opposite answers to the "
                "same question and cannot both be on. natural_progression keeps vanilla's region "
                "SHAPE but SHUFFLES the keys that open it; vanilla_placement puts the keys back "
                "where the base game has them. Together, a region is gated on an item inside "
                "itself -- Stormveil needs the Rusty Key, which lives in the Stormveil Rampart "
                "Tower -- and the collapse is transitive (the Remembrance of the Grafted opens "
                "Liurnia and drops from Godrick, inside the sealed Stormveil), leaving 4 of 32 "
                "regions reachable. Turn one of them off: vanilla_placement for a vanilla run, "
                "natural_progression for vanilla's shape with shuffled keys.")
        # num_regions is IGNORED rather than rejected, and that is deliberate: NumRegions defaults to
        # 6, AP cannot tell an explicit 6 from the default, so rejecting a non-zero value would
        # reject the plain default yaml -- the dumbest possible violation of "every combination
        # generates cleanly". natural_progression is the shipped precedent for a documented ignore.
        # It is LOGGED, because a silent ignore is a silent no-op.
        _nr = getattr(world.options, "num_regions", None)
        if _nr is not None and int(_nr.value) != 0:
            logging.getLogger("Greenfield").info(
                "[eldenring:%s] vanilla_placement: num_regions=%d ignored -- vanilla placement "
                "plays the whole map and lets the base game's own doors gate it",
                world.player, int(_nr.value))
        logging.getLogger("Greenfield").info(
            "[eldenring:%s] vanilla_placement: ON -- every check pays its own vanilla item, no "
            "region locks minted, no items exchanged with other worlds", world.player)


def apply(world) -> None:
    """Lock every walked location to the item core.create_items paired with it.

    Called from core.pre_fill INSTEAD of the normal fill path. The pairing is index-for-index with
    the pool core just built (`world.gf_vanilla_pins`), not a fresh LOCATION_ITEM lookup, so the
    DLC-exclusion / flask-substitution / hold-cap decisions that shaped the pool are honoured
    exactly once and cannot disagree with it.

    Count-exactness is the invariant: every pinned item is REMOVED from the itempool as it is
    placed, and there is one pin per unfilled location, so the pool empties to zero and AP's own
    items-vs-locations check passes untouched. Zero unfilled locations is also what makes the world
    hermetic -- fill has nowhere to put a foreign item.
    """
    pins_ = getattr(world, "gf_vanilla_pins", None)
    if not pins_:
        raise AssertionError(
            "[eldenring] vanilla_placement: core.create_items published no pairing "
            "(world.gf_vanilla_pins). pre_fill cannot pin without it.")
    mw = world.multiworld
    by_name = {}
    for it in mw.itempool:
        if it.player == world.player:
            by_name.setdefault(it.name, []).append(it)
    loc_by_ap = {loc.address: loc for loc in mw.get_locations(world.player)
                 if loc.address is not None}
    taken = set()
    for ap_id, name in pins_:
        loc = loc_by_ap.get(ap_id)
        if loc is None:
            raise AssertionError(
                "[eldenring] vanilla_placement: no location for ap id %r -- create_items walked a "
                "location create_regions did not build." % (ap_id,))
        bucket = by_name.get(name)
        if not bucket:
            raise AssertionError(
                "[eldenring] vanilla_placement: the pool ran out of %r while pinning %s. The pool "
                "and the pairing disagree." % (name, loc.name))
        item = bucket.pop()
        taken.add(id(item))
        loc.place_locked_item(item)
    # ONE rebuild rather than 4916 list removals: `itempool` is the whole multiworld's, so this is
    # the hot list in every other player's fill too.
    mw.itempool = [it for it in mw.itempool if id(it) not in taken]
    logging.getLogger("Greenfield").info(
        "[eldenring:%s] vanilla_placement: pinned %d locations to their base-game items; %d pool "
        "item(s) left for this world (expected 0)",
        world.player, len(pins_),
        sum(1 for it in mw.itempool if it.player == world.player))
