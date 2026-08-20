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
try:  # generated (gen_data): catalog equippables at param rarity 0. Empty pre-regen -> category inert.
    from ..item_ids import JUNK_GEAR_NAMES
except Exception:
    JUNK_GEAR_NAMES = []
try:
    # KEY ITEMS, param-derived (gen_data.py: EquipParamGoods.goodsType == 1). The game's own answer to
    # "is this a key item"; `_is_junk_consumable` subtracts it. Empty on a pre-regen item_ids.py --
    # which is INERT, not safe: see that predicate's docstring.
    from ..item_ids import KEY_ITEM_GOODS
except Exception:
    KEY_ITEM_GOODS = []


def _gate_key_items():
    """The vanilla items of checks the world tags `KeyItem` -- ITS OWN statement of "gate/travel key",
    the same curated set features/progression_surface builds the surface from.

    WHY THE PARAM IS NOT ENOUGH (CI, 2026-07-28). goodsType == 1 emits 204 names -- cookbooks,
    prayerbooks, bell bearings, whetblades, the real gate keys -- and does NOT include
    `Pureblood Knight's Medal`, because the game files it as a single-use travel CONSUMABLE, not a key
    item. Our model disagrees: it is a travel key, it is KeyItem-tagged, and under the id-nibble
    predicate it was displaceable. Two sources, both already generated, and the union is what the junk
    predicate subtracts -- not a hand list bolted on, and not one source pretending to be complete.
    """
    try:
        from ..location_tags import LOCATION_TAGS
        from ..item_ids import LOCATION_ITEM
    except Exception:
        return frozenset()
    return frozenset(nm for ap, tags in LOCATION_TAGS.items()
                     if "KeyItem" in tags and (nm := LOCATION_ITEM.get(ap)))


_KEY_ITEM_GOODS = frozenset(KEY_ITEM_GOODS) | _gate_key_items()
try:
    from ..item_ids import AMMO_ITEM_NAMES   # param-derived (EquipParamWeapon.wepType); see gen_data.py
except Exception:                            # pre-regen item_ids.py lacks it -> category empty, stacks inert
    AMMO_ITEM_NAMES = []
try:
    # The presence-floor roster (physick tears + smithing bell bearings). These are GOODS, so the junk
    # predicate below would seize them as filler and the tail would displace every one of them -- which
    # would mean a roster item's KEPT vanilla check could be trimmed out of the pool. Protect them like
    # the collectathon lines so that when a tear/bell's home region IS kept it survives as itself
    # (present -> features/presence_floor does not inject a duplicate). Same failure shape as the
    # Scadutree Fragment / Revered Spirit Ash omission (test_gf_collectathon_protected).
    from .presence_floor import PRESENCE_FLOOR_ITEMS
except Exception:                            # feature not importable yet (standalone unit load) -> inert
    PRESENCE_FLOOR_ITEMS = frozenset()


def _dlc_pots():
    """DLC 'Hefty ...' throwing pots (Hefty Fire Pot, ...) -- crafted-only, so they enter the catalog
    only once the catalog regen mines them (like _FINISHED_POTS in gen_data.py). Auto-picked by name
    so no ids are guessed; empty pre-regen (curate() skips names not in ITEM_CATALOG). Excludes the
    Hefty Cracked Pot vessel (a start grant, not a thrown pot)."""
    return sorted(n for n in ITEM_CATALOG
                  if n.startswith("Hefty ") and n.endswith(" Pot") and n != "Hefty Cracked Pot")


def _dlc_fire_pots():
    """DLC hefty FIRE-damage throwing pots (Hefty Fire Pot, ...) -- the Furnace Golem tool: you kill
    them by throwing fire into the furnace on their head. Catalog-filtered like _dlc_pots, so empty
    pre-regen and dropped per-world when DLC is off (absent names skipped at draw time)."""
    return sorted(n for n in ITEM_CATALOG
                  if n.startswith("Hefty ") and n.endswith(" Pot")
                  and "Fire" in n and n != "Hefty Cracked Pot")


# DLC perfume consumables (spraymist / aromatic / 'X Perfume Bottle'), auto-picked from the catalog so
# no ids are guessed. The base 'Perfume Bottle' vessel is a start grant, not a filler perfume -> excluded.
# Pre-regen this still yields the five 'X Perfume Bottle' DLC items already in the catalog; the catalog
# regen adds the Spraymist/Aromatic ones.
_PERFUMES = sorted(n for n in ITEM_CATALOG
                   if n.endswith("Spraymist") or n.endswith("Aromatic")
                   or (n.endswith("Perfume Bottle") and n != "Perfume Bottle"))

