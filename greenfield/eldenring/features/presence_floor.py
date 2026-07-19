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

# Vanilla smithing bell-bearing items. Smithing-Stone [1]-[4] + Somberstone [1]-[5] are REQUESTED;
# the catalog is the arbiter (a name that does not resolve is dropped -- see _RESOLVED_ROSTER below
# and the note reported at commit time). Somberstone [1] is NOT in the FMG name catalog (it is not a
# looted item there), so it is dropped automatically; the eight that resolve are kept.
BELL_BEARINGS = (
    [f"Smithing-Stone Miner's Bell Bearing [{i}]" for i in range(1, 5)]
    + [f"Somberstone Miner's Bell Bearing [{i}]" for i in range(1, 6)]
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

# The protection set filler_curation imports (frozen so a caller cannot mutate it).
PRESENCE_FLOOR_ITEMS = frozenset(ROSTER)


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


def absent_roster(world) -> List[str]:
    """Roster names to inject: resolvable, not present, AND not DLC-excluded. Preserves ROSTER order
    (deterministic). Dropping DLC-excluded names is what keeps a DLC-off seed clean: two roster physick
    tears (Bloodsucking Cracked Tear, Deflecting Hardtear) are DLC-only GOODS, so injecting them with
    DLC off would leak DLC content into the pool (the exact class test_gf_dlc_pool_leak guards). With
    DLC off they are simply not part of the floor; with DLC on the exclusion set is empty."""
    present = present_roster(world)
    excl = getattr(world, "gf_dlc_excluded", frozenset())
    return [n for n in ROSTER if n not in present and n not in excl]


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
        for name in absent_roster(world):
            it = world.create_item(name)
            it.classification = ItemClassification.useful
            out.append(it)
        return out
