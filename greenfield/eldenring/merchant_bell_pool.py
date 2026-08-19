"""Seed-time merchant Bell Bearing pool eligibility (#560).

The generated table maps a bell's game FullID to the AP regions where its physical merchant stands.
A bell whose merchants are all sealed opens a wholly vanilla Twin-Maiden menu, so it pays ordinary
filler instead. Bells absent from the table are release-only/non-merchant bells and remain unchanged.
"""
try:
    from .item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}

try:
    from .shop_data import MERCHANT_BELL_REGIONS
except Exception:
    MERCHANT_BELL_REGIONS = {}


def merchant_bell_pool_allowed(name, kept_regions, item_catalog=None, bell_regions=None):
    """True unless `name` is a mapped merchant bell with no merchant in `kept_regions`.

    Empty mapped regions fail closed. An unmapped item is not one of the menu-opening merchant
    bells this rule owns (notably the release-only peddler/miner bells), so it passes unchanged.
    Arguments are injectable to keep the policy AP-free and directly testable.
    """
    catalog = ITEM_CATALOG if item_catalog is None else item_catalog
    regions = MERCHANT_BELL_REGIONS if bell_regions is None else bell_regions
    full_id = catalog.get(name)
    if full_id not in regions:
        return True
    return bool(frozenset(regions[full_id]) & frozenset(kept_regions or ()))
