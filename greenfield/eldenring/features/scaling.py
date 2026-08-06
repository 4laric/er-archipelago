"""SPEC-PARITY Phase 2 -- completion scaling + Scadutree blessing (COMPLETE).

Curve is client-side (smoothstep over sphere; completion_scaling=4); the gate/floor the client
actually reads live in sd["options"] (core._options_echo, F1 fix). This feature adds the option
surface, the legacy top-level echoes, and -- as of I2 (2026-07-06) -- the LIVE scaling wire:

  regionSphereTargetRanges = [[lo, hi, target], ...]   (er-logic/scaling.rs:150-165, SCALING_WIRE)

with lo == hi == a region's 5-digit play_region bucket (runtime play_region_id / 100 -- the SAME
bucket space areaLockFlags speaks; geometry reused from features/area_locks.REGION_PLAY_IDS, itself
REGION_ID_MAP.md-derived, matt-free). target = the region's position in a TOTAL topological order
of the seed's lock chain, normalized to 0..TARGET_MAX (the client re-normalizes by the max emitted
target, tier_for_target).

THE ORDER RAMP (2026-07-15, Alaric playtest: "felt easy... spent most time in sphere 1-2"). Scaling
used to be keyed on the raw FILL SPHERE, so every same-sphere region got the SAME target -- and the
lock DAG is wide early, so most of the map sat at the sphere-1/2 tier. Now the spheres (the DAG's
level structure, from mw.get_spheres()) are LINEARIZED into a total order: sphere ascending, with a
seed-deterministic RANDOM tie-break among same-sphere regions (_order_from_spheres). Scaling ramps
evenly over ORDER POSITION 0..N-1 -> target 0..TARGET_MAX (_targets_from_order), so two same-sphere
regions land on different tiers, the mid/high tiers are actually populated, and the curve still
never puts a region above its reachability: sphere-primary sort means a region's target is always
strictly below every strictly-later-sphere region's target (asserted at gen). Same seed -> same
order -> same scaling (the tie-break RNG is keyed on (multiworld.seed, player), NOT the shared
world.random stream -- see _order_rng). FALLBACK when the fill spheres are uncomputable: SPINE-order
depth (sphere_target_ranges) -- pure + deterministic, independent of num_regions_order roll order,
and already a total order. A bucket absent from the wire (hub, tutorial, unmapped sub-areas) falls
back to the client's floor tier -- unknown = don't scale up. The flat map (regionSphereTargets) is emitted transitionally as {} by core.py;
ranges are the live wire, so this feature deliberately does NOT emit the flat key (merge_slot_data
raises on duplicate keys).
"""
import random

from Options import Range, Choice, Removed, OptionError, NamedRange, Toggle
from ..registry import Feature, register
from ..region_spine import SPINE, DLC_REGIONS
from .. import contract
from ..scaling_ladder import (AUTO_CEILING, SCALING_HP_LADDER, ceiling_multiplier,  # noqa: F401 (re-export)
                              floor_multiplier, ramped_target,
                              resolve_max_difficulty_pct,
                              tier_for_ceiling_multiplier, tier_for_floor_multiplier)
from .area_locks import REGION_PLAY_IDS

# Wire normalization ceiling. The client normalizes by the max emitted target (scaling.rs
# tier_for_target), so the exact ceiling only needs enough integer resolution over er-logic's
# 20-rung ladder (7010..7200); 10000 matches the frozen I2 spec.
TARGET_MAX = 10000


# ---- Intra-fold scaling delta (2026-07-22, Alaric; SPEC-intra-fold-scaling-delta-20260722.md) ----
# A region's sphere target is broadcast FLAT to all its play_region buckets. When a region FOLDS
# several vanilla areas of different native difficulty into one bucket-set, that flattens them --
# worst case Greyoll's Dragonbarrow, a late-tier pocket inside the Caelid bucket, scaled down to
# Caelid's target. This adds a HAND-AUTHORED per-bucket DELTA (target-space, 0..TARGET_MAX) applied
# ON TOP of the region's target, CLAMPED so a bumped bucket can never reach the NEXT region's target
# in the order (a local nudge, never a sphere-jump; preserves the "strictly below every later region"
# invariant the order ramp asserts, and never inflates the max the client normalizes by). Playtest-
# feel values, exactly like DLC_BLESSING_FLOORS. Scope = folded sub-areas ONLY (delta 0 == identity).
# This is INTRA-fold variance, NOT cross-region reordering -- the 2026-06-19 "same sphere = same tier /
# don't fix inversions" ruling is about REGION ordering and is untouched.
_SCALING_BUCKET_DELTA = {
    # bucket (play_region_id // 100) : delta in target space (0..TARGET_MAX)
    64020: 2500,   # !! CONFIRM BUCKET + TUNE VALUE: Greyoll's Dragonbarrow (m60_49_40; m60_51_43 --
                   #    the NE Caelid overworld tiles). Late-tier pocket folded into Caelid; this bumps
                   #    it back toward its vanilla difficulty. 2500 ~= a couple tiers on the 0..10000 ramp.
}


