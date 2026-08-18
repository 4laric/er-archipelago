"""Count-neutral tight-pool compaction (world#849).

Exact duplicate weapon names add no choice: receiving the second copy is the same base weapon row.
The two multiplayer disguise mirrors and Sacrificial Twig likewise spend scarce small-seed slots
without contributing to the intended progression/equipment spread. Replacing those copies with the
ordinary filler sentinel preserves one item per location and gives the shared filler allocator the
vacated economy capacity.

Vanilla placement deliberately does not call this helper: that mode promises the base-game pairing.
"""
from typing import Optional, Set

try:
    from ..item_tiers import ITEM_TIER_CATEGORY
except Exception:
    ITEM_TIER_CATEGORY = {}
try:
    from ..item_ids import ARMOR_NAME_TO_BUNDLE
except Exception:
    ARMOR_NAME_TO_BUNDLE = {}


CUT_NAMES = frozenset({
    "Furled Finger's Trick-Mirror",
    "Host's Trick-Mirror",
    "Sacrificial Twig",
})


def compact_name(name: Optional[str], seen_weapons: Set[str],
                 seen_armor_bundles: Optional[Set[str]] = None) -> Optional[str]:
    """Return ``None`` when this vanilla pool copy should pay normal filler instead.

    The first copy of an exact weapon name survives; later copies do not. Classification comes from
    the generated param/catalog join rather than spelling or an id range.
    """
    if name is None or name in CUT_NAMES:
        return None
    bundle = ARMOR_NAME_TO_BUNDLE.get(name)
    if bundle is not None and seen_armor_bundles is not None:
        if bundle in seen_armor_bundles:
            return None
        seen_armor_bundles.add(bundle)
        return bundle
    if ITEM_TIER_CATEGORY.get(name) == "WEAPON":
        if name in seen_weapons:
            return None
        seen_weapons.add(name)
    return name
