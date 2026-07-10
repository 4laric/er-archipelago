"""Region grace lighting + GRACE GATES.

BASE behavior (non-optional): receiving a region's Lock lights that region's grace warp flags so the
player can warp in (BUNDLE: a lock lights ALL of the region's graces). Region-keyed, matt-free.
REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated from grace_flags.tsv
(gen_data.py) with _BOSS_GATED_GRACE_FLAGS / _ARENA_GRACE_FLAGS already excluded, so a lit grace is
always a real, physically-present warp point (never a sealed boss arena). Region Locks stay the sole
progression, so any seed is winnable by construction.

GRACE GATES (opt-in-by-default; the client half of the legacy_key_gates / leyndell_gate features).
Some regions were folded from separate maps that vanilla gates behind a KEY: Raya Lucaria Academy
(m14, folded into Liurnia) needs the Academy Glintstone Key; the Leyndell capital (m11, folded into
Altus) needs Great Runes. The coarse region-lock model opens the whole folded region on one Lock, so
without a gate those sub-area graces light on the region Lock and the player can WARP straight in,
bypassing the key. These gates PULL the sub-area's graces out of the region-Lock bundle and re-key
them on the gating condition:
  * Raya Lucaria graces (m14 == flags 714xx) -> keyed on the "Academy Glintstone Key" ITEM in
    regionGraces, so they light when the key is received (active iff legacy_dungeon_keys armed the
    Academy Glintstone Key this seed -- world.gf_legacy_keys).
  * Leyndell capital graces (m11 == flags 711xx, minus the 71190 Roundtable/HUB grace) -> moved to
    runeGatedGraces {str(N): [graces]} + greatRuneItemIds, so the client lights them once >= N Great
    Runes are received (N = leyndell_runes_required, clamped -- world.gf_leyndell_runes).
Both degrade safely: with the gate off (or the region not kept) the graces stay in the region bundle
exactly as before; region Locks remain the only progression, so winnability is unaffected either way.

Client contract (see handoff/GRACE_GATES_CLIENT_SPEC.md):
  regionGraces (region.rs): {item_name: [grace_flag,...]} -- light on receipt of ANY keyed item
    (Locks AND key items like "Academy Glintstone Key"). NEW: keys are no longer only "<Region> Lock".
  runeGatedGraces + greatRuneItemIds (region.rs, NEW): light {N: graces} once >= N of greatRuneItemIds
    have been received.
"""
from ..registry import Feature, register
from .. import contract

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}
try:
    from ..item_ids import ITEM_CATALOG
except Exception:
    ITEM_CATALOG = {}

# Grace flag -> map encoding: 71<MM><nn>. Raya Lucaria = m14 (714xx); Leyndell capital = m11 (711xx).
_RAYA_GRACE_LO, _RAYA_GRACE_HI = 71400, 71500
_LEYNDELL_GRACE_LO, _LEYNDELL_GRACE_HI = 71100, 71200
_ROUNDTABLE_GRACE = 71190  # HUB grace (start_grace); an m11 flag but NOT a Leyndell-capital grace.
_ACADEMY_KEY = "Academy Glintstone Key"


def _in(flag, lo, hi):
    return lo <= flag < hi


@register
class RegionGracesFeature(Feature):
    name = "region_graces"

    def slot_data(self, world):
        kept = set(world._kept())
        region_graces = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            # bundle: the lock lights the region's whole grace set.
            region_graces[f"{r} Lock"] = list(fs)

        out = {}

        # --- GATE 1: Raya Lucaria (m14, folded into Liurnia) behind the Academy Glintstone Key. ---
        # Active iff legacy_dungeon_keys armed the key this seed (world.gf_legacy_keys, set in
        # legacy_key_gates.generate_early). Pull 714xx out of the Liurnia bundle, re-key on the item.
        if _ACADEMY_KEY in getattr(world, "gf_legacy_keys", ()) and _ACADEMY_KEY in ITEM_CATALOG:
            liurnia = "Liurnia of the Lakes Lock"
            bundle = region_graces.get(liurnia)
            if bundle:
                raya = [g for g in bundle if _in(g, _RAYA_GRACE_LO, _RAYA_GRACE_HI)]
                if raya:
                    region_graces[liurnia] = [g for g in bundle if g not in raya]
                    # add (not overwrite) -- an item could legitimately carry graces from >1 gate.
                    region_graces[_ACADEMY_KEY] = sorted(set(region_graces.get(_ACADEMY_KEY, [])) | set(raya))

        # --- GATE 2: Leyndell capital (m11, folded into Altus) behind N Great Runes. ---
        # Active iff leyndell_gate picked N runes this seed (world.gf_leyndell_runes). Pull 711xx (minus
        # the 71190 HUB grace) out of the Altus bundle and emit them as a rune-count-gated set.
        need = len(getattr(world, "gf_leyndell_runes", ()) or ())
        if need > 0:
            altus = "Altus Plateau Lock"
            bundle = region_graces.get(altus)
            if bundle:
                leyn = [g for g in bundle
                        if _in(g, _LEYNDELL_GRACE_LO, _LEYNDELL_GRACE_HI) and g != _ROUNDTABLE_GRACE]
                if leyn:
                    region_graces[altus] = [g for g in bundle if g not in leyn]
                    out[contract.RUNE_GATED_GRACES] = {str(need): sorted(leyn)}
                    rune_ids = sorted(ITEM_CATALOG[n] for n in ITEM_CATALOG if n.endswith("Great Rune"))
                    out[contract.GREAT_RUNE_ITEM_IDS] = rune_ids

        out[contract.REGION_GRACES] = region_graces
        return out
