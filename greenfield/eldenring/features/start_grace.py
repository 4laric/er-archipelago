"""Start experience -- Roundtable Hold as the start, early leveling, map reveal (matt-free).

The run starts at Roundtable Hold (the hub). This feature emits:
  startRegion = "Roundtable Hold" (HUB) -- the client's start anchor.
  startGraces = [71190] + early-leveling flags. 71190 is the Roundtable Hold warp-unlock grace
    (Table of Lost Grace, m11_10; confirmed in the prior apworld's base-hub startgraces). The run's
    first OPEN region comes from the precollected region lock (core.create_items; WHICH one is
    pick_anchor_region below -- size-weighted over the kept base-game regions) -- its bundle
    graces light on receipt -- so this list only needs the hub grace to bootstrap the first warp.
  reveal_all_maps (bool).

startGraces doubles as the client's "set these flags at start" list (startgrants.rs), so Early Leveling
rides here: 4680 (Level Up enable) + 951 (Melina first-meeting done) -- the two flags her accord sets,
confirmed in-game (set both, rest, Level Up works, no cutscene). The first entry (a real grace) is the
client's clobber read-back sentinel. All ids are from prior in-game-verified work; none invented.
"""
from Options import DefaultOnToggle, OptionSet, Range, Toggle
from ..registry import Feature, register
from .. import contract
from ..data import HUB
from ..region_spine import REGIONS

_ROUNDTABLE_GRACE = 71190       # Roundtable Hold, Table of Lost Grace (m11_10) warp-unlock flag
_LEVEL_UP_FLAG = 4680           # Level Up enable
_MELINA_SUPPRESS_FLAG = 951     # Melina first-meeting done / suppress her hand-off
# Ranni's-Rise questline flag ("met Ranni"). Nokron's Fingerslayer Blade chest (check 12027080) is
# vanilla-gated behind it via m12_02 event 12023721 -> without it the chest says "You are not destined
# to open this yet". A warp-shuffle player never meets Ranni first, so we force-set it at spawn to keep
# the check reachable (same matt-free NPC-prereq bypass as the Melina flag above). Verified in-game via
# the Hexinton event-flag writer: set 1034509410 -> chest opens.
_FINGERSLAYER_CHEST_GATE = 1034509410
# RADAHN FESTIVAL. Starscourge Radahn (boss 1051360800, m60_51_36) only spawns once the festival is on:
# his arena script does `EndIf(!EventFlag(9410)); WaitFor(EventFlag(9410))`. And common.emevd only turns
# 9410 on after a questline beat OUTSIDE Caelid:
#     WaitFor(EventFlag(1044369223)      -- Blaidd, Mistwood (LIMGRAVE)
#          || EventFlag(1034499224)      -- Ranni's Rise (LIURNIA)
#          || EventFlag(3063));          -- story flag
#     SetNetworkconnectedEventFlagID(9410, ON);
# In a rolled-start seed those regions can all be SEALED, so none of the three can ever be set -- the
# festival never starts, Radahn can never be fought, and his Great Rune (flag 172, tagged GreatRune +
# MajorBoss) and Remembrance (510300) are UNREACHABLE while AP believes Caelid is open. Fill can strand
# a region Lock on them: a hard softlock. (Found in playtest 2026-07-11, seed 22222, Caelid rolled in.)
# Force the festival on at spawn -- same NPC-prereq bypass as the Ranni chest gate above.
_RADAHN_FESTIVAL = 9410
# METYR'S DOOR. Metyr (boss 25000800, m25_00) is reached through an ObjAct on the Cathedral of Manus
# Metyr's overworld tile, and m61_51_45 event 2051452600 only enables it once BOTH halves are on:
#     WaitFor(EventFlag(9440) && EventFlag(2051450180));
#     EnableObjAct(2051451600, 52407);          -- then using it warps you to 25002600 in m25
# and common.emevd turns 9440 on only after a conjunction of two OTHER tiles' flags:
#     $Event(9440): WaitFor(EventFlag(2053460600) && EventFlag(2050400600));
#                   SetNetworkconnectedEventFlagID(9440, ON);
# 🛑 THOSE TWO TILES ARE IN DIFFERENT REGIONS -- 2053460600 is m61_53_46 (Scadu Altus) and
# 2050400600 is m61_50_40 (JAGGED PEAK). So a seed that keeps Scadu Altus and seals Jagged Peak can
# never set 9440: the door never enables, and Metyr's remembrance (510550, tagged Remembrance +
# MajorBoss) is UNREACHABLE while AP believes her region is open -- fill can strand a region Lock on
# it. Identical shape to the Radahn festival above, except the dependency crosses a REGION boundary
# rather than sitting outside one, which is if anything easier to hit.
# Force it on at spawn, the same NPC/questline-prereq bypass as the three flags above.
# 🛑 ONLY 9440. The other half, 2051450180, is Ymir's own state on the CATHEDRAL'S OWN TILE
# (m61_51_45 -- it is the chrEntityId threaded through that map's 90005790..93 NPC lifecycle events),
# so any seed that can reach the door at all sets it naturally. Forcing an NPC-lifecycle flag would
# risk his presence and his shop for no reachability gain; the cross-region half is the whole defect.
_METYR_DOOR = 9440
# (60100, the Spectral Steed Whistle obtained-flag, used to be appended here unconditionally with
# start_with_steed. It moved to features/start_items.py uniqueStartGrants: the flag is now set AS
# PART OF the whistle grant and doubles as its idempotency latch -- see start_items module doc.)