def _apply_bucket_delta(triples):
    """Add _SCALING_BUCKET_DELTA to matching buckets, clamped STRICTLY below the next distinct region
    target (never a sphere-jump; never inflates the client-normalized max). Pure; empty delta ==
    identity. triples = [[lo, hi, target], ...] with lo == hi == the bucket."""
    if not _SCALING_BUCKET_DELTA:
        return triples
    distinct = sorted({t for _, _, t in triples})
    out = []
    for lo, hi, target in triples:
        d = _SCALING_BUCKET_DELTA.get(lo, 0)  # lo == hi == play_region bucket
        if d:
            nxt = next((t for t in distinct if t > target), None)
            ceil = (nxt - 1) if nxt is not None else TARGET_MAX
            target = min(target + d, ceil)
        out.append([lo, hi, target])
    return out


def sphere_target_ranges(kept, ramp_pct=100):
    """[[lo, hi, target], ...] triples for `kept` region names (pure; unit-testable without AP).

    SPINE-ordered depth within the kept set, normalized so the deepest kept region == TARGET_MAX.
    One lo == hi triple per play_region bucket of each kept region (same bucket space as
    areaLockFlags). A single kept region emits target 0 (max target 0 == floor everywhere,
    scaling.rs) -- a one-region seed has no progression depth to scale over.
    """
    ordered = [r for r in SPINE if r in set(kept)]
    span = max(len(ordered) - 1, 1)
    triples = []
    for i, region in enumerate(ordered):
        target = ramped_target(i, span, TARGET_MAX, ramp_pct)
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, target])
    return _apply_bucket_delta(triples)


def _region_fill_spheres(world):
    """kept region -> the playthrough sphere its `<R> Lock` is obtained in (0 = start/precollected).
    TRUE FILL SPHERE: reflects where each lock actually landed this seed, so a random-start
    num_regions seed scales from the region you can reach, not geography. {} if uncomputable."""
    player = world.player
    mw = world.multiworld
    lock_to_region = {f"{r} Lock": r for r in world._kept()}
    sphere = {}
    for it in mw.precollected_items[player]:            # start-open region(s) -> sphere 0
        r = lock_to_region.get(it.name)
        if r is not None:
            sphere[r] = 0
    try:
        for i, locset in enumerate(mw.get_spheres()):   # 0-indexed fill spheres; +1 keeps start below
            for loc in locset:
                it = getattr(loc, "item", None)
                if it is not None and getattr(it, "player", None) == player:
                    r = lock_to_region.get(it.name)
                    if r is not None and r not in sphere:
                        sphere[r] = i + 1
    except Exception:
        return {}
    if sphere:                                          # any lock not located -> treat as deepest
        deepest = max(sphere.values())
        for r in world._kept():
            sphere.setdefault(r, deepest + 1)
    return sphere


def _order_from_spheres(region_sphere, rng):
    """A TOTAL topological order (linearization of the lock-chain DAG) over the regions of
    `region_sphere`. Primary key = the region's fill sphere (the DAG's level structure -- a sphere-i
    lock can only require locks from spheres < i, so sphere-ascending IS a valid topological sort);
    tie-break among same-sphere regions = random jitter from `rng` (seed-deterministic, see
    _order_rng). The base iteration order is sorted() so the jitter is the ONLY tie-breaker -- dict
    insertion order (which leaks set iteration order from mw.get_spheres()) never reaches the wire.
    The topological property is ASSERTED, not trusted: if the order ever puts a region before a
    strictly-earlier-sphere region, generation dies loudly rather than shipping an inverted curve."""
    regions = sorted(region_sphere)
    jitter = {r: rng.random() for r in regions}
    order = sorted(regions, key=lambda r: (region_sphere[r], jitter[r]))
    for a, b in zip(order, order[1:]):
        if region_sphere[a] > region_sphere[b]:
            raise AssertionError(
                f"scaling order is not a topological sort of the lock chain: {a!r} (sphere "
                f"{region_sphere[a]}) precedes {b!r} (sphere {region_sphere[b]})")
    return order


def _targets_from_order(order, ramp_pct=100):
    """region -> target 0..TARGET_MAX: an even, strictly MONOTONIC ramp over the total order
    (position 0 -> 0, last -> TARGET_MAX; a single region -> 0, no depth to scale over). Same-sphere
    regions occupy different positions, so they get DIFFERENT targets -- that is the point of the
    order ramp. Monotone along reachability by construction: the order is sphere-primary, so no
    region's target ever exceeds a region it cannot precede."""
    span = max(len(order) - 1, 1)
    return {r: ramped_target(i, span, TARGET_MAX, ramp_pct) for i, r in enumerate(order)}


def _order_rng(world):
    """Seed-deterministic RNG for the same-sphere tie-breaks. Deliberately NOT world.random: slot_data
    is built more than once for one seed (fill_slot_data re-entry; test_slot_data_is_deterministic),
    and drawing from the shared stream would reshuffle the order on every call. Keyed on
    (multiworld.seed, player) so it is stable per seed and per player, and independent of every other
    roll in the generation -- the guarantee the old SPINE-depth comment promised, kept true."""
    return random.Random(f"{world.multiworld.seed}:{world.player}:er-scaling-order")


def _ranges_from_targets(region_target):
    """[[lo, hi, target], ...] sorted by play_region id.

    DETERMINISM: `region_target` inherits its dict ORDER from `_region_fill_spheres`, which walks
    `mw.get_spheres()` -- and each sphere is a SET, whose iteration order varies between runs. The
    VALUES are stable (every lock in sphere i gets i+1), but the insertion order is not, so emitting
    in dict order made slot_data differ for the SAME seed run twice. Sort so the wire is a pure
    function of the fill result. (Caught by test_gf_world::test_slot_data_is_deterministic.)"""
    triples = []
    for region, target in region_target.items():
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, target])
    return sorted(_apply_bucket_delta(triples))


