"""presence_floor -- a curated QoL "presence floor": guarantee a set of high-value Wondrous Physick
crystal tears and smithing bell bearings are ALWAYS in the item pool, by injecting exactly one copy of
each roster item that is ABSENT this seed (its home-region vanilla check was not kept), and NEVER
duplicating one that is already present.

WHY THIS EXISTS
---------------
`dlc_only` (and any num_regions seed that seals a roster item's home region) drops the vanilla checks
that pay out these tears / bell bearings, so a DLC-only run could never obtain a single physick tear or
smithing-stone bell bearing -- the flask and the upgrade economy would feel amputated even though the
mode is supposed to stand on its own. The presence floor makes the mode feel like its own thing: the
curated QoL set is guaranteed present regardless of which regions survive.

HOW IT STAYS COUNT-NEUTRAL
--------------------------
Modelled on features/progressive.py exactly. create_items() returns one pool item per ABSENT roster
name; core.create_items adds these to the pool BEFORE it sizes the filler tail (slots =
total_locations - len(pool)), so every injected copy displaces exactly one filler/Rune tail item and
the pool stays count-exact. The injected copies are `useful` (never progression -- Region Locks stay
the sole gate, so winnability is unaffected).

PRESENCE, NOT DUPLICATION
-------------------------
A roster item is PRESENT when its vanilla item lands on a kept location this seed (item_shuffle reads
LOCATION_ITEM for [HUB] + kept regions -- the same source core uses to build its item-shuffle pool). A
present roster item is NOT injected; features/filler_curation protects the whole roster from junk
seizure (PRESENCE_FLOOR_ITEMS), so a present tear/bell survives in the pool as ITSELF rather than being
displaced by the filler tail. Absent => inject exactly one copy. So: present xor injected, never both,
never duplicated.

The roster items are real vanilla GOODS (granted by their FullID, already in ITEM_CATALOG /
_AP_IDS_TO_ITEM_IDS), so the client grants them with no client change -- this feature is pool-only.

A ROSTER ITEM ANOTHER FEATURE HAS TAKEN OVER (#539)
---------------------------------------------------
`progressive_stone_bells` replaces every vanilla bell bearing with a progressive ladder and
substitutes the vanilla names out of the item-shuffle pool (features/progressive.vanilla_
substitutions). This floor is the OTHER source of those names, and it is the reason every bearing showed
up in a live seed even where only a few regions were kept: substitution only removes the bearings
that were ON a kept check, and the floor injected every one that was not. Injecting a vanilla bearing
under that toggle hands the player the ladder's TOP RUNG as a single pickup -- the ladder is then not
degraded, it is BYPASSED (boblerrr, live playtest 2026-08-10). So when the toggle is on the bell
bearings drop out of the floor (_toggle_dropped below).

That is a HAND-OFF, not a hole: this floor exists so `dlc_only` / region-sealed seeds are not left
with no bell bearing at all, and features/progressive keeps exactly that guarantee by topping its
copies up to the ladder length in EVERY seed (bell_inject_count), including the ones with zero kept
bell checks. The physick tears have no such owner and are untouched.
"""
from typing import List

from BaseClasses import ItemClassification
from ..registry import Feature, register

try:
    from ..item_ids import ITEM_CATALOG, LOCATION_ITEM
except Exception:  # pre-regen: no catalog -> roster resolves empty, feature is inert
    ITEM_CATALOG, LOCATION_ITEM = {}, {}
try:
    from ..data import HUB, LOCATIONS
except Exception:
    HUB, LOCATIONS = "Roundtable Hold", {}