class RevealAllMaps(DefaultOnToggle):
    """Reveal the whole world map (and the underground view) at the start, so you can navigate the
    shattered world. On by default. The client (startgrants.rs) owns the RE'd flag set -- base map
    reveal flags + underground view-unlock 82001 -- and applies them once, gated on the settled
    world; greenfield just requests it via this bool."""
    display_name = "Reveal All Maps"


class EarlyLeveling(DefaultOnToggle):
    """Level Up at any Site of Grace from the start, skipping Melina's accord and her meeting
    cutscene (sets event flags 4680 + 951). On by default so a Roundtable-start run can level
    immediately. The client sets these via the startGraces flag list."""
    display_name = "Early Leveling (skip Melina)"


class StartWithRegionLock(DefaultOnToggle):
    """Start holding ONE region's lock, so a region is open from Roundtable at run start
    (core.create_items precollects it; count-neutral). WHICH lock is pick_anchor_region below:
    size-weighted by each region's check count over the kept BASE-game regions, so the run opens
    somewhere with room to play -- DLC region locks stay in the pool as normal finds and only anchor
    under dlc_only. ON by default (v0.2): a STRICT Progression Surface needs a sphere-0 anchor, and
    the pick then also intersects the regions that HOST a MajorBoss, so the strict lock-chain seeds
    without the ladder widening. Turn off to start fully sealed -- still beatable (AP fill guarantees
    a Roundtable-reachable first lock), but a strict surface then widens one rung to the Roundtable
    Golden Seeds to bootstrap."""
    display_name = "Start With A Region Lock"


class StartRegions(Range):
    """How many regions are OPEN at run start. 1 (default) is the classic single opening region;
    higher values precollect that many Region Locks, so the run begins with more of the map
    reachable and fewer locks left to find.

    Only consulted when Start With A Region Lock is on, and ignored under Natural Progression
    (which mints no Lock items at all). It must stay BELOW the number of regions the seed actually
    kept -- holding every kept Lock at connect would complete the goal before you play -- and
    generation fails loudly, naming both numbers, if it does not. Remember that Number of Regions
    is a DRAW SIZE: a seed can keep more regions than you asked for, but never fewer.

    The first region is picked exactly as it always was (size-weighted over the kept base-game
    regions, MajorBoss-biased under a strict Progression Surface). The extras are drawn the same
    way from what is left, except that the goal region can never be one: a run that opens on the
    region it ends in is over before it starts."""
    display_name = "Starting Regions"
    range_start = 1
    range_end = 10
    default = 1