# ---- DLC Scadutree-blessing floors (global_scadutree_blessing == 2 "scaled") --------------------
# DLC enemies are tuned around a per-AREA Scadutree Blessing level (a DLC-only player-side damage/
# defence multiplier), decoupled from runes/level. In this rando the fragments that raise blessing are
# scattered multiworld checks, so you can reach a DLC region with ~0 blessing and get brutalised. Mode
# 2 grants a blessing FLOOR keyed on which DLC region you're in (NOT the normalized sphere depth --
# blessing expectation is ABSOLUTE per area: Bayle assumes ~14 whenever you fight him, however deep the
# seed put Jagged Peak). Floors sit ~3-4 levels UNDER vanilla expectation so collected fragments still
# buy visible power; the client's raise-only writer takes max(held-fragment level, floor). (fable
# consult 2026-07-11.)
# Region-spine v2: the DLC split means every floor is per-REGION now; values carried over where the
# region existed before, and the regions split OUT of a coarse one start from vanilla-expectation
# feel (~3-4 under, same rule): Ensis/Cerulean/Charo's were inside Gravesite's floor-1 blanket and
# are tuned a little above it; Stone Coffin keeps the 10 it had as a per-bucket override of
# Gravesite; Scaduview (Metyr, Keep environs) and Rauh Base ride their neighbours. Playtest-feel
# values -- flagged for review in SPEC-region-spine-v2.md, like the boss scaling tiers.
DLC_BLESSING_FLOORS = {
    "Gravesite": 1,
    "Ensis": 2,
    "Cerulean": 2,
    "Charo's": 2,
    "Belurat": 3,
    "Scadu Altus": 7,
    "Shadow Keep": 10,   # includes the folded-in Scaduview Hinterland (2026-07-19); same floor it had
    "Stone Coffin": 10,
    "Rauh Base": 10,
    "Ancient Ruins": 12,
    "Jagged Peak": 12,
    "Abyssal": 12,
    "Enir Ilim": 15,
}
# Per-play_region-bucket overrides for sub-areas whose native tuning diverges from their region
# floor. EMPTY since the v2 split -- Stone Coffin (22000), the only entry, is its own region now.
# Kept as a mechanism: a future shared-bucket sub-area (an Ellac-class fold) may need one.
_DLC_BLESSING_BUCKET_OVERRIDE = {}


def dlc_region_buckets(kept):
    """Sorted play_region buckets belonging to KEPT DLC regions. Pure; [] when no DLC is in play.

    WHY THIS EXISTS. The client needs to know "is this bucket a DLC region?" and until now its only
    way to ask was `blessing_floor_for_region(&cfg.dlc_blessing_floors, region).is_some()` -- i.e. it
    inferred DLC-ness from the presence of a SCADUTREE BLESSING FLOOR. Those floors are emitted only
    when `global_scadutree_blessing == 2`, and the shipped default has been `off` since 2026-07-18,
    so on EVERY default seed that test answers `false` for every bucket in the game. The DLC flag in
    the enemy-scaling log has therefore been dead since the day the default changed, and nobody
    noticed, because a `false` there just prints a shorter line.

    Harmless while it only decorates a log. NOT harmless as the input to a scaling decision -- and
    that is exactly what the DLC enemy ladder (er-logic scaling.rs DLC_SCALING_ID_RANGE, the
    20007xxx block) will need. So the signal is now DERIVED FROM THE REGION SET, which is what it
    always meant, instead of borrowed from an unrelated option's side effect.

    Same lo==hi bucket space as areaLockFlags / regionSphereTargetRanges (play_region_id // 100),
    but emitted as a flat sorted list: this is a MEMBERSHIP set, and shaping it as ranges with a
    meaningless third column would be inventing a value to fit an existing parser.
    """
    keptset = set(kept)
    return sorted({pid for region in DLC_REGIONS if region in keptset
                   for pid in REGION_PLAY_IDS.get(region, [])})


def blessing_floor_ranges(kept):
    """[[lo, hi, floor], ...] Scadutree-blessing floors per DLC-region play_region bucket, for the kept
    DLC regions (pure; unit-testable without AP). Same lo==hi bucket space as regionSphereTargetRanges /
    areaLockFlags. Empty when no DLC region is kept. Per-bucket overrides win over the region floor."""
    keptset = set(kept)
    triples = []
    for region in DLC_REGIONS:
        if region not in keptset:
            continue
        base = DLC_BLESSING_FLOORS.get(region, 0)
        for pid in REGION_PLAY_IDS.get(region, []):
            triples.append([pid, pid, _DLC_BLESSING_BUCKET_OVERRIDE.get(pid, base)])
    return triples


class EnemyScaling(Toggle):
    """Whether enemy difficulty follows your PROGRESSION instead of the map.

    On (default), a region's enemies are re-tiered by how deep it sits in your unlock order, so a
    zone you reach late is dangerous even if it is early on the map, and one you open first is not a
    walkover just because it is late. `minimum_enemy_difficulty`, `maximum_enemy_difficulty` and
    `difficulty_ramp_speed` shape that curve.

    Off = VANILLA. Every enemy keeps exactly the strength the base game gave it, everywhere. The
    client does not touch a single enemy: no re-tiering, no floor, no ceiling, and the three sliders
    above stop meaning anything. Worth choosing if you want the randomizer's item placement without
    its difficulty curve, or if you are playing a route where the vanilla curve already suits you.

    🛑 A seed rolled with this off is not "easier" -- it is the game's own difficulty, which in a
    randomized world can mean meeting a late-game area's enemies at level 20."""
    display_name = "Enemy Scaling"
    default = 1


