"""filler_curation -- seize the junk-consumable filler and refill it from a CONFIGURABLE category
recipe (matt-free). Nightreign-inspired; expanded from the old world's UPLIFT_CONSUMABLES.

ER's vanilla spread is ~half throwaway consumables, and item_shuffle preserves it 1:1, so a big slice
of the pool is noise pool_builder can't touch (it only juices the near-empty Rune tail). curated_filler
is a dict recipe {category: weight}: it seizes the junk-consumable filler and refills each slot by a
weighted category draw. Categories are combat/util consumables (throwables, pots, greases, foods,
utility, funny) AND economy (stones, somber_stones, runes) so you can dial "more upgrade mats / more
leveling / more throwables" freely. A "junk" category keeps that share as vanilla junk. Empty = off.

STACKS: throwables x5, pots x2, greases x2, ammunition x20 are granted in STACKS via slot_data
itemCounts -- so finding one hands you a usable bundle (an arrow drop is a quiver), not a single item. This is a per-item quantity, so ALL members of those
categories grant their stack (curated or vanilla-placed). Emitted by core._base_slot_data.

The beloved FUNNY_JUNK (Raw Meat Dumpling, Gold-Tinged Excrement) is never seized (always survives),
and the placed leveling/upgrade economy is never seized either -- the recipe ADDS on top via the
seized junk slots. Count-neutral in-pool swap, fill-safe, deterministic. Off by default (empty recipe).
Runs from core.create_items via curate(world, pool)."""
from BaseClasses import ItemClassification
from Options import OptionDict
from ..registry import Feature, register

try:
    from ..item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}
try:
    from ..item_ids import AMMO_ITEM_NAMES   # param-derived (EquipParamWeapon.wepType); see gen_data.py
except Exception:                            # pre-regen item_ids.py lacks it -> category empty, stacks inert
    AMMO_ITEM_NAMES = []


def _dlc_pots():
    """DLC 'Hefty ...' throwing pots (Hefty Fire Pot, ...) -- crafted-only, so they enter the catalog
    only once the catalog regen mines them (like _FINISHED_POTS in gen_data.py). Auto-picked by name
    so no ids are guessed; empty pre-regen (curate() skips names not in ITEM_CATALOG). Excludes the
    Hefty Cracked Pot vessel (a start grant, not a thrown pot)."""
    return sorted(n for n in ITEM_CATALOG
                  if n.startswith("Hefty ") and n.endswith(" Pot") and n != "Hefty Cracked Pot")


# DLC perfume consumables (spraymist / aromatic / 'X Perfume Bottle'), auto-picked from the catalog so
# no ids are guessed. The base 'Perfume Bottle' vessel is a start grant, not a filler perfume -> excluded.
# Pre-regen this still yields the five 'X Perfume Bottle' DLC items already in the catalog; the catalog
# regen adds the Spraymist/Aromatic ones.
_PERFUMES = sorted(n for n in ITEM_CATALOG
                   if n.endswith("Spraymist") or n.endswith("Aromatic")
                   or (n.endswith("Perfume Bottle") and n != "Perfume Bottle"))

# Spirit-ash SUMMONS, tier-ordered BEST-FIRST (SS -> S -> A -> B). C/D-tier junk summons are deliberately
# OMITTED so they stay culled (they share the GOODS nibble, so `_is_junk_consumable` seizes the vanilla
# copies; this roster only RE-INJECTS the good ones). Drawn UNIQUE best-first by features/filler_budget
# (like `juice`), so the recipe WEIGHT is the single "how good-only" knob: a small weight surfaces only
# SS/S, a larger one reaches A then B. Every name resolves in ITEM_CATALOG (absent / DLC-excluded members
# are skipped at draw time). Excludes Fanged Imp / Spirit Jellyfish (progression-protected -> they survive
# the cull on their own and would double-place). Tiers: Game8 PvE list + DLC/consensus.
SPIRIT_ASHES = [
    # SS
    "Black Knife Tiche", "Mimic Tear Ashes", "Dung Eater Puppet",
    # S
    "Banished Knight Engvall", "Battlemage Hugues", "Lhutel the Headless", "Greatshield Soldier Ashes",
    "Radahn Soldier Ashes", "Ancient Dragon Knight Kristoff", "Ancient Dragon Florissax",
    "Black Knight Commander Andreas",
    # A
    "Latenna the Albinauric", "Stormhawk Deenh", "Bloodhound Knight Floh", "Cleanrot Knight Finlay",
    "Nightmaiden & Swordstress Puppets", "Omenkiller Rollo", "Marionette Soldier Ashes",
    "Kaiden Sellsword Ashes", "Perfumer Tricia", "Rotten Stray Ashes", "Dolores the Sleeping Arrow Puppet",
    "Fire Knight Queelign", "Fire Knight Hilde", "Black Knight Captain Huw", "Divine Bird Warrior Ornis",
    "Swordhand of Night Jolán", "Curseblade Meera",
    # B
    "Kindred of Rot Ashes", "Warhawk Ashes", "Depraved Perfumer Carmaan", "Blackflame Monk Amon",
    "Finger Maiden Therolina Puppet", "Taylew the Golem Smith", "Demi-Human Swordsman Yosh",
    "Bloodfiend Hexer's Ashes",
]