# Base-game weapon greases (kept explicit -- named, always in the catalog).
_BASE_GREASES = ["Fire Grease", "Lightning Grease", "Magic Grease", "Holy Grease", "Blood Grease",
                 "Poison Grease", "Freezing Grease", "Rot Grease", "Dragonwound Grease", "Soporific Grease"]


def _dlc_greases():
    """DLC weapon grease(s) added to the filler pool -- currently just Messmerfire Grease (SotE).
    Catalog-guarded like _dlc_pots: the name is absent (and so skipped at draw time) when DLC is off.
    NAMED explicitly rather than pattern-matched on ' Grease': most other catalog greases (Dragon
    Communion, Dragonbolt, Festive, Royal Magic, Shield) are BASE-game greases deliberately left out
    of the curated base list, so an ' endswith Grease ' sweep would silently re-include them. Extend
    this tuple for future DLC greases. (Alaric 2026-07-22 "get messmerfire grease into the pool".)"""
    return [n for n in ("Messmerfire Grease",) if n in ITEM_CATALOG]


# ---- category -> member names (all resolve in ITEM_CATALOG; DLC filtered per-world at draw time) ----
CATEGORIES = {
    "throwables": ["Throwing Dagger", "Bone Dart", "Poisonbone Dart", "Crystal Dart", "Kukri", "Fan Daggers",
                   "Gravity Stone Chunk", "Gravity Stone Fan", "Large Glintstone Scrap"],
    # DLC hefty throwing pots (Hefty Fire Pot, ...) are appended by _dlc_pots() below once the catalog
    # regen mines them; absent names are silently skipped, so this is safe pre-regen.
    "pots": ["Fire Pot", "Lightning Pot", "Fetid Pot", "Holy Water Pot", "Freezing Pot", "Poison Pot",
             "Volcano Pot", "Sleep Pot", "Rancor Pot"] + _dlc_pots(),
    # firepots -- fire/volcano-damage throwables. Weight this to lean the mix toward fire for DLC
    # Furnace Golems (killed by throwing fire into the furnace on their head). Overlaps `pots` on
    # purpose: an OPT-IN emphasis category, NOT in the default recipe, so a seed only leans fire when
    # the player asks for it. Base Fire/Volcano Pot + DLC Hefty Fire Pot (catalog/DLC-filtered).
    "firepots": ["Fire Pot", "Volcano Pot"] + _dlc_fire_pots(),
    "greases": _BASE_GREASES + _dlc_greases(),
    # Ammunition (arrows & bolts, base + DLC), PARAM-derived in gen_data.py: EquipParamWeapon rows with
    # wepType in {81 arrow, 83 greatarrow, 85 bolt, 86 ballista bolt} joined to the catalog. NEVER
    # name-derived -- "Honed Bolt" / "Vyke's Dragonbolt" / the Lightning-Strike family are INCANTATIONS
    # and several end in "Bolt". Members grant x20 (STACK_QTY_BY_CATEGORY) so a found arrow is a usable
    # quiver. The curated bundle rides its own `Arrow x20` AP id; vanilla-placed ammo instead keeps
    # the exact quantity carried by its source lot (#624).
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
    # junk_gear -- catalog equippables the GAME rates trivial (param rarity 0), generated as
    # item_ids.JUNK_GEAR_NAMES. NOT in the shipped recipe, so it is inert unless a player weights it
    # and no default seed moves.
    #
    # WHY IT EXISTS. pool_builder's juice floor starts at tier 1 on purpose -- juice means GOOD gear
    # -- so rarity-0 equippables are invisible to it at every intensity. That is right for juice and
    # was wrong as the final word: 96 of these have no check either, because their only sources are
    # UNFLAGGED lots (a random enemy drop fires on every kill, so there is no one-shot event to poll
    # and it can never back an AP location). Celebrant's Cleaver / Rib-Rake / Sickle are the reported
    # case. Registering the catalog name made them injectable in principle; this category is the path
    # that actually reaches them, competing on the filler budget rather than arguing with juice's
    # quality bar.
    "junk_gear": list(JUNK_GEAR_NAMES),
    # "junk" is a pseudo-category: that share is left as the original vanilla junk (not redrawn).
}
_VALID_CATS = frozenset(CATEGORIES) | {"junk"}

# `juice` (the gear injection) is a recipe key with no member list of its own -- it is drawn from the
# curated tier ladder, not from CATEGORIES -- so it has to be added on top. It lived in
# features/filler_budget as a bare `JUICE = "juice"`; it moves HERE because this is the module that
# owns the option, and the option's `valid_keys` cannot import the module that imports it.
JUICE = "juice"