class MinimumEnemyDifficulty(Range):
    """How hard the EASIEST enemies in your run are. 0 (default) leaves the early game at its normal
    strength; higher values lift the whole floor, so nowhere stays trivial once you have outgrown it.

      0    normal -- your first region is as weak as vanilla-ish   (default)
      25   nothing below about 2.3x enemy HP
      50   nothing below about 4x
      100  everything at maximum, everywhere, from your first region on

    Useful because progression here is not geography: a region you unlock late can be an "early"
    one, and this stops it being a walkover. Enemy rune rewards are unchanged at every setting.

    🛑 THE DEFAULT WAS BRIEFLY 25 AND IS BACK TO 0 (2026-08-05, same day, unreleased). The case for
    raising it was that vanilla applies TWO scaling rows per enemy -- a ladder rung and a second row
    at the same index +400 -- so its effective HP floor was 3.56x against our 1.141x. **That was
    arithmetic, not measurement, and per-enemy measurement disproved it.** Observed `max_hp` is
    vanilla base x the RUNG rate exactly, with the second row contributing nothing:
    base 755 with `[7020, 7420]` measures 967, and 755 x 1.281 = 967. Six enemies, plus eleven
    reading residual 1.000 against a rung-only model.

    So vanilla's HP floor IS 1.141x, 0 IS the vanilla-equivalent default, and it never needed
    changing. Do not raise this default again without a measurement rather than a product.
    """
    display_name = "Minimum Enemy Difficulty"
    range_start = 0
    range_end = 100
    default = 0


# ---- RENAMED 2026-07-27 -- stale yamls must FAIL, not be silently ignored ----------------------
# Archipelago drops unknown yaml keys without a word (the hazard test_gf_shipping_yaml exists for),
# so a straight rename would leave `completion_scaling_floor: 50` reading like a setting and doing
# nothing. `Options.Removed` raises instead: "Option removed, please update your options file."
# It is `Visibility.none`, so it does not appear in the wizard or on the webhost.
#
# `completion_scaling_floor` was a real name for months (it is in v0.1-era yamls and in the v0.2
# template's FIXED list). `completion_scaling_ramp` existed for about an hour on main and never
# shipped, but it is cheap to catch and expensive to debug.
class CompletionScalingFloor(Removed):
    """Renamed to `minimum_enemy_difficulty`."""


class CompletionScalingRamp(Removed):
    """Renamed to `difficulty_ramp_speed` -- and INVERTED: higher is now harder."""


# ---------------------------------------------------------------------------------------------
# THE ARM/DISARM SWITCH, RESOLVED IN ONE PLACE (#408).
# ---------------------------------------------------------------------------------------------
# `completion_scaling` ships TWICE: the legacy top-level copy (this feature's slot_data) and
# sd["options"]["completion_scaling"], which is THE COPY THE CLIENT READS
# (er-logic/src/scaling.rs parse_scaling_config -> options::parse_bool_option). Until 2026-08-06
# only the top-level copy consulted the option; core._options_echo emitted a BARE LITERAL 4. So
# `enemy_scaling: false` produced a slot_data reading `completion_scaling: 0` top-level and
# `"completion_scaling": 4` inside `options`, the client read the 4, and the option was
# unreachable from yaml -- confirmed live on 0.3.5 (240 enemies scaled at 1.14x on an off seed).
#
# One resolver, both emitters. A switch that can only be armed from one place cannot be half-gated.
SMOOTHSTEP_CURVE_ID = 4


def completion_scaling_id(world) -> int:
    """The client's scaling curve id for this seed: SMOOTHSTEP_CURVE_ID when on, 0 when off.

    0 is not "curve zero" -- er-logic `parse_scaling_config` returns None on a falsey value, so
    `CONFIG` stays empty and `tick()` returns before the sweep ever runs. That is the vanilla path.

    Defensive `getattr`: `_options_echo` resolves every other key that way, and an ABSENT option
    must mean the SHIPPED DEFAULT, which for EnemyScaling is ON -- so a harness that builds a
    partial options object still gets the historical wire. Never truthiness on the option OBJECT: a
    Toggle whose value is 0 is still a live object, which is how a `False` would read as `True`."""
    opt = getattr(world.options, "enemy_scaling", None)
    on = True if opt is None else bool(opt.value)
    return SMOOTHSTEP_CURVE_ID if on else 0


def resolved_max_difficulty(world):
    """`maximum_enemy_difficulty` as a PERCENT, with `auto` resolved. THE single call site.

    🛑 THREE consumers compare this value and every one of them was a separate bug when they read the
    RAW option instead: generate_early's floor/ceiling validation (a -1 sentinel is below every floor,
    so it raised OptionError on every default seed), slot_data's client-feature handshake (-1 < 100,
    so every default seed demanded a client that understands capping -- a compatibility break for
    everyone, caught by test_an_uncapped_seed_demands_nothing_of_the_client), and core._options_echo's
    emitted cap. They now all route here, so the validated value, the declared dependency and the
    wire cannot disagree.
    """
    nr = getattr(world.options, "num_regions", None)
    # total comes off the option's own bound: NumRegions.range_end == len(REGIONS), so it cannot
    # drift from the region list the way a literal would.
    return resolve_max_difficulty_pct(
        int(world.options.maximum_enemy_difficulty.value),
        int(nr.value) if nr is not None else 0,
        int(nr.range_end) if nr is not None else 30,
        int(world.options.minimum_enemy_difficulty.value))