# ---- category -> member names (all resolve in ITEM_CATALOG; DLC filtered per-world at draw time) ----
CATEGORIES = {
    "throwables": ["Throwing Dagger", "Bone Dart", "Poisonbone Dart", "Crystal Dart", "Kukri", "Fan Daggers",
                   "Gravity Stone Chunk", "Gravity Stone Fan", "Large Glintstone Scrap"],
    # DLC hefty throwing pots (Hefty Fire Pot, ...) are appended by _dlc_pots() below once the catalog
    # regen mines them; absent names are silently skipped, so this is safe pre-regen.
    "pots": ["Fire Pot", "Lightning Pot", "Fetid Pot", "Holy Water Pot", "Freezing Pot", "Poison Pot",
             "Volcano Pot", "Sleep Pot", "Rancor Pot"] + _dlc_pots(),
    "greases": ["Fire Grease", "Lightning Grease", "Magic Grease", "Holy Grease", "Blood Grease",
                "Poison Grease", "Freezing Grease", "Rot Grease", "Dragonwound Grease", "Soporific Grease"],
    # Ammunition (arrows & bolts, base + DLC), PARAM-derived in gen_data.py: EquipParamWeapon rows with
    # wepType in {81 arrow, 83 greatarrow, 85 bolt, 86 ballista bolt} joined to the catalog. NEVER
    # name-derived -- "Honed Bolt" / "Vyke's Dragonbolt" / the Lightning-Strike family are INCANTATIONS
    # and several end in "Bolt". Members grant x20 (STACK_QTY_BY_CATEGORY) so a found arrow is a usable
    # quiver; the stack rides slot_data itemCounts whether the ammo was curated or vanilla-placed.
    # Empty pre-regen (absent names are skipped, same as _dlc_pots).
    "ammunition": list(AMMO_ITEM_NAMES),
    # Boiled Prawn is crafted-only (not in the catalog until the Phase-2 regen mines it) -> added then.
    # Boiled Crab / Boiled Prawn are CRAFTED-ONLY (never looted), so they reach the catalog via the
    # by-name FMG resolve in gen_data, not via a placed row. Absent names are skipped, so listing them
    # is safe even pre-regen.
    "foods": ["Gold-Pickled Fowl Foot", "Silver-Pickled Fowl Foot", "Pickled Turtle Neck",
              "Well-Pickled Turtle Neck", "Exalted Flesh", "Starlight Shards",
              "Warming Stone", "Bewitching Branch", "Boiled Crab", "Boiled Prawn"],
    "boluses": ["Preserving Boluses", "Neutralizing Boluses", "Stanching Boluses", "Clarifying Boluses",
                "Thawfrost Boluses", "Stimulating Boluses", "Rejuvenating Boluses"],
    "perfumes": _PERFUMES,   # DLC spraymist/aromatic consumables; populated once the catalog regen mines them
    "utility": ["Rune Arc", "Larval Tear"],
    # "rare": low-probability injectables -- weight this category tiny in the recipe (e.g. rare: 1).
    # Imbued Sword Key is a KEY ITEM under some classifications (it opens the three Sealed Tunnels).
    # Included deliberately (Alaric 2026-07-11, "I stand by including it"): nothing in this world's logic
    # gates on it, and extra copies enter as FILLER, so it cannot create or satisfy a progression claim.
    "rare": ["Dragon Heart", "Stonesword Key", "Imbued Sword Key"],
    "funny": ["Raw Meat Dumpling", "Gold-Tinged Excrement"],
    "stones": [f"Smithing Stone [{i}]" for i in range(1, 9)],
    "somber_stones": [f"Somber Smithing Stone [{i}]" for i in range(1, 10)],
    "runes": [f"Golden Rune [{i}]" for i in range(1, 14)],
    # Good spirit-ash summons, RE-INJECTED unique best-first (see SPIRIT_ASHES above / the draw branch in
    # features/filler_budget). Without this the GOODS-nibble junk seize strips ~all summons from the pool.
    "spirit_ashes": SPIRIT_ASHES,
    # "junk" is a pseudo-category: that share is left as the original vanilla junk (not redrawn).
}
_VALID_CATS = frozenset(CATEGORIES) | {"junk"}

