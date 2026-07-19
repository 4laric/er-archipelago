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
from ..registry import Feature, register
from .. import contract
from ..region_spine import REGION_PARENT

try:
    from ..region_graces import REGION_GRACE_POINTS
except Exception:  # not yet generated
    REGION_GRACE_POINTS = {}

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


def bundle_withheld(world, region):
    """True when `region`'s grace bundle must NOT be granted on region-open this seed. Only gated
    children (REGION_PARENT) can be withheld; a child with no WALL_ARMED entry is withheld
    unconditionally (fail closed -- never grant past a wall because someone forgot the pairing;
    test_gf_gated_children turns that omission into a red test)."""
    if region not in REGION_PARENT:
        return False
    armed = WALL_ARMED.get(region)
    return True if armed is None else bool(armed(world))


@register
class RegionGracesFeature(Feature):
    name = "region_graces"

    def slot_data(self, world):
        kept = set(world._kept())
        region_graces = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            # bundle: the lock lights the region's whole grace set -- unless the region is a gated
            # child with its wall armed, whose bundle is withheld (module docstring). [] and not
            # key-absence: the client warns about a genuine lock with NO regionGraces entry, and
            # this one is intended.
            region_graces[f"{r} Lock"] = [] if bundle_withheld(world, r) else list(fs)
        return {contract.REGION_GRACES: region_graces}