# ---- the curated roster -----------------------------------------------------------------------
# High-tier Wondrous Physick crystal tears. All 18 GOODS; every name confirmed to resolve in
# ITEM_CATALOG (test_gf_presence_floor.test_roster_resolves guards this).
PHYSICK_CORE = [
    "Opaline Hardtear",
    "Crimsonburst Crystal Tear",
    "Thorny Cracked Tear",
    "Spiked Cracked Tear",
    "Stonebarb Cracked Tear",
    "Bloodsucking Cracked Tear",
    "Cerulean Hidden Tear",
    "Crimsonwhorl Bubbletear",
    "Leaden Hardtear",
    "Deflecting Hardtear",
]
PHYSICK_DEPTH = [
    "Flame-Shrouding Cracked Tear",
    "Magic-Shrouding Cracked Tear",
    "Lightning-Shrouding Cracked Tear",
    "Holy-Shrouding Cracked Tear",
    "Strength-knot Crystal Tear",
    "Dexterity-knot Crystal Tear",
    "Intelligence-knot Crystal Tear",
    "Faith-knot Crystal Tear",
]
PHYSICK_TEARS = PHYSICK_CORE + PHYSICK_DEPTH

# Vanilla upgrade bell-bearing items. Weapon and spirit-ash shop bearings are requested;
# the catalog is the arbiter (a name that does not resolve is dropped -- see _RESOLVED_ROSTER below
# and the note reported at commit time). Somberstone [1] is NOT in the FMG name catalog (it is not a
# looted item there), so it is dropped automatically; the eight that resolve are kept.
BELL_BEARINGS = (
    [f"Smithing-Stone Miner's Bell Bearing [{i}]" for i in range(1, 5)]
    + [f"Somberstone Miner's Bell Bearing [{i}]" for i in range(1, 6)]
    + [f"Glovewort Picker's Bell Bearing [{i}]" for i in range(1, 4)]
    + [f"Ghost-Glovewort Picker's Bell Bearing [{i}]" for i in range(1, 4)]
)

# The requested roster in a fixed, deterministic order (physick tears first, then bell bearings).
_RAW_ROSTER: List[str] = PHYSICK_TEARS + BELL_BEARINGS

# The roster restricted to names that actually resolve in the catalog -- the only ones that can be
# injected (they must be registered AP items with a FullID). Also the set features/filler_curation
# protects from junk seizure, so a present roster item survives in the pool as itself.
ROSTER: List[str] = [n for n in _RAW_ROSTER if n in ITEM_CATALOG] if ITEM_CATALOG else list(_RAW_ROSTER)
# Names that were requested but did not resolve -- reported by the test so a rename cannot silently
# shrink the roster to nothing (same failure shape as the collectathon-protection bug).
UNRESOLVED: List[str] = [n for n in _RAW_ROSTER if ITEM_CATALOG and n not in ITEM_CATALOG]

# The protection set filler_curation imports (frozen so a caller cannot mutate it). Deliberately the
# WHOLE roster, toggle-independent: it only shields a roster item that is ALREADY in the pool from
# junk seizure, and under progressive_stone_bells no vanilla bearing is in the pool to shield, so the
# bell entries are simply inert there. Making it world-dependent would buy nothing and would give
# filler_curation a second, differently-shaped answer to "what is protected".
PRESENCE_FLOOR_ITEMS = frozenset(ROSTER)

# The bell-bearing half of the ROSTER, as a set -- the names another feature can take over. Note the
# intersection keeps the item catalog as the arbiter, so taking the raw list can never ask the floor
# to inject a name that does not resolve. Same arbiter as ROSTER, one filter, no second answer.
BELL_BEARING_ITEMS = frozenset(BELL_BEARINGS) & PRESENCE_FLOOR_ITEMS


def _shuffle_on(world) -> bool:
    o = getattr(world.options, "item_shuffle", None)
    return bool(o is not None and o.value)


def present_roster(world) -> set:
    """Roster names whose vanilla item lands on a kept ([HUB] + kept regions) location this seed --
    i.e. the ones already in the item-shuffle pool. Mirrors core.create_items' extras source
    (LOCATION_ITEM), and honours the DLC-off exclusion. Empty when item_shuffle is off (no vanilla
    item is in the pool at all, so every roster item is absent)."""
    if not _shuffle_on(world) or not LOCATION_ITEM:
        return set()
    roster = PRESENCE_FLOOR_ITEMS
    excl = getattr(world, "gf_dlc_excluded", frozenset())
    name_to_id = getattr(world, "item_name_to_id", {})
    kept = list(world._kept()) if hasattr(world, "_kept") else []
    present = set()
    for rn in [HUB] + kept:
        for (_name, ap_id, _flag) in LOCATIONS.get(rn, []):
            nm = LOCATION_ITEM.get(ap_id)
            if nm in roster and nm in name_to_id and nm not in excl:
                present.add(nm)
    return present