# 🛑 THE ONE LIST OF ACCEPTED RECIPE KEYS. Three consumers read it and they used to be able to
# disagree: AP's `VerifyKeys` (via CuratedFiller.valid_keys), the wizard metadata dumper (which
# cannot draw a control for a dict whose keys it does not know -- #571), and filler_budget's own
# unknown-category OptionError. `_VALID_CATS` alone is NOT it: it omits `juice`, which the shipped
# default weights at 42, so anything validating against `_VALID_CATS` rejects the default recipe.
RECIPE_KEYS = frozenset(_VALID_CATS) | {JUICE}

# STACK quantities (grant size) by category -> emitted as slot_data itemCounts. Others default 1.
# ammunition x20: a quiver per drop (Alaric 2026-07-14, "x20 all the ammunition drops"). Far under the
# game's held caps (999 for basic ammo, 99 for special), so a stack can never overflow a grant.
STACK_QTY_BY_CATEGORY = {
    "throwables": 5,
    "pots": 10,
    "firepots": 10,
    "greases": 2,
    "ammunition": 20,
    "perfumes": 10,
}

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


def curated_stack_name(name):
    """The AP item name for a curated bundle; vanilla source lots do not use this rule."""
    qty = stack_qty_by_name().get(name, 1)
    return "%s x%d" % (name, qty) if qty > 1 else name


class CuratedFiller(OptionDict):
    """Recipe for the WHOLE filler tail: a table of {category: weight}. The tail is split across the
    categories in proportion to their weights -- they are relative, not percentages, and need not sum
    to anything. Categories: juice, junk_gear, stones, somber_stones, runes, throwables, pots,
    firepots, greases, ammunition, foods, boluses, perfumes, utility, rare, funny -- plus 'junk' to
    keep that share as whatever the check already paid. Stacks: throwables x5, pots/firepots/perfumes
    x10, greases x2, ammunition x20.
    NOT off by default. The shipped recipe is juice 63 / stones 6 / somber_stones 6 / runes 10 /
    throwables 6 / pots 4 / greases 3 / foods 2 / boluses 1 / perfumes 2. Perfumes take two points
    from juice, so adding them does not increase the filler budget.
    filler tail is real gear. An EMPTY recipe is honoured and means no gear AND no upgrade economy --
    it warns loudly rather than silently reverting to vanilla junk.
    'juice' is the gear injection (rare/legendary-first equippables, drawn best-first by curated tier
    from ~1013 qualifying items). Its opposite number is 'junk_gear': the ~368 equippables the game
    itself rates trivial, which juice will never hand you at any intensity because its floor starts
    above them. Weight junk_gear if you want the low end of the armoury in your filler -- it is the
    only path to the ~96 pieces (the Celebrant's weapons among them) that have no check at all,
    because their only source is a random enemy drop the game never flags. It competes on the same budget as everything else; raising it past
    what the catalog can supply spills the surplus to junk, with a warning naming the shortfall.
    'stones', 'somber_stones' and 'runes' are an upgrade-economy RESERVATION taken off the top
    proportionally. A tail too small for that reservation to buy a useful number of stones warns by
    name; it does not refuse to generate.
    'firepots' (Fire Pot, Volcano Pot, DLC Hefty Fire Pot) is a fire/volcano lean for DLC Furnace
    Golems -- overlaps 'pots', so weight it only when you want the mix biased toward fire.
    'rare' (Dragon Heart, Stonesword Key) is meant to be weighted TINY (e.g. rare: 1). The placed
    leveling/upgrade economy and the Raw Meat Dumpling / Gold-Tinged Excrement are never removed.
    Example (a consumable-leaning run that still keeps its economy): {juice: 20, stones: 29,
    somber_stones: 6, runes: 10, throwables: 25, pots: 15, greases: 10, foods: 10, boluses: 5,
    perfumes: 8, rare: 1}. Copying an example WITHOUT `juice` and the stone weights is what the
    empty-recipe warning is about."""
    display_name = "Curated Filler recipe (category -> weight)"
    # 🛑 DERIVED FROM `RECIPE_KEYS`, NEVER RETYPED, and NOT from `_VALID_CATS` -- that set omits
    # `juice`, which the shipped default weights at 42, so validating against it rejects this
    # class's own default. (Caught by test_valid_keys_accepts_the_shipped_default, which exists
    # because I made exactly that mistake writing this line.)
    #
    # WHY THE CLASS DECLARES THEM AT ALL: `tools/dump_options_metadata.py` fills the wizard's
    # `valid_keys` from here, and a dict with none leaves the page nothing to enumerate -- it drew
    # the whole recipe as a text box reading `[object Object]` (#571). The keys were only ever
    # knowable from filler_budget, which the wizard cannot see.
    #
    # SORTED because `valid_keys` lands in a committed artifact and a frozenset has no stable
    # iteration order; the dumper sorts too, so `--check` stays byte-comparable either way.
    #
    # ⚠️ This does NOT newly reject anything: features/filler_budget already raises OptionError on
    # an unknown category ("curated_filler: unknown category ..."). What moves is WHEN and in WHOSE
    # words -- AP's `verify_keys` now says it first, at option verification, listing the allowed
    # keys. Both read off RECIPE_KEYS, so the two messages cannot come to disagree.
    valid_keys = sorted(RECIPE_KEYS)
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
    #
    # stones 27 -> 29 (2026-07-28), the SAME mechanism a second time and taken from the same direction.
    # Two changes landed together: KEY_ITEM_GOODS took the key items out of the displaceable tail (so the
    # budget the stone weight is a share OF got smaller), and the NPC-handover corpus + the Fortissax
    # boss-arena tag barred ~35 more checks from carrying progression (so what remains is displaced
    # earlier). Either alone still cleared the floor; together they did not. MEASURED under the fix, 9
    # Re-derived after #624 began paying the source lot's real units: stones 4 produces median 23
    # with five of nine samples under the 24-unit floor; stones 5 clears. The former weight 29 was
    # compensating for 288 stone copies the world discarded. Return those 24 points to juice; core's
    # missable-location reserve trims useful tail picks only on the small seeds that need the room.
    # #843 widens the grantable catalog with the 15 crafted-only Hefty Pots and six perfume goods.
    # That changes the deterministic filler draw and puts stones 5 back below the same measured
    # early +3 floor (median 23, six of nine under 24), so one juice point returns to stones. Two
    # further juice points fund the new perfume share; total recipe weight remains 103.
    default = {"juice": 63, "stones": 6, "somber_stones": 6, "runes": 10,
               "throwables": 6, "pots": 4, "greases": 3, "foods": 2, "boluses": 1,
               "perfumes": 2}


