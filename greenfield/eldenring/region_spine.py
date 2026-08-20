"""Greenfield num_regions spine (matt-free) -- SPEC-PARITY Phase 1.

Progression ORDER over the 28 greenfield regions (region-spine v2). `num_regions` seals the world
down to N regions; `compute_kept` decides which N -- by random draw, never by this order. Pure (no AP import) so it runs
in the data-invariant gate. Keyed by REGION name only (greenfield's own names), never an imported
set -- this is the re-keyed port of the eldenring region spine (SPEC-PARITY.md P1).
"""
from .data import REGIONS

# Lock always required (capital ending). Always kept so the seed stays winnable at any num_regions.
# Region-spine v2: Leyndell is a first-class region again (buckets 11000 Royal + 11050 Ashen fold +
# 19000 Fractured Marika), so the capital-ending checks live in Leyndell -> it is the goal region.
GOAL_REGION = "Leyndell"

# VANILLA HARD WALLS -- gated child -> the parent region it is physically entered from.
#
# These three regions sit behind a wall the GAME already enforces: Raya Lucaria's seal wants the
# Academy Glintstone Key, the capital's main gate wants Great Runes (leyndell_runes_required), and
# the m35 Shunning-Grounds are entered down a well INSIDE the capital (no independent entrance), so
# the Sewer inherits Leyndell's wall transitively. The 2026-07-14 playtest bug was the apworld
# GRANTING a child's grace bundle on region-open -- a warp target on the far side of the wall
# (East Capital Rampart 71102, BonfireWarpParam 110002, straight past the 2-rune gate). The fix is
# to let the game keep enforcing its own walls and encode the containment ONCE, here:
#   * features/graces.py withholds a child's grace bundle (walk in, touch the graces yourself);
#   * core.create_regions parents the child's AP region under this entry, so reachability logic
#     requires the whole ancestor Lock chain (fill can never strand progression in a sealed child);
#   * compute_kept (below) closes the kept set over this map -- a child is never kept parentless;
#   * features/start_grace.pick_anchor_region refuses a child as the run's opening region (the
#     anchor grant is exactly the bundle being withheld).
# tests/test_gf_gated_children.py asserts every region-entry gate feature (legacy_key_gates map
# ranges, leyndell_gate's GOAL_REGION) has an entry here, so a future gate cannot land without one.
REGION_PARENT = {
    "Raya Lucaria Academy": "Liurnia",   # Academy Glintstone Key seal (features/legacy_key_gates)
    "Leyndell": "Altus",                 # capital main gate, N Great Runes (features/leyndell_gate)
    "Sewer": "Leyndell",                 # m35 well is inside the capital walls (SPEC-region-spine-v2)
    # Scaduview's containment entry was REMOVED 2026-07-19: the Hinterland was FOLDED into Shadow Keep
    # (region_groups) rather than kept a contained child, so it is no longer a separate region to gate
    # -- its checks ARE Shadow Keep checks now, under the Keep's own Lock. (Its door ground was always
    # the Keep's bucket 21000, which is exactly why the fold is clean; the Keep's front door is the
    # Hinterland grace 76935, on that same 21000 ground. The m21_00 gate grace 72102 was found
    # 2026-07-21 to stand on Scadu Altus ground instead, so it is no longer pinned as the front door.)
}


def parent_chain(region):
    """Ancestor list for `region`, nearest first (empty for an ungated region). Raises on a cycle
    rather than looping -- a cyclic REGION_PARENT is corrupt data, not a soft case."""
    chain, seen = [], {region}
    r = REGION_PARENT.get(region)
    while r is not None:
        if r in seen:
            raise ValueError(f"REGION_PARENT cycle at {r!r} (from {region!r})")
        chain.append(r)
        seen.add(r)
        r = REGION_PARENT.get(r)
    return chain