# STACK quantities (grant size) by category -> emitted as slot_data itemCounts. Others default 1.
# ammunition x20: a quiver per drop (Alaric 2026-07-14, "x20 all the ammunition drops"). Far under the
# game's held caps (999 for basic ammo, 99 for special), so a stack can never overflow a grant.
STACK_QTY_BY_CATEGORY = {"throwables": 5, "pots": 2, "greases": 2, "ammunition": 20}

# Beloved junk -- never seized, always survives.
FUNNY_JUNK = frozenset({"Raw Meat Dumpling", "Gold-Tinged Excrement"})
# THE COLLECTATHON LINES. Finite, tuned, permanent character-power tracks -- the game's own progression
# curve, not filler. progression_surface.py names all four and pins their counts as ground truth:
# "Sacred Tear 13/13, Golden Seed 43/43, Scadutree Fragment 46/46, Revered 23/23".
#
# The DLC two were NOT protected until 2026-07-13, and they are GOODS, so `_is_junk_consumable` called
# them junk and the filler tail displaced every one of them. A DLC seed therefore contained ZERO
# Scadutree Fragments: the Scadutree blessing -- the DLC's entire damage/defence curve -- could never
# rise above 0 from fragments. (It could not rise from the region FLOOR either: that lookup was broken
# by a separate bug in the play_region bucket table. Two independent bugs, one pinned outcome.)
#
# Note the shape of the omission: the BASE-game lines were guarded and their DLC counterparts were not.
# That is the same blind spot as the bucket table -- the DLC was never played, so nothing that was only
# wrong in the DLC ever surfaced. Guarded as a NAMED SET, and tests/test_gf_collectathon_protected.py
# derives its assertion from this constant, so a fifth line cannot be added without being protected.
COLLECTATHON_ITEMS = ("Golden Seed", "Sacred Tear", "Scadutree Fragment", "Revered Spirit Ash")

# Placed leveling/upgrade economy -- never seized (the recipe ADDS on top, doesn't strip it).
_ECONOMY_SUBSTR = ("Golden Rune", "Shadow Realm Rune", "Lord's Rune", "Hero's Rune", "Numen's Rune",
                   "Smithing Stone", "Glovewort", "Great Rune") + COLLECTATHON_ITEMS


def stack_qty_by_name():
    """{item_name: qty} for items granted as stacks (STACK_QTY_BY_CATEGORY, e.g. throwables x5,
    ammunition x20). core._item_counts emits these as slot_data itemCounts."""
    out = {}
    for cat, qty in STACK_QTY_BY_CATEGORY.items():
        for n in CATEGORIES.get(cat, ()):
            if n in ITEM_CATALOG:
                out[n] = qty
    return out


