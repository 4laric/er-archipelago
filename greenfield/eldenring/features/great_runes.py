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
import logging
from typing import Dict, List

from ..registry import Feature, register
from ..item_categories import GREAT_RUNES
from ..tables.data import HUB, LOCATIONS

try:  # AP is absent in the standalone host harness
    from BaseClasses import ItemClassification
except ImportError:  # pragma: no cover - exercised only outside an AP checkout
    ItemClassification = None


# ---- DETECTION: the six boss runes poll the BOSS DEFEAT flag, not the POSSESSION flag ----------
#
# 🛑 FLAGS 170-179 ARE VANILLA'S GREAT RUNE POSSESSION BAND. THEY ARE NOT OURS TO DETECT ON.
#
# Evidence, from the decompiled corpus in this repo's own bundle:
#
#   * `elden_ring_artifacts/event/common.emevd.dcx.js:3124` -- $Event(6905) derives the possession
#     band from the demigod REMEMBRANCE reward flags, one contiguous slot per rune:
#         510010->171, 510300->172, 510040->173, 510220->174, 510120->175, 510200->176, 197->177.
#   * `elden_ring_artifacts/event/common.emevd.dcx.js:1110` -- $Event(730)
#     大ルーン所持数チェック ("check number of large runes in possession") is
#     `CountEventFlags(EventFlag, 170, 179) >= countThreshold`. THAT is what a rune counter reads:
#     the whole 170-179 band, not any single flag.
#
#   (features/leyndell_gate.py's "ALL SEVEN COUNT AT THE GATE" block walks the same two events for
#   the gate's threshold; this is the same evidence pointed at the detection question instead.)
#
# WHY THIS MOVED (client lost-check scenario, 2026-09-13). clients #685 makes the client SET
# 171-177 when it DELIVERS a Great Rune, so third-party rune counters -- thefifthmatt's gates, and
# vanilla's own $Event(730)/$Event(1045522500) capital wall -- agree with the AP inventory instead
# of reading zero for a player who is holding six runes. That write is correct and wanted. But the
# possession flag was ALSO this location's detection flag, and the boss lot carries it as its
# `getItemFlagId`: setting 171 before Godrick dies marks lot 10010 collected, so the pickup never
# fires the flag the poll is waiting on and check 7770001 CAN NEVER BE SENT. The rune is delivered,
# the location is lost, and the seed is unwinnable if the goal wanted that check.
#
# The fix is to stop overloading one flag with two jobs. The BOSS DEFEAT flag is the honest
# detection signal for "you beat the demigod who holds this rune", it is what 6905 itself keys on,
# and nothing writes it but the boss dying. The possession band is then free for the client.
#
# ⭐ THE data.py ROW IS DELIBERATELY UNTOUCHED -- name, ap_id and flag all stay as they are.
# `[f171]` is the location's IDENTITY (datapackage name) and 171 is still the acquisition flag its
# lot, its vanilla ware and `check_lots` are keyed on; only the DETECTION flag the client polls
# moves. `coverage.py` already models exactly this split -- `rec.detect_flag =
# emitted_location_flags.get(ap_id, flag)` -- so a detect flag that differs from the table flag is
# a shape the world already understands, not a new one. Keeping the row fixed is also what the
# ap-ids-stable ruling asks for: no renumber, no rename, no datapackage churn, and old seeds keep
# working because they never carried this override.
#
# NOT check_lots' problem. `CHECK_LOT_SLOTS_MAP` is keyed by LOT ID, and all six rune lots (10010,
# 10041, 10121, 10201, 10221, 10301) are already in it -- the vanilla rune goods (8148-8153) are
# repointed at AP_PLACEHOLDER_GOODS and suppressed exactly as before. That machinery never read the
# detection flag ("Checks are detected by the FLAG POLL, not by the item id" -- its own docstring),
# so moving the poll leaves suppression untouched.
#
# Rennala/the Unborn rune (7900004) is NOT here: it detects on f197, which is 6905's INPUT for slot
# 177 rather than a slot in the band, so it was never exposed to this collision.
# 🛑 NOT THE 510xxx FLAGS 6905 READS. Those are REMEMBRANCE REWARD `getItemFlagId`s
# (`tables/boss_reward_lots.py:240` -- "reward getItemFlagId -> boss DEFEAT flag"), and every one of
# them is ALREADY the detection flag of its own Remembrance check in data.py -- 510010 is
# `Remembrance of the Grafted` (7770653), 510040 the Omen King (7770654), 510220 the Blasphemous
# (7770663), and so on. Repointing a rune onto one would put TWO locations on ONE flag: picking up
# the Remembrance would send the Great Rune check too, which is the same lost/ghost-check class this
# change exists to remove, only moved one flag to the left. (That shape is legal in this world ONLY
# as an allowlisted co-check family with a distinct lot per member in `LOCATION_LOT` -- which these
# six do not have and do not need.)
#
# The target is the boss's own DEFEAT flag, one hop further on, via `BOSS_REWARD_DEFEAT`. Nothing
# else detects on these, and the client already watches all six as `boss_sweeps` triggers, so the
# poll is not being asked to do anything new.
#
# ⚠️ RADAHN IS THE FESTIVAL-ALIAS TRAP. `BOSS_REWARD_DEFEAT[510300]` is the `10`-prefix ENTITY flag
# 1052380800, but the flag that actually persists after the festival is the `12`-prefix
# **1252380800** -- the form `boss_healthbars` / `boss_taxonomy` / `boss_sweeps` all carry, and the
# one `_festival_alias` exists to bridge (`tests/test_gf_sweep_slot_split.py:105`). A poll on the
# 10-form would never fire. Fire Giant has the same split; he is not a rune boss.
GREAT_RUNE_DETECT_FLAGS: Dict[int, int] = {
    7770001: 10000800,    # Godrick the Grafted        (m10_00 Stormveil)     -- possession f171
    7770002: 1252380800,  # Starscourge Radahn         (m60_52_38 Redmane)    -- possession f172
    7770003: 11000800,    # Morgott, the Omen King     (m11_00 Leyndell)      -- possession f173
    7770004: 16000800,    # Rykard, Lord of Blasphemy  (m16_00 Volcano Manor) -- possession f174
    7770005: 12050800,    # Mohg, Lord of Blood        (m12_05 Mohgwyn)       -- possession f175
    7770006: 15000800,    # Malenia, Blade of Miquella (m15_00 Haligtree)     -- possession f176
}


