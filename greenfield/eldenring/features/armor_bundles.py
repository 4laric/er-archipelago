"""Synthetic complete-armor-set items, generated from protector row families (world#849).

Option-gated since #985: `armor_bundles: off` restores the pre-#849 pool shape -- every
protector piece is its own item and no wrapper is minted. The wrapper ids stay in the catalog
either way (ITEMS is a static class attribute, resolved at import, before any option exists);
the boss_keys precedent applies: an OFF seed's pool is count-identical to an ON seed's, only
the id catalog keeps the unused wrapper names. The OFF seed emits no `armorBundles` slot_data
key and drops the `armor_bundles` client-feature demand, so an older client accepts it.

`mixed` (value 2) keeps the one-slot-per-set pool shape but shuffles which pieces arrive
together: every protector FullID is pooled by slot, shuffled per seed, and dealt back so the
i-th mixed wrapper carries the same per-slot piece counts as the i-th vanilla set (sorted
order). The client is seed-driven -- it grants whatever member list the seed sends -- so the
wire shape (LISTVAL_INT_MAP) is unchanged and no contract bump is owed.
"""
from Options import Choice
from BaseClasses import ItemClassification

from ..registry import Feature, register
from ..tables.item_ids import ARMOR_BUNDLES

# FullID slot suffixes: x456 head, x556 body, x656 arms, x756 legs. The thousands digit
# (5 = base piece, 6/7/8/9 = altered/variant of the same slot) is what varies, so
# fullid % 1000 is the slot for base and variant pieces alike.
ARMOR_SLOTS = (456, 556, 656, 756)


def mixed_set_name(k):
    """The k-th (1-based) shuffled wrapper name. The single spelling both the feature's ITEMS
    catalog and core's pool-compaction remap read, so the two cannot drift."""
    return "Mixed Armor Set %d" % k


# One shuffled wrapper per vanilla set, in deal order: wrapper i carries the shape of the i-th
# vanilla set in sorted order (see build_mixed_sets). Static, like ARMOR_BUNDLES itself -- both
# name families live in the ITEMS catalog regardless of option.
MIXED_ARMOR_SETS = [mixed_set_name(k) for k in range(1, len(ARMOR_BUNDLES) + 1)]


def armor_slot(fullid):
    """Which protector slot a FullID belongs to (456/556/656/756)."""
    return fullid % 1000


def is_bundle_name(name):
    """Whether `name` is a vanilla wrapper ("... Set"). Core's pool walk asks this (it may not
    import the generated table itself, #1464) to decide what the encounter-order remap applies
    to: only a wrapper name compact_name just minted, never a vanilla piece or filler."""
    return name in ARMOR_BUNDLES


def build_mixed_sets(rng):
    """Deal every armor FullID into the mixed wrappers, deterministically for the seed.

    Pools member FullIDs by slot across all vanilla sets, shuffles each slot pool with `rng`
    (the world's own random -- deterministic per seed), and deals wrapper i the same per-slot
    piece counts as the i-th vanilla set in sorted order. Every one of the 600 FullIDs appears
    exactly once across the mixed wrappers. Pure: takes the rng, touches nothing else.
    """
    pools = {slot: [] for slot in ARMOR_SLOTS}
    for name in sorted(ARMOR_BUNDLES):
        for full in ARMOR_BUNDLES[name]:
            pools[armor_slot(full)].append(full)
    for slot in ARMOR_SLOTS:
        pools[slot].sort()
        rng.shuffle(pools[slot])
    out = {}
    for i, name in enumerate(sorted(ARMOR_BUNDLES)):
        want = [armor_slot(full) for full in ARMOR_BUNDLES[name]]
        out[mixed_set_name(i + 1)] = [pools[slot].pop() for slot in want]
    return out


def remap_bundle(bundle, mapping):
    """Map a vanilla wrapper name to its mixed wrapper, in encounter order.

    The k-th distinct vanilla set the pool walk encounters pays "Mixed Armor Set k" -- so the
    pool carries one mixed wrapper per distinct family it would otherwise have carried, and the
    count is identical across off/sets/mixed. `mapping` is owned by the caller (core.create_items
    threads one dict through every compaction site); mutating it here keeps all three sites on
    the same encounter order.
    """
    if bundle not in mapping:
        mapping[bundle] = mixed_set_name(len(mapping) + 1)
    return mapping[bundle]


class ArmorBundles(Choice):
    """How armor sets arrive: as one whole-set item, or piece by piece.

    Set items grant every piece; the other pieces' checks pay other items. sets and mixed
    need an up-to-date client; older ones refuse the seed. Ignored by Vanilla Placement.
    sets: one item per armor set, holding its matching pieces (default)
    mixed: one item per set, holding random pieces from any set
    off: every helm, chest, gauntlet and greave is its own item
    """
    display_name = "Armor Set Bundling"
    option_off = 0
    option_sets = 1
    option_mixed = 2
    # The Toggle this was before mixed landed: yamls in the wild say `armor_bundles: true`.
    # AP's Choice.from_any tests `type(data) == int`, and `type(True)` is `bool`, NOT int -- so
    # a bare yaml boolean falls through to from_text("True") and needs these aliases to resolve
    # at all (the NoEquipLoad precedent in features/body_tuning.py). `true` maps to sets because
    # sets is what `true` has always meant. ("false" needs no alias: AP auto-aliases it from
    # `off`, but it is listed anyway so the mapping reads in one place.)
    # 🛑 NOT `option_random`. Archipelago RESERVES "random" on every Choice as the built-in
    # meta-value that rolls the option itself (Options.py asserts at class-creation time), so the
    # shuffled mode is spelled `mixed` in yaml; `is_random` is still its predicate's name.
    alias_true = 1
    alias_false = 0
    alias_on = 1
    alias_off = 0
    default = 1


def armor_bundles_on(world):
    o = getattr(world.options, "armor_bundles", None)
    return True if o is None else bool(o.value)


def is_random(world):
    o = getattr(world.options, "armor_bundles", None)
    return False if o is None else int(o.value) == ArmorBundles.option_mixed


@register
class ArmorBundlesFeature(Feature):
    name = "armor_bundles"
    OPTIONS = {"armor_bundles": ArmorBundles}
    ITEMS = {name: ItemClassification.useful for name in list(ARMOR_BUNDLES) + MIXED_ARMOR_SETS}

    def generate_early(self, world) -> None:
        # The per-seed shuffle. Drawn here (not in slot_data) so the pool walk in create_items
        # and the wire agree on one mapping, and so the tests can read it off the world.
        if is_random(world):
            world.gf_mixed_armor_sets = build_mixed_sets(world.random)

    def slot_data(self, world):
        # Vanilla/off seeds never mint wrappers and therefore require no newer client.
        from . import vanilla_placement
        if not armor_bundles_on(world) or not world._shuffle_on() or vanilla_placement.is_on(world):
            return {}
        if is_random(world):
            mixed = getattr(world, "gf_mixed_armor_sets", None) or {}
            return {
                "armorBundles": {
                    str(world.item_name_to_id[name]): members
                    for name, members in mixed.items()
                },
                "requiresClientFeatures": ["armor_bundles"],
            }
        return {
            "armorBundles": {
                str(world.item_name_to_id[name]): members
                for name, members in sorted(ARMOR_BUNDLES.items())
            },
            "requiresClientFeatures": ["armor_bundles"],
        }