class StartRegionPool(OptionSet):
    """WHICH regions the run may open in, by name. Empty (default) = any kept region, drawn the way
    it always was. Name one and the run opens there; name several and the opening region is drawn
    from just those.

    Region names are the ones the spoiler and the client use: Limgrave, Liurnia, Caelid, Altus,
    Stormveil, Raya Lucaria Academy, Leyndell, Mt. Gelmir, Mountaintops of the Giants, Weeping,
    Deeproot Depths, Siofra River, Ainsel River, Mohgwyn, Farum Azula, Sewer, and the DLC's
    Gravesite, Belurat, Ensis, Scadu Altus, Shadow Keep, Rauh Base, Ancient Ruins, Cerulean,
    Abyssal, Jagged Peak, Enir Ilim.

    🛑 EVERY REGION YOU NAME IS FORCE-KEPT, so this can make a seed BIGGER than `num_regions` asked
    for -- that number is a DRAW SIZE, and force-keeps are additive (the same seam a named `goal`
    uses). The generation log names the contribution. Naming three regions and asking for one is
    therefore a three-region seed, not a one-region seed with a choice; if you want "just play
    Caelid", name one.

    The alternative -- draw the opening region from your pool FIRST and force-keep only the winner --
    was considered and rejected: it needs a second draw before the kept set exists, and two draws
    that must agree about the same region is precisely the shape that has produced drift here before.
    One mechanism, stated, beats two that have to be kept in step.

    Ignored when Start With A Region Lock is off and under Natural Progression / Vanilla Placement,
    which mint no Lock items -- exactly like Starting Regions above. Naming a region this seed
    cannot open in (sealed by your DLC toggles, needed by your goal, or a child region that is
    reached through its parent) fails generation and says which and why, rather than quietly
    dropping it."""
    display_name = "Starting Region Pool"
    valid_keys = frozenset(REGIONS)