# Fixed progression path (Limgrave-first). It is BOTH an ordering and, since 2026-08-11, a
# selection mode again: `num_regions_order: vanilla_order` keeps the first N eligible entries
# (see compute_kept). It was a selection mode until 2026-08-05, deprecated between those dates.
# What SPINE decides besides the draw: poptracker display order, the test reference, and
# `_SPINE_RANK` -- which features/goal_locations walks deepest-first to pick the region that
# ENDS the run. Those three are why the LIST survived the period when the draw did not.
# Must be a permutation of REGIONS, and its TAIL must be exactly DLC_REGIONS (both guarded
# by test_gf_data).
SPINE = [
    # base game, rough vanilla progression order
    "Limgrave", "Weeping", "Stormveil", "Liurnia", "Raya Lucaria Academy",
    "Caelid", "Siofra River", "Altus", "Mt. Gelmir",
    "Leyndell", "Sewer", "Ainsel River", "Deeproot Depths", "Mohgwyn",
    "Mountaintops of the Giants", "Haligtree", "Farum Azula",
    # DLC (rides as plain lock gates -- SPEC-PARITY.md P7), entry-first
    "Gravesite", "Ensis", "Cerulean", "Belurat",
    "Scadu Altus", "Shadow Keep",
    "Ancient Ruins", "Rauh Base", "Jagged Peak", "Abyssal", "Enir Ilim",
]

# The Shadow of the Erdtree DLC regions. These are the last 11 entries of SPINE and are the pool the
# EnableDLC / DLCOnly toggles filter on (core.py). Kept as a frozenset for O(1) membership; the
# base-game pool is REGIONS minus these. Pure data (no AP import) so region-scope filtering can run
# in the data-invariant gate.
DLC_REGIONS = frozenset({
    "Gravesite", "Ensis", "Cerulean", "Belurat",
    "Scadu Altus", "Shadow Keep",
    "Ancient Ruins", "Rauh Base", "Jagged Peak", "Abyssal", "Enir Ilim",
})


def base_regions():
    """Base-game (non-DLC) region names, in REGIONS order."""
    return [r for r in REGIONS if r not in DLC_REGIONS]


def dlc_regions():
    """DLC region names, in REGIONS order."""
    return [r for r in REGIONS if r in DLC_REGIONS]


def earliest_kept_site(sites, kept):
    """The EARLIEST of `sites` (in SPINE order) that this seed actually KEPT, or None.

    #701 option B. A check whose seller stands in SEVERAL regions is reachable from ANY of them -- a
    disjunction the region-lock world cannot express (#320/#502), which is why gen_data collapses the
    row onto the hub and option C bars it from carrying progression. Requiring ONE of the sites is
    STRICTER than the disjunction, so it can never claim reachability the player does not have; it is
    a conservative approximation, and an EXACT one when the seed kept only one of the sites.

    SPINE, not the tsv order and not alphabetical: it is the order the rest of the world already means
    by "earliest", so the chosen site is the one the player is likeliest to hold soonest. A site that
    is not in SPINE at all is IGNORED rather than guessed at -- an unknown region name is a data bug,
    and picking it would gate the row on a lock that does not exist.

    Returns None when the seed keeps none of them: the caller must then keep option C's bar. That
    fallback is the whole reason option B does not replace option C -- a `num_regions` draw holding
    none of a merchant's regions is a legitimate seed, not a generation failure."""
    keep = set(kept)
    for r in SPINE:
        if r in sites and r in keep:
            return r
    return None


