"""Region grace lighting -- a region Lock lights the region's grace warp flags, EXCEPT past a wall.

BASE behavior (non-optional): receiving a region's Lock lights that region's grace warp flags so the
player can warp in (BUNDLE: a lock lights ALL of the region's graces). Region-keyed, matt-free.
REGION_GRACE_POINTS (all warp graces per major region, sorted) is generated from grace_flags.tsv
(gen_data.py) with _BOSS_GATED_GRACE_FLAGS / _ARENA_GRACE_FLAGS already excluded, so a lit grace is
always a real, physically-present warp point (never a sealed boss arena). Region Locks stay the sole
progression, so any seed is winnable by construction.

GATED CHILDREN are the exception (region_spine.REGION_PARENT: Raya Lucaria Academy, Leyndell, Sewer).
Each sits behind a wall the GAME already enforces -- the Academy seal wants the Academy Glintstone
Key, the capital main gate wants Great Runes, and the Sewer is entered down a well inside the capital.
Granting such a region's bundle hands the player a warp target on the FAR side of that wall: the
2026-07-14 playtest opened on Altus and was handed East Capital Rampart (71102, BonfireWarpParam
110002), a free walk into Leyndell past the 2-rune gate, and the run ended at Morgott. So while the
wall is ARMED IN LOGIC, the child's bundle is WITHHELD -- emitted as an EMPTY list, never granted.
The player walks in from the parent the vanilla way (key / runes in hand; the client's key-item
grants make the game's own gate open) and touches the graces themselves; a touched grace is the
vanilla warp unlock and persists in the save. The empty list is deliberate contract shape: the
client logs "graces: 0 requested" for a lock with an empty bundle but WARNS about a lock with a
MISSING one (region.rs), and this is intent, not drift. Reachability honesty is the other half of
the same fix: core.create_regions parents the child's AP region under REGION_PARENT, so AP logic
knows the child's checks need the whole ancestor Lock chain.

ARMED IN LOGIC is load-bearing, not a hedge. The game's wall is FIXED (the capital always wants 2
runes) but the LOGIC gate is optional -- and when the gate is disarmed (leyndell_runes_required: 0,
or no rune survives the seed's kept set), fill no longer guarantees the wall's key reachable, so
withholding the bundle would leave the child physically unwinnable while logic reads green. Disarmed
gate -> the bundle is GRANTED, i.e. the warp deliberately bypasses the game's wall, which is the only
honest reading of "0 disables the gate". WALL_ARMED below pairs every REGION_PARENT child with its
arming predicate; an unpaired child withholds unconditionally (never grant past a wall by default)
and test_gf_gated_children fails until the pairing is written down. The Sewer has no predicate to
consult: its wall is containment itself (parent access), always sound to withhold because the parent
chain is exactly what the region graph requires.

This RETIRES the two half-shipped grace gates that used to live here:
  * runeGatedGraces / greatRuneItemIds ("light the capital graces at >= N received runes") is no
    longer emitted. Its client half was NEVER built -- the key appears in contract_gen.rs and in no
    consumer, verified over the client repo's full history -- so with the gate armed the capital
    graces could never light at all, and with it disarmed the whole capital bundle rode the Leyndell
    Lock straight past the wall. Both failure modes end here; contract.py tags both keys DEAD.
  * the Academy-key re-key (Raya graces lighting on "Academy Glintstone Key" receipt) is gone the
    same way -- the key opens the Academy's own seal in-game; warping in for free was the same
    past-the-wall grant one wall shallower.

Client contract: regionGraces (region.rs) {item_name: [grace_flag,...]} -- light on receipt of ANY
keyed item. Keys are region Locks; a gated child's Lock maps to [] while its wall is armed.
"""
from Options import Choice

from ..registry import Feature, register
from .. import contract
from ..region_spine import REGION_PARENT

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}
try:
    from ..region_graces import REGION_GRACE_LANDMARKS
except ImportError:      # table predates the landmarks tier -- see _bundle_for()
    REGION_GRACE_LANDMARKS = {}

# Gated child -> "is its wall armed in logic this seed?". Reads the state the gate features publish
# in generate_early (leyndell_gate.gf_leyndell_runes, legacy_key_gates.gf_legacy_keys), so the
# bundle decision and the fill rules can never disagree. Sewer: containment wall, always armed.
WALL_ARMED = {
    "Raya Lucaria Academy":
        lambda world: "Academy Glintstone Key" in getattr(world, "gf_legacy_keys", ()),
    "Leyndell":
        lambda world: bool(getattr(world, "gf_leyndell_runes", ())),
    "Sewer":
        lambda world: True,
    # Scaduview's wall was REMOVED 2026-07-19: the Hinterland was folded into Shadow Keep, so it is no
    # longer a gated child with a bundle to withhold -- its graces ride the Keep's own bundle.
}


def _grace_tier(world):
    """This seed's grace tier: "all" | "landmarks" | "entrance"."""
    opt = getattr(getattr(world, "options", None), "region_grace_unlock", None)
    return getattr(opt, "current_key", None) or "all"


def _bundle_for(region, flags, tier):
    """The warp graces a region's unlock lights, at `tier`. `flags` is the full set, non-empty."""
    if tier == "entrance":
        return [entrance_grace(flags)]
    if tier == "landmarks":
        picks = [f for f in REGION_GRACE_LANDMARKS.get(region, ()) if f in flags]
        # An absent/stale landmarks table must not silently degrade to a thinner OR fatter bundle:
        # fall back to the entrance (the one answer we can always derive here) and say so.
        if not picks:
            return [entrance_grace(flags)]
        return sorted(picks)
    return list(flags)