def pick_anchor_region(kept, rng, check_counts, dlc_regions, major=None, gated=frozenset(),
                       never_anchor=frozenset()):
    """The run's opening region: which kept region's Lock core.create_items precollects.

    Size-weighted draw -- weight = the region's emitted check count, from `check_counts`, which the
    caller derives from the world's own LOCATIONS at gen time (never a frozen table: a re-tag that
    moves checks between regions moves these weights with it) -- over the kept BASE-game regions.
    The anchor IS the opening region, so its size is playability: a uniform pick over all kept locks
    opened ~1 run in 3 on a region under 80 checks (playtest 2026-07-14: Castle Ensis, 31 checks --
    the seed becomes a corridor and fill has almost nowhere to host the next Lock), and every such
    region is DLC, where a fresh character also has zero scadutree blessing. So:

      * base regions kept  -> size-weighted draw over them ("base-weighted"). DLC locks stay in the
        pool as normal finds; they are just never the anchor here.
      * no base region kept (dlc_only) -> size-weighted draw over the kept DLC regions
        ("dlc-fallback-weighted"): a small start is then unavoidable, but a small DLC region
        should be rare, not equal-odds with the big ones.
      * `major` is not None (STRICT progression_surface_mode == 2: the MajorBoss-hosting kept
        regions) -> it INTERSECTS the eligible set ("major-boss^..."). An empty intersection
        DEGRADES to the plain size-weighted draw (the returned rule says so) -- never raises.

    `gated` (region_spine.REGION_PARENT keys) is excluded from eligibility outright -- a gated
    child's opening grant is exactly the grace bundle features/graces.py withholds, so it can
    never be the run's opening region.

    `never_anchor` is excluded from EVERY draw including the first -- which is exactly how it
    differs from `pick_anchor_regions`' `never_extra`, whose whole point is to leave the first draw
    alone. It carries the DLC terminus (Enir Ilim): on a dlc_only seed that is the region the run
    ENDS in, and a run that opens where it ends is not a run. Unlike `gated` it DEGRADES rather
    than raising if it would empty the pool -- the returned rule string says so -- because a seed
    with nothing else to open on must still be playable, and the caller's own force-keep already
    guarantees a second region in every case core can produce.

    ⭐ Its blast radius is naturally tiny: the eligible pool is the kept BASE regions whenever any
    are kept, and the DLC terminus is not one, so this filter can only ever bite on the
    dlc-fallback branch. Base-game and mixed seeds are byte-identical.

    Pure + deterministic (rng = world.random; two runs of the same seed agree). Returns
    (region, rule, eligible_count); the rule string is the gen-log telemetry ("which rule fired").
    Raises ValueError on an empty kept set or an all-zero weight sum: an empty eligible pool is a
    LOUD failure, not a silent shrug (CONTRIBUTING: an empty result is a failure, not a clean run).
    """
    kept = list(kept)
    if not kept:
        raise ValueError("start anchor: the kept region set is EMPTY -- nothing to anchor the run on")
    # A GATED CHILD (region_spine.REGION_PARENT) may never anchor: anchoring precollects its Lock,
    # and (pre-fix) granted its grace bundle -- a warp target past the vanilla wall its parent
    # guards, exactly the 2026-07-14 East-Capital-Rampart playtest bug. Post-fix a child's bundle
    # is withheld, so a child anchor would open the run on a region the player cannot even warp
    # into. compute_kept closes the kept set over REGION_PARENT, so every kept child implies a
    # kept non-child ancestor -- the exclusion can never empty a non-empty eligible pool.
    kept = [r for r in kept if r not in gated]
    if not kept:
        raise ValueError(
            "start anchor: every kept region is a gated child -- REGION_PARENT closure is broken "
            "(a child must always pull a non-child ancestor into the kept set)")
    # NEVER THE OPENING REGION (2026-08-09). Applied before the base/DLC split so it cannot be
    # smuggled back in by the fallback branch -- which is the only branch it can reach at all.
    _bar_degraded = False
    if never_anchor:
        _left = [r for r in kept if r not in never_anchor]
        if _left:
            kept = _left
        else:
            _bar_degraded = True
    base = [r for r in kept if r not in dlc_regions]
    if base:
        eligible, rule = base, "base-weighted"
    else:
        eligible, rule = kept, "dlc-fallback-weighted"
    if _bar_degraded:
        # Say it. A seed that opens on its own ending is worth a line in the gen log, not a silent
        # pick -- and if this ever fires, the force-keep upstream did not do its job.
        rule += " (never_anchor EMPTIED the pool -> degraded; this seed opens on its goal region)"
    if major is not None:
        inter = [r for r in eligible if r in major]
        if inter:
            eligible, rule = inter, "major-boss^" + rule
        else:
            rule += " (major-boss intersection EMPTY -> degraded to plain size-weighted)"
    weights = [int(check_counts.get(r, 0)) for r in eligible]
    if sum(weights) <= 0:
        raise ValueError(
            "start anchor: eligible regions %s carry ZERO emitted checks -- location data is "
            "missing or ungenerated; refusing to answer" % (sorted(eligible),))
    return rng.choices(eligible, weights=weights, k=1)[0], rule, len(eligible)