class MaximumEnemyDifficulty(NamedRange):
    """How hard the TOUGHEST enemies get.

      auto  scale the cap to the LENGTH of your run        (default)
       100  no cap -- the deepest region hits the game's maximum, about 7.4x enemy HP
        75  nothing above about 5.5x enemy HP
        50  nothing above about 4x
        25  nothing above about 2x

    `auto` exists because the curve is relative and your gear is not. Scaling ramps over the ORDER
    your regions unlock, so the deepest one is "the end of the run" whether that is 30 regions or 5 --
    but Somber +10 still needs a Somber [9]. On a short seed you therefore meet endgame-strength
    enemies on a mid-game weapon, and fewer regions makes the ramp steeper rather than gentler.
    `auto` lowers the top of the curve with the length of the run: about 4.1x at 5 regions, the full
    7.4x at 30. Give a number instead to pick the cap yourself.

    ⚠️ The `auto` curve has ONE playtested point -- about 3.7x at 5 regions, where the ladder used to
    top out. Above that it is extrapolation, so treat the high end as untested.

    Must be at least Minimum Enemy Difficulty; generation refuses the inverted pair rather than
    quietly picking one.

    ⚠️ Needs a client that understands it. A seed setting this below 100 tells the client so at
    connect, and an older client refuses with a message rather than ignoring the cap."""
    display_name = "Maximum Enemy Difficulty"
    range_start = 0
    range_end = 100
    special_range_names = {"auto": AUTO_CEILING}
    default = AUTO_CEILING


class DifficultyRampSpeed(Range):
    """How quickly enemies get harder as you progress. 0 (default) spreads the climb evenly across
    the whole run; higher values front-load it, so you hit the hardest enemies sooner and the rest of
    the run stays there.

      0    even across the run -- your last region is the first to reach maximum   (default)
      50   maximum from about halfway; everything after that is equally hard
      75   maximum about a quarter of the way in
      100  maximum almost immediately

    This does not change how hard the HARDEST enemies are -- that ceiling is fixed. It changes how
    much of your run is spent below it. Pairs with Minimum Enemy Difficulty, which raises the
    BOTTOM instead."""
    display_name = "Difficulty Ramp Speed"
    range_start = 0
    range_end = 100
    default = 0


def ramp_pct_from_speed(speed):
    """Player-facing SPEED (0..100, higher = harder) -> `scaling_ladder.ramped_target`'s ramp_pct
    (the percent of the run by which the top tier is reached; LOWER = harder).

    Two representations, one conversion, in one place -- the same discipline as `floor_multiplier`,
    and for the same reason. `ramp_pct` is the honest mechanical quantity, but as a player-facing
    knob it points the wrong way: 25 would be harder than 100, while the neighbouring
    `minimum_enemy_difficulty` gets harder as it RISES. Two difficulty sliders that disagree about
    which direction is harder is a usability bug, so the option is inverted here and only here."""
    return max(1, 100 - max(0, min(100, int(speed))))


# ---- NO CEILING BUT THE GAME'S OWN (2026-08-06, Alaric) ----------------------------------------
# `SCADU_BLESSING_CAP = 12` lived here and was sent as `scaduBlessingCap`. It is GONE: the only
# ceiling is now the vanilla ladder's, level 20, which is what the client already falls back to when
# the key is absent. A ceiling the base game does not have is a rule the player has to be told
# about, and no seed was telling them.
#
# 🛑 THE 12 HAS NOT VANISHED -- IT MOVED, because one constant was doing two unrelated jobs. The
# arithmetic that chose it was never about a ceiling: levels 13..20 cost 24 more fragments (half the
# whole budget, SCADU_CUM[20]=50 vs SCADU_CUM[12]=26) to buy +11% attack, and in a base-game seed
# every one of those is a forced-`useful` item displacing filler against an economy that is one seed
# thick (gf-early-economy-floor-knife-edge). That is an argument about how many fragments to PUT IN
# THE POOL, not about where to stop applying them. It now lives beside the code it governs, as
# scadu_supply.SCADU_INJECTION_TARGET, and it is still 12: this change removes a ceiling, it does
# not double anyone's filler displacement.
#
# So a seed GUARANTEES the fragments for level 12 and lets the region draw carry you past it if it
# happens to. Nothing clamps the top any more.


class ScadutreeBlessingScope(Choice):
    """WHERE the Scadutree blessing applies. dlc_only = vanilla: the blessing is a Land of Shadow
    mechanic and does nothing in Limgrave, exactly as FromSoft shipped it. anywhere = the blessing
    becomes a GAME-WIDE power curve driven by the fragments the multiworld has sent you, so it works
    everywhere. Enemies are untouched either way, so `anywhere` is explicitly a power fantasy.

    HOW `anywhere` IS POSSIBLE AT ALL. Every vanilla rung 20000100+level carries
    effectEndurance = 0.05 -- 50ms. It is not a persistent buff; a refresher loop that only runs in
    the Land of Shadow re-applies it every tick. The client clones the rung onto a row of its own
    with effectEndurance = -1 and applies that (see the client's `scadu_blessing` module and
    docs/specs/SPEC-global-scadutree-blessing-20260729.md). Measured in-game 2026-07-29."""
    display_name = "Scadutree Blessing Scope"
    option_dlc_only = 0
    option_anywhere = 1
    default = 0


