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
    🛑 SUPERSEDED 2026-08-16, and the retirement argument does NOT carry to what replaced it. That
    re-key fired on the KEY ALONE, so it granted a warp to a player who might not hold the region
    Lock: genuinely past the wall. The ruling now is that there is no wall -- the Academy Glintstone
    Key gate was removed from features/legacy_key_gates entirely (bobler + Alaric, "have the minted
    Academy Lock be the thing that grants all the graces"), so WALL_ARMED's Raya predicate is False
    in every seed and the bundle rides the Lock like any ungated region's. Nothing is granted on a
    key receipt; the Lock is the only permission, and holding it is the whole entitlement.

Client contract: regionGraces (region.rs) {item_name: [grace_flag,...]} -- light on receipt of ANY
keyed item. Keys are region Locks; a gated child's Lock maps to [] while its wall is armed.
"""
from Options import Choice, Range

from ..registry import Feature, register
from . import vanilla_placement as _vp
from .. import contract
from ..region_spine import REGION_PARENT
from ..region_open_flags import REGION_OPEN_FLAGS
from ..data import FINALE_REGION as _FINALE_REGION

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
    # 🛑 FALSE IN EVERY SEED SINCE 2026-08-16, and deliberately expressed this way rather than as
    # `lambda world: False`. The Academy Glintstone Key was removed from legacy_key_gates._LEGACY_KEYS,
    # so it can never be in gf_legacy_keys and this wall can never arm -- but the pairing has to STAY,
    # because bundle_withheld withholds UNCONDITIONALLY for a REGION_PARENT child with no entry.
    # Written as the live predicate so that restoring the key gate restores the wall in one edit.
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


# Logical regions are usually one connected traversal space, but Ainsel River is not. Its lower
# well and its Nokstella/Lake of Rot half have no walkable edge between them. A single "entrance"
# therefore makes one half unreachable while AP logic exposes checks in both. Keep one safe anchor
# per disconnected component (#806); 71218 is Grand Cloister, beside the coffin route into Astel,
# while 71211 preserves lower Ainsel. Lake of Rot Shoreside (71216) is not the Astel handoff: the
# live map witness places the required anchor at Grand Cloister.
_ENTRANCE_COMPONENT_GRACES = {
    "Ainsel River": [71211, 71218],
}


def _bundle_for(region, flags, tier):
    """The warp graces a region's unlock lights, at `tier`. `flags` is the full set, non-empty."""
    if tier == "entrance":
        component_graces = _ENTRANCE_COMPONENT_GRACES.get(region)
        if component_graces is not None:
            missing = [f for f in component_graces if f not in flags]
            if missing:
                raise ValueError(f"{region}: component entrance grace(s) absent from bundle: {missing}")
            return list(component_graces)
        return [entrance_grace(flags, region)]
    if tier == "landmarks":
        picks = [f for f in REGION_GRACE_LANDMARKS.get(region, ()) if f in flags]
        # An absent/stale landmarks table must not silently degrade to a thinner OR fatter bundle:
        # fall back to the entrance (the one answer we can always derive here) and say so.
        if not picks:
            return [entrance_grace(flags, region)]
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
# Human rulings where designer order is not traversal order. A pin must remain in the region's
# emitted grace set; entrance_grace fails loudly if it goes stale.
_ENTRANCE_GRACE_PIN = {"Altus": 76301}  # Altus Plateau, at the Grand Lift; #641


def entrance_grace(flags, region=None):
    """The one warp grace that IS the way into a region. `flags` must be non-empty."""
    if not flags:
        raise ValueError("entrance_grace() on an empty grace set -- callers must skip empty regions")
    if region in _ENTRANCE_GRACE_PIN:
        pin = _ENTRANCE_GRACE_PIN[region]
        if pin not in flags:
            raise ValueError("entrance grace pin %s for %s is absent from its grace set" %
                             (pin, region))
        return pin
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
    entrance -- only the region's front door; disconnected regions receive one entry per traversal
    component, so every check AP considers open is physically reachable. You walk to and touch the
    rest yourself, the vanilla way.

    It moves no item. Region Locks remain the only progression and every check stays exactly where
    it was, so nothing here changes what your seed contains or where any of it sits. A region whose
    bundle is WITHHELD (a gated child behind an armed wall) grants nothing at any value -- no
    setting here is a way past a wall.

    🛑 THAT IS NOT THE SAME AS SAFE. The intent is that a grace you were not handed is still
    reachable on foot and still lights when you touch it. The bundles have not been walked region
    by region, though, so which ones can leave you somewhere you cannot get out of is genuinely not
    known. `all` is the setting that has been played. Treat the other two as experimental, and
    please report anything that strands you.
    """
    # WHY THE OLD "cannot make a seed unwinnable" LINE CAME DOWN (Alaric, 2026-08-13): nobody ever
    # measured it. The half about items and checks is STRUCTURAL and stays -- nothing in this option
    # touches placement, and that is readable off the code. The half about walkability was an
    # INFERENCE from "the grace is still physically there", and it was doing the work of a tested
    # claim: an unverified assertion of safety is worse in a docstring than an admission, because
    # this docstring IS the wizard tooltip, AP's own option help, and the comment in the generated
    # yaml -- three places a player reads BEFORE choosing. Restore the strong wording when someone
    # has walked the bundles, not before.
    display_name = "Region Grace Unlock"
    option_all = 0
    option_landmarks = 1
    option_entrance = 2
    default = 0                      # vanilla-to-this-apworld behaviour: no change


class GraceAttunement(Range):
    """Warp points arrive by exploring, not all at once. Unlocking a region lights ONE of its Sites
    of Grace; touch this many more and the rest light. 0 (default) keeps the current behaviour --
    a region Lock lights every grace it has.

    Regions with too few graces to reach the number are left alone entirely, so a two-grace region
    never ends up with warps it can never open. Requires a client that supports grace attunement;
    a seed using it refuses an older one rather than connecting and silently ignoring it.

    🛑 EXPERIMENTAL, and not for the reason a version number would tell you. Holding warps back
    means you walk more of the world on foot, and the grace bundles have not been walked region by
    region -- so which regions can leave you somewhere you cannot get out of is not known. It moves
    no item and no check, so your seed still contains everything it did; what is untested is
    whether you can always get to it. 0 is the setting that has been played. Please report anything
    that strands you."""
    display_name = "Grace Attunement"
    range_start = 0
    range_end = 10
    default = 0


class GraceAttunementAnchor(Choice):
    """Which Site of Grace a region hands you when it unlocks. `front_door` (default) is the
    region's own entrance, so you always arrive somewhere sensible. `random_grace` picks one of the
    region's graces instead, which can drop you deeper in and cuts more traversal -- every
    candidate is a real, physically-present warp point, so it can never strand you in a sealed
    arena. Only used when Grace Attunement is on."""
    # 🛑 NOT `option_random`. Archipelago RESERVES "random" on every Choice as the built-in
    # meta-value that rolls the option itself, and Options.py asserts at CLASS-CREATION time:
    # "Choice option 'random' cannot be manually assigned." That is an import-time crash for the
    # whole apworld, not a validation error on a seed -- so the collision is unmissable, but only
    # once something imports the module.
    display_name = "Grace Attunement Anchor"
    option_front_door = 0
    option_random_grace = 1
    default = 0


# The er-logic client_features SUPPORTED tag. Named once: a handshake whose two halves disagree
# about the spelling is worse than no handshake.
_CLIENT_FEATURE_TAG = "grace_attunement"


def _attune_split(world, region, bundle):
    """Split a region's grace bundle into (what the Lock lights now, the attunement gate).

    Returns `(bundle, None)` unchanged whenever the gate does not apply, which is the off default
    and every case below.

    🛑 SKIPPED FOR SMALL REGIONS, DELIBERATELY. The test is `touchable <= threshold`, and the
    boundary is `<=` rather than `<` for a reason: a region with EXACTLY `threshold` touchable
    graces DOES attune, but only on the very last one, and then blooms NOTHING. A banner that fires
    to grant an empty set is worse than no gate. Below the boundary it is worse still -- the region
    could never attune at all and its remaining graces would stay dark for the whole run, which
    reads as a bug rather than a setting. At threshold 4 this skips 12 of the 28 bundled regions
    and gates 16. Traversal is not the problem in a two-grace region anyway.

    🛑 A WITHHELD BUNDLE IS NEVER GATED. Gated children (REGION_PARENT: Raya Lucaria Academy,
    Leyndell, Sewer) already emit [] while their vanilla wall is armed -- there is nothing to split,
    and handing them an anchor would be the 2026-07-14 bug this module exists to prevent (a warp
    target on the far side of a wall the game enforces).

    THE ANCHOR is the region's own front door by default: REGION_OPEN_FLAGS[region], which is a
    member of the region's grace points for all 28 bundled regions (the three where it is not are
    exactly the gated children, which return above). `random_grace` picks any of them -- safe
    because REGION_GRACE_POINTS already excludes boss-gated and arena graces, so every candidate is
    a real, physically-present warp point.
    """
    threshold = int(getattr(world.options, "grace_attunement", None).value
                    if getattr(world.options, "grace_attunement", None) is not None else 0)
    if threshold <= 0 or not bundle:
        return bundle, None
    # touchable = everything except the one we are about to hand over
    if len(bundle) - 1 <= threshold:
        return bundle, None
    front = REGION_OPEN_FLAGS.get(region)
    use_random = bool(getattr(getattr(world.options, "grace_attunement_anchor", None), "value", 0))
    # 🛑 THE DRAW ONLY HAPPENS WHEN THE OPTION IS ON. Pulling from world.random on a default seed
    # would move the rng stream and change every rolled seed in existence -- the same rule
    # region_spine.compute_kept's comment enforces about its rng.sample.
    if use_random or front not in bundle:
        # 🛑🛑 MEMOISED, because fill_slot_data() IS CALLED MORE THAN ONCE. Drawing here
        # directly makes slot_data non-idempotent: the second call rolls a DIFFERENT anchor, so the
        # bundle from one call and the gate from another disagree about which grace is the anchor
        # -- one grace duplicated, one lost, and the region's warp network quietly wrong. Found by
        # the conservation test on 2026-08-08 (it read `region_graces` and `grace_attunement` from
        # two separate calls, which is exactly what a caller is entitled to do). The cache lives on
        # the world, so it is per-seed and dies with it.
        cache = getattr(world, "_grace_anchor_draw", None)
        if cache is None:
            cache = world._grace_anchor_draw = {}
        if region not in cache:
            cache[region] = world.random.choice(sorted(bundle))
        anchor = cache[region]
    else:
        anchor = front
    rest = [f for f in bundle if f != anchor]
    return [anchor], {"threshold": threshold, "members": rest, "bloom": rest}


@register
class RegionGracesFeature(Feature):
    name = "region_graces"
    OPTIONS = {"region_grace_unlock": RegionGraceUnlock,
               "grace_attunement": GraceAttunement,
               "grace_attunement_anchor": GraceAttunementAnchor}

    def slot_data(self, world):
        kept = set(world._kept())
        # SPEC-ashen-capital-lock: the Ashen Capital is never KEPT (never rolled) but it does carry
        # a Lock, and its four graces ARE the way in -- the region has no walk-in entrance at all.
        # Withholding them would ship a lock that opens nothing. They were force-SKIPPED in
        # gen_data until 2026-08-06 for the opposite reason: while they rode LEYNDELL's lock,
        # lighting them warped the player into a capital they had not burned.
        if getattr(world, "gf_finale_active", False):
            kept = kept | {_FINALE_REGION}
        tier = _grace_tier(world)
        region_graces = {}
        grace_attunement = {}
        for r, fs in REGION_GRACE_POINTS.items():
            if r not in kept or not fs:
                continue
            # bundle: the lock lights the region's whole grace set -- unless the region is a gated
            # child with its wall armed, whose bundle is withheld (module docstring). [] and not
            # key-absence: the client warns about a genuine lock with NO regionGraces entry, and
            # this one is intended.
            # gated child behind an armed wall: grant nothing, at every tier
            bundle = [] if bundle_withheld(world, r) else _bundle_for(r, fs, tier)
            bundle, gate = _attune_split(world, r, bundle)
            if gate is not None:
                grace_attunement[f"{r} Lock"] = gate
            region_graces[f"{r} Lock"] = bundle
        if _vp.is_on(world):
            # No "<Region> Lock" is ever received in this mode, so a bundle keyed to one could
            # never light. The player lights graces by walking to them, which is the point --
            # and attunement has nothing to gate for the same reason.
            return {contract.REGION_GRACES: {}}
        out = {contract.REGION_GRACES: region_graces}
        if grace_attunement:
            out[contract.GRACE_ATTUNEMENT] = grace_attunement
            # A client that cannot read the key would hand the player ONE grace per region and
            # never light the rest -- indistinguishable from a broken seed. Refuse instead.
            out[contract.REQUIRES_CLIENT_FEATURES] = [_CLIENT_FEATURE_TAG]
        return out
