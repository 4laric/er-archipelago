"""SPEC-PARITY Phase 6 -- grace rando (freebie + scatter, v3).

Region-keyed, matt-free. REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated
from grace_flags.tsv. The GraceRando option:
  ON  (default, FREEBIE + SCATTER): receiving a region lock lights ONE grace (the front-door, the
      first flag) so you can warp in; the region's OTHER graces become in-region AP items
      ("Grace: <region> #k") that light their specific grace flag when received. Count-neutral --
      each scatter item displaces a Rune. Client contract (region.rs tick_grace_items): graceItems
      is {item_name: grace_flag}; receiving an item whose name is in the set sets that flag.
  OFF (BUNDLE): a lock lights ALL of that region's graces on receipt; no scatter items.
Scatter items are filler (convenience only) -- region Locks stay the sole progression, so winnable.
"""
from BaseClasses import ItemClassification
from Options import DefaultOnToggle
from ..registry import Feature, register
from .. import contract

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}


def _scatter_name(region: str, k: int) -> str:
    return f"Grace: {region} #{k}"


class GraceRando(DefaultOnToggle):
    """On (freebie+scatter): a region lock lights one grace (front door) to warp in; the rest become
    in-region 'Grace: ...' item drops. Off (bundle): a lock lights all of the region's graces."""
    display_name = "Grace Rando"


@register
class GraceRandoFeature(Feature):
    name = "grace_rando"
    # one scatter item per non-front-door grace, across ALL regions (ids allocate once at import;
    # per-seed kept-scoping happens in create_items / slot_data). Filler = convenience only.
    ITEMS = {_scatter_name(r, k): ItemClassification.filler
             for r, fs in REGION_GRACE_POINTS.items() for k in range(1, len(fs))}
    OPTIONS = {"grace_rando": GraceRando}

    def create_items(self, world):
        # attunement gate: the scatter graces fold into the bloom (client-lit on attunement),
        # NOT the pool -- so mint no scatter items (freed slots become filler, count-neutral).
        if getattr(world, "gf_attunement", None) is not None:
            return []
        if not world.options.grace_rando.value:      # bundle mode: no scatter items
            return []
        kept = set(world._kept())
        return [world.create_item(_scatter_name(r, k))
                for r in REGION_GRACE_POINTS if r in kept
                for k in range(1, len(REGION_GRACE_POINTS[r]))]

    def slot_data(self, world):
        kept = set(world._kept())
        att = getattr(world, "gf_attunement", None)   # attunement plan, or None when the gate is off
        freebie = bool(world.options.grace_rando.value)
        region_graces, grace_items = {}, {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            if att is not None:
                # attunement gate: the lock lights ONLY the K seeded random-start graces; the
                # region's remaining graces bloom on attunement (regionAttunement.bloom_flags).
                # No scatter items -- create_items mints none under the gate.
                region_graces[f"{r} Lock"] = list(att.get(r, {}).get("region_lit", [fs[0]]))
            elif freebie:
                region_graces[f"{r} Lock"] = [fs[0]]
                for k in range(1, len(fs)):
                    grace_items[_scatter_name(r, k)] = fs[k]
            else:
                region_graces[f"{r} Lock"] = list(fs)
        return {contract.REGION_GRACES: region_graces, contract.GRACE_ITEMS: grace_items}