class DlcBlessingCatchup(Toggle):
    """Guarantee each DLC region's expected Scadutree Blessing while you are standing in it.

    WHY IT EXISTS, AND WHY IT IS NOT A DIFFICULTY KNOB. DLC enemies are tuned around a per-AREA
    blessing level. In this rando the fragments that raise blessing are scattered multiworld checks,
    so the fill can hand you Shadow Keep while your blessing is 0 -- through no decision of yours.
    This lifts you to that area's floor (DLC_BLESSING_FLOORS, ~3-4 under vanilla expectation) so
    collected fragments still buy visible power above it. Compose is MAX, never a replacement.

    🛑 IT IS SCOPED TO WHERE YOU STAND, NOT TO WHAT YOU UNLOCKED. The client re-reads your current
    play_region every tick; leave the region and the floor goes with you. Nothing is granted.

    Inert outside the DLC: base-game buckets have no floor, so a base-only seed emits no wire at all.
    """
    display_name = "DLC Blessing Catch-up"


# ---- the legacy key -----------------------------------------------------------------------------
# `global_scadutree_blessing` asked TWO questions with one Choice: `off -> player_only` moves SCOPE,
# `player_only -> scaled` adds the FLOOR. That is why value 2 had to be called `scaled`, a word this
# codebase already spends on enemy scaling, and why the combination a lot of players actually want --
# vanilla scope, but the DLC does not brutalise you for the fill's choices -- COULD NOT BE EXPRESSED.
#
# Kept as a live, translating option rather than an `Options.Removed` stub (the 2026-07-27 rename
# pattern): a Removed option RAISES, and the point here is that old yamls keep working. Translation
# happens in Scaling.generate_early; every consumer reads the two new options via blessing_mode().
LEGACY_BLESSING_MAP = {
    0: (0, 0),   # off         -> dlc_only,  no catchup
    1: (1, 0),   # player_only -> anywhere,  no catchup
    2: (1, 1),   # scaled      -> anywhere + catchup
}


class GlobalScadutreeBlessing(Choice):
    """DEPRECATED 2026-08-06 -- split into `scadutree_blessing_scope` + `dlc_blessing_catchup`.

    Still honoured, so an existing yaml keeps generating the same seed: off -> (dlc_only, off),
    player_only -> (anywhere, off), scaled -> (anywhere, on). Setting this AND either replacement to
    values that disagree is an OptionError rather than a silent winner -- see Scaling.generate_early.

    Prefer the replacements: they can also express (dlc_only, on), which this key cannot say."""
    display_name = "Global Scadutree Blessing (deprecated)"
    option_off = 0
    option_player_only = 1
    option_scaled = 2
    default = 0


def resolve_legacy_blessing(world) -> None:
    """Translate the deprecated `global_scadutree_blessing` into the two options that replaced it.

    Called from Scaling.generate_early, BEFORE anything reads the pair, so every consumer sees one
    resolved truth instead of each deciding for itself which key wins.

    CONTRADICTION IS AN ERROR, NOT A PRECEDENCE RULE. A yaml naming both the old key and a new one
    with different intent has no correct reading -- picking a winner means a player's stated setting
    is silently dropped, which is the failure the 2026-07-27 renames were made loud to avoid. Name
    both keys in the message so the fix is obvious from the traceback alone.

    🛑 THE ONE CASE THIS CANNOT SEE. Archipelago does not record whether a value was typed or
    defaulted, so an explicit `global_scadutree_blessing: off` is indistinguishable from not naming
    it at all. A yaml with an explicit `off` next to `scadutree_blessing_scope: anywhere` therefore
    resolves to `anywhere` rather than raising. That is the right way round -- the new key wins and
    the deprecated one is the one being ignored -- but it is a real limit, not an oversight.
    """
    legacy = int(world.options.global_scadutree_blessing.value)
    if legacy == 0:
        return
    want = LEGACY_BLESSING_MAP[legacy]
    have = (int(world.options.scadutree_blessing_scope.value),
            int(world.options.dlc_blessing_catchup.value))
    legacy_name = world.options.global_scadutree_blessing.current_key
    if have != (0, 0) and have != want:
        raise OptionError(
            f"global_scadutree_blessing ({legacy_name}) contradicts the options that replaced it. "
            f"It means scadutree_blessing_scope="
            f"{'anywhere' if want[0] else 'dlc_only'}, dlc_blessing_catchup="
            f"{'on' if want[1] else 'off'}, but this yaml also sets scadutree_blessing_scope="
            f"{'anywhere' if have[0] else 'dlc_only'}, dlc_blessing_catchup="
            f"{'on' if have[1] else 'off'}. Drop global_scadutree_blessing -- it is deprecated and "
            f"the two replacements can say everything it could, plus dlc_only + catchup, which it "
            f"could not.")
    world.options.scadutree_blessing_scope.value = want[0]
    world.options.dlc_blessing_catchup.value = want[1]


def blessing_mode(world) -> int:
    """The WIRE value the client reads, derived from the two live options.

    0 off | 1 anywhere | 2 anywhere+catchup | 3 dlc_only+catchup (NEW 2026-08-06).

    🛑 THIS, not `world.options.global_scadutree_blessing.value`, is what every consumer must call --
    including core._options_echo, which is the copy the client actually reads. A consumer that keeps
    reading the legacy option sees 0 for every player who used the new names, and the setting
    evaporates with slot_data reporting OK. That is #408's exact shape.

    Mode 3 is the whole reason the split was worth a compat surface: vanilla scope + the floor.
    """
    scope = int(world.options.scadutree_blessing_scope.value)
    catchup = int(world.options.dlc_blessing_catchup.value)
    if scope == 0:
        return 3 if catchup else 0
    return 2 if catchup else 1