def bundle_withheld(world, region):
    """True when `region`'s grace bundle must NOT be granted on region-open this seed. Only gated
    children (REGION_PARENT) can be withheld; a child with no WALL_ARMED entry is withheld
    unconditionally (fail closed -- never grant past a wall because someone forgot the pairing;
    test_gf_gated_children turns that omission into a red test)."""
    if region not in REGION_PARENT:
        return False
    armed = WALL_ARMED.get(region)
    return True if armed is None else bool(armed(world))


# ---- entrance-grace derivation -----------------------------------------------------------------
# Warp-grace flags fall in blocks the game itself assigns: 71xxx legacy dungeon, 72xxx DLC legacy,
# 73xxx cave/catacomb/tunnel, 76xxx OVERWORLD site-of-grace. The overworld block is numbered in
# designer order per region (Limgrave 761xx, Liurnia 762xx, Altus 763xx, Caelid 764xx...), so its
# lowest member is the region's front door. An interior-only region (Stormveil, Leyndell, Haligtree,
# the rivers) has no 76xxx member at all, and there its lowest flag IS the entrance.
#
# 🛑 WHY NOT THE OBVIOUS TABLES. Two nearby ones look right and are not:
#   * `region_open_flags.REGION_OPEN_FLAGS` is one flag per region and equals REGION_GRACE_POINTS[r][0]
#     for 27 of the 30 -- the three gated children (Leyndell, Raya Lucaria Academy, Sewer) carry a
#     SYNTHETIC 7698x flag instead, precisely so that setting it cannot light a warp target past the
#     wall this module withholds the bundle for (#278; gen_data._GATED_CHILD_OPEN_FLAGS) --
#     but it is a region-OPEN DETECTION anchor, and it resolves to cave interiors
#     (Limgrave -> Murkwater Cave, Liurnia -> Raya Lucaria Crystal Tunnel, Caelid -> Gael Tunnel).
#     Granting those as "the grace at the start of the region" is worse than granting all of them.
#   * `BonfireWarpParam.bonfireSubCategorySortId` is a real ordering, but it sorts within the WARP
#     MENU's 55 subcategories, not our 30 regions -- a region spans several, so the minimum TIES in
#     12 of 30 regions. Wrong arity, the same trap as [tiles span regions].
# Verified by NAME over all 30 regions (BonfireWarpParam.textId1 -> PlaceName, 351/351 resolve):
# Liurnia -> Lake-Facing Cliffs, Weeping -> Church of Pilgrimage, Limgrave -> Church of Elleh,
# Stormveil -> Gateside Chamber, Leyndell -> East Capital Rampart. test_gf_grace_entrance pins them.
_OVERWORLD_LO, _OVERWORLD_HI = 76000, 77000


def entrance_grace(flags):
    """The one warp grace that IS the way into a region. `flags` must be non-empty."""
    if not flags:
        raise ValueError("entrance_grace() on an empty grace set -- callers must skip empty regions")
    overworld = [f for f in flags if _OVERWORLD_LO <= f < _OVERWORLD_HI]
    return min(overworld) if overworld else min(flags)


class RegionGraceUnlock(Choice):
    """How many of a region's Sites of Grace a region unlock hands you.

    all (default) -- every warp grace in the region, so you can fast-travel anywhere in it at once.
    Liurnia lights 59 at once, Caelid 38, Limgrave 28, which is what makes a region you have never
    walked read as already-explored.
    landmarks -- one per sub-area, using the warp menu's OWN grouping (Liurnia resolves to
    Lake-Facing Cliffs, East Raya Lucaria Gate, Moonlight Altar and Ruin-Strewn Precipice). 50 across
    the map. A middle setting: you can still cross a big region in a couple of hops.
    entrance -- only the region's front door; you walk to and touch the rest yourself, the vanilla way.

    🛑 This cannot make a seed unwinnable and does not move an item: Region Locks remain the only
    progression, every check stays exactly where it was, and a grace you have not been handed is
    still reachable on foot and still unlocks by touching it. It is a convenience/pacing setting.
    A region whose bundle is WITHHELD (a gated child behind an armed wall) grants nothing under
    either value -- entrance mode must never become a way past a wall.
    """
    display_name = "Region Grace Unlock"
    option_all = 0
    option_landmarks = 1
    option_entrance = 2
    default = 0                      # vanilla-to-this-apworld behaviour: no change


@register
class RegionGracesFeature(Feature):
    name = "region_graces"

    OPTIONS = {"region_grace_unlock": RegionGraceUnlock}

    def slot_data(self, world):
        kept = set(world._kept())
        tier = _grace_tier(world)
        region_graces = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            # bundle: the lock lights the region's whole grace set -- unless the region is a gated
            # child with its wall armed, whose bundle is withheld (module docstring). [] and not
            # key-absence: the client warns about a genuine lock with NO regionGraces entry, and
            # this one is intended.
            # gated child behind an armed wall: grant nothing, at every tier
            bundle = [] if bundle_withheld(world, r) else _bundle_for(r, fs, tier)
            region_graces[f"{r} Lock"] = bundle
        return {contract.REGION_GRACES: region_graces}