def _toggle_dropped(world) -> frozenset:
    """Roster names another feature owns this seed, so this floor must NOT inject them (#539).

    Only one so far: with `progressive_stone_bells` on, the bell bearings are the progressive
    ladder's rungs and a loose vanilla copy is the top rung handed over in one pickup. See this
    module's docstring -- the guarantee is kept, features/progressive just keeps it instead."""
    o = getattr(world.options, "progressive_stone_bells", None)
    return BELL_BEARING_ITEMS if (o is not None and o.value) else frozenset()


def absent_roster(world) -> List[str]:
    """Roster names to inject: resolvable, not present, not DLC-excluded, AND not owned by another
    feature this seed (_toggle_dropped -- #539). Preserves ROSTER order
    (deterministic). Dropping DLC-excluded names is what keeps a DLC-off seed clean: two roster physick
    tears (Bloodsucking Cracked Tear, Deflecting Hardtear) are DLC-only GOODS, so injecting them with
    DLC off would leak DLC content into the pool (the exact class test_gf_dlc_pool_leak guards). With
    DLC off they are simply not part of the floor; with DLC on the exclusion set is empty.

    🛑 #618 -- `vanilla_pool` STANDS THIS FLOOR DOWN ENTIRELY. Until then this feature had no option
    and was not frozen: it was unconditional, and that is precisely why `curated_filler: {}` did not
    give anyone a vanilla pool. It looked like it had, and 18 tears still arrived. Gated HERE rather
    than in create_items so that both callers see the same answer -- the tests read this function,
    and a floor that is off for the pool but on for the predicate is the kind of split that gets
    asserted green while the seed disagrees."""
    from . import vanilla_pool as _vp
    if _vp.is_on(world):
        return []
    present = present_roster(world)
    excl = getattr(world, "gf_dlc_excluded", frozenset())
    dropped = _toggle_dropped(world)
    return [n for n in ROSTER if n not in present and n not in excl and n not in dropped]


@register
class PresenceFloor(Feature):
    name = "presence_floor"
    # No NEW item names: every roster entry is already a registered ITEM_CATALOG good (with its FullID
    # in _AP_IDS_TO_ITEM_IDS), so the client grants it unchanged. Declaring them in ITEMS would give
    # them a fresh feature id and DROP the FullID mapping -- so we deliberately do NOT.
    ITEMS = {}

    def create_items(self, world) -> List:
        # One `useful` copy per ABSENT roster item. Added to core's pool before it sizes the filler
        # tail, so each copy displaces exactly one filler/Rune slot -- count-neutral, exactly like
        # features/progressive.create_items. Present roster items are left alone (filler_curation
        # protects them from the tail), so we never duplicate one already in the pool.
        out: List = []
        # 🛑 THIS LINE IS NARROWER THAN IT LOOKS SINCE 2026-08-12. The 18 physick tears are
        # `crystal_tears`, which item_categories.CATEGORY_CLASS now classes `useful` on its own, so
        # for them this assignment is a no-op. It is still load-bearing for the BELL BEARINGS --
        # `key_items`, still filler -- and it must stay: a roster the floor guarantees should not
        # arrive in the pool labelled junk. Do not delete it as redundant without checking the
        # roster's categories, and do not read the label back to identify an injection: the test
        # that did exactly that broke on the flip (see tests/test_gf_presence_floor._roster_copy_counts).
        for name in absent_roster(world):
            it = world.create_item(name)
            it.classification = ItemClassification.useful
            out.append(it)
        return out