def compute_kept(n, rng, eligible=None, forced=(), parts=None, bar_from_draw=(), order="rolled"):
    """Kept-region list, drawn from `eligible` (defaults to all of REGIONS).

    `eligible` is the already-filtered pool of regions in play this seed (e.g. base-only when
    EnableDLC is off, or DLC-only when DLCOnly is on -- computed in core.generate_early). Passing it
    in keeps num_regions selection honest: N is always drawn from the eligible set, never from a
    sealed region.

    n<=0 or n>=len(eligible) -> the whole eligible pool (full Shattering of what's in play).
    Otherwise N regions are chosen by `order`:

      * `"rolled"` (the DEFAULT, and what every seed that does not name the option gets) -- N drawn
        at RANDOM with rng.sample.
      * `"vanilla_order"` -- the first N eligible regions in SPINE order, i.e. Limgrave-first along
        the rough vanilla progression path. Fully deterministic: the rng is not consulted at all.

    ⚠️ HISTORY, because the numbers matter and the option has been round the houses. The SPINE draw
    was REMOVED on 2026-08-05 (14b5269) and the option deprecated, on a measurement: at the default
    num_regions=6 it made every seed keep the SAME eight regions -- Limgrave, Weeping, Stormveil,
    Liurnia, Raya Lucaria Academy, Caelid, plus Leyndell and Altus by closure -- and NINE base
    regions could never appear at all, against a 34-37% band for every base region under the random
    draw (3000 seeds). It was RESTORED on 2026-08-11 at Alaric's request, verbatim, as an OPT-IN
    under a name that says what it does. That property is not a bug in it -- determinism is the
    point -- but it is exactly why `rolled` stays the default and why the option's docstring says so
    to the player.

    THE GOAL REGION IS GOAL-SENSITIVE (2026-08-05, Alaric). GOAL_REGION is force-kept only when the
    seed has NO explicitly named goal -- i.e. only under `auto`, where the goal is DERIVED from
    whatever the draw kept, so the base-game terminus has to be there for that derivation to find
    it. When the player NAMES a goal, `forced` already carries exactly the regions that goal needs,
    and appending Leyndell on top kept the capital -- and Altus, its REGION_PARENT -- in 100% of
    seeds with no use for either. A `promised_consort` seed needs Enir Ilim, not the capital.
    `elden_beast` is unaffected: its own forced set names Leyndell.

    Seeds under `auto` are byte-identical to before this change: `forced` is empty there, so the
    append fires exactly as it always did.

    The goal region is appended only when it is itself eligible -- under DLCOnly the base-game goal
    (Leyndell) is not eligible, and the goal collapses to "hold every kept lock" over the eligible
    set (still winnable; see core.set_rules). That no-Leyndell shape is neither new nor untested:
    DLCOnly has always produced it.

    `forced` is the explicit-goal force-keep set (features/goal_locations.GOAL_CHOICES): when the
    player NAMES a goal, the kept set is BUILT to contain its region instead of the goal being
    derived from whatever the draw happened to keep. It is appended in exactly the same place as
    GOAL_REGION -- AFTER the rng.sample -- so the rng stream, and therefore every default rolled
    seed, is byte-identical to before this parameter existed. Callers guarantee eligibility (core
    raises OptionError on an ineligible choice); a forced region outside the pool is dropped here
    rather than smuggled past the scope filter.

    ⭐ SUPERSEDED 2026-08-06 (SPEC-ashen-capital-lock): the paragraph above describes a force-keep
    that NO LONGER EXISTS. `auto` force-keeps nothing now -- see the note at the append site. The
    `forced` parameter is unchanged and still carries an explicit goal's needs; `elden_beast`'s
    forced set is simply empty these days, because the finale no longer needs a region kept.

    `bar_from_draw` removes regions from the rng.sample POOL only -- see the note at the draw. It
    is the DLC terminus today: a region core force-keeps, and which therefore must not also be able
    to consume one of the player's N. It never removes a region from the SEED (the full-pool branch
    ignores it), and it degrades to the unbarred pool rather than emptying it.

    `parts` is an OPTIONAL out-dict for telemetry (#409): pass a dict and it is filled with
    {"drawn": [...], "forced": [...], "closure": [...]}, the three contributions that make up the
    return value, in the order they were added. It is an out-param rather than a second return
    value on purpose -- every existing caller keeps working unchanged, and nothing about the draw
    (least of all the rng stream) may move for a telemetry feature. Purely observational: nothing
    in here reads it back."""
    def _record(drawn, forced_kept, final, full_pool=False):
        if parts is None:
            return
        pre = set(drawn) | set(forced_kept)
        parts["drawn"] = list(drawn)
        parts["forced"] = list(forced_kept)
        parts["closure"] = [r for r in final if r not in pre]
        # WHICH BRANCH RAN, stated rather than re-derived. "n was 0" and "n happened to equal the
        # kept count" are different facts that produce identical numbers, and describe_kept prints
        # a different sentence for each -- inferring it from the counts would print the wrong one.
        parts["full_pool"] = bool(full_pool)

    regions = list(REGIONS) if eligible is None else [r for r in REGIONS if r in set(eligible)]
    if not regions:
        _record((), (), (), full_pool=True)
        return regions
    if n <= 0 or n >= len(regions):
        full = _close_over_parents(regions, regions)
        _record(regions, (), full, full_pool=True)
        return full
    # ⭐ BARRED FROM THE DRAW, NOT FROM THE SEED (2026-08-09, the DLC terminus).
    # `bar_from_draw` names regions the CALLER is going to force-keep anyway. Removing them from
    # the sample is what makes that force additive instead of a coin flip: left in the pool, the
    # draw can spend one of the player's N on a region that was going to be kept regardless, and at
    # `n == 1` it can return a seed whose ONLY region is the one the run ends in. Barred and then
    # forced, `num_regions: 1` means "one region to play, plus the ending" -- which is exactly what
    # the Ashen Capital gives a base-game seed by not being a rollable region at all.
    #
    # It is applied HERE and not to `regions` above on purpose: the full-pool branch (`n <= 0`, or
    # an N at/above the pool) means "keep the whole eligible map", and a barred region is still IN
    # that map -- barring it there would silently DELETE the seed's terminus from a Shattering.
    #
    # 🛑 THIS MOVES THE RNG STREAM for any seed whose pool contains a barred region: the sample is
    # drawn from a shorter list. Unavoidable for a fix in this shape, and scoped -- core passes a
    # non-empty bar only when the base game is sealed, so every base-game seed is byte-identical.
    draw_pool = [r for r in regions if r not in set(bar_from_draw)] or regions
    # 🛑 THE RNG IS NOT CONSULTED ON THE vanilla_order PATH, and that is deliberate rather than an
    # oversight: consuming a sample here "for stream parity" would be a lie in the other direction,
    # since the two orders keep different regions and every downstream draw diverges anyway. The
    # `rolled` branch is untouched, so every seed that does not name the option is byte-identical.
    # `bar_from_draw` applies to BOTH paths -- a region the caller is about to force-keep must not
    # consume one of the player's N whichever way the N is chosen.
    if order == "vanilla_order":
        base = [r for r in SPINE if r in draw_pool][:n]
    else:
        base = rng.sample(draw_pool, min(n, len(draw_pool)))
    kept = list(dict.fromkeys(base))
    drawn = list(kept)
    forced_kept = []
    # 🛑 The append MUST stay here, after the draw: moving it above rng.sample changes every
    # rolled seed in existence (the economy floor is one seed thick).
    #
    # ⭐ THE `auto` GOAL_REGION FORCE-KEEP IS GONE (SPEC-ashen-capital-lock, 2026-08-06). It used to
    # sit right here: under `auto` the goal is DERIVED from whatever the draw kept, so the base
    # game's terminus had to be present for that derivation to find one -- which meant Leyndell,
    # and behind it Altus (its REGION_PARENT), in EVERY auto seed. That is the other half of
    # bobler's "num_regions: 1 gave me four regions" (describe_kept below tells the goal: elden_beast
    # half of the same story).
    #
    # It is dead weight now, not a judgement call: decision 3 of the spec makes `auto` resolve to
    # the Elden Beast on every seed with the base game in play, and the Ashen Capital exists on
    # every such seed WITHOUT being kept -- it is reached by warping to its own graces behind the
    # Ashen Capital Lock. So the derivation can always find a terminus, and force-keeping the
    # capital to guarantee one guarantees nothing that is not already true. Under dlc_only the
    # append never fired anyway (Leyndell is not eligible), and that path -- the terminus-first
    # spine walk -- is untouched.
    #
    # The rng stream does NOT move: the append was always after rng.sample, so `drawn` is
    # byte-identical. What changes is that an auto seed now keeps what it drew, which is the
    # entire point of calling num_regions a draw size.
    for r in forced:
        if r in regions and r not in kept:
            kept.append(r)
            forced_kept.append(r)
    final = _close_over_parents(kept, regions)
    _record(drawn, forced_kept, final)
    return final