@register
class Scaling(Feature):
    name = "scaling"
    OPTIONS = {
        "enemy_scaling": EnemyScaling,
        "minimum_enemy_difficulty": MinimumEnemyDifficulty,
        "maximum_enemy_difficulty": MaximumEnemyDifficulty,
        "difficulty_ramp_speed": DifficultyRampSpeed,
        "scadutree_blessing_scope": ScadutreeBlessingScope,
        "dlc_blessing_catchup": DlcBlessingCatchup,
        # DEPRECATED alias for the two above; translated in generate_early.
        "global_scadutree_blessing": GlobalScadutreeBlessing,
        # Renamed 2026-07-27; these raise on a stale yaml rather than being ignored.
        "completion_scaling_floor": CompletionScalingFloor,
        "completion_scaling_ramp": CompletionScalingRamp,
    }

    def generate_early(self, world):
        """Reject an inverted floor/ceiling here rather than letting it reach the client.

        CONTRIBUTING's headline gate: an incompatible combination fails at options-validation time
        with a message naming BOTH options, not as a FillError and not as a config that generates but
        plays wrong. `tier_for_target` also resolves the contradiction defensively (the floor wins),
        because it is a pure fn reachable from foreign slot_data -- but a player who typed these two
        numbers deserves to be told, not silently corrected."""
        lo = int(world.options.minimum_enemy_difficulty.value)
        raw = int(world.options.maximum_enemy_difficulty.value)
        # Resolved through the SAME function core._options_echo uses, so validation and the emitted
        # cap cannot disagree. It also matters for correctness, not tidiness: comparing the raw `auto`
        # sentinel (-1) against a floor would raise on EVERY DEFAULT SEED, since every floor exceeds
        # -1. total_regions comes off the option's own bound (NumRegions.range_end == len(REGIONS)),
        # which cannot drift from it.
        hi = resolved_max_difficulty(world)
        if raw != AUTO_CEILING and lo > hi:
            raise OptionError(
                f"minimum_enemy_difficulty ({lo}) is above maximum_enemy_difficulty ({hi}) -- the "
                f"weakest enemies would be stronger than the strongest. Set the minimum at or below "
                f"the maximum (both are 0-100, higher = harder).")
        # The deprecated blessing key becomes the two live ones here -- before slot_data,
        # _options_echo or any test reads either. See resolve_legacy_blessing.
        resolve_legacy_blessing(world)

    def slot_data(self, world):
        # ORDER RAMP (2026-07-15): the fill spheres (TRUE per-seed reachability, 2026-07-07) are
        # linearized into a total topological order with seed-deterministic tie-breaks, and the
        # target ramps over ORDER POSITION -- so same-sphere regions scale differently and the
        # mid/high tiers are populated even though the lock DAG is wide early ("felt easy").
        # SPINE-order depth is the fallback when the fill sphere can't be computed (no world /
        # degenerate); it is already a total order.
        ramp = ramp_pct_from_speed(world.options.difficulty_ramp_speed.value)
        region_sphere = _region_fill_spheres(world)
        if region_sphere:
            order = _order_from_spheres(region_sphere, _order_rng(world))
            ranges = _ranges_from_targets(_targets_from_order(order, ramp))
        else:
            ranges = sphere_target_ranges(world._kept(), ramp)
        blessing = blessing_mode(world)
        kept_regions = world._kept()
        # VANILLA MODE. `completion_scaling` is the client's own arm/disarm switch: er-logic
        # `parse_scaling_config` returns None on a falsey value, so `CONFIG` stays empty, `tick()`
        # returns immediately, and the sweep never runs -- no clear, no apply, every enemy exactly as
        # the base game shipped it. That path already existed and is already the documented degrade;
        # nothing here is new client behaviour, and no client release is needed.
        #
        # The rest of the payload is emitted UNCHANGED either way, deliberately. The client
        # short-circuits on this key before reading any of it, so withholding the ranges would buy
        # nothing and would make an off-seed's slot_data a second shape to reason about. One switch,
        # read in one place.
        out = {
            # smoothstep (client curve id; SPEC-PARITY P2), or 0 = OFF -> vanilla. Resolved through
            # completion_scaling_id so this copy and the one core._options_echo emits into
            # sd["options"] cannot disagree -- they did, and #408 is what that cost.
            "completion_scaling": completion_scaling_id(world),
            # UNIT SPACE: this legacy TOP-LEVEL copy is the raw player-facing PERCENT (0..100). The
            # key the client actually reads is sd["options"]["completion_scaling_floor"], emitted by
            # core._options_echo as the HP MULTIPLIER (see floor_multiplier). Two keys, same name,
            # DIFFERENT UNITS -- named here on purpose rather than left to be discovered
            # (CONTRIBUTING rule 3: name the space wherever two components exchange a value), and
            # asserted in tests/test_gf_scaling_floor_units.py so the pair cannot silently converge.
            "completion_scaling_floor": int(world.options.minimum_enemy_difficulty.value),
            contract.REGION_SPHERE_TARGET_RANGES: ranges,
        }
        # NO `scaduBlessingCap`. Absent has always meant "no extra cap -> the ladder ceiling", it is
        # pinned on both sides, and that is now the only answer any greenfield seed gives. Emitting a
        # constant 20 instead would be a bare literal saying exactly what absence already says.
        # WHICH BUCKETS ARE DLC -- independent of every option, because that is what the question
        # actually depends on. Emitted whenever a DLC region is kept; absent (inert) otherwise, so a
        # base-game seed's slot_data is unchanged. See dlc_region_buckets for why the client could
        # not previously ask this without accidentally asking about Scadutree blessing instead.
        # CLIENT FEATURE HANDSHAKE. Only a seed that actually CAPS declares the dependency: at 100
        # the ceiling is the top rung, which is what tier_for_target clamped to anyway, so a default
        # seed connects to any client. See er_logic::client_features for why the contract hash does
        # not cover this (it folds in CONTRACT, not OPTIONS_SUBKEYS).
        # RESOLVED, not raw: `auto` is -1, and -1 < 100, so reading the raw value here declared the
        # dependency on EVERY default seed. `auto` on a full map resolves to 100 and demands nothing.
        # 🛑 ONE ASSIGNMENT, MANY TAGS. This used to be a bare `= ["scaling_ceiling"]`, which was
        # correct only while exactly one feature could ever declare a dependency. The blessing split
        # made that two, and a second bare assignment would have silently dropped whichever ran
        # first -- a handshake key that loses half its content is worse than no handshake.
        _needs = []
        if resolved_max_difficulty(world) < 100:
            _needs.append("scaling_ceiling")
        # MODE 3 IS THE ONLY NEW WIRE VALUE (dlc_only scope + catch-up). Modes 0/1/2 mean exactly
        # what they meant, so only a mode-3 seed declares anything: an older client reads
        # `global_scadutree_blessing` as a number it does not recognise, falls through
        # `mode != 1 && mode != 2`, and writes nothing -- the player's catch-up would evaporate with
        # "VERSION: OK", because the contract hash folds CONTRACT and not OPTIONS_SUBKEYS. This is
        # exactly the gap requiresClientFeatures exists to close.
        if blessing == 3:
            _needs.append("dlc_blessing_catchup")
        if _needs:
            out[contract.REQUIRES_CLIENT_FEATURES] = _needs
        if set(kept_regions) & DLC_REGIONS:
            buckets = dlc_region_buckets(kept_regions)
            if buckets:
                out[contract.DLC_REGION_BUCKETS] = buckets
        # mode 2 (scaled): emit the per-DLC-region blessing floor wire, but only when DLC regions are
        # actually kept (otherwise inert -- no key, so a base-game seed is byte-identical to mode 1).
        if blessing in (2, 3) and set(kept_regions) & DLC_REGIONS:
            floors = blessing_floor_ranges(kept_regions)
            if floors:
                out[contract.DLC_SCADUTREE_FLOOR_RANGES] = floors

        # ---- TELEMETRY: state the curve this seed actually emitted -----------------------------
        # Same pattern and same reason as progression_surface's SPILLED line: a per-seed measurement
        # in the gen log, which tools/fill_regression.py aggregates across a seed sweep. Until this
        # existed, the ONLY scaling coverage was a couple of hand-built worlds in pytest -- so a
        # change that quietly flattened the curve on 1-in-20 seeds had nothing looking at it.
        #
        # Reports the RESOLVED tiers, not the option values, because the option values are the thing
        # a bug would leave looking correct. tier_lo/tier_hi are computed the way the CLIENT computes
        # them (round(frac * (NUM-1)), clamped by floor and ceiling), so this line is the curve the
        # player gets, not the curve gen intended.
        _n = len(SCALING_HP_LADDER)
        _floor_t = tier_for_floor_multiplier(floor_multiplier(
            int(world.options.minimum_enemy_difficulty.value)))
        # 🛑 RESOLVED, not raw. `auto` is -1, and ceiling_multiplier clamps to 0..100 -- so the raw
        # sentinel became the BOTTOM rung and this line reported `ceiling 0 / tiers 0..0` on every
        # default seed from 55bafb2 (the auto default) onward. That is the fourth consumer to make
        # this exact mistake; 81c90b0 routed the other three through resolved_max_difficulty and
        # missed this one because it is a log line rather than a consumer. It is not merely a log
        # line: tools/fill_regression.py parses it (_SCALING_RE) as its ONLY scaling telemetry, so a
        # wrong ceiling here fired the harness's "🛑 a FLAT run" alarm on every default-curve run.
        _ceil_t = tier_for_ceiling_multiplier(ceiling_multiplier(
            resolved_max_difficulty(world)))
        _targets = [t for _lo, _hi, t in ranges]
        _mx = max(_targets) if _targets else 0
        _tiers = sorted(
            min(max(round(t / _mx * (_n - 1)) if _mx else 0, _floor_t), _ceil_t) for t in _targets)
        import logging
        logging.getLogger("Greenfield").info(
            "[greenfield] enemy scaling: %d buckets, tiers %d..%d of %d (floor %d, ceiling %d), "
            "%d at ceiling, median %d; ramp %d",
            len(_targets), _tiers[0] if _tiers else 0, _tiers[-1] if _tiers else 0, _n - 1,
            _floor_t, _ceil_t, sum(1 for t in _tiers if t == _ceil_t),
            _tiers[len(_tiers) // 2] if _tiers else 0, ramp)
        return out