class CuratedFiller(OptionDict):
    """Recipe for replacing junk-consumable filler: a table of {category: weight}. The junk slots are
    split across the categories by weight. Categories: throwables, pots, greases, ammunition, foods,
    boluses, perfumes, utility, rare, funny, stones, somber_stones, runes -- plus 'junk' to keep that
    share as vanilla junk. Empty (default) = off (vanilla junk). Stacks: throwables x5, pots x2,
    greases x2, ammunition x20.
    'rare' (Dragon Heart, Stonesword Key) is meant to be weighted TINY (e.g. rare: 1). The placed
    leveling/upgrade economy and the Raw Meat Dumpling / Gold-Tinged Excrement are never removed.
    Example: {throwables: 25, pots: 15, greases: 10, foods: 10, boluses: 5, perfumes: 8, rare: 1,
    stones: 15, runes: 15}."""
    display_name = "Curated Filler recipe (category -> weight)"
    # v0.2: this recipe owns the ENTIRE filler tail (features/filler_budget), so its default IS the
    # pool economy -- {} would mean a seed with no upgrade materials and no gear injection at all.
    # `juice` is the old pool_builder gear injection, now a weight competing on the same budget rather
    # than a private allocation that consumed the whole thing and starved the stones.
    # stones/somber_stones/runes are a RESERVATION: paid off the top, never scaled down.
    # Weights sum to 100, so they read as plain percentages of the filler tail.
    #
    # The stone weight is TUNED TO A SPEC, not picked by feel: tests/test_gf_filler_economy_floor.py
    # states the bar in player terms -- a player who has cleared a realistic fraction of what is open
    # to them at shallow depth must be able to afford a modest weapon level -- and this weight is the
    # smallest one that satisfies it with margin. If the bar is wrong, argue with the bar (the
    # COLLECTION_RATE and EARLY_TARGET_LEVEL constants in that file), not with this number.
    # stones 24 -> 27 (2026-07-11). ERDTREE_BURN_APS bars advancement from the 79 m11_00 checks (they
    # are destroyed when Maliketh burns the Erdtree), which displaces progression into earlier slots and
    # pushed the early stone economy BELOW the floor: test_early_weapon_upgrade_is_affordable found 21
    # placed across spheres 0-1 where 24 are needed to afford +3 at a 25% clear rate. The floor exists to
    # stop a player being stuck at +0 deep into a seed, so the right move is to feed the economy, not to
    # weaken the softlock guard -- a check the player can destroy must not be REQUIRED, full stop.
    # spirit_ashes 8: the good summons re-injected best-first (SS->S->A->B). The roster is ~36 unique
    # items and the draw is capped there, so on a normal tail this surfaces most of the good ashes and
    # scales down to SS/S-only on small seeds; raise for more, lower for a leaner spread. Competes on the
    # non-economy remainder (stones/somber/runes are reserved off the top), so it never starves upgrades.
    default = {"juice": 44, "stones": 27, "somber_stones": 6, "runes": 10,
               "throwables": 6, "pots": 4, "greases": 3, "foods": 2, "boluses": 1, "spirit_ashes": 8}


@register
class FillerCurationFeature(Feature):
    name = "filler_curation"
    OPTIONS = {"curated_filler": CuratedFiller}
    # No NEW item names beyond the catalog pots (registered by core). Pure in-pool swap from
    # core.create_items via curate(); the STACK quantities go out as itemCounts from _base_slot_data.


def _is_junk_consumable(name):
    """A filler good that is throwaway junk -- NOT the tuned economy and NOT protected funny junk."""
    if name in FUNNY_JUNK or any(s in name for s in _ECONOMY_SUBSTR):
        return False
    full = ITEM_CATALOG.get(name)
    return name == "Rune" or (full is not None and (full & 0xF0000000) == 0x40000000)


def displaceable_filler(world, name) -> bool:
    """True iff a VANILLA pool item `name` may be displaced by pool_builder juice under
    pool_builder_scope=all_filler. Economy-safe: `_is_junk_consumable` already excludes the tuned
    economy (Golden/Lord's/Hero's/Numen's Runes, Smithing/Somber stones, Golden Seed, Sacred Tear,
    Glovewort, Great Rune) and FUNNY_JUNK; we additionally exclude anything the world classifies as
    PROGRESSION -- vanilla keys promoted to gates by features/legacy_key_gates (e.g. Academy Glintstone
    Key) share the GOODS nibble and would otherwise slip through. Purely name-based (reads the world's
    static classification, no live pool object), so features/pool_builder's budget count and core's
    extras-sort rank use the IDENTICAL rule and can never drift (a mismatch could drop a protected
    item). Never called on the FILLER/Rune sentinel (core ranks that separately)."""
    if not _is_junk_consumable(name):
        return False
    return not (world._class_for(name) & ItemClassification.progression)


def curate(world, pool):
    """RETIRED -- kept as a tombstone so nothing silently re-adds a second pass over the filler tail.

    curate() used to seize junk-consumable filler and redraw it from the recipe. It ran AFTER
    pool_builder, whose juice had already re-classified the entire larder `useful` -- which is the
    predicate curate() excludes on. So it found nothing and the recipe delivered ~3 items against an
    entitlement of ~534. The recipe now runs ONCE, inside features/filler_budget, as the single owner
    of the tail. CATEGORIES / STACK_QTY_BY_CATEGORY / the junk predicate all still live here and are
    read by the allocator; only the second pass is gone.
    """
    raise AssertionError(
        "filler_curation.curate() is retired -- the filler tail has a single owner "
        "(features/filler_budget). Do not add a second pass over it.")