def describe_kept(n, parts, kept, goal="auto", start_region_pool=()):
    """ONE LINE naming every contribution to the kept set, for the gen log / spoiler (#409).

    THE MOTIVATING CASE (CONTRIBUTING rule 11), and it is a player-support cost, not a crash.
    bobler set `num_regions: 1` on 0.3.5 and got FOUR regions. He asked twice, an hour apart, still
    unsure what had happened -- and every step was correct: the draw took Liurnia, `goal:
    elden_beast` force-kept Farum Azula and Leyndell, and the parent closure pulled Altus in behind
    Leyndell. Nothing anywhere said so. N IS A DRAW SIZE, NOT A REGION COUNT, and until this line
    existed the only way to learn that was to read compute_kept.

        num_regions: 1 drawn (Liurnia) + 1 forced by start_region_pool (Caelid)
        + 2 forced by goal=elden_beast (Farum Azula, Leyndell)
        + 1 parent closure (Altus) = 5 kept

    Empty contributions are OMITTED rather than printed as "+ 0", so the common case (a plain draw
    that needed nothing) stays one short clause. Pure and AP-free like the rest of this module, so
    it is unit-testable without a world."""
    total = len(kept)
    drawn = list(parts.get("drawn", ()))
    forced = list(parts.get("forced", ()))
    start_names = set(start_region_pool or ())
    forced_start = [r for r in forced if r in start_names]
    forced_goal = [r for r in forced if r not in start_names]
    closure = list(parts.get("closure", ()))
    if parts.get("full_pool"):
        # 0 (or an N at/above the eligible pool) is "the whole eligible map" -- there is no draw to
        # explain, and listing thirty region names would bury the number the reader came for.
        bits = ["num_regions: %d = the whole eligible map" % n]
    else:
        bits = ["num_regions: %d drawn (%s)" % (len(drawn), ", ".join(drawn) or "none")]
    if forced_start:
        bits.append("%d forced by start_region_pool (%s)"
                    % (len(forced_start), ", ".join(forced_start)))
    if forced_goal:
        bits.append("%d forced by goal=%s (%s)"
                    % (len(forced_goal), goal, ", ".join(forced_goal)))
    if closure:
        bits.append("%d parent closure (%s)" % (len(closure), ", ".join(closure)))
    return "%s = %d kept" % (" + ".join(bits), total)


def _close_over_parents(kept, pool):
    """Close `kept` over REGION_PARENT: a kept gated child PULLS ITS ANCESTORS IN (never the other
    way -- dropping the child instead is impossible for the always-kept goal region, whose parent
    chain is exactly why Altus rides along on every base seed: the capital has no other way in).
    The closure keeps the seed winnable by construction; a kept-but-unreachable child is a
    dead-drop generator. An ancestor missing from the eligible pool is a hard error, not a shrug:
    it means a gated child was declared eligible while its only entrance was not (a scope-filter
    bug) -- and it applies on EVERY path, including the n<=0 / n>=len full-pool returns."""
    kept = list(kept)
    in_pool = set(pool)
    for r in list(kept):
        for anc in parent_chain(r):
            if anc in kept:
                continue
            if anc not in in_pool:
                raise ValueError(
                    f"compute_kept: kept region {r!r} needs ancestor {anc!r}, which is not in the "
                    f"eligible pool -- a gated child must never be eligible without its parent")
            kept.append(anc)
    return kept
