"""Region grace lighting + GRACE GATES.

BASE behavior (non-optional): receiving a region's Lock lights that region's grace warp flags so the
player can warp in (BUNDLE: a lock lights ALL of the region's graces). Region-keyed, matt-free.
REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated from grace_flags.tsv
(gen_data.py) with _BOSS_GATED_GRACE_FLAGS / _ARENA_GRACE_FLAGS already excluded, so a lit grace is
always a real, physically-present warp point (never a sealed boss arena). Region Locks stay the sole
progression, so any seed is winnable by construction.

GRACE GATES (opt-in-by-default; the client half of the legacy_key_gates / leyndell_gate features).
Region-spine v2 made Raya Lucaria Academy and Leyndell first-class regions, so the gates no longer
pull graces out of a PARENT's bundle -- they re-key the gated region's OWN bundle, mirroring the
vanilla "you cannot walk in without the key" on top of the region Lock:
  * Raya Lucaria Academy graces (m14 == flags 714xx) -> keyed on the "Academy Glintstone Key" ITEM
    in regionGraces INSTEAD of the region's Lock, so warping in needs the key exactly like walking
    in does (active iff legacy_dungeon_keys armed the key this seed -- world.gf_legacy_keys; the
    AP-side rule in legacy_key_gates keeps fill honest about it).
  * Leyndell capital graces (m11 == flags 711xx, minus the 71190 Roundtable/HUB grace) -> moved to
    runeGatedGraces {str(N): [graces]} + greatRuneItemIds, so the client lights them once >= N Great
    Runes are received (N = leyndell_runes_required, clamped -- world.gf_leyndell_runes).
    The m35 Shunning-Grounds graces used to ride this gate (they leaked into the ALTUS bundle,
    in-game 2026-07-10); m35 is the SEWER region now, with its own Lock-keyed bundle, so the rune
    gate holds the capital only.
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

# Grace flag -> map encoding: 7<MM><nn>. Raya Lucaria = m14 (714xx); the Leyndell capital = m11
# (Royal, 711xx). m35 (Shunning-Grounds, 735xx) rode the rune gate while it was folded into Altus;
# it is the Sewer region now and its bundle is Lock-keyed like any other region's. (m19 Fractured
# Marika is an arena grace excluded from the bundle upstream, so it needs no entry here.)
_RAYA_GRACE_LO, _RAYA_GRACE_HI = 71400, 71500
_LEYNDELL_GRACE_LO, _LEYNDELL_GRACE_HI = 71100, 71200          # m11 Leyndell Royal
_ROUNDTABLE_GRACE = 71190  # HUB grace (start_grace); an m11 flag but NOT a Leyndell-capital grace.
_ACADEMY_KEY = "Academy Glintstone Key"


def _in(flag, lo, hi):
    return lo <= flag < hi


def _is_capital_grace(g):
    """A capital grace the Great-Rune gate must hold: m11 Leyndell Royal, minus the 71190
    Roundtable HUB grace. Mirrors leyndell_gate's CHECK set (m11/m19 prefixes over the goal
    region)."""
    return _in(g, _LEYNDELL_GRACE_LO, _LEYNDELL_GRACE_HI) and g != _ROUNDTABLE_GRACE


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

        # --- GATE 1: Raya Lucaria Academy behind the Academy Glintstone Key. Active iff
        # legacy_dungeon_keys armed the key this seed (world.gf_legacy_keys, set in
        # legacy_key_gates.generate_early). Re-key the region's 714xx graces on the item.
        if _ACADEMY_KEY in getattr(world, "gf_legacy_keys", ()) and _ACADEMY_KEY in ITEM_CATALOG:
            academy = "Raya Lucaria Academy Lock"   # its OWN region since region-spine v2
            bundle = region_graces.get(academy)
            if bundle:
                raya = [g for g in bundle if _in(g, _RAYA_GRACE_LO, _RAYA_GRACE_HI)]
                if raya:
                    region_graces[academy] = [g for g in bundle if g not in raya]
                    # add (not overwrite) -- an item could legitimately carry graces from >1 gate.
                    region_graces[_ACADEMY_KEY] = sorted(set(region_graces.get(_ACADEMY_KEY, [])) | set(raya))

        # --- GATE 2: the Leyndell capital behind N Great Runes. Active iff leyndell_gate picked N
        # runes this seed (world.gf_leyndell_runes). Pull the capital graces (711xx minus the 71190
        # HUB grace) out of Leyndell's own bundle; the client lights them at >= N runes.
        need = len(getattr(world, "gf_leyndell_runes", ()) or ())
        if need > 0:
            leyndell = "Leyndell Lock"              # its OWN region since region-spine v2
            bundle = region_graces.get(leyndell)
            if bundle:
                leyn = [g for g in bundle if _is_capital_grace(g)]
                if leyn:
                    region_graces[leyndell] = [g for g in bundle if g not in leyn]
                    out[contract.RUNE_GATED_GRACES] = {str(need): sorted(leyn)}
                    rune_ids = sorted(ITEM_CATALOG[n] for n in ITEM_CATALOG if n.endswith("Great Rune"))
                    out[contract.GREAT_RUNE_ITEM_IDS] = rune_ids

        out[contract.REGION_GRACES] = region_graces
        return out