def pick_anchor_regions(kept, rng, check_counts, dlc_regions, n=1, major=None,
                        gated=frozenset(), never_extra=frozenset(), never_anchor=frozenset(),
                        only=frozenset()):
    """The run's opening regionS: which kept regions' Locks core.create_items precollects.

    ONE DRAW OR N, THE FIRST ONE IS THE SAME DRAW IT ALWAYS WAS. `n == 1` calls
    `pick_anchor_region` once and consumes the rng stream exactly as before, so every existing
    defaulted seed still rolls identically -- the same reason region_spine appends GOAL_REGION
    AFTER its rng.sample. Extras are drawn from what is left by the same size-weighted rule, one
    at a time, so a big region is still likelier to open than a corridor.

    `never_extra` (core passes the goal region) bars a region from the EXTRAS ONLY. The first
    draw is left alone deliberately: filtering it there would move the anchor of every seed already
    rolled. A seed that opens on the region it ends in is a non-run (Alaric, 2026-08-06), and at
    start_regions 3 that would stop being a rarity.

    🛑 Do NOT read that as "the goal region may still open a run". Core's goal region is a
    REGION_PARENT child, and `gated` below bars gated regions from every draw INCLUDING the first,
    so today the goal region cannot anchor at all -- by that rule, not by this one. `never_extra`
    is the rule that survives the goal region moving off a vanilla wall.

    The MajorBoss intersection applies to the FIRST draw only. Requiring all n anchors to host a
    MajorBoss can empty the eligible set outright, and `pick_anchor_region` degrades rather than
    raises precisely so a bias never becomes a hard filter.

    Raises ValueError when the eligible pool cannot supply n regions -- an empty result is a
    failure, not a clean run. The caller checks the cheaper `n < len(kept)` bound first and dies
    with an OptionError naming the yaml; this is the backstop for the gated / goal / zero-weight
    exclusions that bound cannot see.

    `only` (features/start_grace.StartRegionPool -- the player named the regions the run may open
    in) NARROWS `kept` before anything else happens, so it constrains the first draw AND the extras
    by one expression. Empty = no constraint, which is why a defaulted seed's rng stream is
    untouched: the filter is not applied at all rather than applied to everything.

    🛑 IT IS A HARD FILTER, unlike `major`, and that difference is the point. `major` is a BIAS the
    world chose and degrades when it cannot be satisfied; `only` is a sentence the player typed, and
    silently opening somewhere they did not name would be worse than refusing. Core validates the
    named set against the DLC toggles, the goal and the gated children BEFORE it gets here and dies
    with an OptionError naming the region; reaching the ValueError below means the pool survived all
    of that and still could not seat `n` regions.

    Returns (regions, rules, eligible_count) -- `regions[0]` and `rules[0]` are exactly what
    `pick_anchor_region` would have returned alone.
    """
    n = max(1, int(n))
    if only:
        kept = [r for r in kept if r in only]
        if not kept:
            raise ValueError(
                "start anchors: start_region_pool named %s, and none of them is a region this seed "
                "can open in" % ", ".join(sorted(only)))
    first, rule, pool_n = pick_anchor_region(kept, rng, check_counts, dlc_regions,
                                             major=major, gated=gated,
                                             never_anchor=never_anchor)
    picks, rules = [first], [rule]
    # The extras' pool, filtered ONCE up front so a shortfall is reported before anything is drawn:
    # a partial answer would be a silently shorter start than the yaml asked for.
    pool = [r for r in kept
            if r != first and r not in never_extra and r not in gated
            and r not in never_anchor
            and int(check_counts.get(r, 0)) > 0]
    if len(pool) < n - 1:
        raise ValueError(
            "start anchors: asked for %d starting regions, but only %d region(s) can open a run "
            "in this seed (the goal region and gated children are excluded as extras, and a "
            "region with zero emitted checks can never anchor) -- lower start_regions or raise "
            "num_regions" % (n, len(pool) + 1))
    while len(picks) < n:
        r, rule_r, _ = pick_anchor_region(pool, rng, check_counts, dlc_regions, gated=gated,
                                          never_anchor=never_anchor)
        picks.append(r)
        rules.append("extra:" + rule_r)
        pool = [x for x in pool if x != r]
    return picks, rules, pool_n


@register
class StartGrace(Feature):
    name = "start_grace"
    OPTIONS = {
        "reveal_all_maps": RevealAllMaps,
        "early_leveling": EarlyLeveling,
        "start_with_region_lock": StartWithRegionLock,
        "start_regions": StartRegions,
        "start_region_pool": StartRegionPool,
    }

    def slot_data(self, world):
        graces = [_ROUNDTABLE_GRACE]
        if world.options.early_leveling.value:
            graces += [_LEVEL_UP_FLAG, _MELINA_SUPPRESS_FLAG]
        graces.append(_FINGERSLAYER_CHEST_GATE)   # open the Ranni-gated Nokron chest (check 12027080)
        graces.append(_RADAHN_FESTIVAL)           # start the Radahn Festival so Radahn is fightable
        graces.append(_METYR_DOOR)                # open Metyr's door (its prereqs cross into Jagged Peak)
        return {
            contract.START_REGION: HUB,
            contract.START_GRACES: graces,
            contract.REVEAL_ALL_MAPS: bool(world.options.reveal_all_maps.value),
        }