@register
class FillerCurationFeature(Feature):
    name = "filler_curation"
    OPTIONS = {"curated_filler": CuratedFiller}
    # No NEW item names beyond the catalog pots (registered by core). Pure in-pool swap from
    # core.create_items via curate(); the STACK quantities go out as itemCounts from _base_slot_data.


def _is_junk_consumable(name):
    """A filler good that is throwaway junk -- NOT the tuned economy, NOT protected funny junk, and
    (2026-07-28) NOT A KEY ITEM.

    THE BUG THIS CLOSES. The predicate was "carries the GOODS FullID nibble (0x4)", which is a claim
    about an ID RANGE, not about junk -- and in Elden Ring every key item is a Goods item. So the
    allocator was free to overwrite key items, and it did: `pool_builder_scope` is FROZEN to
    `all_filler`, the default curated_filler recipe carries no `junk` weight, and therefore a
    displaceable slot is overwritten except for rounding residue. Measured on main 2026-07-28: BOTH
    `Cursemark of Death` copies are gone from the pool in essentially every seed -- and that item is
    what Fia's Deathbed Dream (i.e. the Lichdragon Fortissax fight) is gated on. A player reported
    exactly that on 2026-07-27: no Cursemark anywhere in a three-world spoiler log, and a region Lock
    stranded behind Fortissax. Rusty Key, Storeroom Key, Well Depths Key, Drawing-Room Key, Prayer
    Room Key, Pureblood Knight's Medal and the Dectus/Rold/Haligtree medallion halves were in the
    same position; the ones features/legacy_key_gates promotes to progression were saved by
    `displaceable_filler`'s classification check, the rest by nothing.

    The game ships the datum and gen_data already reads this param for FILLER_POOL:
    EquipParamGoods.goodsType (1 = KEY ITEM, 3 = remembrance, ...) -- unioned with the vanilla items of
    our own KeyItem-tagged checks, because the param does not file single-use travel items as key
    items and our model does (see _gate_key_items). Both sources are generated; the name lists above
    stay as a SECOND layer for what neither can separate (funny junk, the presence-floor roster)
    rather than as the only layer.

    🛑 INERT WITHOUT A REGEN. A pre-regen item_ids.py has no KEY_ITEM_GOODS, the set is empty, and
    this predicate is exactly the old one -- key items displaceable again. That is why
    tests/test_gf_quest_gated_boss_arenas.py asserts the set is PRESENT and non-empty instead of
    asserting a behaviour that silently degrades to the bug.
    """
    if name in FUNNY_JUNK or name in PRESENCE_FLOOR_ITEMS or any(s in name for s in _ECONOMY_SUBSTR):
        return False
    if name in _KEY_ITEM_GOODS:
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
