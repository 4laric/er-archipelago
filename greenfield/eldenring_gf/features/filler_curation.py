"""filler_curation -- seize the junk-consumable filler and refill it from a CONFIGURABLE category
recipe (matt-free). Nightreign-inspired; expanded from the old world's UPLIFT_CONSUMABLES.

ER's vanilla spread is ~half throwaway consumables, and item_shuffle preserves it 1:1, so a big slice
of the pool is noise pool_builder can't touch (it only juices the near-empty Rune tail). curated_filler
is a dict recipe {category: weight}: it seizes the junk-consumable filler and refills each slot by a
weighted category draw. Categories are combat/util consumables (throwables, pots, greases, foods,
utility, funny) AND economy (stones, somber_stones, runes) so you can dial "more upgrade mats / more
leveling / more throwables" freely. A "junk" category keeps that share as vanilla junk. Empty = off.

STACKS: throwables x5, pots x2, greases x2 are granted in STACKS via slot_data itemCounts -- so finding
one hands you a usable bundle, not a single item. This is a per-item quantity, so ALL members of those
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
    # Boiled Prawn is crafted-only (not in the catalog until the Phase-2 regen mines it) -> added then.
    "foods": ["Gold-Pickled Fowl Foot", "Silver-Pickled Fowl Foot", "Pickled Turtle Neck",
              "Well-Pickled Turtle Neck", "Exalted Flesh", "Starlight Shards",
              "Warming Stone", "Bewitching Branch"],
    "boluses": ["Preserving Boluses", "Neutralizing Boluses", "Stanching Boluses", "Clarifying Boluses",
                "Thawfrost Boluses", "Stimulating Boluses", "Rejuvenating Boluses"],
    "perfumes": _PERFUMES,   # DLC spraymist/aromatic consumables; populated once the catalog regen mines them
    "utility": ["Rune Arc", "Larval Tear"],
    # "rare": low-probability injectables -- weight this category tiny in the recipe (e.g. rare: 1).
    "rare": ["Dragon Heart", "Stonesword Key"],
    "funny": ["Raw Meat Dumpling", "Gold-Tinged Excrement"],
    "stones": [f"Smithing Stone [{i}]" for i in range(1, 9)],
    "somber_stones": [f"Somber Smithing Stone [{i}]" for i in range(1, 10)],
    "runes": [f"Golden Rune [{i}]" for i in range(1, 14)],
    # "junk" is a pseudo-category: that share is left as the original vanilla junk (not redrawn).
}
_VALID_CATS = frozenset(CATEGORIES) | {"junk"}

# STACK quantities (grant size) by category -> emitted as slot_data itemCounts. Others default 1.
STACK_QTY_BY_CATEGORY = {"throwables": 5, "pots": 2, "greases": 2}

# Beloved junk -- never seized, always survives.
FUNNY_JUNK = frozenset({"Raw Meat Dumpling", "Gold-Tinged Excrement"})
# Placed leveling/upgrade economy -- never seized (the recipe ADDS on top, doesn't strip it).
_ECONOMY_SUBSTR = ("Golden Rune", "Shadow Realm Rune", "Lord's Rune", "Hero's Rune", "Numen's Rune",
                   "Smithing Stone", "Golden Seed", "Sacred Tear", "Glovewort", "Great Rune")


def stack_qty_by_name():
    """{item_name: qty} for items granted as stacks (throwables x10, pots x4). core emits itemCounts."""
    out = {}
    for cat, qty in STACK_QTY_BY_CATEGORY.items():
        for n in CATEGORIES.get(cat, ()):
            if n in ITEM_CATALOG:
                out[n] = qty
    return out


class CuratedFiller(OptionDict):
    """Recipe for replacing junk-consumable filler: a table of {category: weight}. The junk slots are
    split across the categories by weight. Categories: throwables, pots, greases, foods, boluses,
    perfumes, utility, rare, funny, stones, somber_stones, runes -- plus 'junk' to keep that share as
    vanilla junk. Empty (default) = off (vanilla junk). Stacks: throwables x5, pots x2, greases x2.
    'rare' (Dragon Heart, Stonesword Key) is meant to be weighted TINY (e.g. rare: 1). The placed
    leveling/upgrade economy and the Raw Meat Dumpling / Gold-Tinged Excrement are never removed.
    Example: {throwables: 25, pots: 15, greases: 10, foods: 10, boluses: 5, perfumes: 8, rare: 1,
    stones: 15, runes: 15}."""
    display_name = "Curated Filler recipe (category -> weight)"
    default = {}


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


def curate(world, pool):
    """core.create_items hook: seize junk-consumable filler and refill each slot by a weighted draw over
    the curated_filler recipe categories. 'junk' weight keeps that share vanilla. Deterministic."""
    opt = getattr(world.options, "curated_filler", None)
    recipe = dict(getattr(opt, "value", None) or {})
    cats = [(c, int(w)) for c, w in recipe.items() if c in _VALID_CATS and int(w) > 0]
    if not cats:
        return
    excl = set(getattr(world, "gf_dlc_excluded", ()))
    members = {c: [m for m in CATEGORIES[c] if m in ITEM_CATALOG and m not in excl]
               for c, _ in cats if c in CATEGORIES}
    names = [c for c, _ in cats]
    weights = [w for _, w in cats]
    if sum(weights) <= 0:
        return
    # Seize ONLY pure-filler slots. Elden Ring keys (Academy Glintstone Key, ...) share the GOODS
    # nibble with junk consumables, so _is_junk_consumable alone would evict a progression key and
    # make the seed unwinnable -- guard on classification so progression/useful items always survive.
    _protected = ItemClassification.progression | ItemClassification.useful
    cand = [i for i, it in enumerate(pool)
            if _is_junk_consumable(it.name) and not (it.classification & _protected)]
    world.random.shuffle(cand)
    for idx in cand:
        c = world.random.choices(names, weights=weights, k=1)[0]
        if c == "junk":
            continue  # keep the original vanilla junk item
        pool_c = members.get(c)
        if pool_c:
            pool[idx] = world.create_item(world.random.choice(pool_c))
