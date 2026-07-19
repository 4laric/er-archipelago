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
from Options import DefaultOnToggle, Toggle
from ..registry import Feature, register
from .. import contract
from ..data import HUB

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


def pick_anchor_region(kept, rng, check_counts, dlc_regions, major=None, gated=frozenset()):
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
    base = [r for r in kept if r not in dlc_regions]
    if base:
        eligible, rule = base, "base-weighted"
    else:
        eligible, rule = kept, "dlc-fallback-weighted"
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


@register
class StartGrace(Feature):
    name = "start_grace"
    OPTIONS = {
        "reveal_all_maps": RevealAllMaps,
        "early_leveling": EarlyLeveling,
        "start_with_region_lock": StartWithRegionLock,
    }

    def slot_data(self, world):
        graces = [_ROUNDTABLE_GRACE]
        if world.options.early_leveling.value:
            graces += [_LEVEL_UP_FLAG, _MELINA_SUPPRESS_FLAG]
        graces.append(_FINGERSLAYER_CHEST_GATE)   # open the Ranni-gated Nokron chest (check 12027080)
        graces.append(_RADAHN_FESTIVAL)           # start the Radahn Festival so Radahn is fightable
        return {
            contract.START_REGION: HUB,
            contract.START_GRACES: graces,
            contract.REVEAL_ALL_MAPS: bool(world.options.reveal_all_maps.value),
        }
