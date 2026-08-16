"""Every seed holds all SEVEN Great Runes, whoever the draw kept.

WHY THIS FILE EXISTS (#764, Alaric's ruling 2026-08-16: *inject to seven*).

A Great Rune sits on exactly one region's boss, one region each:

    Stormveil Godrick's f171 | Raya Lucaria the Unborn f197 | Caelid Radahn's f172
    Leyndell Morgott's f173  | Mt. Gelmir Rykard's f174     | Mohgwyn Mohg's f175
    Haligtree Malenia's f176

So before this, the number of Great Runes in a seed was *whatever the region draw happened to keep* --
seven on a full Shattering, one on a three-region seed -- and every consumer downstream silently
clamped to that number. bobler's seed `75791261719639771134` is the case that settled it: three
regions kept, exactly ONE rune in the whole multiworld, `goal_great_runes: 2` resolved to
`great_rune_items = ["Godrick's Great Rune"]`, and nothing anywhere told him his 2 had become a 1.

🛑 PARTIAL INJECTION ALREADY EXISTED AND WAS IN THE WRONG PLACE. `features/leyndell_gate` topped the
pool up to the capital wall's floor (`shortfall = max(0, want - len(avail))`), because #589 -- a
seed with one countable rune sealed Leyndell, the Sewer and Ashen Capital behind a door nothing
could open, stranding forty-two other players' items. That fix was right and is now this file's
job instead, for one reason: it was conditioned on **the capital being in the draw**. bobler's seed
had no Leyndell, so nothing topped anything up. A supply floor that only exists when one particular
consumer is present is not a floor.

The wall now READS a supply it does not CREATE. That separation is the whole point of moving it.

WHAT THIS BUYS, and it is more than tidiness:

* `core._resolve_required_runes` clamps `want` to `len(avail)`. With seven always available, the
  clamp cannot bite: a player who asks for six gets six (#504).
* `goal_great_runes`'s range is `1..len(GREAT_RUNES)` = 1-7. It now means what it says on every
  seed, instead of offering 7 on a seed that can supply 1.
* A rune arriving for a demigod who is not in your run stops being an anomaly needing a per-seed
  explanation (#730) and becomes a documented rule of the randomizer.

⚠️ DETERMINISM: the old injection selected with `sorted`, never `world.random`, specifically so a
seed that needed no repair rolled byte-identically. Injecting unconditionally moves the item pool on
EVERY seed, so that property is spent -- deliberately, and said out loud here rather than discovered
in a fill regression.

🛑 NOT A PRESENCE-FLOOR ENTRY. `features/presence_floor` guarantees an item TYPE appears and marks
its copies `useful`. Great Runes need more than presence: a required one must be `progression` so
fill guarantees it reachable, and that upgrade lives in `core._class_for`, which reads
`_required_runes()` / `gf_leyndell_runes`. Filing them under the floor would have split one item's
classification across two owners.
"""
from typing import List

from ..registry import Feature, register
from ..item_categories import GREAT_RUNES

try:  # AP is absent in the standalone host harness
    from BaseClasses import ItemClassification
except ImportError:  # pragma: no cover - exercised only outside an AP checkout
    ItemClassification = None


def naturally_present(world) -> List[str]:
    """Great Rune names that sit on a KEPT region's own boss this seed -- i.e. the ones the draw
    supplies without help. This is what `core._available_runes` used to be, kept here under a name
    that says which question it answers."""
    return list(world._runes_on_kept_regions())


def injected(world) -> List[str]:
    """The runes this feature has to mint: every Great Rune the draw did NOT supply.

    Sorted for a stable, reviewable order. NOT `world.random`: the SELECTION is not a choice -- it
    is "all of them minus the ones already there" -- so there is nothing to randomise and no reason
    to touch the rng stream. (Which rune the GOAL then requires is a separate question, and #640 is
    where that one stops being alphabetical.)"""
    if not GREAT_RUNES:
        return []
    return sorted(set(GREAT_RUNES) - set(naturally_present(world)))


@register
class GreatRuneSupply(Feature):
    name = "great_runes"
    # No NEW item names: every Great Rune is already an ITEM_CATALOG good carrying its FullID, so
    # the client grants it unchanged. Declaring them in ITEMS would mint a fresh feature id and DROP
    # that mapping -- the same trap presence_floor documents.
    ITEMS = {}

    def generate_early(self, world) -> None:
        # Recorded on the world so leyndell_gate, the spoiler and the tests can all read the same
        # answer rather than each recomputing it. Empty on a full-Shattering seed, which is the
        # signal that the draw already supplied everything.
        world.gf_great_runes_injected = injected(world) if world._shuffle_on() else []

    def create_items(self, world) -> List:
        """Mint one copy of every rune the draw did not supply.

        Rides core.create_items' existing seam (`pool += f.create_items(self)` BEFORE the filler
        tail is sized), so each copy displaces exactly one filler slot and items == locations by
        construction. Never touch `multiworld.itempool` directly.

        Classification is `useful` HERE and may be raised to `progression` by `core._class_for` --
        which it will be for any rune the goal requires or the capital wall arms on. Leaving it at
        the GOODS default of `filler` is the bug #640 names on the other axis: a Great Rune is never
        junk, whether or not this particular seed's goal happens to want it.
        """
        out: List = []
        for name in getattr(world, "gf_great_runes_injected", []):
            it = world.create_item(name)
            if ItemClassification is not None and it.classification == ItemClassification.filler:
                it.classification = ItemClassification.useful
            out.append(it)
        return out