def detect_flag_overrides(world) -> Dict[int, int]:
    """The subset of GREAT_RUNE_DETECT_FLAGS whose location is actually IN this seed.

    Scoped on purpose. `core._base_slot_data` merges `gf_extra_location_flags` into locationFlags
    unconditionally and then back-fills loc_regions from data.LOCATIONS, so an unscoped override
    would PUBLISH a check whose region the draw never kept -- inventing a location on a seed that
    does not have it. Only rows whose region is in `[HUB] + kept` are emitted; on a seed without
    Stormveil there is simply nothing to override.
    """
    scope = set([HUB] + list(world._kept()))
    in_scope = {int(ap) for rn in scope for (_n, ap, _f) in LOCATIONS.get(rn, ())}
    return {ap: fl for ap, fl in GREAT_RUNE_DETECT_FLAGS.items() if ap in in_scope}


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
        # Repoint the six boss runes' DETECTION onto the boss defeat flag -- see the evidence block
        # above GREAT_RUNE_DETECT_FLAGS. Same documented seam features/finale.py uses, and the same
        # merge idiom, so the two compose instead of clobbering each other.
        _overrides = detect_flag_overrides(world)
        if _overrides:
            flags = dict(getattr(world, "gf_extra_location_flags", {}))
            flags.update(_overrides)
            world.gf_extra_location_flags = flags
        logging.getLogger("Greenfield").info(
            "[eldenring:%s] great runes: %d injected, %d boss-rune check(s) repointed off the "
            "170-179 possession band onto boss defeat flags",
            world.player, len(world.gf_great_runes_injected), len(_overrides))

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
